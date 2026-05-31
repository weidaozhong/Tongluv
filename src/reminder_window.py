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
