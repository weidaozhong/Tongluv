"""番茄钟状态机 —— 纯逻辑,无 Qt,可单测。
建在 timer_core.Countdown 之上:专注 → 短休 → 专注 …… 第 N 轮专注后进长休。
是一个"前台计时器"(与快捷倒计时二选一,由 main 协调)。
now_fn 可注入便于单测。
"""
from __future__ import annotations
import time

from src.timer_core import Countdown

# 阶段
IDLE = "idle"
FOCUS = "focus"
SHORT_BREAK = "short_break"
LONG_BREAK = "long_break"

_PHASE_LABEL = {FOCUS: "专注", SHORT_BREAK: "短休", LONG_BREAK: "长休"}
_PHASE_MIN_KEY = {
    FOCUS: "focus_min",
    SHORT_BREAK: "short_break_min",
    LONG_BREAK: "long_break_min",
}

DEFAULT_CONFIG = {
    "focus_min": 25,
    "short_break_min": 5,
    "long_break_min": 15,
    "cycles_before_long": 4,
}


class PomodoroTimer:
    def __init__(self, config: dict | None = None, now_fn=time.monotonic):
        self.cfg = dict(DEFAULT_CONFIG)
        if config:
            self.cfg.update(config)
        self._cd = Countdown(now_fn=now_fn)
        self.phase = IDLE
        self.completed_focus = 0   # 本轮已完成的专注次数(用于判断长休)
        self._active = False
        self._paused = False

    # ── 控制 ──────────────────────────────────────────────
    def start(self) -> None:
        """从头开始一个番茄钟(进入专注)。"""
        self.completed_focus = 0
        self._active = True
        self._paused = False
        self._enter(FOCUS)

    def pause(self) -> None:
        if self._active and not self._paused:
            self._cd.pause()
            self._paused = True

    def resume(self) -> None:
        if self._active and self._paused:
            self._cd.resume()
            self._paused = False

    def reset(self) -> None:
        self._cd.stop()
        self.phase = IDLE
        self.completed_focus = 0
        self._active = False
        self._paused = False

    # ── 查询 ──────────────────────────────────────────────
    @property
    def active(self) -> bool:
        return self._active

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def remaining(self) -> float:
        return self._cd.remaining

    @property
    def label(self) -> str:
        return _PHASE_LABEL.get(self.phase, "")

    # ── 推进(每秒由 main 调)─────────────────────────────
    def update(self) -> str | None:
        """当前阶段到点则切到下一阶段,返回新阶段名(供 main 播报/换动画);否则 None。"""
        if not self._active or self._paused:
            return None
        if self._cd.is_done:
            return self._advance()
        return None

    # ── 内部 ──────────────────────────────────────────────
    def _enter(self, phase: str) -> None:
        self.phase = phase
        mins = self.cfg[_PHASE_MIN_KEY[phase]]
        self._cd.start(mins * 60, _PHASE_LABEL[phase])

    def _advance(self) -> str:
        if self.phase == FOCUS:
            self.completed_focus += 1
            if self.completed_focus % self.cfg["cycles_before_long"] == 0:
                self._enter(LONG_BREAK)
            else:
                self._enter(SHORT_BREAK)
        else:
            # 休息结束 → 回到专注
            self._enter(FOCUS)
        return self.phase
