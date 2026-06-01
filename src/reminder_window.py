"""提醒·番茄钟 独立窗口。
窗体/配色/缩放沿用 StatusPanel、MemoryWindow:暖色卡片、圆角、Microsoft YaHei。
左右两栏:快捷倒计时(左半) | 番茄钟(右半),不用滚动条。
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QLineEdit, QGridLayout, QSizePolicy,
                             QApplication)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal
from PyQt5.QtGui import QFont, QIntValidator
from src.status_panel import BG, CARD, CARD2, BD, T1, T2, T3, TB
from src.pomodoro import DEFAULT_CONFIG

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
    # 快捷倒计时
    start_countdown = pyqtSignal(float, str)   # 秒, 待完成事件
    toggle_pause    = pyqtSignal()
    reset_timer     = pyqtSignal()
    # 番茄钟
    start_pomodoro        = pyqtSignal(dict)   # 时长配置
    toggle_pomodoro_pause = pyqtSignal()
    reset_pomodoro        = pyqtSignal()

    _BASE_W, _BASE_H = 730, 470

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        scr = QApplication.primaryScreen()
        logical_h = scr.geometry().height() if scr else 1440
        global _scale
        _scale = min(1.0, logical_h / _DESIGN_H)
        self.W = max(480, int(self._BASE_W * _scale))
        self.H = max(360, int(self._BASE_H * _scale))
        self.setFixedSize(self.W, self.H)
        self._dp = QPoint(); self._dg = False
        g = scr.geometry()
        self.move((g.width() - self.W) // 2, (g.height() - self.H) // 2)
        self._build()
        self.set_timer_state(False, False)
        self.set_pomodoro_state(False, False)

    # ── 拖拽移动 ──
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

    # ── 整体布局 ──
    def _build(self):
        root = QWidget(self); root.setGeometry(0, 0, self.W, self.H)
        root.setObjectName("RR")
        root.setStyleSheet(
            f"QWidget#RR{{background:{BG};border-radius:{_s(20)}px;border:1.5px solid {BD};}}")
        ml = QVBoxLayout(root)
        ml.setContentsMargins(_s(16), _s(14), _s(16), _s(14)); ml.setSpacing(_s(10))

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

        # 左右两栏:快捷倒计时 | 番茄钟
        cards = QHBoxLayout(); cards.setSpacing(_s(12))
        qc = self._build_quick_card()
        pc = self._build_pomodoro_card()
        for c in (qc, pc):
            c.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        cards.addWidget(qc, 1)
        cards.addWidget(pc, 1)
        ml.addLayout(cards, 1)

    # ── 快捷倒计时分区(左)──
    def _build_quick_card(self):
        card = QWidget(); card.setObjectName("QC")
        card.setStyleSheet(f"QWidget#QC{{background:{CARD};border-radius:{_s(14)}px;border:1px solid {BD};}}")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(_s(14), _s(12), _s(14), _s(14)); cl.setSpacing(_s(10))
        cl.addWidget(_lbl("⏱ 快捷倒计时", 11, T1, True))

        grid = QGridLayout(); grid.setSpacing(_s(8))
        for i, (label, secs) in enumerate(
                [("5 分", 300), ("10 分", 600), ("15 分", 900), ("30 分", 1800)]):
            b = QPushButton(label); b.setFixedHeight(_s(42)); b.setCursor(Qt.PointingHandCursor)
            b.setFont(QFont("Microsoft YaHei", _fs(11), QFont.Bold))
            b.setStyleSheet(self._soft_css())
            b.clicked.connect(lambda _, sec=secs: self.start_countdown.emit(float(sec), ""))
            grid.addWidget(b, i // 2, i % 2)
        cl.addLayout(grid)

        cl.addWidget(_lbl("自定义", 10, T2))
        hms = QHBoxLayout(); hms.setSpacing(_s(4))
        self._h_inp = self._num_input()
        self._m_inp = self._num_input()
        self._s_inp = self._num_input()
        for inp, unit in ((self._h_inp, "时"), (self._m_inp, "分"), (self._s_inp, "秒")):
            hms.addWidget(inp); hms.addWidget(_lbl(unit, 10, T2))
        hms.addStretch()
        cl.addLayout(hms)

        ev_row = QHBoxLayout(); ev_row.setSpacing(_s(6))
        ev_row.addWidget(_lbl("待完成事件", 10, T2))
        self._lbl_inp = QLineEdit(); self._lbl_inp.setStyleSheet(self._input_css())
        ev_row.addWidget(self._lbl_inp, 1)
        cl.addLayout(ev_row)

        sb = QPushButton("开始"); sb.setFixedHeight(_s(42)); sb.setCursor(Qt.PointingHandCursor)
        sb.setFont(QFont("Microsoft YaHei", _fs(11), QFont.Bold))
        sb.setStyleSheet(self._primary_css())
        sb.clicked.connect(self._start_custom)
        cl.addWidget(sb)

        ctrl = QHBoxLayout(); ctrl.setSpacing(_s(8))
        self._pause_btn = self._mk_ctrl_btn("暂停", lambda _: self.toggle_pause.emit())
        self._reset_btn = self._mk_ctrl_btn("重置", lambda _: self.reset_timer.emit())
        ctrl.addWidget(self._pause_btn); ctrl.addWidget(self._reset_btn)
        cl.addLayout(ctrl)
        cl.addStretch()
        return card

    # ── 番茄钟分区(右)──
    def _build_pomodoro_card(self):
        card = QWidget(); card.setObjectName("PC")
        card.setStyleSheet(f"QWidget#PC{{background:{CARD};border-radius:{_s(14)}px;border:1px solid {BD};}}")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(_s(14), _s(12), _s(14), _s(14)); cl.setSpacing(_s(10))
        title_row = QHBoxLayout()
        title_row.addWidget(_lbl("🍅 番茄钟", 11, T1, True))
        title_row.addStretch()
        rb = QPushButton("↺"); rb.setFixedSize(_s(24), _s(24))
        rb.setCursor(Qt.PointingHandCursor); rb.setToolTip("重置为默认时长")
        rb.setStyleSheet(
            f"QPushButton{{background:transparent;color:{T3};border:none;"
            f"font-size:{_s(16)}px;border-radius:{_s(12)}px;}}"
            f"QPushButton:hover{{background:{CARD2};color:{TB};}}")
        rb.clicked.connect(lambda _: self.set_pomodoro_config(DEFAULT_CONFIG))
        title_row.addWidget(rb)
        cl.addLayout(title_row)

        pgrid = QGridLayout(); pgrid.setSpacing(_s(8))
        for i, (label, cfg) in enumerate([
                ("经典 25/5", (25, 5, 15, 4)),
                ("深度 50/10", (50, 10, 20, 3)),
                ("轻量 15/3", (15, 3, 10, 4)),
                ("长时 45/15", (45, 15, 25, 2))]):
            b = QPushButton(label); b.setFixedHeight(_s(42)); b.setCursor(Qt.PointingHandCursor)
            b.setFont(QFont("Microsoft YaHei", _fs(10), QFont.Bold))
            b.setStyleSheet(self._soft_css())
            f, sh, lo, cy = cfg
            b.setToolTip(f"专注 {f} · 短休 {sh} · 长休 {lo} · 每 {cy} 轮长休")
            b.clicked.connect(lambda _, c=cfg: self._apply_pomo_preset(c))
            pgrid.addWidget(b, i // 2, i % 2)
        cl.addLayout(pgrid)

        self._foc_inp = self._num_input("25")
        self._sht_inp = self._num_input("5")
        self._lng_inp = self._num_input("15")
        self._cyc_inp = self._num_input("4")

        row1 = QHBoxLayout(); row1.setSpacing(_s(4))
        row1.addWidget(_lbl("专注", 10, T2)); row1.addWidget(self._foc_inp); row1.addWidget(_lbl("分", 10, T3))
        row1.addSpacing(_s(12))
        row1.addWidget(_lbl("短休", 10, T2)); row1.addWidget(self._sht_inp); row1.addWidget(_lbl("分", 10, T3))
        row1.addStretch()
        cl.addLayout(row1)

        row2 = QHBoxLayout(); row2.setSpacing(_s(4))
        row2.addWidget(_lbl("长休", 10, T2)); row2.addWidget(self._lng_inp); row2.addWidget(_lbl("分", 10, T3))
        row2.addSpacing(_s(12))
        row2.addWidget(_lbl("每", 10, T2)); row2.addWidget(self._cyc_inp); row2.addWidget(_lbl("轮后长休", 10, T3))
        row2.addStretch()
        cl.addLayout(row2)

        sb = QPushButton("开始专注"); sb.setFixedHeight(_s(42)); sb.setCursor(Qt.PointingHandCursor)
        sb.setFont(QFont("Microsoft YaHei", _fs(11), QFont.Bold))
        sb.setStyleSheet(self._primary_css())
        sb.clicked.connect(self._start_pomodoro)
        cl.addWidget(sb)

        ctrl = QHBoxLayout(); ctrl.setSpacing(_s(8))
        self._pomo_pause_btn = self._mk_ctrl_btn("暂停", lambda _: self.toggle_pomodoro_pause.emit())
        self._pomo_reset_btn = self._mk_ctrl_btn("重置", lambda _: self.reset_pomodoro.emit())
        ctrl.addWidget(self._pomo_pause_btn); ctrl.addWidget(self._pomo_reset_btn)
        cl.addLayout(ctrl)

        self._pomo_status = _lbl("未开始", 10, T3)
        self._pomo_status.setAlignment(Qt.AlignCenter)
        cl.addWidget(self._pomo_status)
        cl.addStretch()
        return card

    # ── 样式 / 小工具 ──
    def _soft_css(self):
        return (f"QPushButton{{background:{BG};color:{T1};border:1px solid {BD};border-radius:{_s(10)}px;}}"
                f"QPushButton:hover{{background:{CARD2};border:1px solid {TB};}}")

    def _primary_css(self):
        return (f"QPushButton{{background:{TB};color:white;border:none;border-radius:{_s(12)}px;}}"
                f"QPushButton:hover{{background:#b06838;}}")

    def _ctrl_css(self):
        return (f"QPushButton{{background:{BG};color:{T1};border:1px solid {BD};border-radius:{_s(10)}px;}}"
                f"QPushButton:hover{{background:{CARD2};border:1px solid {TB};}}"
                f"QPushButton:disabled{{background:{CARD2};color:{T3};border:1px solid {BD};}}")

    def _input_css(self):
        return (f"QLineEdit{{background:white;color:{T1};border:1px solid {BD};"
                f"border-radius:{_s(8)}px;padding:{_s(6)}px {_s(8)}px;"
                f"font-family:'Microsoft YaHei';font-size:{_s(11)}px;}}"
                f"QLineEdit:focus{{border:1px solid {TB};}}")

    def _mk_ctrl_btn(self, text, slot):
        b = QPushButton(text); b.setFixedHeight(_s(38)); b.setCursor(Qt.PointingHandCursor)
        b.setFont(QFont("Microsoft YaHei", _fs(10), QFont.Bold))
        b.setStyleSheet(self._ctrl_css())
        b.clicked.connect(slot)
        return b

    def _num_input(self, prefill=""):
        e = QLineEdit()
        if prefill:
            e.setText(prefill)
        e.setFixedWidth(_s(46)); e.setAlignment(Qt.AlignCenter)
        e.setStyleSheet(self._input_css())
        e.setValidator(QIntValidator(0, 999, self))
        return e

    # ── 状态同步(供 main 调)──
    def set_timer_state(self, active: bool, paused: bool):
        self._pause_btn.setEnabled(active)
        self._reset_btn.setEnabled(active)
        self._pause_btn.setText("继续" if paused else "暂停")

    def set_pomodoro_state(self, active: bool, paused: bool):
        self._pomo_pause_btn.setEnabled(active)
        self._pomo_reset_btn.setEnabled(active)
        self._pomo_pause_btn.setText("继续" if paused else "暂停")

    def set_pomodoro_status(self, text: str):
        self._pomo_status.setText(text)

    def set_pomodoro_config(self, cfg: dict):
        self._foc_inp.setText(str(cfg.get("focus_min", 25)))
        self._sht_inp.setText(str(cfg.get("short_break_min", 5)))
        self._lng_inp.setText(str(cfg.get("long_break_min", 15)))
        self._cyc_inp.setText(str(cfg.get("cycles_before_long", 4)))

    def _apply_pomo_preset(self, cfg):
        f, sh, lo, cy = cfg
        self._foc_inp.setText(str(f)); self._sht_inp.setText(str(sh))
        self._lng_inp.setText(str(lo)); self._cyc_inp.setText(str(cy))

    # ── 触发 ──
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

    def _start_pomodoro(self):
        def _v(e, d):
            try:
                v = int(e.text().strip())
                return v if v > 0 else d
            except ValueError:
                return d
        cfg = {
            "focus_min":          _v(self._foc_inp, 25),
            "short_break_min":    _v(self._sht_inp, 5),
            "long_break_min":     _v(self._lng_inp, 15),
            "cycles_before_long": _v(self._cyc_inp, 4),
        }
        self.start_pomodoro.emit(cfg)
