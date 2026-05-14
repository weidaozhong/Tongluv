from __future__ import annotations

import json
import math
import os
import sys
import threading
import zipfile
from typing import Callable

from PyQt5.QtCore import Qt, QRectF, QByteArray
from PyQt5.QtGui import (
    QPainter, QPixmap, QColor, QBrush, QPen, QPainterPath,
)

# .pak 加载支持（可选；不存在时回退到散装 PNG）
try:
    from src.pak_loader import open_pak, read_frame_bytes as _read_frame_bytes
    _PAK_AVAILABLE = True
except ImportError:
    _PAK_AVAILABLE = False


def _root_dir() -> str:
    """返回项目根目录"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    # src/ 的父目录即为项目根目录
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _asset_dir() -> str:
    return os.path.join(_root_dir(), "assets", "animations")

def _item_dir() -> str:
    return os.path.join(_root_dir(), "assets", "items")


class FrameSequence:
    """
    帧序列加载器。
    优先从同目录下的 {prefix}.pak 读帧，回退到散装 PNG（向后兼容）。

    .pak 采用懒加载：__init__ 只记录路径，第一次实际读帧时才解包。
    这样启动时不需要一次性解混淆全部 100MB+ 数据。
    """
    def __init__(self, prefix: str, count: int, size: int,
                 fps: float = 25.0, loop: bool = True, adir: str | None = None):
        self._prefix = prefix
        self._count  = max(count, 1)
        self._size   = size
        self._fps    = fps
        self._loop   = loop
        self._cache: dict[int, QPixmap] = {}
        self._adir   = adir or _asset_dir()

        # 懒加载：只存路径，首次读帧时才真正打开
        self._pak_zf:     zipfile.ZipFile | None = None
        self._pak_path:   str | None = None
        self._pak_failed: bool = False
        self._pak_lock:   threading.Lock = threading.Lock()
        if _PAK_AVAILABLE:
            pak_path = os.path.join(self._adir, f"{prefix}.pak")
            if os.path.exists(pak_path):
                self._pak_path = pak_path   # 记路径，不立刻读文件

    def _open_pak(self):
        """首次读帧时调用，打开并解混淆 .pak（线程安全）"""
        if self._pak_failed or self._pak_path is None:
            return
        if self._pak_zf is not None:   # fast path，无锁
            return
        with self._pak_lock:           # 防止主线程/后台线程同时打开
            if self._pak_zf is not None:
                return
            try:
                self._pak_zf = open_pak(self._pak_path)
            except Exception:
                self._pak_zf    = None
                self._pak_failed = True   # 标记失败，不再重试

    def get(self, idx: int) -> QPixmap | None:
        if self._loop:
            idx = idx % self._count
        else:
            idx = min(idx, self._count - 1)
        if idx not in self._cache:
            px = self._load(idx)
            self._cache[idx] = px if (px and not px.isNull()) else QPixmap()
        cached = self._cache[idx]
        return cached if not cached.isNull() else None

    def _load(self, idx: int) -> QPixmap | None:
        """从 .pak 或散装 PNG 加载一帧，返回缩放后的 QPixmap"""
        px = QPixmap()

        if self._pak_path is not None:
            # ── 从 .pak 读取（懒加载：首次调用时才解混淆）────────────
            self._open_pak()
            if self._pak_zf is not None:
                data = _read_frame_bytes(self._pak_zf, idx)
                if data:
                    ba = QByteArray(data)
                    px.loadFromData(ba, "PNG")
        else:
            # ── 散装 PNG 回退 ─────────────────────────────────────────
            path = os.path.join(self._adir, f"{self._prefix}_{idx:04d}.png")
            if os.path.exists(path):
                px = QPixmap(path)

        if not px.isNull() and (px.width() > self._size or px.height() > self._size):
            px = px.scaled(self._size, self._size,
                           Qt.KeepAspectRatio,
                           Qt.SmoothTransformation)
        return px

    def __del__(self):
        """关闭 ZipFile 句柄"""
        if self._pak_zf is not None:
            try:
                self._pak_zf.close()
            except Exception:
                pass

    @property
    def count(self) -> int:   return self._count
    @property
    def fps(self)   -> float: return self._fps
    @property
    def loop(self)  -> bool:  return self._loop


class SpriteRenderer:
    """
    动画状态机

    动作分类
    --------
    LOOP_ONLY      : idle               —— 循环，由 state_action 驱动
    ONESHOT_FREEZE : sleep              —— 一次性，播完冻结最后一帧等待 wake
    ONESHOT_RETURN : walk/eat/pet/wake/play —— 一次性，播完回 idle 并触发 on_action_done

    优先级：frozen_sleep > 正在播 ONESHOT > 队列中有待播 > 普通 idle
    """

    BLEND_FRAMES   = 5
    ONESHOT_FREEZE = frozenset({"sleep"})
    ONESHOT_RETURN = frozenset({"walk", "eat", "pet", "wake", "play",
                                "cat", "study",
                                "item_apple", "item_cake", "item_candy",
                                "item_coffee", "item_plush", "item_gift",
                                "item_star"})
    ONESHOT_ALL    = ONESHOT_FREEZE | ONESHOT_RETURN

    def __init__(self, size: int = 320):
        self.size  = size
        self._adir = _asset_dir()
        self._seqs: dict[str, FrameSequence] = {}
        self._load_sequences()

        self._action:      str   = "idle"
        self._frame_i:     int   = 0
        self._frame_accum: float = 0.0

        self._prev_action:  str = "idle"
        self._prev_frame_i: int = 0
        self._blend_remain: int = 0

        # 后台线程预加载所有非 idle 的 .pak，消除首次触发延迟
        self._start_bg_preload()

        self._pending: list[str] = []
        self._frozen_sleep: bool = False
        self._freeze_idle_timer: float = 0.0

        # 道具使用底图：icon_tray.png，缩放到与动画帧相同尺寸
        self._item_base_px: QPixmap | None = None
        _base_path = os.path.join(_root_dir(), "icons", "icon_tray.png")
        if os.path.exists(_base_path):
            _px = QPixmap(_base_path)
            if not _px.isNull():
                self._item_base_px = _px.scaled(
                    self.size, self.size,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation)

        # 播完/冻结回调
        self.on_action_done: Callable[[str], None] | None = None

    # ------------------------------------------------------------------ #
    ITEM_PREFIXES = frozenset({"item_apple", "item_cake", "item_candy",
                                  "item_coffee", "item_plush", "item_gift",
                                  "item_star"})

    def _load_sequences(self):
        cfg_path = os.path.join(self._adir, "anim_config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, encoding="utf-8") as f:
                cfg = json.load(f)
        else:
            cfg = self._scan_dir()
        for name, info in cfg.items():
            adir = _item_dir() if name in self.ITEM_PREFIXES else self._adir
            self._seqs[name] = FrameSequence(
                prefix=name, count=info["frames"], size=self.size,
                fps=info.get("fps", 25.0), loop=info.get("loop", True),
                adir=adir,
            )

    def _scan_dir(self) -> dict:
        cfg: dict = {}
        anim_prefixes = ["idle", "walk", "pet", "eat", "sleep", "wake", "play"]
        item_prefixes = ["item_apple", "item_cake", "item_candy",
                         "item_coffee", "item_plush", "item_gift",
                         "item_star"]
        for prefix in anim_prefixes:
            count = 0
            while os.path.exists(
                    os.path.join(self._adir, f"{prefix}_{count:04d}.png")):
                count += 1
            if count > 0:
                cfg[prefix] = {"frames": count, "fps": 25.0,
                                "loop": prefix == "idle"}
        for prefix in item_prefixes:
            count = 0
            while os.path.exists(
                    os.path.join(_item_dir(), f"{prefix}_{count:04d}.png")):
                count += 1
            if count > 0:
                cfg[prefix] = {"frames": count, "fps": 25.0,
                                "loop": False}
        return cfg

    def _start_bg_preload(self):
        """
        后台线程预加载所有非 idle 的 .pak。
        idle 在首帧渲染时由主线程加载（体积小 ~0.1MB，不阻塞）；
        其余动作（最大 ~14MB）在后台提前解包，用户触发时无感知延迟。
        """
        seqs = {k: v for k, v in self._seqs.items()
                if not k.startswith("idle") and v._pak_path is not None}
        if not seqs:
            return

        def _worker():
            # 按包体大小从小到大加载，优先让常用小包就绪
            ordered = sorted(seqs.values(),
                             key=lambda s: os.path.getsize(s._pak_path or ""))
            for seq in ordered:
                seq._open_pak()

        t = threading.Thread(target=_worker, daemon=True, name="PakPreload")
        t.start()

    # ------------------------------------------------------------------ #
    #  外部触发                                                             #
    # ------------------------------------------------------------------ #
    def trigger(self, action: str):
        """
        触发一次性动作。
        wake 优先插队（唯一能解除 sleep 冻结的动作）。
        同一动作不重复入队。
        """
        if action not in self._seqs:
            return
        if action == "wake":
            if "wake" not in self._pending:
                self._pending.insert(0, "wake")
        elif action in self.ONESHOT_ALL:
            if action not in self._pending:
                self._pending.append(action)

    def trigger_priority(self, action: str):
        """高优先级触发：清除队列 + 打断当前非道具 oneshot，立即排入队首。
        用于道具动画，确保不被 walk/eat 等随机动画阻塞。"""
        if action not in self._seqs:
            return
        # 1. 清空 pending 队列（保留 wake）
        self._pending = [a for a in self._pending if a == "wake"]
        # 2. 如果当前正在播非目标 oneshot，强制中断回 idle
        if (self._action in self.ONESHOT_ALL
                and self._action != action
                and self._action not in self.ONESHOT_FREEZE):
            self._action = "idle"
        # 3. 插入队首
        if action not in self._pending:
            self._pending.insert(0, action)

    def trigger_pet(self): self.trigger("pet")
    def trigger_eat(self): self.trigger("eat")

    def freeze_to_idle(self, duration: float):
        """使用道具时锁定显示 idle 第一帧 duration 秒，结束后自动恢复"""
        self._freeze_idle_timer = duration

    # ------------------------------------------------------------------ #
    #  主更新                                                               #
    # ------------------------------------------------------------------ #
    def update(self, dt: float, state_action: str):
        if self._freeze_idle_timer > 0:
            self._freeze_idle_timer -= dt

        # A: sleep 冻结中 ─────────────────────────────────────────────────
        if self._frozen_sleep:
            if self._pending and self._pending[0] == "wake":
                self._pending.pop(0)
                self._frozen_sleep = False
                self._switch("wake")
                self._advance(dt)   # 立即推进首帧，消除 wake 起始停顿
            # else: 什么都不做，停在 sleep 最后一帧
            if self._blend_remain > 0:
                self._blend_remain -= 1
            return

        # B: 一次性动画正在播 ───────────────────────────────────────────────
        if self._action in self.ONESHOT_ALL:
            done = self._advance(dt)
            if done:
                finished = self._action
                if finished in self.ONESHOT_FREEZE:
                    # sleep 播完 → 冻结
                    self._frozen_sleep = True
                else:
                    # 其余 → 回 idle，并立即推进首帧消除停顿
                    self._switch("idle")
                    self._advance(dt)
                if self.on_action_done:
                    self.on_action_done(finished)
            if self._blend_remain > 0:
                self._blend_remain -= 1
            return

        # C: 队列中有待播动作 ────────────────────────────────────────────────
        if self._pending:
            self._switch(self._pending.pop(0))
            self._advance(dt)
            if self._blend_remain > 0:
                self._blend_remain -= 1
            return

        # D: 普通 idle 循环 ──────────────────────────────────────────────────
        self._switch("idle")
        self._advance(dt)
        if self._blend_remain > 0:
            self._blend_remain -= 1

    # ------------------------------------------------------------------ #
    def _advance(self, dt: float) -> bool:
        seq = self._seqs.get(self._action) or self._seqs.get("idle")
        if seq is None:
            return False
        self._frame_accum += dt * seq.fps
        steps = int(self._frame_accum)
        if steps > 0:
            self._frame_i    += steps
            self._frame_accum -= steps
        if not seq.loop and self._frame_i >= seq.count:
            self._frame_i = seq.count - 1
            return True
        return False

    def _switch(self, new_action: str):
        if new_action == self._action:
            return
        self._prev_action  = self._action
        self._prev_frame_i = self._frame_i
        self._action       = new_action
        self._frame_i      = 0
        self._frame_accum  = 0.0
        # 从 idle 切出或切回 idle 时不做混合过渡，避免静态帧与动画帧重叠
        if self._prev_action == "idle" or new_action == "idle":
            self._blend_remain = 0
        else:
            self._blend_remain = self.BLEND_FRAMES

    # ------------------------------------------------------------------ #
    #  绘制                                                                 #
    # ------------------------------------------------------------------ #
    def draw(self, painter: QPainter, cx: float, cy: float,
             transform: dict | None = None, particles=None, **_):
        tr    = transform or {}
        sx    = tr.get("scale_x",  1.0)
        sy    = tr.get("scale_y",  1.0)
        rot   = math.degrees(tr.get("rotation", 0.0))
        oy    = tr.get("offset_y", 0.0)

        if self._freeze_idle_timer > 0:
            px_cur = self._item_base_px or self._get_px("idle", 0)
            blend, px_prev = 0.0, None
        else:
            px_cur  = self._get_px(self._action, self._frame_i)
            blend   = self._blend_remain / self.BLEND_FRAMES if self._blend_remain > 0 else 0.0
            px_prev = self._get_px(self._prev_action, self._prev_frame_i) if blend > 0 else None

        if px_cur is None and px_prev is None:
            return

        painter.save()
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(cx, cy + self.size * 0.5 + oy)
        painter.rotate(rot)
        painter.scale(sx, sy)
        if px_prev and blend > 0:
            painter.setOpacity(blend)
            self._blit(painter, px_prev)
        if px_cur:
            painter.setOpacity(1.0 - blend)
            self._blit(painter, px_cur)
        if self._freeze_idle_timer > 0 and self._action in self.ITEM_PREFIXES:
            px_item = self._get_px(self._action, self._frame_i)
            if px_item:
                painter.setOpacity(1.0)
                self._blit(painter, px_item)
        painter.setOpacity(1.0)
        painter.restore()

        if particles:
            self._draw_particles(painter, cx, cy, particles)

    def _get_px(self, action: str, idx: int) -> QPixmap | None:
        seq = self._seqs.get(action) or self._seqs.get("idle")
        return seq.get(idx) if seq else None

    def _blit(self, painter: QPainter, px: QPixmap):
        painter.drawPixmap(int(-px.width() * .5), int(-px.height()), px)

    # ------------------------------------------------------------------ #
    #  粒子                                                                 #
    # ------------------------------------------------------------------ #
    def _draw_particles(self, p: QPainter, cx: float, cy: float, particles):
        _CH = QColor(255, 100, 130)
        _CS = QColor(255, 220,  60)
        _CZ = QColor(180, 200, 255)
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        for pt in particles:
            if pt.alpha <= 0:
                continue
            p.save()
            p.translate(cx + pt.x, cy + pt.y)
            p.rotate(math.degrees(pt.angle))
            p.setOpacity(pt.alpha)
            r = pt.size * 10.0
            if pt.type == "heart":
                p.setBrush(QBrush(_CH))
                path = QPainterPath()
                path.moveTo(0, r*.30)
                path.cubicTo(-r,-r*.50,-r*.30,-r,0,-r*.40)
                path.cubicTo(r*.30,-r,r,-r*.50,0,r*.30)
                p.drawPath(path)
            elif pt.type == "star":
                p.setBrush(QBrush(_CS))
                path = QPainterPath()
                for i in range(5):
                    oa = math.pi/2 + i*math.pi*2/5
                    ia = oa + math.pi/5
                    v  = (math.cos(oa)*r,    -math.sin(oa)*r)
                    vi = (math.cos(ia)*r*.4, -math.sin(ia)*r*.4)
                    if i == 0: path.moveTo(*v)
                    else:      path.lineTo(*v)
                    path.lineTo(*vi)
                path.closeSubpath()
                p.drawPath(path)
            elif pt.type == "zzz":
                from PyQt5.QtGui import QFont
                p.setPen(QPen(_CZ))
                p.setFont(QFont("Arial", max(6, int(9*pt.size))))
                p.drawText(QRectF(-20,-20,40,40), Qt.AlignCenter, "Z")
                p.setPen(Qt.NoPen)
            p.restore()
        p.setOpacity(1.0)
        p.restore()
