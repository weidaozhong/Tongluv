from __future__ import annotations

import math
import os
import random
import sys
import time
from datetime import datetime

# ── 单实例锁：阻止重复启动 ──────────────────────────────────────
if sys.platform == "win32":
    import ctypes
    _mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "XiaotongDesktopPet_SingleInstance")
    if ctypes.windll.kernel32.GetLastError() == 183:
        def _dup_dialog():
            from PyQt5.QtWidgets import (QApplication, QDialog, QLabel,
                QPushButton, QVBoxLayout, QHBoxLayout, QFrame,
                QGraphicsDropShadowEffect)
            from PyQt5.QtCore import Qt
            from PyQt5.QtGui import QFont, QPixmap, QColor
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
            app = QApplication(sys.argv)
            dlg = QDialog(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
            dlg.setAttribute(Qt.WA_TranslucentBackground)
            lay = QVBoxLayout(dlg)
            lay.setContentsMargins(16, 12, 16, 16)
            card = QFrame(); card.setObjectName("c")
            card.setStyleSheet(
                "QFrame#c{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                "stop:0 #f8faff,stop:1 #eef2fa);"
                "border-radius:16px;border:1px solid #d0d8e8}"
                "QLabel{background:transparent;border:none}")
            sh = QGraphicsDropShadowEffect()
            sh.setBlurRadius(24); sh.setColor(QColor(0,0,0,50)); sh.setOffset(0,4)
            card.setGraphicsEffect(sh)
            lay.addWidget(card)
            inner = QVBoxLayout(card)
            inner.setContentsMargins(28, 22, 28, 20); inner.setSpacing(10)
            row = QHBoxLayout()
            _base = (sys._MEIPASS if getattr(sys, "frozen", False)
                     else os.path.dirname(os.path.abspath(__file__)))
            ico = QLabel()
            px = QPixmap(os.path.join(_base, "icons", "icon.png"))
            if not px.isNull():
                ico.setPixmap(px.scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            ico.setFixedSize(40, 40)
            row.addWidget(ico)
            t = QLabel("蓝色小嗵")
            t.setFont(QFont("Microsoft YaHei", 13, QFont.Bold))
            t.setStyleSheet("color:#3a4a6a;")
            row.addWidget(t); row.addStretch()
            inner.addLayout(row)
            m = QLabel("桌宠已经在运行中了哦~\n\n请检查系统托盘 \U0001f43e")
            m.setFont(QFont("Microsoft YaHei", 11))
            m.setStyleSheet("color:#5a6a8a;")
            m.setAlignment(Qt.AlignCenter)
            inner.addWidget(m)
            inner.addSpacing(6)
            btn = QPushButton("我知道了")
            btn.setFixedSize(110, 36)
            btn.setFont(QFont("Microsoft YaHei", 10))
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                "QPushButton{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                "stop:0 #6a8fd8,stop:1 #5a7fc8);"
                "color:white;border-radius:10px;border:none}"
                "QPushButton:hover{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                "stop:0 #7a9fe8,stop:1 #6a8fd8)}"
                "QPushButton:pressed{background:#4a6fb8}")
            btn.clicked.connect(dlg.accept)
            brow = QHBoxLayout()
            brow.addStretch(); brow.addWidget(btn); brow.addStretch()
            inner.addLayout(brow)
            dlg.setFixedSize(350, 260)
            g = app.primaryScreen().availableGeometry()
            dlg.move((g.width() - 350) // 2, (g.height() - 260) // 2)
            dlg.exec_()
        _dup_dialog()
        sys.exit(0)

from PyQt5.QtCore import (Qt, QTimer, QPoint, QRectF, pyqtSignal)
from PyQt5.QtGui import (QPainter, QIcon, QCursor, QColor, QFont,
                         QLinearGradient, QBrush, QFontMetrics)
from PyQt5.QtWidgets import (
    QApplication, QWidget, QMenu, QAction,
    QSystemTrayIcon, QSlider, QWidgetAction, QLabel,
)

# Windows 高 DPI 感知：让托盘图标、窗口在高分屏上正常显示
if sys.platform == "win32":
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)   # Per-Monitor DPI Aware
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()     # fallback for Win8.0
        except Exception:
            pass

# Qt 高 DPI 缩放：让控件随 DPI 等比放大，避免打包后文字裁切
# 必须在 QApplication 创建前调用
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

from src.user_data import migrate_old_data
migrate_old_data()  # 首次启动：旧数据迁移到用户目录

from src.pet_state import PetState, PetAction, PetMood
from src.pet_animator import PetAnimator
from src.pet_renderer_sprite import SpriteRenderer as PetRenderer
from src.bubble_widget import BubbleWidget
from src.status_panel import StatusPanel
from src.input_monitor import InputMonitor, InputState
from src.game_systems import GameSystems
from src.chat_service import ChatService
from src.snap_system import SnapSystem, TASKBAR_MARGIN
from src.timer_core import Countdown, format_remaining
from src.countdown_float import CountdownFloat
from src.reminder_bubble import ReminderBubbleManager
from src.reminder_window import ReminderWindow
from src.pomodoro import PomodoroTimer, FOCUS, SHORT_BREAK
from src import reminder_store

PET_SIZE = 210   # 基准值，main() 中根据屏幕逻辑高度重新计算
PET_WINDOW_MARGIN = 20   # 窗口四周透明 padding，_sync_window_pos 中用到
FPS = 60
SAVE_EVERY = 30
_DESIGN_H = 1440  # 设计基准：2560×1440 @ 100% DPI 下的逻辑屏幕高度

_DIALOGUES: dict[str, list[str]] = {
    "morning":  ["早上好！今天也要加油哦~", "嗯...还没睡醒呢...", "新的一天，元气满满！", "早安！要吃早饭了吗？"],
    "noon":     ["中午了，要记得吃饭哦！", "午休一会儿？我也想睡...", "下午茶时间到～", "补充能量！"],
    "evening":  ["傍晚了，今天辛苦了！", "夕阳好漂亮，一起看看？", "该放松一下了~", "今天有没有开心的事？"],
    "night":    ["好晚了，要注意休息哦...", "夜深了...困不困？", "再玩一会儿就睡哦~", "陪你到深夜，嘿嘿~"],
    "idle":     ["......", "发呆中...（o_o）", "哼哼哼～", "有人在吗？", "好无聊哦..."],
    "happy":    ["好开心！！！", "嘿嘿嘿～最喜欢你了！", "今天心情超好！"],
    "hungry":   ["肚子好饿...咕噜噜...", "可以喂我吗？求求了！", "有没有好吃的？(눈_눈)"],
    "sleepy":   ["好困啊...眼睛睁不开了...", "让我睡一会儿吧...", "Zzz...不是...没睡着..."],
    "typing":   ["好厉害，打字这么快！", "在工作吗？加油！", "啪啪啪～键盘真响", "好忙好忙的样子~", "一起努力！"],
    "typing_intense": ["这手速！！", "停不下来了？！", "啊啊啊好快！！", "你是打字机吗！"],
    "clicking": ["点击！！", "鼠标点得好快！", "在打羽毛球吗？"],
    "pet":      ["好舒服～", "再摸摸我嘛~", "最喜欢这样了！", "嗯嗯嗯～"],
    "game":     ["好耶！！！打羽毛球啦！", "发球！接好咯～", "这球我能接！我能接！", "运动时间到～", "来打一局嘛～"],
    "drag":     ["呜！放我下来！", "转转转～", "好晕哦...", "要去哪里呀？"],
    "cling":    ["嘿咻！抓住了！", "挂在这里休息一下~", "好高呀！", "这里视角真不错！", "稳稳~"],
    "throw":    ["啊啊啊！被扔了！", "飞起来了～", "我能飞！...啊不能", "哇——！"],
    "fall":     ["啊————！", "我掉下来了！", "救命！", "重力好讨厌！"],
    "land":     ["好痛！屁股摔两半了...", "安全着陆！...才怪", "哎哟～", "总算落地了..."],
    "cat":      ["喵～学猫叫！", "喵喵喵？我是小猫咪！", "伸个懒腰～喵~", "呼噜呼噜～", "猫猫模式启动！"],
    "study":    ["认真学习中...📖", "知识就是力量！", "好多要学的呀...", "嘘...我在看书呢", "学习使我快乐！...吧？"],
}

def _time_slot() -> str:
    h = datetime.now().hour
    if 6  <= h < 11: return "morning"
    if 11 <= h < 14: return "noon"
    if 14 <= h < 18: return "evening"
    return "night"

def _pick(category: str) -> str:
    pool = _DIALOGUES.get(category, _DIALOGUES["idle"])
    return random.choice(pool)

def _mood_to_dialogue_key(mood: PetMood) -> str | None:
    return {PetMood.HAPPY: "happy", PetMood.HUNGRY: "hungry",
            PetMood.SLEEPY: "sleepy"}.get(mood)

def _mood_to_str(mood: PetMood) -> str:
    return {PetMood.HAPPY: "happy", PetMood.NORMAL: "normal",
            PetMood.SAD: "sad", PetMood.HUNGRY: "hungry",
            PetMood.SLEEPY: "sleepy", PetMood.SLEEPING: "sleepy"}.get(mood, "normal")


# (emoji, stat_label, num_delta, badge_text, badge_color_or_"rainbow", orbit_dot_colors)
_ITEM_FLOAT: dict[str, tuple] = {
    "apple":    ("🍎", "饱食度", "+15", "饱食", "#f4922a", ("#f4922a", "#ffcf80", "#ff6b35")),
    "cake":     ("🍰", "饱食度", "+30", "饱食", "#f4922a", ("#f4922a", "#ffcf80", "#ff6b35")),
    "candy":    ("🍬", "心情值", "+15", "心情", "#d4a800", ("#ffd600", "#ff9de2", "#ffe899")),
    "coffee":   ("☕",  "体力值", "+20", "体力", "#20a8b8", ("#4db6c4", "#a0e8f0", "#007c90")),
    "plush":    ("🧸", "亲密度", "+10", "亲密", "#e0608a", ("#f06292", "#ffb3cc", "#c2185b")),
    "star":     ("⭐", "经验值", "+50", "经验", "#7b52d0", ("#9c6fff", "#c9aaff", "#5a3aaa")),
    "gift_box": ("🎁", "全属性", "+10", "🌈",  "rainbow",  ("#ff6b6b", "#6be084", "#40b0ff")),
}


class FloatLabel(QWidget):
    """RPG 斜角爆出浮动数值标签 — 从角色右侧弹出向右上飞散"""

    _DURATION_MS = 2000  # 总动画时长 2.0 s

    # keyframes: (progress 0~1, tx px, ty px, rotation deg, scale, opacity)
    _KF = (
        (0.00,  0.0,  8.0, -6.0, 0.55, 0.0),
        (0.20, 31.0, -26.0,  5.0, 1.18, 1.0),
        (0.60, 57.0, -49.0, -2.0, 1.00, 1.0),
        (1.00, 86.0, -86.0,  4.0, 0.80, 0.0),
    )

    _W, _H = 200, 130  # widget fixed size (generous to accommodate max-scale clipping)

    def __init__(self, item_id: str, pet_x: float, pet_y: float, pet_size: int):
        super().__init__(None)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(self._W, self._H)

        cfg = _ITEM_FLOAT.get(item_id,
              ("❓", "属性", "+?", "?", "#888888", ("#888", "#888", "#888")))
        self._emoji, self._stat, self._num_text, self._badge_text, self._badge_color, _ = cfg

        # Origin: right side of pet torso, roughly mid-height
        self._ox = int(pet_x + pet_size * 0.58)
        self._oy = int(pet_y + pet_size * 0.38)

        # Current render state (updated per tick)
        self._rot   = -6.0
        self._scale =  0.55
        self._t_ms  =  0.0
        self._last_perf: float | None = None

        # Timer drives ~60 fps animation
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

        # Initial position (keyframe 0)
        self._apply_kf(0.0, 8.0)
        self.setWindowOpacity(0.0)

    # ── interpolation helpers ─────────────────────────────────────────────
    @staticmethod
    def _lerp(a: float, b: float, t: float) -> float:
        return a + (b - a) * t

    def _interp(self, progress: float):
        kf = self._KF
        for i in range(len(kf) - 1):
            p0, tx0, ty0, r0, s0, o0 = kf[i]
            p1, tx1, ty1, r1, s1, o1 = kf[i + 1]
            if p0 <= progress <= p1:
                a = (progress - p0) / (p1 - p0)
                L = self._lerp
                return L(tx0, tx1, a), L(ty0, ty1, a), L(r0, r1, a), L(s0, s1, a), L(o0, o1, a)
        last = kf[-1]
        return last[1], last[2], last[3], last[4], last[5]

    def _apply_kf(self, tx: float, ty: float) -> None:
        x = self._ox - self._W // 2 + int(tx)
        y = self._oy - self._H // 2 + int(ty)
        self.move(x, y)

    # ── animation tick ────────────────────────────────────────────────────
    def _tick(self) -> None:
        now = time.perf_counter() * 1000.0
        if self._last_perf is None:
            self._last_perf = now
        self._t_ms += now - self._last_perf
        self._last_perf = now

        progress = min(self._t_ms / self._DURATION_MS, 1.0)
        tx, ty, rot, scale, opacity = self._interp(progress)

        self._rot   = rot
        self._scale = scale
        self._apply_kf(tx, ty)
        self.setWindowOpacity(max(0.0, min(1.0, opacity)))
        self.update()

        if progress >= 1.0:
            self._timer.stop()
            self.close()

    # ── public entry ──────────────────────────────────────────────────────
    def show_float(self) -> None:
        self.show()
        self._t_ms     = 0.0
        self._last_perf = None
        self._timer.start()

    # ── painting ──────────────────────────────────────────────────────────
    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)

        W, H = self._W, self._H
        cx, cy = W / 2.0, H / 2.0

        # Apply rotation + scale around widget center
        p.translate(cx, cy)
        p.rotate(self._rot)
        p.scale(self._scale, self._scale)
        p.translate(-cx, -cy)

        # ── Large gold number (+XX) ───────────────────────────────────────
        num_font = QFont()
        num_font.setFamily("Impact")
        num_font.setPixelSize(40)
        num_font.setBold(True)
        num_font.setLetterSpacing(QFont.AbsoluteSpacing, 2)
        p.setFont(num_font)
        nfm = p.fontMetrics()
        nw  = nfm.horizontalAdvance(self._num_text)
        nh  = nfm.height()
        na  = nfm.ascent()

        # Position: slightly left of center to leave room for the badge
        nx = int(cx - nw / 2.0 - 14)
        ny = int(cy - nh / 2.0 + 4)   # rect top
        nb = ny + na                    # baseline

        # Outline — 8 offsets at ±3 px
        p.setPen(QColor(0, 0, 0, 215))
        for ddx, ddy in ((-3,-3),(0,-3),(3,-3),(-3,0),(3,0),(-3,3),(0,3),(3,3)):
            p.drawText(nx + ddx, nb + ddy, self._num_text)

        # Gold fill
        p.setPen(QColor("#ffe566"))
        p.drawText(nx, nb, self._num_text)

        # ── Attribute badge (top-right corner of number block) ────────────
        badge_font = QFont()
        badge_font.setFamily("Microsoft YaHei")
        badge_font.setPixelSize(12)
        badge_font.setBold(True)
        p.setFont(badge_font)
        bfm  = p.fontMetrics()
        btw  = bfm.horizontalAdvance(self._badge_text)
        bth  = bfm.height()
        bpx, bpy = 6, 3              # inner padding
        brect = QRectF(nx + nw + 0, ny - 8,
                       btw + bpx * 2, bth + bpy * 2)

        p.setPen(Qt.NoPen)
        if self._badge_color == "rainbow":
            grad = QLinearGradient(brect.left(), 0, brect.right(), 0)
            for pos, col in ((0.0,"#ff6b6b"),(0.2,"#ffa640"),(0.4,"#ffe140"),
                             (0.6,"#6be084"),(0.8,"#40b0ff"),(1.0,"#c06bff")):
                grad.setColorAt(pos, QColor(col))
            p.setBrush(QBrush(grad))
        else:
            p.setBrush(QColor(self._badge_color))
        p.drawRoundedRect(brect, 6, 6)

        # Badge text (white, centered inside badge)
        p.setPen(QColor("white"))
        p.setFont(badge_font)
        inner = QRectF(brect.left() + bpx, brect.top() + bpy,
                       btw, bth)
        p.drawText(inner.toRect(), Qt.AlignCenter, self._badge_text)

        # ── Bottom row: emoji  +  "stat_label num_text" ──────────────────
        row_y_top = ny + nh + 4    # a few px below number bottom

        emoji_font = QFont()
        emoji_font.setFamily("Segoe UI Emoji")
        emoji_font.setPixelSize(16)
        p.setFont(emoji_font)
        efm = p.fontMetrics()
        ew  = efm.horizontalAdvance(self._emoji)
        ea  = efm.ascent()

        stat_text = f"{self._stat} {self._num_text}"
        stat_font = QFont()
        stat_font.setFamily("Microsoft YaHei")
        stat_font.setPixelSize(12)
        stat_font.setBold(True)
        sfm = QFontMetrics(stat_font)
        sw  = sfm.horizontalAdvance(stat_text)
        sa  = sfm.ascent()

        gap     = 5
        row_w   = ew + gap + sw
        row_x   = int(cx - row_w / 2.0)
        # align baselines of emoji and stat text
        max_a   = max(ea, sa)
        e_y     = row_y_top + max_a
        s_y     = row_y_top + max_a

        # Emoji with subtle glow shadow
        p.setFont(emoji_font)
        p.setPen(QColor(255, 200, 0, 100))
        for ddx, ddy in ((-1, 1), (1, 1), (0, 2)):
            p.drawText(row_x + ddx, e_y + ddy, self._emoji)
        p.setPen(QColor(255, 240, 180))
        p.drawText(row_x, e_y, self._emoji)

        # Stat text with thin shadow
        p.setFont(stat_font)
        p.setPen(QColor(0, 0, 0, 160))
        p.drawText(row_x + ew + gap + 1, s_y + 1, stat_text)
        p.setPen(QColor("#ffd070"))
        p.drawText(row_x + ew + gap, s_y, stat_text)

        p.end()


class PetWindow(QWidget):
    _proactive_reply = pyqtSignal(str, str)  # reply, error

    def __init__(self):
        super().__init__()
        self._proactive_reply.connect(self._on_proactive_reply)

        # DPI 等比缩放系数（与 status_panel._ui_scale 同公式）
        _scr = QApplication.primaryScreen()
        self._ui_scale = min(1.0, _scr.geometry().height() / _DESIGN_H) if _scr else 1.0

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(PET_SIZE + 40, PET_SIZE + 40)

        self.state    = PetState()
        self.animator = PetAnimator()
        self.renderer = PetRenderer(size=PET_SIZE)
        self.renderer.on_action_done = self._on_anim_done
        self.bubble   = BubbleWidget()
        self.game     = GameSystems()
        self.chat_svc = ChatService()
        self.panel    = StatusPanel(game_systems=self.game, chat_service=self.chat_svc)

        # ── 提醒·番茄钟模块(P1:快捷倒计时)──
        self.countdown        = Countdown()
        self._countdown_active = False
        self._countdown_paused = False
        self.countdown_float  = CountdownFloat()
        self.reminder_bubbles = ReminderBubbleManager()
        self.reminder_window  = ReminderWindow()
        self.reminder_window.start_countdown.connect(self._on_start_countdown)
        self.reminder_window.toggle_pause.connect(self._on_toggle_pause)
        self.reminder_window.reset_timer.connect(self._on_reset_countdown)
        self.pomodoro         = PomodoroTimer()
        self.reminder_window.start_pomodoro.connect(self._on_start_pomodoro)
        self.reminder_window.toggle_pomodoro_pause.connect(self._on_toggle_pomodoro_pause)
        self.reminder_window.reset_pomodoro.connect(self._on_reset_pomodoro)
        _saved_pomo = reminder_store.load_pomodoro_config()
        if _saved_pomo:
            self.pomodoro.cfg.update(_saved_pomo)
            self.reminder_window.set_pomodoro_config(self.pomodoro.cfg)

        self.input_state = InputState()

        self.monitor = InputMonitor(idle_timeout=10.0)
        # 加载无眼底图（用于 idle 状态眼睛跟随），预缩放到 PET_SIZE
        # 优先从 idle_noeyes.pak 读取，回退到散装 PNG
        from PyQt5.QtGui import QPixmap
        from PyQt5.QtCore import QByteArray as _QBA
        _base_dir  = sys._MEIPASS if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
        _anim_dir  = os.path.join(_base_dir, "assets", "animations")
        _raw = QPixmap()
        _pak_path  = os.path.join(_anim_dir, "idle_noeyes.pak")
        _png_path  = os.path.join(_anim_dir, "idle_noeyes_0000.png")
        if os.path.exists(_pak_path):
            try:
                from src.pak_loader import open_pak, read_frame_bytes as _rfb
                _zf   = open_pak(_pak_path)
                _data = _rfb(_zf, 0)
                _zf.close()
                if _data:
                    _raw.loadFromData(_QBA(_data), "PNG")
            except Exception:
                pass
        if _raw.isNull() and os.path.exists(_png_path):
            _raw = QPixmap(_png_path)
        if not _raw.isNull():
            _dpr = QApplication.primaryScreen().devicePixelRatio()
            _ds = int(PET_SIZE * _dpr)
            self._idle_noeyes_px = _raw.scaled(
                _ds, _ds, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self._idle_noeyes_px.setDevicePixelRatio(_dpr)
        else:
            self._idle_noeyes_px = None
        self._face_scale = PET_SIZE / 1024.0
        self._connect_input_signals()
        self.monitor.start()

        screen = QApplication.primaryScreen().geometry()
        self._pet_x = float(screen.width()  - PET_SIZE - 194)
        self._pet_y = float(screen.height() - PET_SIZE - 182)
        self._sync_window_pos()

        # ── 视线跟踪 ──────────────────────────────────────────────────
        self._gaze_x = self._pet_x + PET_SIZE / 2
        self._gaze_y = self._pet_y + PET_SIZE / 2
        self._gaze_smooth_x = 0.0
        self._gaze_smooth_y = 0.0

        # ── 鼠标快速移动时的头部倾侧（已弃用，保留变量兼容） ────────
        self._mouse_tilt       = 0.0
        self._mouse_tilt_target= 0.0
        self._prev_mouse_x     = 0.0
        self._mouse_speed_smooth = 0.0



        # ── 打字抖动效果 ──────────────────────────────────────────────
        # _typing_anim_timer > 0 时宠物处于"打字忙碌"视觉状态
        self._typing_anim_timer  = 0.0
        self._typing_bob_phase   = 0.0   # 上下抖动相位（mod 2π 循环）
        self._typing_sway_phase  = 0.0   # 左右摇摆相位（与 bob 错开频率）
        self._typing_bob_amp     = 0.0   # 上下抖动振幅（独立变量，弹簧衰减）
        self._typing_sway_amp    = 0.0   # 左右摇摆振幅
        self._typing_squish      = 1.0   # 当前挤压比例
        self._typing_squish_tgt  = 1.0

        # ── 鼠标点击闪烁 ─────────────────────────────────────────────
        self._click_anim_timer   = 0.0
        self._click_flash        = 0.0   # 0~1 亮度叠加

        # ── 拖拽 & 物理 ────────────────────────────────────────────────
        self._dragging       = False
        self._drag_offset    = QPoint()
        self._drag_start_time= 0.0
        self._throw_vx       = 0.0
        self._throw_vy       = 0.0
        self._is_thrown      = False
        self._is_falling     = False
        self._current_rotation   = 0.0
        self._target_rotation    = 0.0
        self._drag_history: list[tuple[float, float, float]] = []
        self._drag_from_physics  = False
        self._land_squash        = 1.0
        self._land_squash_timer  = 0.0

        # ── 吸附系统 ────────────────────────────────────────────────
        self._dpr = QApplication.primaryScreen().devicePixelRatio()
        self._snap_system = SnapSystem(dpr=self._dpr, pet_size=PET_SIZE)
        self._is_snapped       = False
        self._snap_target_type = ""
        self._snap_target_hwnd: int | None = None
        self._cling_press_pos = None  # 吸附状态下记录点击位置
        self._SNAP_DISTANCE    = 50

        self._opacity_pct    = 100
        self._auto_walk_timer= random.uniform(20.0, 40.0)
        self._last_action_time = time.time()
        self._item_playing   = False   # True while item animation is running
        self._last_time      = time.time()
        self._save_timer     = 0.0
        self._dialogue_timer = random.uniform(15.0, 35.0)

        # ── 主动聊天（长时间无互动时桌宠找用户说话）────────────────
        self._last_interact_time = time.time()   # 最近一次用户互动时间
        self._proactive_count    = 0             # 本轮空闲已主动说话次数
        self._proactive_max      = 0             # 本轮空闲最多说话次数（1~3 随机）
        self._proactive_cd       = 0.0           # 两次主动说话的冷却（秒）
        self._proactive_waiting  = False         # 正在等待 API 回复

        # ── 体力自动睡觉/唤醒 ────────────────────────────────────────
        self._auto_sleep_cd      = 0.0           # 唤醒后冷却（防止立刻重新入睡）

        self._loop = QTimer(self)
        self._loop.timeout.connect(self._tick)
        self._loop.start(1000 // FPS)

        self.panel.feed_clicked.connect(self._on_feed)
        self.panel.sleep_clicked.connect(self._on_sleep)
        self.panel.wake_clicked.connect(self._on_wake)
        self.panel.pet_clicked.connect(self._on_pet)
        self.panel.game_clicked.connect(self._on_game)
        self.panel.cat_clicked.connect(self._on_cat)
        self.panel.study_clicked.connect(self._on_study)
        self.panel.rename_requested.connect(self._on_rename)
        self.panel.item_used.connect(self._on_item_used)
        self.panel.action_bubble.connect(self._on_action_bubble)

        self._setup_tray()

        if self.state.is_new:
            self.state.is_new = False
            self._say(_pick(_time_slot()), mood="happy")
        else:
            self._say(_pick(_time_slot()))

        self.show()

    # ── 输入信号连接 ──────────────────────────────────────────────────
    def _connect_input_signals(self):
        m = self.monitor
        m.mouse_moved.connect(self._on_mouse_global_move)
        m.mouse_pressed.connect(self._on_mouse_global_press)
        m.mouse_released.connect(self._on_mouse_global_release)
        m.key_pressed.connect(self._on_key_global_press)
        m.input_idle.connect(self._on_input_idle)

    def _on_mouse_global_move(self, x: int, y: int):
        self.input_state.on_mouse_move(x, y)
        lx = x / self._dpr
        ly = y / self._dpr
        self._prev_mouse_x = lx
        self._gaze_x = lx
        self._gaze_y = ly


    def _on_mouse_global_press(self, btn: str):
        self.input_state.on_mouse_press(btn)
        if not self._dragging and not self.state.is_sleeping and not self._is_snapped:
            self._click_anim_timer = 0.35
            if random.random() < 0.18:
                self._say(_pick("clicking"), trigger_anim=False)

    def _on_mouse_global_release(self, btn: str):
        self.input_state.on_mouse_release(btn)

    def _on_key_global_press(self, key: str):
        self.input_state.on_key_press(key)
        if self.state.is_sleeping or self._dragging or self._is_snapped:
            return

        intensity = self.input_state.typing_intensity
        # NOTE: timer 仅作为“最后一次按键后保持动画”的短窗口，停止打字后快速进入衰减。
        if intensity == "intense":
            self._typing_anim_timer = 0.8
        elif intensity == "normal":
            self._typing_anim_timer = 0.6
        elif intensity == "light":
            self._typing_anim_timer = 0.4

        # NOTE: 每次按键触发一次横向挤压脉冲，强度随打字速度分级。
        # _typing_squish_tgt 是目标值，在 _update_input_effects 中弹簧插值回 1.0。
        if intensity == "intense":
            self._typing_squish_tgt = 0.92
        elif intensity == "normal":
            self._typing_squish_tgt = 0.95
        elif intensity == "light":
            self._typing_squish_tgt = 0.97

        # 偶尔说话
        spd = self.input_state.typing_speed
        if spd > 10 and random.random() < 0.08:
            self._say(_pick("typing_intense"), mood="happy", trigger_anim=False)
        elif spd > 5 and random.random() < 0.04:
            self._say(_pick("typing"), mood="normal", trigger_anim=False)

    def _on_input_idle(self):
        if (self.state.is_sleeping or self._dragging or self._is_snapped
                or self._pomodoro_focusing()):
            return
        self._say(_pick("idle"))

    # ── 主循环 ────────────────────────────────────────────────────────
    def _tick(self):
        now = time.time()
        dt  = min(now - self._last_time, 0.05)
        self._last_time = now

        self.state.update(dt)

        # ── 体力值自动睡觉/唤醒（优先级最高，在 animator.update 之前） ──
        # energy <= 20 → 自动入睡 ; energy >= 80 → 自动唤醒
        # NOTE: 使用冷却防止刚唤醒时 energy 短暂跌回阈值又立刻重新入睡
        if (not self.state.is_sleeping and self.state.energy <= 20
                and not self._pomodoro_focusing()):
            if self._auto_sleep_cd <= 0:
                self._on_sleep()
        elif self.state.is_sleeping and self.state.energy >= 80:
            self._on_wake()
            self._auto_sleep_cd = 5.0   # 唤醒后 5 秒内不再自动入睡
        if self._auto_sleep_cd > 0:
            self._auto_sleep_cd -= dt

        renderer_busy = (
            self._item_playing or (
            hasattr(self.renderer, '_action') and (
                self.renderer._action in getattr(self.renderer, 'ONESHOT_ALL', set()) or
                getattr(self.renderer, '_frozen_sleep', False) or
                getattr(self.renderer, '_frozen_stay', False) or
                bool(getattr(self.renderer, '_pending', []))
            ))
        )
        animator_blocked = renderer_busy or self._dragging or self._is_snapped
        if not animator_blocked:
            self.animator.update(dt, self.state)

        # ── 睡眠状态同步：animator 自动触发睡眠时同步驱动渲染器 ──────
        if (self.state.is_sleeping
                and not getattr(self.renderer, '_frozen_sleep', False)
                and getattr(self.renderer, '_action', '') not in ('sleep', 'wake')
                and 'wake' not in getattr(self.renderer, '_pending', [])):
            self.renderer.trigger("sleep")

        self._update_gaze(dt)
        self._update_input_effects(dt)   # ← 键鼠视觉效果更新
        self._tick_physics(dt)
        self._tick_land_squash(dt)
        if not self._is_thrown and not self._is_falling:
            self._clamp_to_screen()
        self._tick_snap_follow()
        self._tick_auto_walk(dt)
        self._apply_walk_movement()
        self._sync_window_pos()
        self._tick_foreground()
        self._restack_above_pet()

        if hasattr(self.renderer, 'update'):
            action_str = (
                getattr(self.animator, "get_action_str", lambda a: "idle")(self.state.current_action)
                if hasattr(self.animator, "get_action_str")
                else str(self.state.current_action).lower().replace("petaction.", "")
            )
            self.renderer.update(dt, action_str)

        if self.panel.isVisible():
            self.panel.update_status(self.state)

        self._tick_dialogue(dt)

        self._save_timer += dt
        if self._save_timer >= SAVE_EVERY:
            self._save_timer = 0.0
            self.state.total_keystrokes   = max(self.state.total_keystrokes,   self.input_state.today_keystrokes)
            self.state.total_mouse_clicks = max(self.state.total_mouse_clicks, self.input_state.today_mouse_clicks)
            self.state.save()
            # 游戏系统：记录在线时长 + 检查成就
            self.game.record_action("online", int(self.input_state.session_minutes))
            new_achs = self.game.check_achievements(self.state)
            for a in new_achs:
                self._say(f"🏆 解锁成就：{a['name']}！+{a['reward']}金币", mood="happy")
            self.game.save()

        self.update()

    # ── 键鼠视觉效果更新 ─────────────────────────────────────────────
    _TWO_PI = math.pi * 2.0

    def _update_input_effects(self, dt: float):
        # 打字动画计时器衰减
        if self._typing_anim_timer > 0:
            self._typing_anim_timer -= dt

        # ── 相位推进（始终循环，不断积累）+ 振幅弹簧驱动 ──
        if self._typing_anim_timer > 0:
            # 打字进行中：相位持续推进，振幅弹簧逼近目标值
            intensity = self.input_state.typing_intensity
            bob_speed = {"intense": 18.0, "normal": 12.0, "light": 8.0}.get(intensity, 8.0)
            sway_speed = {"intense": 11.0, "normal": 7.5, "light": 5.0}.get(intensity, 5.0)
            self._typing_bob_phase = (self._typing_bob_phase + dt * bob_speed) % self._TWO_PI
            self._typing_sway_phase = (self._typing_sway_phase + dt * sway_speed) % self._TWO_PI
            # 振幅快速趋近目标值
            bob_tgt = {"intense": 3.0, "normal": 1.8, "light": 1.0}.get(intensity, 1.0)
            sway_tgt = {"intense": 2.5, "normal": 1.5, "light": 0.8}.get(intensity, 0.8)
            self._typing_bob_amp += (bob_tgt - self._typing_bob_amp) * min(1.0, dt * 10.0)
            self._typing_sway_amp += (sway_tgt - self._typing_sway_amp) * min(1.0, dt * 10.0)
        else:
            # 停止打字：相位冻结，振幅快速衰减到 0
            self._typing_bob_amp *= max(0.0, 1.0 - dt * 12.0)
            self._typing_sway_amp *= max(0.0, 1.0 - dt * 12.0)
            if self._typing_bob_amp < 0.01:
                self._typing_bob_amp = 0.0
                self._typing_bob_phase = 0.0
            if self._typing_sway_amp < 0.01:
                self._typing_sway_amp = 0.0
                self._typing_sway_phase = 0.0

        # ── 打字横向挤压弹簧（_typing_squish → _typing_squish_tgt）──
        # 每次按键把 tgt 设为 <1.0（挤扁），然后 tgt 快速弹回 1.0，
        # squish 用较慢的弹簧追 tgt，产生"按下→弹回"的果冻效果。
        self._typing_squish_tgt += (1.0 - self._typing_squish_tgt) * min(1.0, dt * 15.0)
        self._typing_squish += (self._typing_squish_tgt - self._typing_squish) * min(1.0, dt * 10.0)
        if abs(self._typing_squish - 1.0) < 0.002:
            self._typing_squish = 1.0

        # 鼠标点击闪烁衰减
        if self._click_anim_timer > 0:
            self._click_anim_timer -= dt
            self._click_flash = self._click_anim_timer / 0.35
        else:
            self._click_flash = 0.0

    def _apply_walk_movement(self):
        if (hasattr(self.renderer, '_action') and self.renderer._action == "walk"):
            self._pet_x += 1.2

    def _tick_auto_walk(self, dt: float):
        if self.state.is_sleeping or self._is_thrown or self._is_falling \
                or self._dragging or self._is_snapped or self._pomodoro_focusing():
            return
        # 道具动画期间完全跳过 auto_walk
        if self._item_playing:
            self._auto_walk_timer = random.uniform(20.0, 40.0)
            return
        if hasattr(self.renderer, '_action') and \
           self.renderer._action in getattr(self.renderer, 'ONESHOT_ALL', set()):
            self._auto_walk_timer = random.uniform(20.0, 40.0)
            return
        if hasattr(self.renderer, '_pending') and self.renderer._pending:
            return
        self._auto_walk_timer -= dt
        if self._auto_walk_timer <= 0:
            self._auto_walk_timer = random.uniform(20.0, 45.0)
            self.renderer.trigger("walk")
            self.state.current_action = PetAction.WALK_RIGHT

    # ── 物理系统 ─────────────────────────────────────────────────────
    _GRAVITY     = 1200.0
    _THROW_MIN   = 250.0
    _BOUNCE      = 0.35
    _WALL_BOUNCE = 0.5

    def _tick_physics(self, dt: float):
        rot_diff = self._target_rotation - self._current_rotation
        if abs(rot_diff) > 0.01:
            self._current_rotation += rot_diff * min(1.0, dt * 8.0)
        else:
            self._current_rotation = self._target_rotation

        if not self._is_thrown and not self._is_falling:
            return

        self._throw_vy += self._GRAVITY * dt
        self._pet_x    += self._throw_vx * dt
        self._pet_y    += self._throw_vy * dt

        if self._is_thrown:
            speed = (self._throw_vx**2 + self._throw_vy**2)**0.5
            if speed > 50:
                self._target_rotation = math.atan2(self._throw_vy, self._throw_vx) * 0.3

        screen = QApplication.primaryScreen().geometry()
        sw, sh = float(screen.width()), float(screen.height())

        # NOTE: _pet_y 最小值为 PET_WINDOW_MARGIN(20)，确保窗口上边缘不超出屏幕
        if self._pet_y < PET_WINDOW_MARGIN:
            self._pet_y = float(PET_WINDOW_MARGIN)
            self._throw_vy = abs(self._throw_vy) * self._WALL_BOUNCE
        if self._pet_x < PET_WINDOW_MARGIN:
            self._pet_x = float(PET_WINDOW_MARGIN)
            self._throw_vx = abs(self._throw_vx) * self._WALL_BOUNCE
        if self._pet_x > sw - PET_SIZE - PET_WINDOW_MARGIN:
            self._pet_x = sw - PET_SIZE - PET_WINDOW_MARGIN
            self._throw_vx = -abs(self._throw_vx) * self._WALL_BOUNCE

        ground = sh - PET_SIZE - 40
        if self._pet_y >= ground:
            self._pet_y = ground
            if abs(self._throw_vy) > 120:
                self._throw_vy = -self._throw_vy * self._BOUNCE
                self._throw_vx *= 0.6
            else:
                self._land()

    def _land(self):
        self._is_thrown = self._is_falling = False
        self._throw_vx = self._throw_vy = 0.0
        self._target_rotation = self._current_rotation = 0.0
        self._land_squash = 0.55
        self._land_squash_timer = 0.8
        self.state.current_action = PetAction.IDLE
        self._say(_pick("land"), trigger_anim=False)

    def _tick_land_squash(self, dt: float):
        if self._land_squash_timer > 0:
            self._land_squash_timer -= dt
            self._land_squash += (1.0 - self._land_squash) * dt * 6.0
            if self._land_squash_timer <= 0:
                self._land_squash = 1.0

    def _calc_throw_velocity(self) -> tuple[float, float]:
        now    = time.time()
        recent = [(t, x, y) for t, x, y in self._drag_history if now - t < 0.08]
        if len(recent) < 2:
            return 0.0, 0.0
        t0, x0, y0 = recent[0]
        t1, x1, y1 = recent[-1]
        elapsed = t1 - t0
        if elapsed < 0.001:
            return 0.0, 0.0
        return (x1 - x0) / elapsed, (y1 - y0) / elapsed

    # ── 视线跟踪 ─────────────────────────────────────────────────────
    def _update_gaze(self, dt: float):
        pet_cx = self._pet_x + PET_SIZE / 2
        pet_cy = self._pet_y + PET_SIZE / 2
        raw_dx = self._gaze_x - pet_cx
        raw_dy = self._gaze_y - pet_cy
        dist   = (raw_dx**2 + raw_dy**2)**0.5 + 0.001
        max_gaze = 30.0
        gaze_dx  = (raw_dx / dist) * min(dist * 0.20, max_gaze)
        gaze_dy  = (raw_dy / dist) * min(dist * 0.14, max_gaze * 0.6)
        alpha = 1.0 - 0.82 ** (dt * 60)
        self._gaze_smooth_x += (gaze_dx - self._gaze_smooth_x) * alpha
        self._gaze_smooth_y += (gaze_dy - self._gaze_smooth_y) * alpha

    def _clamp_to_screen(self):
        screen = QApplication.primaryScreen().geometry()
        min_x, max_x = float(PET_WINDOW_MARGIN), float(screen.width() - PET_SIZE - PET_WINDOW_MARGIN)
        # NOTE: min_y 使用 PET_WINDOW_MARGIN 而非 0，确保窗口上边缘不超出屏幕顶部
        min_y, max_y = float(PET_WINDOW_MARGIN), float(screen.height() - PET_SIZE - 40)
        is_walking = (hasattr(self.renderer, '_action') and
                      self.renderer._action == "walk")
        if self._pet_x < min_x: self._pet_x = min_x
        if self._pet_x > max_x:
            self._pet_x = max_x
            if is_walking:
                self._auto_walk_timer = random.uniform(20.0, 40.0)
        self._pet_y = max(min_y, min(self._pet_y, max_y))

    def _sync_window_pos(self):
        self.move(int(self._pet_x) - 20, int(self._pet_y) - 20)

    def _tick_snap_follow(self):
        """吸附后跟随窗口移动，或检测窗口关闭后脱离吸附。"""
        if not self._is_snapped:
            return
        if self._snap_target_hwnd is None:
            # 屏幕边缘吸附：不需要跟随，但 clamp 保证不超出屏幕
            screen = QApplication.primaryScreen().geometry()
            self._clamp_to_screen()
            return
        # 窗口吸附：跟踪目标窗口位置
        rect = self._snap_system.get_window_rect(self._snap_target_hwnd)
        if rect is None:
            # 窗口已关闭/最小化/不可见 → 脱离吸附，回到右下角
            self._is_snapped = False
            self._snap_target_type = ""
            self._snap_target_hwnd = None
            screen = QApplication.primaryScreen().geometry()
            self._pet_x = float(screen.width() - PET_SIZE - 194)
            self._pet_y = float(screen.height() - PET_SIZE - 182)
            self.state.current_action = PetAction.IDLE
            return
        left, top, right, bottom = rect
        ww = right - left
        wh = bottom - top
        if ww < 100 or wh < 100:
            # 窗口变得太小 → 脱离吸附，回到右下角
            self._is_snapped = False
            self._snap_target_type = ""
            self._snap_target_hwnd = None
            screen = QApplication.primaryScreen().geometry()
            self._pet_x = float(screen.width() - PET_SIZE - 194)
            self._pet_y = float(screen.height() - PET_SIZE - 182)
            self.state.current_action = PetAction.IDLE
            return
        # 更新吸附位置：截图窗口完全在上方，普通窗口一半一半
        if self._snap_target_type == "preview_top":
            self._pet_y = float(top - int(PET_SIZE * 0.7))
        else:
            self._pet_y = float(top - PET_SIZE / 2)
        self._pet_x = max(float(left), min(float(right) - PET_SIZE, self._pet_x))
        # 确保不完全超出屏幕
        screen = QApplication.primaryScreen().geometry()
        sw, sh = float(screen.width()), float(screen.height())
        min_x, max_x = 0.0, sw - PET_SIZE
        max_y = sh - PET_SIZE - TASKBAR_MARGIN
        self._pet_x = max(min_x, min(max_x, self._pet_x))
        # NOTE: 当窗口上边缘贴近屏幕顶部时，桌宠实际是「趴在屏幕上方」，
        # 此时必须确保完整显示；否则允许部分超出顶部以跟随窗口。
        if top < PET_SIZE * 0.4:
            self._pet_y = max(float(PET_WINDOW_MARGIN), min(max_y, self._pet_y))
        else:
            self._pet_y = min(max_y, self._pet_y)

    # ── 绘制 ─────────────────────────────────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setOpacity(max(0.0, min(1.0, self._opacity_pct / 100.0)))

        cx = 20 + PET_SIZE / 2
        cy = 20 + PET_SIZE / 2

        # ── 从 animator 获取基础 transform ───────────────────────────
        get_tf = getattr(self.animator, "get_transform", None)
        if callable(get_tf):
            try:
                transform = get_tf()
            except Exception:
                transform = {}
        else:
            base_squash = self._land_squash if self._land_squash_timer > 0 \
                          else getattr(self.animator, "squash", 1.0)
            # NOTE: 打字效果通过 transform 数值叠加，与眼睛跟随独立通道、互不干涉。
            # offset_y: 身体上下微颤；cx 偏移: 左右摇摆；scale_x/y: 横向挤压弹跳。
            base_offset = getattr(self.animator, "get_breathe_offset", lambda: 0.0)()
            # 振幅由 _update_input_effects 独立驱动，这里直接读取
            typing_bob = math.sin(self._typing_bob_phase) * self._typing_bob_amp
            typing_sway = math.sin(self._typing_sway_phase) * self._typing_sway_amp

            typing_sx = self._typing_squish
            typing_sy = 1.0 + (1.0 - self._typing_squish) * 0.6 if self._typing_squish < 1.0 else 1.0

            # 左右摇摆直接偏移绘制中心，眼睛会跟着身体一起摇
            cx += typing_sway

            transform = {
                "scale_x":  base_squash * typing_sx,
                "scale_y":  (1.0 + (1.0 - base_squash) * 0.5 if base_squash < 1.0 else 1.0) * typing_sy,
                "rotation": self._current_rotation,
                "offset_y": base_offset + typing_bob,
                "facing":   getattr(self.animator, "facing", 1.0),
                "gaze_x":   self._gaze_smooth_x,
                "gaze_y":   self._gaze_smooth_y,
            }

        # ── 物理旋转（仅抛出时） ─────────────────────────────────────
        is_physics = self._is_thrown or self._is_falling
        transform["rotation"] = self._current_rotation if is_physics else 0.0

        # ── 判断是否 idle 状态（需要画眼睛跟随） ────────────────────
        cur_action = getattr(self.renderer, '_action', 'idle')
        frozen_sleep = getattr(self.renderer, '_frozen_sleep', False)
        is_item_anim = cur_action.startswith('item_')

        if is_item_anim:
            transform = {
                "scale_x": 1.0, "scale_y": 1.0,
                "rotation": 0.0, "offset_y": 0.0,
                "facing": 1.0, "gaze_x": 0.0, "gaze_y": 0.0,
            }

        is_idle = (cur_action == 'idle' and not is_physics
                   and not frozen_sleep and not self.state.is_sleeping
                   and not is_item_anim)

        if is_idle:
            if self._idle_noeyes_px is not None:
                # 用无眼底图 + 绘制跟随眼睛
                self._draw_idle_with_eyes(painter, cx, cy, transform)
            else:
                # 底图缺失：先渲染 idle 帧再叠加眼睛
                try:
                    self.renderer.draw(painter=painter, cx=cx, cy=cy,
                                       transform=transform, particles=None)
                except Exception:
                    pass
                self._draw_eyes_overlay(painter, cx, cy, transform)
        else:
            try:
                self.renderer.draw(
                    painter=painter,
                    cx=cx, cy=cy,
                    transform=transform,
                    particles=None,
                )
            except Exception:
                pass

        # 鼠标点击时叠加一圈淡白色光晕
        if self._click_flash > 0.01:
            from PyQt5.QtGui import QRadialGradient, QBrush
            from PyQt5.QtCore import QPointF
            gx = QRadialGradient(QPointF(cx, cy), PET_SIZE * 0.5)
            c1 = QColor(255, 255, 255, int(55 * self._click_flash))
            c2 = QColor(255, 255, 255, 0)
            gx.setColorAt(0.0, c1)
            gx.setColorAt(1.0, c2)
            painter.save()
            painter.setOpacity(1.0)
            painter.setBrush(QBrush(gx))
            painter.setPen(Qt.NoPen)
            r = int(PET_SIZE * 0.55)
            painter.drawEllipse(int(cx) - r, int(cy) - r, r * 2, r * 2)
            painter.restore()

        painter.end()

    # ── idle 状态：无眼底图 + 动态表情绘制 ─────────────────────────
    def _draw_idle_with_eyes(self, painter: QPainter, cx: float, cy: float, transform: dict):
        tr  = transform
        sx  = tr.get("scale_x",  1.0)
        sy  = tr.get("scale_y",  1.0)
        rot = math.degrees(tr.get("rotation", 0.0))
        oy  = tr.get("offset_y", 0.0)

        px   = self._idle_noeyes_px
        size = self.renderer.size if hasattr(self.renderer, 'size') else PET_SIZE

        painter.save()
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(cx, cy + size * 0.5 + oy)
        painter.rotate(rot)
        painter.scale(sx, sy)
        if px is not None:
            _d = px.devicePixelRatio()
            painter.drawPixmap(int(-px.width() / _d * 0.5), int(-px.height() / _d), px)

        self._draw_face(painter, sx, self._face_scale)
        painter.restore()

    def _draw_eyes_overlay(self, painter: QPainter, cx: float, cy: float, transform: dict):
        """当无眼底图缺失时，在已绘制的 idle 帧上叠加动态眼睛（坐标系独立 save/restore）"""
        tr  = transform
        sx  = tr.get("scale_x",  1.0)
        sy  = tr.get("scale_y",  1.0)
        rot = math.degrees(tr.get("rotation", 0.0))
        oy  = tr.get("offset_y", 0.0)
        size = self.renderer.size if hasattr(self.renderer, 'size') else PET_SIZE

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(cx, cy + size * 0.5 + oy)
        painter.rotate(rot)
        painter.scale(sx, sy)
        self._draw_face(painter, sx, self._face_scale)
        painter.restore()

    def _draw_face(self, painter: QPainter, sx: float, S: float):
        """在当前 painter 坐标系内绘制跟随眼睛和嘴巴（S = face_scale）"""
        from PyQt5.QtGui import QPainterPath, QPen
        from PyQt5.QtCore import QPointF

        # 把屏幕空间鼠标偏移映射为 [-1, +1] 范围的注视方向
        gx = max(-1.0, min(1.0, self._gaze_smooth_x / 12.0))
        gy = max(-1.0, min(1.0, self._gaze_smooth_y / 10.0))
        actual_gx = gx * (1.0 if sx >= 0 else -1.0)

        painter.setOpacity(1.0)
        painter.setPen(Qt.NoPen)

        # ── 眼睛 ────────────────────────────────────────────────────
        # 水平偏移和垂直偏移分开控制，避免向下看时眼睛贴近嘴巴
        EYE_SHIFT_X = max(2.0, 14.0 * S)   # 左右位移（保证最小位移量）
        EYE_SHIFT_Y = max(1.0,  5.0 * S)   # 上下位移（限制小，保持与嘴的距离）
        EYE_R       = max(2.0, 18.0 * S)   # 眼睛半径
        # 使用 QRectF 浮点绘制，避免 int 截断导致高 DPI 下高光错位
        eye_base  = [(-81.0 * S, -655.0 * S), (+75.0 * S, -655.0 * S)]
        for bx, by in eye_base:
            ex = bx + actual_gx * EYE_SHIFT_X
            ey = by + gy * EYE_SHIFT_Y
            painter.setBrush(QColor(10, 10, 15, 245))
            painter.drawEllipse(QRectF(ex - EYE_R, ey - EYE_R, EYE_R * 2, EYE_R * 2))
            # 高光 — 参数全部基于 EYE_R，任意 DPI 下比例恒定
            painter.setBrush(QColor(255, 255, 255, 110))
            hr = EYE_R * 0.81                                     # 高光直径
            h_cx = ex + EYE_R * 0.54 + actual_gx * EYE_R * 0.17  # 中心 x
            h_cy = ey + EYE_R * 0.13                              # 中心 y
            # 钳位：确保高光圆不超出眼球圆
            _dx, _dy = h_cx - ex, h_cy - ey
            _d = (_dx * _dx + _dy * _dy) ** 0.5
            _lim = EYE_R - hr * 0.5
            if _d > _lim > 0:
                _r = _lim / _d
                h_cx = ex + _dx * _r
                h_cy = ey + _dy * _r
            painter.drawEllipse(QRectF(h_cx - hr * 0.5, h_cy - hr * 0.5, hr, hr))

        # ── 嘴巴（1.2×） ────────────────────────────────────────────
        MOUTH_SHIFT_X = 5.0 * S
        MOUTH_SHIFT_Y = 3.5 * S
        mouth_bx, mouth_by = -3.5 * S, -612.0 * S
        mx = mouth_bx + actual_gx * MOUTH_SHIFT_X
        my = mouth_by + gy * MOUTH_SHIFT_Y
        mouth_w = 46.0 * S
        curve   = -gy * 11.52 * S
        path = QPainterPath()
        path.moveTo(QPointF(mx - mouth_w, my))
        path.quadTo(QPointF(mx, my + curve), QPointF(mx + mouth_w, my))
        pen = QPen(QColor(10, 10, 15, 220), max(1.0, 6.9 * S))
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

    # ── 鼠标事件 ─────────────────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 吸附状态下：不立即脱离，等用户真正拖拽时才解除吸附
            if self._is_snapped:
                self._cling_press_pos = event.globalPos()
                return

            if self._is_thrown or self._is_falling:
                # 物理状态下：先记录点击，等 mouseDoubleClickEvent 窗口期
                # 用一个短 timer 区分单击 vs 双击
                self._physics_click_pos   = event.pos()
                if hasattr(self, '_physics_click_timer') and self._physics_click_timer.isActive():
                    self._physics_click_timer.stop()
                self._physics_click_timer = QTimer(self)
                self._physics_click_timer.setSingleShot(True)
                self._physics_click_timer.timeout.connect(self._on_physics_single_click)
                self._physics_click_timer.start(220)   # 220ms 内没有双击就确认为单击
                return   # 不进入拖拽流程
            _quiet = self.state.is_sleeping or getattr(self.renderer, '_frozen_stay', False)
            if _quiet:
                self._drag_from_physics = False
                self._dragging        = True
                self._drag_start_time = time.time()
                self._drag_offset     = event.globalPos() - QPoint(int(self._pet_x), int(self._pet_y))
                self._drag_history.clear()
                self.setCursor(QCursor(Qt.ClosedHandCursor))
            else:
                self._drag_from_physics = False
                self._dragging        = True
                self._drag_start_time = time.time()
                self._drag_offset     = event.globalPos() - QPoint(int(self._pet_x), int(self._pet_y))
                self._drag_history.clear()
                self.state.current_action = PetAction.DRAG
                # 立即打断随机动画，切换到 drag 动画（道具动画播放中不打断）
                if not self._item_playing:
                    self.renderer.switch_loop("drag")
                self._say(_pick("drag"), trigger_anim=False)
                self.setCursor(QCursor(Qt.ClosedHandCursor))
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPos())

    def _on_physics_single_click(self):
        """物理弹跳中单击确认：停在当前位置"""
        self._is_thrown = self._is_falling = False
        self._throw_vx  = self._throw_vy  = 0.0
        self._target_rotation = self._current_rotation = 0.0
        self._land_squash = 0.75
        self._land_squash_timer = 0.4
        self.state.current_action = PetAction.IDLE

    def mouseMoveEvent(self, event):
        # 吸附状态下：鼠标移动超过阈值才脱离吸附并开始拖拽
        if self._cling_press_pos is not None:
            if (event.globalPos() - self._cling_press_pos).manhattanLength() > 8:
                self._cling_press_pos = None
                self._is_snapped = False
                self._snap_target_type = ""
                self._snap_target_hwnd = None
                self._dragging = True
                self._drag_start_time = time.time()
                self._drag_offset = event.globalPos() - QPoint(int(self._pet_x), int(self._pet_y))
                self._drag_history.clear()
                self.state.current_action = PetAction.DRAG
                if not self._item_playing:
                    self.renderer.switch_loop("drag")
                self._say(_pick("drag"), trigger_anim=False)
                self.setCursor(QCursor(Qt.ClosedHandCursor))
            return

        if self._dragging:
            new_pos     = event.globalPos() - self._drag_offset
            self._pet_x = float(new_pos.x())
            self._pet_y = float(new_pos.y())
            now = time.time()
            self._drag_history.append((now, self._pet_x, self._pet_y))
            while self._drag_history and now - self._drag_history[0][0] > 0.15:
                self._drag_history.pop(0)

            # 拖拽中不做磁力吸附，自由移动，松手时再检测吸附目标

    def mouseReleaseEvent(self, event):
        # 吸附状态下短按：不做任何反应，拦截状态切换
        if self._cling_press_pos is not None:
            self._cling_press_pos = None
            return

        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            self.setCursor(QCursor(Qt.ArrowCursor))
            held = time.time() - self._drag_start_time
            # NOTE: 睡觉状态下拖动释放的特殊处理：
            # 短按（< 0.2s）视为点击，触发轻颤；真实拖动则静默放下，不触发抳物理
            if self.state.is_sleeping:
                self._drag_from_physics = False
                if held < 0.2:
                    self._sleep_nudge()
                return
            if getattr(self.renderer, '_frozen_stay', False):
                self._drag_from_physics = False
                return
            if held < 0.2 and not self._drag_from_physics:
                self._handle_body_click(event.pos())
                return
            self._drag_from_physics = False
            vx, vy = self._calc_throw_velocity()
            speed  = (vx**2 + vy**2)**0.5
            screen = QApplication.primaryScreen().geometry()
            # 松手后优先检测吸附目标（无论速度/高度，靠近窗口上边框就吸附）
            snap = self._snap_system.find_nearest_snap(
                self._pet_x, self._pet_y,
                int(self.winId()),
                screen,
                self._SNAP_DISTANCE,
            )
            if snap is not None:
                self._pet_x = snap.snap_x
                self._pet_y = snap.snap_y
                # NOTE: 当吸附目标窗口上边缘贴近屏幕顶部时（如最大化窗口），
                # 桌宠实际是「趴在屏幕上方」，需确保完整显示。
                if snap.snap_y < float(PET_WINDOW_MARGIN):
                    win_top = (snap.snap_y + PET_SIZE * 0.7) if snap.edge_type == "preview_top" \
                              else (snap.snap_y + PET_SIZE / 2.0)
                    if win_top < PET_SIZE * 0.4:
                        self._pet_y = float(PET_WINDOW_MARGIN)
                self._is_snapped = True
                self._snap_target_type = snap.edge_type
                self._snap_target_hwnd = snap.hwnd
                self.state.current_action = PetAction.CLING
                self._say(_pick("cling"), trigger_anim=False)
            elif speed > self._THROW_MIN:
                self._is_thrown  = True
                self._throw_vx   = vx * 0.7
                self._throw_vy   = vy * 0.7
                self.state.current_action = PetAction.FALL
                self._say(_pick("throw"), trigger_anim=False)
            else:
                ground = float(screen.height() - PET_SIZE - 40)
                if self._pet_y < ground - 10:
                    self._is_falling = True
                    self._throw_vx = self._throw_vy = 0.0
                    self.state.current_action = PetAction.FALL
                else:
                    self.state.current_action = PetAction.IDLE

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._is_thrown or self._is_falling:
                # 弹跳中双击：取消单击 timer，停止 + 摸头
                if hasattr(self, '_physics_click_timer') and self._physics_click_timer.isActive():
                    self._physics_click_timer.stop()
                self._is_thrown = self._is_falling = False
                self._throw_vx  = self._throw_vy  = 0.0
                self._target_rotation = self._current_rotation = 0.0
            # NOTE: 睡觉时双击只轻颤，不触发摸头（不打断睡眠）
            if self.state.is_sleeping:
                self._sleep_nudge()
                return
            # 所有状态下双击都触发摸摸头
            self._on_pet()

    def _handle_body_click(self, local_pos: QPoint):
        rel_y = local_pos.y() - self.height() / 2
        if rel_y < -PET_SIZE * 0.25 or -PET_SIZE * 0.25 <= rel_y <= PET_SIZE * 0.25:
            self._on_pet()
        else:
            self.state.current_action = PetAction.WALK_RIGHT

    # ── 互动动作 ─────────────────────────────────────────────────────
    def _reset_interact_time(self):
        """用户与桌宠产生互动时重置空闲计时"""
        self._last_interact_time = time.time()
        self._proactive_count    = 0
        self._proactive_max      = 0

    def _sleep_nudge(self):
        """
        睡觉时用户点击身体的回应：短促左右轻颤。
        给一个小振幅脉冲，不设 timer，让衰减分支立即接管（约 0.3 秒消失）。
        """
        self._typing_sway_phase = 1.0
        self._typing_sway_amp   = 1.5
        self._typing_bob_phase  = 0.5
        self._typing_bob_amp    = 0.8

    def _reset_walk_timer(self):
        self._auto_walk_timer  = random.uniform(20.0, 45.0)
        self._last_action_time = time.time()
        self._reset_interact_time()

    def _on_anim_done(self, action: str):
        if action == "sleep":
            self.state.is_sleeping     = True
            self.state.current_action  = PetAction.SLEEP
        elif action == "study":
            pass
        else:
            self.state.is_sleeping    = False
            if self._is_snapped:
                self.state.current_action = PetAction.CLING
            elif self._dragging:
                self.state.current_action = PetAction.DRAG
            else:
                self.state.current_action = PetAction.IDLE
            if hasattr(self.animator, 'action_timer'):
                self.animator.action_timer = 0.0
            if hasattr(self.animator, 'auto_action_timer'):
                self.animator.auto_action_timer = random.uniform(5.0, 10.0)

    def _on_feed(self):
        if self.state.is_sleeping:
            self._say("Zzz...正在睡觉呢...", mood="sleepy")
            return
        msg = self.state.feed()
        self.state.current_action = PetAction.EAT
        self.renderer.trigger_priority("eat")
        self._reset_walk_timer()
        self.game.record_action("feed")
        self._say(msg or _pick("pet"), mood=_mood_to_str(self.state.current_mood), trigger_anim=False)
        self.panel.notify_action("feed")

    def _on_pet(self):
        if self.state.is_sleeping:
            self._say("嗯...别闹...在睡觉...", mood="sleepy")
            return
        msg = self.state.pet_touch()
        self.state.current_action = PetAction.PLAY
        self.renderer.trigger_priority("pet")
        self._reset_walk_timer()
        self.game.record_action("pet")
        self._say(msg or _pick("pet"), mood=_mood_to_str(self.state.current_mood), trigger_anim=False)
        self.panel.notify_action("pet")

    def _on_game(self):
        if self.state.is_sleeping:
            self._say("睡着了...别吵我打球...", mood="sleepy")
            return
        self.state.current_action = PetAction.PLAY
        self.renderer.trigger_priority("play")
        self._reset_walk_timer()
        self.game.record_action("play")
        self._say(_pick("game"), mood="happy", trigger_anim=False)
        self.panel.notify_action("play")

    def _on_sleep(self):
        if self.state.is_sleeping:
            self._say("已经在睡觉了哦~", mood="sleepy")
            return
        msg = self.state.sleep()
        self.renderer.trigger_priority("sleep")
        self._reset_walk_timer()
        self._say(msg, mood="sleepy", trigger_anim=False)
        self.game.record_action("sleep")
        self.panel.notify_action("sleep")

    def _on_wake(self):
        if not self.state.is_sleeping:
            self._say("还没睡觉呢~", mood="normal")
            return
        self.renderer.trigger("wake")
        msg = self.state.wake_up()
        self._reset_walk_timer()
        self._say(msg, mood="happy", trigger_anim=False)

    def _on_cat(self):
        if self.state.is_sleeping:
            self._say("Zzz...梦到小鱼干了...", mood="sleepy")
            return
        self.state.current_action = PetAction.CAT
        self.renderer.trigger_priority("cat")
        self._reset_walk_timer()
        self.game.record_action("cat")
        self.state.happiness = min(100, self.state.happiness + 8)
        self._say(_pick("cat"), mood="happy", trigger_anim=False)
        self.panel.notify_action("cat")

    def _on_study(self):
        if self.state.is_sleeping:
            self._say("睡梦中也在学习...才怪", mood="sleepy")
            return
        self.state.current_action = PetAction.STUDY
        self.renderer.trigger_priority("study")
        self._reset_walk_timer()
        self.game.record_action("study")
        self.state.total_study_times += 1
        self.state.energy = max(0, self.state.energy - 5)
        self.state.exp += 5
        self._say(_pick("study"), mood="normal", trigger_anim=False)
        self.panel.notify_action("study")

    def _on_item_used(self, item_id: str, msg: str):
        """使用背包物品：播放道具动画(.pak 已含底图) + RPG浮动数值标签"""
        _ITEM_ANIM = {
            "apple":    "item_apple",
            "cake":     "item_cake",
            "candy":    "item_candy",
            "coffee":   "item_coffee",
            "plush":    "item_plush",
            "star":     "item_star",
            "gift_box": "item_gift",
        }
        if self.state.is_sleeping:
            self._say("Zzz...先让我睡醒再用吧...", mood="sleepy")
            return

        anim = _ITEM_ANIM.get(item_id, "play")

        self.state.current_action = PetAction.EAT
        # 高优先级触发：清除 pending 队列 + 打断当前非道具 oneshot
        self.renderer.trigger_priority(anim)
        self._reset_walk_timer()

        # 道具动画期间压制：自动对话 + 关键词动画 + 气泡 + auto_walk
        self._item_playing = True
        # 根据实际动画帧数计算时长，fallback 2200ms
        _seq = self.renderer._seqs.get(anim)
        _dur = int(_seq.count / _seq.fps * 1000) + 200 if _seq else 2200
        QTimer.singleShot(_dur, self._clear_item_playing)

        # 显示 RPG 斜角爆出数值标签（不弹气泡，避免视觉干扰）
        # 必须保持引用，否则 CPython 立即 GC → QTimer 被销毁 → 动画不播放
        self._active_float_label = FloatLabel(item_id, self._pet_x, self._pet_y, PET_SIZE)
        self._active_float_label.show_float()

    def _clear_item_playing(self) -> None:
        self._item_playing = False

    def _on_rename(self, new_name: str):
        self.state.name = new_name
        self.state.save()
        self._tray.setToolTip(f"{new_name}  右键查看菜单")
        self._say(f"以后就叫我 {new_name} 吧！", mood="happy")

    def _on_action_bubble(self, reply: str):
        """用户执行动作后，AI 的后续回复通过桌宠气泡展示"""
        self._say(reply, mood="happy")

    def _tick_dialogue(self, dt: float):
        # 道具动画播放 / 拖拽 / 吸附期间暂停自动对话
        if (self._item_playing or self._dragging or self._is_snapped
                or self._pomodoro_focusing()):
            return
        # 期待动作期间（5 分钟内）暂停自动对话，避免随机动画干扰用户执行动作
        _pa = getattr(self.panel, '_pending_action', None)
        if _pa is not None and (time.time() - getattr(self.panel, '_pending_action_ts', 0)) < 300:
            return
        self._dialogue_timer -= dt
        if self._dialogue_timer <= 0:
            self._dialogue_timer = random.uniform(20.0, 45.0)
            self._fire_auto_dialogue()
        self._tick_proactive(dt)

    # ── 主动聊天计时 ─────────────────────────────────────────────────
    def _tick_proactive(self, dt: float):
        """检测长时间无互动，触发桌宠主动找用户说话"""
        if self.state.is_sleeping or self._proactive_waiting or self._dragging:
            return

        # 如果用户最近有聊天记录，同步更新互动时间
        recent = self.chat_svc._memory.get("recent", [])
        if recent:
            last_msg = recent[-1]
            msg_ts = last_msg.get("ts", 0)
            if msg_ts > self._last_interact_time:
                self._last_interact_time = msg_ts
                self._proactive_count = 0
                self._proactive_max = 0

        # 冷却中
        if self._proactive_cd > 0:
            self._proactive_cd -= dt
            return

        # 本轮已达上限
        if self._proactive_max > 0 and self._proactive_count >= self._proactive_max:
            return

        # 检查是否空闲足够久（30~45 分钟）
        idle_sec = time.time() - self._last_interact_time
        threshold = 30 * 60  # 30 分钟
        if idle_sec < threshold:
            return

        # API 当日未验证可用则不触发
        if not self.chat_svc.api_ready_today:
            return

        # 首次触发：随机决定本轮最多说几次（1~3）
        if self._proactive_max == 0:
            self._proactive_max = random.randint(1, 3)

        # 发起主动聊天
        self._proactive_waiting = True

        def _cb(reply, error):
            self._proactive_reply.emit(reply or "", error or "")

        self.chat_svc.proactive_chat(pet_state=self.state, callback=_cb)

    def _on_proactive_reply(self, reply: str, error: str):
        """主动聊天 API 回复（主线程）"""
        self._proactive_waiting = False
        if reply and not error:
            self._proactive_count += 1
            self._say(reply, mood="happy")
            # 下次主动说话的冷却：随机 8~15 分钟
            self._proactive_cd = random.uniform(8 * 60, 15 * 60)

    def _fire_auto_dialogue(self):
        if self.state.is_sleeping or self._dragging or self._is_snapped:
            return
        mood_key = _mood_to_dialogue_key(self.state.current_mood)
        if mood_key and random.random() < 0.65:
            category = mood_key
        else:
            category = _time_slot()
        self._say(_pick(category), mood=_mood_to_str(self.state.current_mood))

    # ── 提醒·番茄钟(P1)────────────────────────────────────────────────
    def _on_start_countdown(self, seconds: float, label: str):
        """独立窗口请求开始一个快捷倒计时(前台计时器,替换式)。"""
        if self.pomodoro.active:            # 前台互斥:停掉番茄钟
            self.pomodoro.reset()
            self.reminder_window.set_pomodoro_state(False, False)
            self.reminder_window.set_pomodoro_status("未开始")
        self.countdown.start(seconds, label)
        self._countdown_active = True
        self._countdown_paused = False
        self.reminder_window.set_timer_state(True, False)

    def _on_toggle_pause(self):
        if not self._countdown_active:
            return
        if self._countdown_paused:
            self.countdown.resume()
            self._countdown_paused = False
        else:
            self.countdown.pause()
            self._countdown_paused = True
        self.reminder_window.set_timer_state(True, self._countdown_paused)

    def _on_reset_countdown(self):
        self.countdown.stop()
        self._countdown_active = False
        self._countdown_paused = False
        self.countdown_float.set_text("")
        self.reminder_window.set_timer_state(False, False)

    def _tick_countdown(self):
        """每帧:更新浮窗;暂停时冻结显示;到点弹持久气泡并停。"""
        if not self._countdown_active:
            self.countdown_float.set_text("")
            return
        label = self.countdown.label
        if self._countdown_paused:
            rem = format_remaining(self.countdown.remaining)
            self.countdown_float.set_text(f"⏸ {label} {rem}" if label else f"⏸ {rem}")
            return
        if self.countdown.is_done:
            self._countdown_active = False
            self.countdown.stop()
            self.countdown_float.set_text("")
            text = f"{label} 时间到" if label else "时间到!"
            self.reminder_bubbles.show_bubble(text)
            self.reminder_window.set_timer_state(False, False)
            return
        rem = format_remaining(self.countdown.remaining)
        self.countdown_float.set_text(f"⏰ {label} {rem}" if label else f"⏰ {rem}")

    def _tick_foreground(self):
        """前台计时器(番茄钟 或 快捷倒计时,二选一)驱动头顶浮窗。"""
        if self.pomodoro.active:
            self._tick_pomodoro()
        else:
            self._tick_countdown()

    # ── 番茄钟(P2)─────────────────────────────────────────────────────
    def _on_start_pomodoro(self, cfg: dict):
        if self._countdown_active:          # 前台互斥:停掉快捷倒计时
            self._countdown_active = False
            self._countdown_paused = False
            self.countdown.stop()
            self.reminder_window.set_timer_state(False, False)
        self.pomodoro.cfg.update(cfg)
        reminder_store.save_pomodoro_config(self.pomodoro.cfg)
        self.pomodoro.start()
        self.reminder_window.set_pomodoro_state(True, False)
        self._say("开始专注!我陪你~📖", mood="happy", trigger_anim=False)
        self.renderer.trigger("study")
        self.state.current_action = PetAction.STUDY

    def _on_toggle_pomodoro_pause(self):
        if not self.pomodoro.active:
            return
        if self.pomodoro.paused:
            self.pomodoro.resume()
        else:
            self.pomodoro.pause()
        self.reminder_window.set_pomodoro_state(True, self.pomodoro.paused)

    def _on_reset_pomodoro(self):
        self.pomodoro.reset()
        self.countdown_float.set_text("")
        self.reminder_window.set_pomodoro_state(False, False)
        self.reminder_window.set_pomodoro_status("未开始")

    def _pomodoro_focusing(self) -> bool:
        """番茄钟正处于专注阶段(未暂停)——此时抑制自动走动/说话/睡觉,保持学习姿势。"""
        return (self.pomodoro.active and not self.pomodoro.paused
                and self.pomodoro.phase == FOCUS)

    def _tick_pomodoro(self):
        if self.pomodoro.paused:
            rem = format_remaining(self.pomodoro.remaining)
            self.countdown_float.set_text(f"⏸ {self.pomodoro.label} {rem}")
            self.reminder_window.set_pomodoro_status(f"已暂停 · {self.pomodoro.label}")
            return
        new_phase = self.pomodoro.update()
        if new_phase is not None:
            self._on_pomodoro_phase(new_phase)
        # 专注期间保持学习姿势:被打断回到 idle 时重新埋头
        if (self.pomodoro.phase == FOCUS
                and getattr(self.renderer, "_action", "idle") == "idle"
                and not getattr(self.renderer, "_pending", [])):
            self.renderer.trigger("study")
            self.state.current_action = PetAction.STUDY
        rem = format_remaining(self.pomodoro.remaining)
        self.countdown_float.set_text(f"🍅 {self.pomodoro.label} {rem}")
        self.reminder_window.set_pomodoro_status(
            f"{self.pomodoro.label} · 已完成 {self.pomodoro.completed_focus} 轮专注")

    def _on_pomodoro_phase(self, phase: str):
        """阶段切换:自动淡出气泡播报 + 切桌宠动画(专注=study,休息=wake)。"""
        if phase == FOCUS:
            self._say("休息结束,继续加油!💪", mood="happy", trigger_anim=False)
            self.renderer.trigger("study")
            self.state.current_action = PetAction.STUDY
        else:
            tip = "专注结束,起来活动下~☕" if phase == SHORT_BREAK else "完成一组!好好长休一下~🌟"
            self._say(tip, mood="happy", trigger_anim=False)
            self.renderer.trigger("wake")

    def _restack_above_pet(self):
        """桌宠头顶浮动元素竖直堆叠,避免重叠。
        顺序(贴近头顶→往上):倒计时浮窗 → 聊天气泡 → 到点气泡。
        头顶放不下则改到桌宠下方。"""
        widgets = []
        if self.countdown_float.isVisible():
            widgets.append(self.countdown_float)
        if self.bubble.isVisible():
            widgets.append(self.bubble)
        widgets.extend(self.reminder_bubbles.active_bubbles())
        if not widgets:
            return
        cx = int(self._pet_x + PET_SIZE / 2)
        gap = 6
        total_h = sum(w.height() for w in widgets) + gap * (len(widgets) - 1)
        pet_top = int(self._pet_y)
        if pet_top + 8 - total_h >= 0:
            y = pet_top + 8                       # 最低元素底边,略压头顶
            for w in widgets:
                w.move(int(cx - w.width() / 2), int(y - w.height()))
                y = y - w.height() - gap
        else:
            y = pet_top + PET_SIZE - 8            # 头顶放不下:挪到桌宠下方
            for w in widgets:
                w.move(int(cx - w.width() / 2), int(y))
                y = y + w.height() + gap

    def _show_reminder_window(self):
        self.reminder_window.show()
        self.reminder_window.raise_()
        self.reminder_window.activateWindow()

    def _say(self, text: str, mood: str = "normal", trigger_anim: bool = True):
        # NOTE: 睡觉状态下不弹出任何文字气泡，保持安静沉浸感
        if self.state.is_sleeping:
            return
        # 道具动画播放期间完全静默：不弹气泡、不触发关键词动画
        if self._item_playing:
            return
        self.bubble.show_message(text, duration=3200, mood=mood)
        # NOTE: 根据气泡文字关键词触发对应动画，增强拟人感。
        # renderer 的 ONESHOT_RETURN 动作播完后会自动回 idle，无需手动还原。
        # trigger_anim=False 时跳过：调用方已触发专属动画，避免重复/冲突。
        if trigger_anim:
            self._try_trigger_by_text(text)

    # ── 关键词 → 动画映射 ─────────────────────────────────────────────
    # 格式: (关键词列表, 渲染器动作名)，按优先级从高到低排列。
    # NOTE: 所有关键词至少 2 字，避免单字子串匹配导致误触发。
    # 仅对 trigger_anim=True 的调用生效（自动对话、AI 回复等），
    # 互动按钮触发的 _say 已传入 trigger_anim=False 跳过匹配。
    _KEYWORD_ANIM: list[tuple[tuple[str, ...], str]] = [
        # eat — 饮食相关
        (("喂食", "喂我", "吃饭", "吃东西", "好饿", "肚子饿", "饿了",
          "早饭", "午饭", "晚饭", "早餐", "午餐", "晚餐",
          "零食", "蛋糕", "饺子", "咖啡", "好吃"), "eat"),
        # play — 运动/游戏
        (("羽毛球", "打球", "运动", "玩游戏", "玩耍",
          "锻炼", "竞技", "比赛", "踢球", "打一局"), "play"),
        # pet — 亲密互动
        (("摸摸", "摸头", "抱抱", "贴贴", "蹭蹭", "亲亲",
          "喜欢你", "最喜欢", "好孩子", "真乖", "好可爱", "好舒服"), "pet"),
        # cat — 猫咪
        (("喵喵", "猫咪", "猫猫", "小猫", "学猫", "猫叫",
          "猫粮", "呼噜呼噜", "毛茸茸"), "cat"),
        # study — 学习
        (("学习", "读书", "看书", "写作业", "做作业", "考试",
          "上课", "复习", "预习", "研究"), "study"),
    ]

    def _try_trigger_by_text(self, text: str):
        """
        识别气泡文字关键词，触发对应一次性动画。
        仅在安静 idle（鼠标跟随）状态下触发，打字动画进行中不触发。
        """
        # 睡觉/吸附/拖拽时不打断
        if self.state.is_sleeping or self._is_snapped or self._dragging:
            return
        # 道具动画期间不触发关键词动画
        if self._item_playing:
            return
        # NOTE: 打字状态中不触发关键词动画，避免与键盘互动效果冲突。
        # 关键词动画只适用于鼠标跟随的安静 idle 中。
        if self._typing_anim_timer > 0:
            return
        # 渲染器正在播一次性动作时不叠加，避免动作堆积
        renderer_busy = (
            getattr(self.renderer, "_action", "idle") in
            getattr(self.renderer, "ONESHOT_ALL", set())
        )
        if renderer_busy:
            return
        for keywords, anim in self._KEYWORD_ANIM:
            if any(kw in text for kw in keywords):
                self.renderer.trigger(anim)
                # 同步 state.current_action，让 animator._NO_AUTO 保护生效
                anim_action_map = {
                    "eat":   PetAction.EAT,
                    "play":  PetAction.PLAY,
                    "pet":   PetAction.IDLE,   # pet 无独立 PetAction，用 IDLE 占位
                    "cat":   PetAction.CAT,
                    "study": PetAction.STUDY,
                }
                if anim in anim_action_map:
                    self.state.current_action = anim_action_map[anim]
                return


    # ── 托盘 & 菜单 ─────────────────────────────────────────────────
    def _make_tray_icon(self) -> QIcon:
        from PyQt5.QtGui import QPixmap
        icon = QIcon()
        base_dir = sys._MEIPASS if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
        # 优先使用裁剪后的紧凑托盘图标（无多余留白）
        for name in ("icon_tray.ico", "icon_tray.png", "icon.ico", "icon.png"):
            src_path = os.path.join(base_dir, "icons", name)
            if os.path.exists(src_path):
                if name.endswith(".ico"):
                    icon = QIcon(src_path)
                else:
                    base_px = QPixmap(src_path)
                    if not base_px.isNull():
                        for sz in (16, 24, 32, 48, 64):
                            icon.addPixmap(base_px.scaled(sz, sz,
                                           Qt.KeepAspectRatio,
                                           Qt.SmoothTransformation))
                if not icon.isNull():
                    break
        return icon

    # ── 共用菜单样式（DPI 缩放） ──────────────────────────────────
    def _menu_css(self):
        u = self._ui_scale
        def p(v): return max(1, round(v * u))
        def f(v): return max(7, round(v * u))
        return (
            f"QMenu {{ background:#f5f7fb; border:{max(1,round(1.5*u))}px solid #c8d4e8;"
            f"  border-radius:{p(10)}px; padding:{p(6)}px 0;"
            f"  font-family:'Microsoft YaHei'; font-size:{f(13)}px; }}"
            f"QMenu::item {{ padding:{p(6)}px {p(16)}px; color:#3a4a6a;"
            f"  border-radius:{p(6)}px; margin:{p(1)}px {p(4)}px; }}"
            f"QMenu::item:selected {{ background:#dce8fa; color:#2a5bb5; }}"
            f"QMenu::separator {{ height:1px; background:#dce4f0;"
            f"  margin:{p(4)}px {p(12)}px; }}"
            f"QSlider::groove:horizontal {{ height:{p(4)}px; background:#dce4f0;"
            f"  border-radius:{p(2)}px; }}"
            f"QSlider::handle:horizontal {{ width:{p(12)}px; height:{p(12)}px;"
            f"  margin:-{p(4)}px 0; background:#6a8fd8; border-radius:{p(6)}px; }}"
            f"QSlider::sub-page:horizontal {{ background:#6a8fd8;"
            f"  border-radius:{p(2)}px; }}"
        )

    def _setup_tray(self):
        self._tray = QSystemTrayIcon(self)
        self._tray.setIcon(self._make_tray_icon())
        self._tray.setToolTip("蓝色小嗵  右键查看菜单")
        menu = QMenu()
        menu.setWindowFlags(menu.windowFlags() | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        menu.setAttribute(Qt.WA_TranslucentBackground)
        menu.setStyleSheet(self._menu_css())
        a_panel = QAction("📊 个人中心", self)
        a_panel.triggered.connect(self._show_panel)
        menu.addAction(a_panel)
        a_mem = QAction("📝 记忆管理", self)
        a_mem.triggered.connect(self._open_memory_from_tray)
        menu.addAction(a_mem)
        a_rem = QAction("⏰ 提醒·番茄钟", self)
        a_rem.triggered.connect(self._show_reminder_window)
        menu.addAction(a_rem)
        menu.addSeparator()
        a_quit = QAction("❌ 退出", self); a_quit.triggered.connect(self._quit)
        menu.addAction(a_quit)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _open_memory_from_tray(self):
        """从托盘打开记忆管理 — 关闭时不回退到个人中心"""
        cs = getattr(self.panel, '_cs', None)
        if not cs:
            return
        from src.knowledge_hub import KnowledgeHub
        self._mem_win_tray = KnowledgeHub(cs, parent_panel=None, parent=None)
        self._mem_win_tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.showNormal(); self.raise_(); self.activateWindow()

    def _set_opacity(self, val: int):
        self._opacity_pct = val; self.update()

    def _show_panel(self):
        """在桌宠旁弹出个人中心，确保不超出屏幕且不遮挡桌宠"""
        pw = self.panel.width()
        ph = self.panel.height()
        gap = 25  # 大于桌宠窗口边距(20)，避免窗口重叠

        screen = QApplication.primaryScreen().geometry()
        pet_ix = int(self._pet_x)
        pet_iy = int(self._pet_y)

        # 面板 x：优先放桌宠右边，放不下就放左边
        px = pet_ix + PET_SIZE + gap
        if px + pw > screen.width() - 10:
            px = pet_ix - pw - gap
        px = max(10, min(px, screen.width() - pw - 10))

        # 面板 y：垂直居中对齐桌宠中心
        py = pet_iy + PET_SIZE // 2 - ph // 2
        if py < 10:
            py = max(10, pet_iy)
        py = min(py, screen.height() - ph - 10)

        self.panel.move(px, py)
        self.panel.show()
        self.panel.raise_()

    def _show_context_menu(self, global_pos: QPoint):
        from PyQt5.QtWidgets import QHBoxLayout
        menu = QMenu(self)
        menu.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        menu.setAttribute(Qt.WA_TranslucentBackground)
        menu.setStyleSheet(self._menu_css())
        u = self._ui_scale
        _p = lambda v: max(1, round(v * u))
        _f = lambda v: max(7, round(v * u))
        # ── 日常 ──
        for label, slot in [("🍔 喂食", self._on_feed),
                             ("📖 学习", self._on_study),
                             ("💤 睡觉", self._on_sleep),
                             ("🌅 唤醒", self._on_wake)]:
            a = QAction(label, self); a.triggered.connect(slot); menu.addAction(a)
        menu.addSeparator()
        # ── 不透明度 ──
        ow = QWidget(); ow.setAttribute(Qt.WA_TranslucentBackground)
        ol = QHBoxLayout(ow); ol.setContentsMargins(_p(16), _p(4), _p(16), _p(4))
        lbl = QLabel("不透明度"); lbl.setStyleSheet(f"color:#8a96b0; font-size:{_f(12)}px; background:transparent;")
        sld = QSlider(Qt.Horizontal); sld.setRange(20, 100); sld.setValue(self._opacity_pct)
        sld.setFixedWidth(_p(90)); sld.valueChanged.connect(self._set_opacity)
        ol.addWidget(lbl); ol.addWidget(sld)
        wa = QWidgetAction(self); wa.setDefaultWidget(ow); menu.addAction(wa)
        menu.addSeparator()
        # ── 互动 ──
        for label, slot in [("✋ 摸摸头", self._on_pet),
                             ("🏸 羽毛球", self._on_game),
                             ("🐱 变猫猫", self._on_cat)]:
            a = QAction(label, self); a.triggered.connect(slot); menu.addAction(a)
        menu.addSeparator()
        # ── 底部 ──
        a_p = QAction("📊 个人中心", self)
        a_p.triggered.connect(self._show_panel)
        menu.addAction(a_p)
        # ── 弹出位置：避让桌宠，优先出现在宠物右侧 ──
        msz = menu.sizeHint()
        scr = QApplication.primaryScreen().availableGeometry()
        gap = round(-10 * u)
        pet_r = int(self._pet_x) + PET_SIZE
        pet_l = int(self._pet_x)
        mx = pet_r + gap
        if mx + msz.width() > scr.right():
            mx = pet_l - gap - msz.width()
        mx = max(scr.left(), min(mx, scr.right() - msz.width()))
        my = int(self._pet_y) + PET_SIZE * 2 // 3
        my = max(scr.top(), min(my, scr.bottom() - msz.height()))
        menu.exec_(QPoint(mx, my))

    def _quit(self):
        self.monitor.stop(); self.state.save(); self.game.save(); self.chat_svc.save_config(); QApplication.quit()

    def closeEvent(self, event):
        event.ignore(); self.hide()


def main():
    global PET_SIZE
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    # ── 根据屏幕逻辑高度动态调整桌宠尺寸 ──
    # AA_EnableHighDpiScaling 已按 DPR 缩放逻辑坐标，
    # 此处只需用逻辑高度适配不同物理屏幕，Qt 自动处理 DPR 放大
    _scr = QApplication.primaryScreen()
    if _scr:
        _scale = min(1.0, _scr.geometry().height() / _DESIGN_H)
        PET_SIZE = max(120, int(210 * _scale))
    window = PetWindow()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
