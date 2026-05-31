"""提醒·番茄钟 独立窗口 —— P1 只放快捷倒计时。
窗体/配色/缩放沿用 StatusPanel、MemoryWindow:暖色卡片、圆角、Microsoft YaHei。
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QLineEdit, QGridLayout, QApplication)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal
from PyQt5.QtGui import QFont, QIntValidator
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
    toggle_pause    = pyqtSignal()
    reset_timer     = pyqtSignal()

    _BASE_W, _BASE_H = 400, 540

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        scr = QApplication.primaryScreen()
        logical_h = scr.geometry().height() if scr else 1440
        global _scale
        _scale = min(1.0, logical_h / _DESIGN_H)
        self.W = max(300, int(self._BASE_W * _scale))
        self.H = max(380, int(self._BASE_H * _scale))
        self.setFixedSize(self.W, self.H)
        self._dp = QPoint(); self._dg = False
        g = scr.geometry()
        self.move((g.width() - self.W) // 2, (g.height() - self.H) // 2)
        self._build()
        self.set_timer_state(False, False)

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

        # 预设
        grid = QGridLayout(); grid.setSpacing(_s(8))
        for i, (label, secs) in enumerate(
                [("5 分", 300), ("10 分", 600), ("15 分", 900), ("30 分", 1800)]):
            b = QPushButton(label); b.setFixedHeight(_s(42))
            b.setCursor(Qt.PointingHandCursor)
            b.setFont(QFont("Microsoft YaHei", _fs(11), QFont.Bold))
            b.setStyleSheet(self._preset_css())
            b.clicked.connect(lambda _, sec=secs: self.start_countdown.emit(float(sec), ""))
            grid.addWidget(b, i // 2, i % 2)
        cl.addLayout(grid)

        # 自定义:时 / 分 / 秒(直接填,无需换算)
        cl.addWidget(_lbl("自定义", 10, T2))
        hms = QHBoxLayout(); hms.setSpacing(_s(4))
        self._h_inp = self._num_input()
        self._m_inp = self._num_input()
        self._s_inp = self._num_input()
        for inp, unit in ((self._h_inp, "时"), (self._m_inp, "分"), (self._s_inp, "秒")):
            hms.addWidget(inp); hms.addWidget(_lbl(unit, 10, T2))
        hms.addStretch()
        cl.addLayout(hms)

        # 标签
        lab_row = QHBoxLayout(); lab_row.setSpacing(_s(6))
        lab_row.addWidget(_lbl("标签", 10, T2))
        self._lbl_inp = QLineEdit()
        self._lbl_inp.setStyleSheet(self._input_css())
        lab_row.addWidget(self._lbl_inp, 1)
        cl.addLayout(lab_row)

        # 开始(启动一个新倒计时)
        sb = QPushButton("开始"); sb.setFixedHeight(_s(42))
        sb.setCursor(Qt.PointingHandCursor)
        sb.setFont(QFont("Microsoft YaHei", _fs(11), QFont.Bold))
        sb.setStyleSheet(
            f"QPushButton{{background:{TB};color:white;border:none;border-radius:{_s(12)}px;}}"
            f"QPushButton:hover{{background:#b06838;}}")
        sb.clicked.connect(self._start_custom)
        cl.addWidget(sb)

        # 暂停/重置(控制进行中的倒计时)
        ctrl = QHBoxLayout(); ctrl.setSpacing(_s(8))
        self._pause_btn = QPushButton("暂停"); self._pause_btn.setFixedHeight(_s(38))
        self._pause_btn.setCursor(Qt.PointingHandCursor)
        self._pause_btn.setFont(QFont("Microsoft YaHei", _fs(10), QFont.Bold))
        self._pause_btn.setStyleSheet(self._ctrl_css())
        self._pause_btn.clicked.connect(lambda _: self.toggle_pause.emit())
        self._reset_btn = QPushButton("重置"); self._reset_btn.setFixedHeight(_s(38))
        self._reset_btn.setCursor(Qt.PointingHandCursor)
        self._reset_btn.setFont(QFont("Microsoft YaHei", _fs(10), QFont.Bold))
        self._reset_btn.setStyleSheet(self._ctrl_css())
        self._reset_btn.clicked.connect(lambda _: self.reset_timer.emit())
        ctrl.addWidget(self._pause_btn); ctrl.addWidget(self._reset_btn)
        cl.addLayout(ctrl)

        ml.addWidget(card)
        ml.addStretch()

    # ── 样式 ──
    def _preset_css(self):
        return (f"QPushButton{{background:{BG};color:{T1};border:1px solid {BD};"
                f"border-radius:{_s(10)}px;}}"
                f"QPushButton:hover{{background:{CARD2};border:1px solid {TB};}}")

    def _ctrl_css(self):
        return (f"QPushButton{{background:{BG};color:{T1};border:1px solid {BD};"
                f"border-radius:{_s(10)}px;}}"
                f"QPushButton:hover{{background:{CARD2};border:1px solid {TB};}}"
                f"QPushButton:disabled{{background:{CARD2};color:{T3};border:1px solid {BD};}}")

    def _input_css(self):
        return (f"QLineEdit{{background:white;color:{T1};border:1px solid {BD};"
                f"border-radius:{_s(8)}px;padding:{_s(6)}px {_s(8)}px;"
                f"font-family:'Microsoft YaHei';font-size:{_s(11)}px;}}"
                f"QLineEdit:focus{{border:1px solid {TB};}}")

    def _num_input(self):
        e = QLineEdit()
        e.setFixedWidth(_s(50)); e.setAlignment(Qt.AlignCenter)
        e.setStyleSheet(self._input_css())
        e.setValidator(QIntValidator(0, 999, self))
        return e

    # ── 状态:供 main 同步暂停/重置按钮 ──
    def set_timer_state(self, active: bool, paused: bool):
        self._pause_btn.setEnabled(active)
        self._reset_btn.setEnabled(active)
        self._pause_btn.setText("继续" if paused else "暂停")

    def _start_custom(self):
        def _v(e):
            t = e.text().strip()
            return int(t) if t else 0
        total = _v(self._h_inp) * 3600 + _v(self._m_inp) * 60 + _v(self._s_inp)
        if total <= 0:
            return
        label = self._lbl_inp.text().strip()
        self._h_inp.clear(); self._m_inp.clear(); self._s_inp.clear()
        self._lbl_inp.clear()
        self.start_countdown.emit(float(total), label)
