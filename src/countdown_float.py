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
