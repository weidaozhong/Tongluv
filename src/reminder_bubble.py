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
