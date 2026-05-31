# P1:计时核心 + 快捷倒计时 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 跑通"计时核心 + 头顶浮窗 + 持久气泡 + 最小独立窗口"这套地基,以最简单的快捷倒计时作为第一个消费者验证它。

**Architecture:** 纯逻辑 `Countdown`(无 Qt、可单测)作底层计时;三个 Qt 小部件(头顶浮窗、持久气泡、独立窗口)各司其职;`main.py` 作编排者,在既有 60fps 主循环里检测到点、随桌宠移动浮窗、到点弹气泡。后续 P2 番茄钟 / P3 提醒复用同一套地基。

**Tech Stack:** Python 3.14、PyQt5。测试:stdlib `unittest`(纯逻辑)+ 导入冒烟 + 运行程序观察(GUI)。

**测试取向(已按项目现状裁剪):** 本项目无测试基建、无 pytest,GUI 历来靠运行观察。故:`timer_core`(纯逻辑)写真正的 `unittest`;Qt 部件用 `python -c "import ..."` 冒烟(抓导入/语法错)+ 末尾运行程序做行为验证。不为 GUI 硬造假单测。

**UI 强约束:** 新部件视觉必须与现有 `StatusPanel`/`MemoryWindow`/`bubble_widget` 一致 —— 复用配色 token(`BG/CARD/CARD2/BD/T1/T2/T3/TB`)、DPI 缩放、Microsoft YaHei、圆角与间距。气泡/浮窗为暖色药丸,窗口为暖色卡片,不引入新审美。

---

## 文件结构

| 文件 | 职责 | 新建/改动 |
|---|---|---|
| `src/timer_core.py` | 纯逻辑倒计时原语 `Countdown` + `format_remaining()` | 新建 |
| `tests/test_timer_core.py` | `Countdown`/`format_remaining` 单测(注入假时钟) | 新建 |
| `tests/__init__.py` | 让 tests 成为包 | 新建(空) |
| `src/countdown_float.py` | 桌宠头顶倒计时浮窗(显示型,不可点) | 新建 |
| `src/reminder_bubble.py` | 持久可点击气泡 `ReminderBubble` + 堆叠管理 `ReminderBubbleManager` | 新建 |
| `src/reminder_window.py` | 独立窗口(P1 只放快捷倒计时) | 新建 |
| `main.py` | 编排:持有上述对象、每秒检测、浮窗随桌宠移动、到点弹气泡、托盘入口 | 改动 |

---

## Task 1:计时核心 `timer_core.py`(TDD)

**Files:**
- Create: `tests/__init__.py`、`tests/test_timer_core.py`
- Create: `src/timer_core.py`

- [ ] **Step 1:写失败测试**

`tests/__init__.py` 留空。`tests/test_timer_core.py`:

```python
import unittest
from src.timer_core import Countdown, format_remaining


class FakeClock:
    def __init__(self, t=1000.0):
        self.t = t
    def __call__(self):
        return self.t
    def advance(self, dt):
        self.t += dt


class TestFormatRemaining(unittest.TestCase):
    def test_under_hour(self):
        self.assertEqual(format_remaining(0), "00:00")
        self.assertEqual(format_remaining(65), "01:05")
        self.assertEqual(format_remaining(599), "09:59")
    def test_over_hour(self):
        self.assertEqual(format_remaining(3661), "1:01:01")
    def test_negative_clamps_zero(self):
        self.assertEqual(format_remaining(-5), "00:00")
    def test_rounds(self):
        self.assertEqual(format_remaining(59.6), "01:00")


class TestCountdown(unittest.TestCase):
    def test_start_and_remaining(self):
        clk = FakeClock()
        c = Countdown(now_fn=clk)
        c.start(10, "喝水")
        self.assertEqual(c.label, "喝水")
        self.assertTrue(c.running)
        self.assertAlmostEqual(c.remaining, 10.0)
        self.assertFalse(c.is_done)
        self.assertAlmostEqual(c.fraction, 0.0)

    def test_counts_down(self):
        clk = FakeClock()
        c = Countdown(now_fn=clk)
        c.start(10)
        clk.advance(4)
        self.assertAlmostEqual(c.remaining, 6.0)
        self.assertAlmostEqual(c.fraction, 0.4)
        clk.advance(6)
        self.assertAlmostEqual(c.remaining, 0.0)
        self.assertTrue(c.is_done)
        self.assertAlmostEqual(c.fraction, 1.0)

    def test_remaining_never_negative(self):
        clk = FakeClock()
        c = Countdown(now_fn=clk)
        c.start(5)
        clk.advance(99)
        self.assertEqual(c.remaining, 0.0)

    def test_pause_resume(self):
        clk = FakeClock()
        c = Countdown(now_fn=clk)
        c.start(10)
        clk.advance(3)
        c.pause()
        self.assertFalse(c.running)
        self.assertAlmostEqual(c.remaining, 7.0)
        clk.advance(100)               # 暂停期间时钟走动不影响
        self.assertAlmostEqual(c.remaining, 7.0)
        c.resume()
        self.assertTrue(c.running)
        clk.advance(7)
        self.assertTrue(c.is_done)

    def test_stop(self):
        clk = FakeClock()
        c = Countdown(now_fn=clk)
        c.start(10)
        c.stop()
        self.assertFalse(c.running)
        self.assertFalse(c.is_done)
        self.assertEqual(c.remaining, 0.0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2:运行,确认失败**

Run: `python -m unittest tests.test_timer_core -v`
Expected: FAIL / ERROR —— `ModuleNotFoundError: No module named 'src.timer_core'`

- [ ] **Step 3:写最小实现** `src/timer_core.py`:

```python
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
```

- [ ] **Step 4:运行,确认通过**

Run: `python -m unittest tests.test_timer_core -v`
Expected: PASS(9 项全过)

- [ ] **Step 5:提交**

```bash
git add src/timer_core.py tests/__init__.py tests/test_timer_core.py
git commit -m "feat: 计时核心 Countdown 原语 + 单测"
```

---

## Task 2:头顶倒计时浮窗 `countdown_float.py`

**Files:**
- Create: `src/countdown_float.py`

显示型小药丸(暖色,与气泡同语言),不可点(`WindowTransparentForInput`),随桌宠移动。

- [ ] **Step 1:写实现** `src/countdown_float.py`:

```python
"""桌宠头顶倒计时浮窗 —— 显示当前前台/最近的倒计时。
显示型(不接收点击),随桌宠移动(复用 bubble.update_position 思路)。
配色取自 status_panel 设计 token,保证与现有界面一致。
"""
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import (QPainter, QColor, QFont, QFontMetrics,
                         QPainterPath, QBrush, QPen)
from src.status_panel import CARD, TB, T1

_DESIGN_H = 1440


class CountdownFloat(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint |
            Qt.Tool | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        scr = QApplication.primaryScreen()
        self._scale = min(1.0, scr.geometry().height() / _DESIGN_H) if scr else 1.0
        self._font_sz = max(8, round(11 * self._scale))
        self._text = ""
        self._visible = False

    def set_text(self, text: str):
        """设置文字(如 '⏰ 喝水 04:59');空串隐藏。"""
        if text == self._text and self._visible == bool(text):
            return
        self._text = text
        if not text:
            self._visible = False
            self.hide()
            return
        fm = QFontMetrics(QFont("Microsoft YaHei", self._font_sz, QFont.Bold))
        tw = fm.horizontalAdvance(text) + round(28 * self._scale)
        th = fm.height() + round(12 * self._scale)
        self.setFixedSize(max(tw, round(72 * self._scale)), th)
        self._visible = True
        self.show()
        self.update()

    def update_position(self, pet_x, pet_y, pet_w):
        bx = int(pet_x + pet_w / 2 - self.width() / 2)
        by = int(pet_y - self.height() - round(2 * self._scale))
        if by < 0:
            by = int(pet_y + pet_w + round(2 * self._scale))
        self.move(bx, by)

    def paintEvent(self, _):
        if not self._visible or not self._text:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(2, 2, -2, -2)
        rad = r.height() / 2.0
        path = QPainterPath()
        path.addRoundedRect(float(r.x()), float(r.y()),
                            float(r.width()), float(r.height()), rad, rad)
        p.setBrush(QBrush(QColor(CARD)))
        p.setPen(QPen(QColor(TB), max(1.0, 1.5 * self._scale)))
        p.drawPath(path)
        p.setPen(QColor(T1))
        p.setFont(QFont("Microsoft YaHei", self._font_sz, QFont.Bold))
        p.drawText(r, Qt.AlignCenter, self._text)
```

- [ ] **Step 2:导入冒烟**

Run: `python -c "import src.countdown_float; print('ok')"`
Expected: 打印 `ok`,无异常(抓语法/导入错)。

- [ ] **Step 3:提交**

```bash
git add src/countdown_float.py
git commit -m "feat: 桌宠头顶倒计时浮窗 CountdownFloat"
```

---

## Task 3:持久可点击气泡 `reminder_bubble.py`

**Files:**
- Create: `src/reminder_bubble.py`

与聊天气泡的区别:**不加** `WindowTransparentForInput`(可点)、**无**淡出定时器(不自动消失)、支持多个堆叠。

- [ ] **Step 1:写实现** `src/reminder_bubble.py`:

```python
"""到点提醒气泡 —— 持久、可点击关闭、可堆叠。
区别于聊天气泡(bubble_widget):不自动淡出、可接收点击、支持堆叠。
由"提醒到点"与"快捷倒计时到 0"共用。配色取自 status_panel token。
"""
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import Qt, QRect, pyqtSignal
from PyQt5.QtGui import (QPainter, QColor, QFont, QFontMetrics,
                         QPainterPath, QBrush, QPen)
from src.status_panel import CARD, TB, T1, T2

_DESIGN_H = 1440


class ReminderBubble(QWidget):
    closed = pyqtSignal(object)   # 发出自身,供管理器回收

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        # 不加 WindowTransparentForInput → 可点击
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setCursor(Qt.PointingHandCursor)
        scr = QApplication.primaryScreen()
        self._scale = min(1.0, scr.geometry().height() / _DESIGN_H) if scr else 1.0
        self._fs_main = max(8, round(11 * self._scale))
        self._fs_hint = max(7, round(8 * self._scale))
        self._text = text
        self._hint = "点击关闭"
        self._build_size()

    def _build_size(self):
        fmain = QFont("Microsoft YaHei", self._fs_main, QFont.Bold)
        fhint = QFont("Microsoft YaHei", self._fs_hint)
        wm = QFontMetrics(fmain).horizontalAdvance("⏰ " + self._text)
        wh = QFontMetrics(fhint).horizontalAdvance(self._hint)
        tw = max(wm, wh) + round(34 * self._scale)
        th = (QFontMetrics(fmain).height() + QFontMetrics(fhint).height()
              + round(24 * self._scale))
        self.setFixedSize(max(tw, round(100 * self._scale)), th)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.closed.emit(self)
            self.close()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(3, 3, -3, -3)
        rad = round(14 * self._scale)
        path = QPainterPath()
        path.addRoundedRect(float(r.x()), float(r.y()),
                            float(r.width()), float(r.height()), rad, rad)
        p.setBrush(QBrush(QColor(CARD)))
        p.setPen(QPen(QColor(TB), max(1.0, 1.8 * self._scale)))  # 橙棕边:提示到点
        p.drawPath(path)
        # 主行:⏰ 事件
        fmain = QFont("Microsoft YaHei", self._fs_main, QFont.Bold)
        p.setPen(QColor(T1)); p.setFont(fmain)
        hm = QFontMetrics(fmain).height()
        top = QRect(r.x(), r.y() + round(7 * self._scale), r.width(), hm)
        p.drawText(top, Qt.AlignCenter, "⏰ " + self._text)
        # 次行:点击关闭
        fhint = QFont("Microsoft YaHei", self._fs_hint)
        p.setPen(QColor(T2)); p.setFont(fhint)
        hh = QFontMetrics(fhint).height()
        bot = QRect(r.x(), r.bottom() - round(7 * self._scale) - hh, r.width(), hh)
        p.drawText(bot, Qt.AlignCenter, self._hint)


class ReminderBubbleManager:
    """管理多个到点气泡:桌宠上方往上堆叠。位置由 main 每帧调 reposition 更新。"""
    def __init__(self):
        self._bubbles = []

    def show_bubble(self, text: str) -> ReminderBubble:
        b = ReminderBubble(text)
        b.closed.connect(self._on_closed)
        self._bubbles.append(b)
        b.show()
        b.raise_()
        return b

    def _on_closed(self, b):
        if b in self._bubbles:
            self._bubbles.remove(b)

    def reposition(self, pet_x, pet_y, pet_w):
        # 最新的在最上面;从桌宠正上方往上叠
        y = pet_y
        for b in self._bubbles:
            bx = int(pet_x + pet_w / 2 - b.width() / 2)
            y = y - b.height() - round(6 * b._scale)
            b.move(bx, int(y))

    def has_active(self) -> bool:
        return bool(self._bubbles)
```

- [ ] **Step 2:导入冒烟**

Run: `python -c "import src.reminder_bubble; print('ok')"`
Expected: 打印 `ok`。

- [ ] **Step 3:提交**

```bash
git add src/reminder_bubble.py
git commit -m "feat: 持久可点击提醒气泡 + 堆叠管理"
```

---

## Task 4:独立窗口 `reminder_window.py`(P1 仅快捷倒计时)

**Files:**
- Create: `src/reminder_window.py`

无边框 `Tool` 窗,沿用 `MemoryWindow` 的窗体外观与拖拽;暖色卡片;预设按钮 + 自定义分钟 + 可选标签 + 开始。

- [ ] **Step 1:写实现** `src/reminder_window.py`:

```python
"""提醒·番茄钟 独立窗口 —— P1 只放快捷倒计时。
窗体/配色/缩放沿用 StatusPanel、MemoryWindow:暖色卡片、圆角、Microsoft YaHei。
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QLineEdit, QGridLayout, QApplication)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal
from PyQt5.QtGui import QFont
from src.status_panel import BG, CARD, CARD2, BD, T1, T2, T3, TB

_DESIGN_H = 1440
_scale = 1.0


def _s(px):
    return max(1, round(px * _scale))


def _fs(pt):
    return max(7, round(pt * _scale))


def _lbl(text, pt, color, bold=False):
    l = QLabel(text)
    f = QFont("Microsoft YaHei", _fs(pt)); f.setBold(bold)
    l.setFont(f)
    l.setStyleSheet(f"color:{color};background:transparent;border:none;")
    return l


class ReminderWindow(QWidget):
    start_countdown = pyqtSignal(float, str)   # 秒, 标签

    _BASE_W, _BASE_H = 400, 470

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        scr = QApplication.primaryScreen()
        logical_h = scr.geometry().height() if scr else 1440
        global _scale
        _scale = min(1.0, logical_h / _DESIGN_H)
        self.W = max(300, int(self._BASE_W * _scale))
        self.H = max(340, int(self._BASE_H * _scale))
        self.setFixedSize(self.W, self.H)
        self._dp = QPoint(); self._dg = False
        g = scr.geometry()
        self.move((g.width() - self.W) // 2, (g.height() - self.H) // 2)
        self._build()

    # 拖拽移动
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._dg = True; self._dp = e.globalPos() - self.frameGeometry().topLeft()
    def mouseMoveEvent(self, e):
        if self._dg and e.buttons() == Qt.LeftButton:
            self.move(e.globalPos() - self._dp)
    def mouseReleaseEvent(self, _):
        self._dg = False
    def paintEvent(self, _):
        pass

    def _build(self):
        root = QWidget(self); root.setGeometry(0, 0, self.W, self.H)
        root.setObjectName("RR")
        root.setStyleSheet(
            f"QWidget#RR{{background:{BG};border-radius:{_s(20)}px;border:1.5px solid {BD};}}")
        ml = QVBoxLayout(root)
        ml.setContentsMargins(_s(16), _s(14), _s(16), _s(14)); ml.setSpacing(_s(12))

        # 标题栏
        h = QHBoxLayout()
        h.addWidget(_lbl("⏰ 提醒 · 番茄钟", 13, T1, True)); h.addStretch()
        cb = QPushButton("✕"); cb.setFixedSize(_s(28), _s(28))
        cb.setCursor(Qt.PointingHandCursor)
        cb.setStyleSheet(
            f"QPushButton{{background:transparent;color:{T3};border:none;"
            f"font-size:{_s(14)}px;border-radius:{_s(14)}px;}}"
            f"QPushButton:hover{{background:{CARD2};color:{T2};}}")
        cb.clicked.connect(self.close); h.addWidget(cb)
        ml.addLayout(h)

        # 快捷倒计时卡片
        card = QWidget(); card.setObjectName("QC")
        card.setStyleSheet(
            f"QWidget#QC{{background:{CARD};border-radius:{_s(14)}px;border:1px solid {BD};}}")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(_s(14), _s(12), _s(14), _s(14)); cl.setSpacing(_s(10))
        cl.addWidget(_lbl("⏱ 快捷倒计时", 11, T1, True))

        grid = QGridLayout(); grid.setSpacing(_s(8))
        for i, (label, secs) in enumerate(
                [("5 分", 300), ("10 分", 600), ("15 分", 900), ("25 分", 1500)]):
            b = QPushButton(label); b.setFixedHeight(_s(42))
            b.setCursor(Qt.PointingHandCursor)
            b.setFont(QFont("Microsoft YaHei", _fs(11), QFont.Bold))
            b.setStyleSheet(
                f"QPushButton{{background:{BG};color:{T1};border:1px solid {BD};"
                f"border-radius:{_s(10)}px;}}"
                f"QPushButton:hover{{background:{CARD2};border:1px solid {TB};}}")
            b.clicked.connect(lambda _, sec=secs: self.start_countdown.emit(float(sec), ""))
            grid.addWidget(b, i // 2, i % 2)
        cl.addLayout(grid)

        cl.addWidget(_lbl("自定义", 10, T2))
        row = QHBoxLayout(); row.setSpacing(_s(6))
        self._min_inp = QLineEdit(); self._min_inp.setPlaceholderText("分钟")
        self._min_inp.setFixedWidth(_s(70)); self._min_inp.setStyleSheet(self._input_css())
        self._lbl_inp = QLineEdit(); self._lbl_inp.setPlaceholderText("标签(可选,如 泡茶)")
        self._lbl_inp.setStyleSheet(self._input_css())
        row.addWidget(self._min_inp); row.addWidget(self._lbl_inp, 1)
        cl.addLayout(row)

        sb = QPushButton("开始"); sb.setFixedHeight(_s(42))
        sb.setCursor(Qt.PointingHandCursor)
        sb.setFont(QFont("Microsoft YaHei", _fs(11), QFont.Bold))
        sb.setStyleSheet(
            f"QPushButton{{background:{TB};color:white;border:none;border-radius:{_s(12)}px;}}"
            f"QPushButton:hover{{background:#b06838;}}")
        sb.clicked.connect(self._start_custom)
        cl.addWidget(sb)

        ml.addWidget(card)
        ml.addStretch()

    def _input_css(self):
        return (f"QLineEdit{{background:white;color:{T1};border:1px solid {BD};"
                f"border-radius:{_s(8)}px;padding:{_s(6)}px {_s(8)}px;"
                f"font-family:'Microsoft YaHei';font-size:{_s(11)}px;}}"
                f"QLineEdit:focus{{border:1px solid {TB};}}")

    def _start_custom(self):
        try:
            mins = float(self._min_inp.text().strip())
        except ValueError:
            return
        if mins <= 0:
            return
        label = self._lbl_inp.text().strip()
        self._min_inp.clear(); self._lbl_inp.clear()
        self.start_countdown.emit(mins * 60.0, label)
```

- [ ] **Step 2:导入冒烟**

Run: `python -c "import src.reminder_window; print('ok')"`
Expected: 打印 `ok`。

- [ ] **Step 3:提交**

```bash
git add src/reminder_window.py
git commit -m "feat: 提醒窗口(P1 快捷倒计时:预设/自定义/标签)"
```

---

## Task 5:`main.py` 接线 + 托盘入口 + 整体验证

**Files:**
- Modify: `main.py`(导入区、`PetWindow.__init__`、`_tick`、`_setup_tray`,新增 `_on_start_countdown`/`_tick_countdown`/`_show_reminder_window`)

- [ ] **Step 1:加导入**

在 `main.py` 现有 `from src.snap_system import ...` 一行之后加:

```python
from src.timer_core import Countdown, format_remaining
from src.countdown_float import CountdownFloat
from src.reminder_bubble import ReminderBubbleManager
from src.reminder_window import ReminderWindow
```

- [ ] **Step 2:`__init__` 里创建对象并接信号**

在 `self.panel = StatusPanel(...)` 一行之后加:

```python
        # ── 提醒·番茄钟模块(P1:快捷倒计时)──
        self.countdown        = Countdown()
        self._countdown_active = False
        self.countdown_float  = CountdownFloat()
        self.reminder_bubbles = ReminderBubbleManager()
        self.reminder_window  = ReminderWindow()
        self.reminder_window.start_countdown.connect(self._on_start_countdown)
```

- [ ] **Step 3:`_tick` 里驱动倒计时 + 跟随定位**

在 `_tick` 中 `self.bubble.update_position(self._pet_x, self._pet_y, PET_SIZE)` 一行之后加:

```python
        self._tick_countdown()
        self.countdown_float.update_position(self._pet_x, self._pet_y, PET_SIZE)
        self.reminder_bubbles.reposition(self._pet_x, self._pet_y, PET_SIZE)
```

- [ ] **Step 4:新增三个方法**(放在 `_say` 方法之前,与其它 `_on_*` 同区):

```python
    # ── 提醒·番茄钟(P1)────────────────────────────────────────────────
    def _on_start_countdown(self, seconds: float, label: str):
        """独立窗口请求开始一个快捷倒计时(前台计时器,替换式)。"""
        self.countdown.start(seconds, label)
        self._countdown_active = True

    def _tick_countdown(self):
        """每帧:更新浮窗;到点弹持久气泡并停。"""
        if not self._countdown_active:
            self.countdown_float.set_text("")
            return
        if self.countdown.is_done:
            self._countdown_active = False
            label = self.countdown.label
            self.countdown.stop()
            self.countdown_float.set_text("")
            text = f"{label} 时间到" if label else "时间到!"
            self.reminder_bubbles.show_bubble(text)
            return
        label = self.countdown.label
        rem = format_remaining(self.countdown.remaining)
        self.countdown_float.set_text(f"⏰ {label} {rem}" if label else f"⏰ {rem}")

    def _show_reminder_window(self):
        self.reminder_window.show()
        self.reminder_window.raise_()
        self.reminder_window.activateWindow()
```

- [ ] **Step 5:托盘加入口**

在 `_setup_tray` 中,`a_mem`(记忆管理)那两行之后、`menu.addSeparator()` 之前加:

```python
        a_rem = QAction("⏰ 提醒·番茄钟", self)
        a_rem.triggered.connect(self._show_reminder_window)
        menu.addAction(a_rem)
```

- [ ] **Step 6:导入冒烟 + 单测回归**

Run: `python -c "import main; print('ok')"`
Expected: 打印 `ok`(无导入/语法错)。

Run: `python -m unittest tests.test_timer_core -v`
Expected: 仍 PASS。

- [ ] **Step 7:运行程序,人工验证(P1 验收标准)**

Run: `python main.py`

依次确认:
1. 托盘右键 → 「⏰ 提醒·番茄钟」→ 弹出暖色窗口,风格与个人中心一致、不突兀。
2. 点「5 分」→ 桌宠头顶出现药丸浮窗,`⏰ 04:59` 起每秒递减。
3. 自定义填 `0.1` 分(6 秒)+ 标签「泡茶」→ 点开始 → 浮窗显示 `⏰ 泡茶 0:05…` 递减。
4. 到 0 → 浮窗消失,桌宠上方弹出 `⏰ 泡茶 时间到` 气泡,带「点击关闭」,**不自动消失**。
5. 点该气泡 → 关闭。
6. 拖动桌宠 → 浮窗/气泡跟随移动。

- [ ] **Step 8:提交**

```bash
git add main.py
git commit -m "feat: main 接入快捷倒计时(浮窗/到点气泡/托盘入口)"
```

---

## 自检(Self-Review)

**Spec 覆盖(P1 部分):**
- 计时核心 → Task 1 ✓
- 头顶浮窗 → Task 2 ✓
- 持久可点击气泡(到点不消失、点击关、堆叠)→ Task 3 ✓
- 最小独立窗口(快捷倒计时:预设/自定义/可选标签)→ Task 4 ✓
- main 接线(每秒检测、浮窗随桌宠移动、到点弹气泡、托盘入口)→ Task 5 ✓
- 验收标准(点 5 分→倒数→到 0 弹持久气泡点击关)→ Task 5 Step 7 ✓
- `user_data.py` 的 `reminder_data_path()`:P1 快捷倒计时为临时态、无持久化需求,按 YAGNI **推迟到 P2/P3**(届时才有配置/列表要落盘)。

**占位符扫描:** 无 TBD/TODO;每个改动步骤均含完整代码与确切命令。

**类型/签名一致性:**
- `Countdown(now_fn=...)`、`.start(seconds, label)`、`.remaining`、`.is_done`、`.stop()`、`.label` —— Task 1 定义,Task 5 调用一致。
- `format_remaining(seconds)` —— Task 1 定义,Task 5 调用一致。
- `CountdownFloat.set_text/update_position` —— Task 2 定义,Task 5 调用一致。
- `ReminderBubbleManager.show_bubble/reposition` —— Task 3 定义,Task 5 调用一致。
- `ReminderWindow.start_countdown(float, str)` 信号 —— Task 4 定义,Task 5 `_on_start_countdown(seconds, label)` 槽签名一致。

**已知小取舍(不阻塞 P1,后续打磨):** 聊天气泡与倒计时浮窗位置可能短暂重叠;P1 不处理避让,留待后续。
