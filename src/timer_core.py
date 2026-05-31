"""计时核心 — 纯逻辑倒计时原语,无 Qt 依赖,可单测。
提醒/番茄钟/快捷倒计时共用。每个实例只关心:剩余、是否到点。
时间基准用 time.monotonic(),免受系统时钟回拨影响(快捷倒计时/番茄钟语义:
数足设定的真实时长)。提醒(P3)走墙钟 due_ts,是另一套机制,不用此原语。
now_fn 可注入,便于单测。
"""
from __future__ import annotations
import time


def format_remaining(seconds: float) -> str:
    """剩余秒数 → MM:SS(<1h)或 H:MM:SS;负数按 0。"""
    s = max(0, int(round(seconds)))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h > 0:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m:02d}:{sec:02d}"


class Countdown:
    def __init__(self, label: str = "", now_fn=time.monotonic):
        self.label = label
        self._now = now_fn
        self._duration = 0.0
        self._end = 0.0
        self._running = False
        self._paused_remaining = 0.0

    def start(self, seconds: float, label: str | None = None) -> None:
        if label is not None:
            self.label = label
        self._duration = max(0.0, float(seconds))
        self._end = self._now() + self._duration
        self._running = True
        self._paused_remaining = 0.0

    @property
    def running(self) -> bool:
        return self._running

    @property
    def remaining(self) -> float:
        if not self._running:
            return self._paused_remaining
        return max(0.0, self._end - self._now())

    @property
    def is_done(self) -> bool:
        return self._running and self.remaining <= 0.0

    @property
    def duration(self) -> float:
        return self._duration

    @property
    def fraction(self) -> float:
        if self._duration <= 0:
            return 1.0
        return min(1.0, max(0.0, 1.0 - self.remaining / self._duration))

    def pause(self) -> None:
        if self._running:
            self._paused_remaining = self.remaining
            self._running = False

    def resume(self) -> None:
        if not self._running and self._paused_remaining > 0:
            self._end = self._now() + self._paused_remaining
            self._running = True
            self._paused_remaining = 0.0

    def stop(self) -> None:
        self._running = False
        self._paused_remaining = 0.0
        self._end = 0.0
