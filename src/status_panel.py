"""
个人中心面板 — 多 Tab（状态 | 任务 | 背包 | 商店 | 成就 | 聊天 | 设置）
"""
import os, sys, re, html as _html_mod
from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QPoint, QTimer, QEvent
from PyQt5.QtGui import (QFont, QColor, QPainter, QLinearGradient, QBrush,
                          QPainterPath, QPen, QPixmap)
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QInputDialog, QFileDialog, QSizePolicy, QApplication,
    QGridLayout, QLineEdit, QScrollArea, QMessageBox,
)
from src.knowledge_hub import _MultiLineInput

# URL 正则（与 chat_service 保持一致）
_URL_RE  = re.compile(r"https?://\S+", re.IGNORECASE)
_TRAIL   = '.,;:!?\'"），。！？；：、'


def _text_to_html(text):
    """纯文本 → HTML：URL 转可点击链接，换行转 <br>"""
    parts = _URL_RE.split(text)
    urls  = _URL_RE.findall(text)
    out   = []
    for i, part in enumerate(parts):
        out.append(_html_mod.escape(part).replace("\n", "<br>"))
        if i < len(urls):
            u = urls[i].rstrip(_TRAIL)
            short = u if len(u) <= 46 else u[:43] + "…"
            out.append(
                f'<a href="{u}" style="color:#4a7cc7;text-decoration:underline;">'
                f'{_html_mod.escape(short)}</a>'
            )
    return "".join(out)

BG = "#fdf6f0"; CARD = "#fff8f3"; CARD2 = "#f5ede4"
BD = "#e8d8cc"; BD2 = "#d4c4b8"
T1 = "#5a4035"; T2 = "#8a7060"; T3 = "#c4a898"
TB = "#c4784a"; BGB = "#f0e8e0"; ACC = "#b09480"
CH = ("#f0b060","#f8d090"); CHP = ("#f0c850","#f8e080")
CE = ("#70c8c8","#a0e8e8"); CI = ("#f080a8","#f8b0c8"); CX = ("#c4a8d8","#a088c8")
MC = {"happy":"#7cc8a0","normal":"#5ba8d4","sad":"#7070c0",
      "hungry":"#e0a060","sleepy":"#c488d8","sleeping":"#c488d8"}
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from src.user_data import avatar_path as _avatar_path
AVATAR_SAVE = _avatar_path()
ATTR_W = 96

def _asset(n):
    b = os.path.dirname(sys.executable) if getattr(sys,"frozen",False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(b, n)

# ── 工具控件 ────────────────────────────────────────────────
class AvatarWidget(QWidget):
    clicked = pyqtSignal()
    def __init__(self, sz=64, parent=None):
        super().__init__(parent); self._sz=sz; self.setFixedSize(sz+6,sz+6)
        self._px=None; self._mc=QColor(MC["normal"]); self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("点击更换头像"); self._load()
    def _load(self):
        for p in [_asset(AVATAR_SAVE), _asset(os.path.join("assets","animations","idle_0000.png")), _asset(os.path.join("icons","icon.png"))]:
            if os.path.exists(p):
                px=QPixmap(p)
                # NOTE: KeepAspectRatioByExpanding 会让某边超出 sz，改用 KeepAspectRatio 并手动居中，
                # 确保图片始终完整显示在圆圈内且视觉居中
                if not px.isNull(): self._px=px.scaled(self._sz,self._sz,Qt.KeepAspectRatio,Qt.SmoothTransformation); return
    def load_custom(self,path):
        px=QPixmap(path)
        if not px.isNull():
            self._px=px.scaled(self._sz,self._sz,Qt.KeepAspectRatio,Qt.SmoothTransformation)
            self._px.save(_asset(AVATAR_SAVE),"PNG"); self.update()
    def set_mood(self,k): self._mc=QColor(MC.get(k,"#5ba8d4")); self.update()
    def paintEvent(self,_):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing); p.setRenderHint(QPainter.SmoothPixmapTransform)
        s=self._sz; o=3
        # 绘制彩色圆圈边框
        p.setPen(QPen(self._mc,3)); p.setBrush(Qt.NoBrush)
        p.drawEllipse(o//2, o//2, s+o, s+o)
        # 裁剪到圆形区域
        cl=QPainterPath(); cl.addEllipse(QRectF(o,o,s,s)); p.setClipPath(cl)
        if self._px:
            # 精确居中：以圆心为基准，图片居中绘制
            px_w, px_h = self._px.width(), self._px.height()
            draw_x = o + (s - px_w) // 2
            draw_y = o + (s - px_h) // 2
            p.drawPixmap(draw_x, draw_y, self._px)
        p.end()
    def mousePressEvent(self,e):
        if e.button()==Qt.LeftButton: self.clicked.emit()

class GradBar(QWidget):
    def __init__(self,cs,ce,parent=None):
        super().__init__(parent); self._v=80; self._cs=cs; self._ce=ce
        self.setFixedHeight(10); self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
    def set_value(self,v): self._v=max(0,min(100,v)); self.update()
    def paintEvent(self,_):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w,h,r=self.width(),self.height(),self.height()/2
        p.setPen(Qt.NoPen); p.setBrush(QColor(CARD2)); p.drawRoundedRect(0,0,w,h,r,r)
        fw=max(int(w*self._v/100),h)
        g=QLinearGradient(0,0,fw,0); g.setColorAt(0,QColor(self._cs)); g.setColorAt(1,QColor(self._ce))
        p.setBrush(QBrush(g)); p.drawRoundedRect(0,0,fw,h,r,r); p.end()

def _div():
    f=QFrame(); f.setFixedHeight(1); f.setStyleSheet(f"background:{BD};border:none;"); return f

def _lbl(t="",sz=12,c=T1,bold=False):
    lb=QLabel(t); f=QFont("Microsoft YaHei",sz); f.setBold(bold); lb.setFont(f)
    lb.setStyleSheet(f"color:{c};background:transparent;border:none;padding:0;margin:0;"); return lb

def _ibtn(icon,label):
    b=QPushButton(f"{icon}\n{label}"); b.setFixedHeight(52); b.setFont(QFont("Microsoft YaHei",9))
    b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    b.setStyleSheet(f"QPushButton{{background:{CARD};color:{T2};border:1.5px solid {BD};border-radius:10px;padding:4px 0;}}"
                    f"QPushButton:hover{{background:{BGB};border-color:{BD2};color:{T1};}}"
                    f"QPushButton:pressed{{background:{CARD2};}}")
    return b

def _clear_layout(layout):
    """递归清除 layout 内所有 widget 和子 layout"""
    if layout is None:
        return
    while layout.count():
        it = layout.takeAt(0)
        w = it.widget()
        if w:
            w.setParent(None)
            w.deleteLater()
        sub = it.layout()
        if sub:
            _clear_layout(sub)

# ══════════════════════════════════════════════════════════════
#  独立记忆管理窗口
# ══════════════════════════════════════════════════════════════
class MemoryWindow(QWidget):
    MW, MH = 400, 560

    def __init__(self, chat_service, parent=None):
        super().__init__(parent)
        self._cs = chat_service
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(self.MW, self.MH)
        self._dp = QPoint(); self._dg = False
        # 居中显示
        from PyQt5.QtWidgets import QApplication
        scr = QApplication.primaryScreen().geometry()
        self.move((scr.width() - self.MW) // 2, (scr.height() - self.MH) // 2)
        self._build()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton: self._dg = True; self._dp = e.globalPos() - self.frameGeometry().topLeft()
    def mouseMoveEvent(self, e):
        if self._dg and e.buttons() == Qt.LeftButton: self.move(e.globalPos() - self._dp)
    def mouseReleaseEvent(self, _): self._dg = False

    def _build(self):
        root = QWidget(self); root.setGeometry(0, 0, self.MW, self.MH); root.setObjectName("MR")
        root.setStyleSheet(f"QWidget#MR{{background:{BG};border-radius:20px;border:1.5px solid {BD};}}")
        ml = QVBoxLayout(root); ml.setContentsMargins(16, 14, 16, 12); ml.setSpacing(0)

        # 标题栏
        h = QHBoxLayout()
        h.addWidget(_lbl("📝 记忆管理", 13, T1, True)); h.addStretch()
        mi = self._cs.get_memory_info()
        self._stat_lbl = _lbl(f"{mi['facts_count']} 条记忆", 10, T3)
        h.addWidget(self._stat_lbl); h.addSpacing(8)
        cb = QPushButton("✕"); cb.setFixedSize(28, 28)
        cb.setStyleSheet(f"QPushButton{{background:transparent;color:{T3};border:none;font-size:14px;border-radius:14px;}}"
                         f"QPushButton:hover{{background:{CARD2};color:{T2};}}")
        cb.clicked.connect(self.close); h.addWidget(cb)
        ml.addLayout(h); ml.addSpacing(10)

        # 记忆列表（可滚动）
        self._mem_widget = QWidget()
        self._mem_widget.setStyleSheet("background:transparent;border:none;")
        self._mem_layout = QVBoxLayout(self._mem_widget)
        self._mem_layout.setContentsMargins(4, 4, 4, 4)
        self._mem_layout.setSpacing(4)

        sa = QScrollArea(); sa.setWidgetResizable(True)
        sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sa.setStyleSheet(
            f"QScrollArea{{border:1px solid {BD};border-radius:12px;background:{CARD};}}"
            f"QScrollBar:vertical{{width:5px;background:{CARD2};}}"
            f"QScrollBar::handle:vertical{{background:{BD};border-radius:2px;}}"
            f"QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0px;}}")
        sa.setWidget(self._mem_widget)
        ml.addWidget(sa, 1)

        self._rebuild()

        # 添加记忆
        ml.addSpacing(10)
        ml.addWidget(_lbl("手动添加记忆", 10, T2)); ml.addSpacing(4)
        ar = QHBoxLayout(); ar.setSpacing(6)
        self._inp = _MultiLineInput("输入想让它记住的内容…")
        self._inp.submitted.connect(self._add)
        ar.addWidget(self._inp, 1)
        ab = QPushButton("添加"); ab.setFixedSize(56, 36)
        ab.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        ab.setStyleSheet(
            f"QPushButton{{background:#e8d0c0;color:{T1};border:none;border-radius:10px;}}"
            f"QPushButton:hover{{background:#dcc0b0;}}")
        ab.clicked.connect(self._add); ar.addWidget(ab)
        ml.addLayout(ar)

        # 清空按钮
        ml.addSpacing(10)
        clr = QPushButton("清除所有记忆"); clr.setFixedHeight(36)
        clr.setFont(QFont("Microsoft YaHei", 10))
        clr.setStyleSheet(
            f"QPushButton{{background:#fbe9e7;color:#c62828;border:1px solid #ef9a9a;"
            f"border-radius:10px;padding:0 16px;}}"
            f"QPushButton:hover{{background:#ffcdd2;}}")
        clr.clicked.connect(self._clear_all)
        cr = QHBoxLayout(); cr.addWidget(clr); cr.addStretch()
        ml.addLayout(cr)

    def _rebuild(self):
        while self._mem_layout.count():
            it = self._mem_layout.takeAt(0)
            if it.widget(): it.widget().deleteLater()

        facts = self._cs.get_facts()
        mi = self._cs.get_memory_info()
        self._stat_lbl.setText(f"{mi['facts_count']} 条记忆")

        if not facts:
            empty = _lbl("暂无记忆，说说你的喜好让我记住吧~", 10, T3)
            empty.setAlignment(Qt.AlignCenter); empty.setWordWrap(True)
            self._mem_layout.addWidget(empty)
        else:
            for idx, fact in enumerate(reversed(facts)):
                real_idx = len(facts) - 1 - idx
                row = QHBoxLayout(); row.setContentsMargins(10, 4, 8, 4); row.setSpacing(8)
                txt = QLabel(fact)
                txt.setFont(QFont("Microsoft YaHei", 10))
                txt.setWordWrap(True)
                txt.setStyleSheet(f"color:{T1};background:transparent;border:none;padding:0;")
                del_btn = QPushButton("×"); del_btn.setFixedSize(24, 24)
                del_btn.setFont(QFont("Arial", 12, QFont.Bold))
                del_btn.setStyleSheet(
                    f"QPushButton{{background:transparent;color:{T3};border:none;"
                    f"border-radius:12px;}}"
                    f"QPushButton:hover{{background:#fde8e8;color:#c62828;}}")
                del_btn.clicked.connect(lambda _, i=real_idx: self._del(i))
                row.addWidget(txt, 1); row.addWidget(del_btn, 0, Qt.AlignTop)
                w = QWidget()
                w.setStyleSheet(f"background:{CARD};border-radius:10px;border:none;")
                w.setLayout(row)
                self._mem_layout.addWidget(w)
        self._mem_layout.addStretch()

    def _add(self):
        text = self._inp.toPlainText().strip()
        if not text: return
        self._cs.manual_add_fact(text)
        self._inp.clear()
        self._rebuild()

    def _del(self, index):
        self._cs.manual_remove_fact(index)
        self._rebuild()

    def _clear_all(self):
        ret = QMessageBox.question(
            self, "清除记忆",
            "确定要清除桌宠的所有记忆吗？\n这将删除所有对话历史和关于主人的记忆。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if ret == QMessageBox.Yes:
            self._cs.clear_memory()
            self._rebuild()

    def paintEvent(self, _): pass


# ══════════════════════════════════════════════════════════════
class StatusPanel(QWidget):
    feed_clicked=pyqtSignal(); sleep_clicked=pyqtSignal(); wake_clicked=pyqtSignal()
    pet_clicked=pyqtSignal(); game_clicked=pyqtSignal()
    cat_clicked=pyqtSignal(); study_clicked=pyqtSignal()
    rename_requested=pyqtSignal(str)
    item_used=pyqtSignal(str, str)
    _chat_reply_signal=pyqtSignal(str, str)  # reply, error
    _test_result_signal=pyqtSignal(str)    # status text

    PW, PH = 420, 820

    def __init__(self, game_systems=None, chat_service=None, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowStaysOnTopHint|Qt.Tool|Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(self.PW, self.PH)
        self._dp=QPoint(); self._dg=False
        self._gs=game_systems; self._cs=chat_service; self._ps=None
        # 首次使用时自动打开设置页引导用户填 API Key
        self._tab = "settings" if (chat_service and chat_service.is_first_launch) else "status"
        self._chat_reply_signal.connect(self._on_chat_reply)
        self._test_result_signal.connect(self._on_test_result)
        self._pending_typing_lbl=None
        self._build()

    def mousePressEvent(self,e):
        if e.button()==Qt.LeftButton: self._dg=True; self._dp=e.globalPos()-self.frameGeometry().topLeft()
    def mouseMoveEvent(self,e):
        if self._dg and e.buttons()==Qt.LeftButton: self.move(e.globalPos()-self._dp)
    def mouseReleaseEvent(self,_): self._dg=False

    def _build(self):
        root=QWidget(self); root.setGeometry(0,0,self.PW,self.PH); root.setObjectName("R")
        root.setStyleSheet(f"QWidget#R{{background:{BG};border-radius:20px;border:1.5px solid {BD};}}")
        ml=QVBoxLayout(root); ml.setContentsMargins(16,14,16,12); ml.setSpacing(0)

        # 标题
        h=QHBoxLayout(); h.addWidget(_lbl("个人中心",12,T3))
        h.addStretch()
        self._coin=_lbl("🪙 0",12,TB,True); h.addWidget(self._coin); h.addSpacing(8)
        cb=QPushButton("✕"); cb.setFixedSize(28,28)
        cb.setStyleSheet(f"QPushButton{{background:transparent;color:{T3};border:none;font-size:14px;border-radius:14px;}}"
                         f"QPushButton:hover{{background:{CARD2};color:{T2};}}")
        cb.clicked.connect(self.hide); h.addWidget(cb)
        ml.addLayout(h); ml.addSpacing(8)

        # Tab 栏
        tr=QHBoxLayout(); tr.setSpacing(2)
        self._tbs={}
        for tid,nm in [("status","状态"),("tasks","任务"),("bag","背包"),("shop","商店"),("ach","成就"),("chat","聊天"),("settings","设置")]:
            tb=QPushButton(nm); tb.setFixedHeight(30); tb.setFont(QFont("Microsoft YaHei",10))
            tb.setCursor(Qt.PointingHandCursor)
            tb.clicked.connect(lambda _=None,t=tid: self._go(t))
            tr.addWidget(tb); self._tbs[tid]=tb
        ml.addLayout(tr); ml.addSpacing(8)
        self._style_tabs()

        # 内容区容器
        self._container=QWidget()
        self._container.setStyleSheet("background:transparent;border:none;")
        self._cl=QVBoxLayout(self._container)
        self._cl.setContentsMargins(0,0,0,0); self._cl.setSpacing(6)
        ml.addWidget(self._container,1)
        # 根据 _tab 初始页
        {"status":self._pg_status,"settings":self._pg_settings}.get(self._tab, self._pg_status)()

    def _style_tabs(self):
        for tid,tb in self._tbs.items():
            if tid==self._tab:
                tb.setStyleSheet(f"QPushButton{{background:#e8d0c0;color:{T1};border:none;border-radius:8px;font-weight:bold;padding:2px 6px;}}")
            else:
                tb.setStyleSheet(f"QPushButton{{background:transparent;color:{T2};border:none;border-radius:8px;padding:2px 6px;}}"
                                 f"QPushButton:hover{{background:#f0e4d8;}}")

    def _go(self,t):
        self._tab=t; self._style_tabs(); self._clear()
        {"status":self._pg_status,"tasks":self._pg_tasks,"bag":self._pg_bag,
         "shop":self._pg_shop,"ach":self._pg_ach,"chat":self._pg_chat,
         "settings":self._pg_settings}[t]()

    def _clear(self):
        _clear_layout(self._cl)

    # ════════════════════  状态页  ════════════════════════════
    def _pg_status(self):
        L=self._cl

        # NOTE: 将状态页全部内容包在可滚动区域中，避免内容过多时互相挤压
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet(
            f"QScrollArea{{border:none;background:transparent;}}"
            f"QScrollBar:vertical{{width:5px;background:{CARD2};}}"
            f"QScrollBar::handle:vertical{{background:{BD};border-radius:2px;}}"
            f"QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0px;}}")
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background:transparent;border:none;")
        S = QVBoxLayout(scroll_content)
        S.setContentsMargins(0, 0, 4, 0)
        S.setSpacing(0)

        # 头像行
        hr=QHBoxLayout(); hr.setSpacing(14)
        self._avatar=AvatarWidget(64); self._avatar.clicked.connect(self._pick_av)
        # NOTE: AlignVCenter 让头像在头像行内垂直居中，避免贴顶显示
        hr.addWidget(self._avatar,0,Qt.AlignVCenter)
        ic=QVBoxLayout(); ic.setSpacing(4)
        nr=QHBoxLayout(); nr.setSpacing(4)
        self.name_label=_lbl("嗵",15,T1,True)
        self.name_label.setSizePolicy(QSizePolicy.Preferred,QSizePolicy.Preferred)
        rb=QPushButton("✏"); rb.setFixedSize(20,20)
        rb.setStyleSheet(f"QPushButton{{background:transparent;color:{T3};border:none;font-size:11px;}}"
                         f"QPushButton:hover{{color:{ACC};}}")
        rb.clicked.connect(self._rename); nr.addWidget(self.name_label); nr.addWidget(rb); nr.addStretch()
        ic.addLayout(nr)
        self.mood_label=_lbl("😊 开心",11,T2); ic.addWidget(self.mood_label)
        self._lv=_lbl("⭐ Lv.1",10,TB)
        self._lv.setStyleSheet(f"color:{TB};background:{BGB};border:none;border-radius:8px;padding:2px 8px;")
        lc=QHBoxLayout(); lc.addWidget(self._lv); lc.addStretch(); ic.addLayout(lc)
        hr.addLayout(ic)
        S.addLayout(hr); S.addSpacing(4)

        # 心情色环图例
        ring_row = QHBoxLayout(); ring_row.setSpacing(4)
        ring_row.setContentsMargins(0, 0, 0, 0)
        for color, mood_name in [
            ("#7cc8a0", "开心"), ("#5ba8d4", "普通"), ("#7070c0", "难过"),
            ("#e0a060", "饥饿"), ("#c488d8", "困倦"),
        ]:
            dot = QLabel("●")
            dot.setFont(QFont("Microsoft YaHei", 7))
            dot.setStyleSheet(f"color:{color};background:transparent;border:none;padding:0;margin:0;")
            ring_row.addWidget(dot)
            mood_lbl = QLabel(mood_name)
            mood_lbl.setFont(QFont("Microsoft YaHei", 8))
            mood_lbl.setStyleSheet(f"color:{T3};background:transparent;border:none;padding:0;margin:0;")
            ring_row.addWidget(mood_lbl)
        ring_row.addStretch()
        S.addLayout(ring_row); S.addSpacing(8)

        # 经验
        er=QHBoxLayout(); er.addWidget(_lbl("经验值",10,T3)); er.addStretch()
        self._ev=_lbl("0/100",10,T3); er.addWidget(self._ev)
        S.addLayout(er); S.addSpacing(3)
        self._eb=GradBar(*CX); S.addWidget(self._eb); S.addSpacing(4)

        # 经验获取提示
        exp_tip = _lbl("💡 陪伴自动积累 · 📖学习+5 · ⭐经验星+20 · 📅签到奖励", 8, T3)
        exp_tip.setWordWrap(True)
        exp_tip.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        exp_tip.setStyleSheet(
            f"color:{T3};background:{CARD};border:1px dashed {BD};"
            f"border-radius:8px;padding:4px 8px;margin:0;")
        S.addWidget(exp_tip); S.addSpacing(10)
        S.addWidget(_div()); S.addSpacing(8)

        # 签到
        sr=QHBoxLayout()
        self._sb=QPushButton("📅 签到"); self._sb.setFixedHeight(34); self._sb.setFont(QFont("Microsoft YaHei",11))
        self._sb.setStyleSheet(f"QPushButton{{background:#e8f5e9;color:#388e3c;border:1.5px solid #a5d6a7;border-radius:10px;padding:0 16px;}}"
                               f"QPushButton:hover{{background:#c8e6c9;}}"
                               f"QPushButton:disabled{{background:{CARD2};color:{T3};border-color:{BD};}}")
        self._sb.clicked.connect(self._sign)
        self._si=_lbl("",10,T3); sr.addWidget(self._sb); sr.addSpacing(8); sr.addWidget(self._si,1)
        S.addLayout(sr); S.addSpacing(8); S.addWidget(_div()); S.addSpacing(8)

        # 属性
        S.addWidget(_lbl("属性",11,T3)); S.addSpacing(6)
        self._bars={}; self._vl={}
        for label_text,colors,key in [("饱食度",CH,"hunger"),("心情值",CHP,"happy"),("体力值",CE,"energy"),("亲密度",CI,"intimacy")]:
            row=QHBoxLayout(); row.setSpacing(8); row.setContentsMargins(0,2,0,2)
            nl=_lbl(label_text,11,T2)
            nl.setFixedWidth(ATTR_W)
            nl.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
            bar=GradBar(*colors)
            vl=_lbl("80",10,T2); vl.setFixedWidth(32); vl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
            self._bars[key]=bar; self._vl[key]=vl
            row.addWidget(nl); row.addWidget(bar,1); row.addWidget(vl)
            S.addLayout(row); S.addSpacing(4)

        S.addSpacing(6); S.addWidget(_div()); S.addSpacing(8)

        # 互动
        S.addWidget(_lbl("互动",11,T3)); S.addSpacing(6)
        grid=QGridLayout(); grid.setSpacing(6)
        btns=[("🍔","喂食",self.feed_clicked),("✋","摸摸",self.pet_clicked),
              ("🏸","羽毛球",self.game_clicked),("🐱","变猫猫",self.cat_clicked),
              ("📖","学习",self.study_clicked),("💤","睡觉",self.sleep_clicked),
              ("🌅","唤醒",self.wake_clicked)]
        for idx,(icon,label,sig) in enumerate(btns):
            b=_ibtn(icon,label); b.clicked.connect(sig.emit)
            grid.addWidget(b, idx//4, idx%4)
        S.addLayout(grid)

        # 底部信息
        S.addSpacing(12); S.addWidget(_div()); S.addSpacing(6)
        self.info_label=_lbl("",10,T3); self.info_label.setAlignment(Qt.AlignCenter); self.info_label.setWordWrap(True)
        S.addWidget(self.info_label)
        S.addSpacing(4)

        scroll_area.setWidget(scroll_content)
        L.addWidget(scroll_area, 1)

    # ════════════════════  任务页  ════════════════════════════
    def _pg_tasks(self):
        L=self._cl; L.addWidget(_lbl("📋 每日任务",13,T1,True)); L.addSpacing(8)
        if not self._gs: L.addWidget(_lbl("系统未初始化",11,T3)); L.addStretch(); return
        for t in self._gs.get_tasks_status():
            c=QWidget(); c.setStyleSheet(f"background:{CARD};border-radius:12px;border:1px solid {BD};")
            cl=QVBoxLayout(c); cl.setContentsMargins(12,10,12,10); cl.setSpacing(4)
            tr=QHBoxLayout(); tr.addWidget(_lbl(t["name"],12,T1,True)); tr.addStretch()
            if t["claimed"]:
                tr.addWidget(_lbl("✅ 已领取",10,"#7cc8a0"))
            elif t["done"]:
                cb=QPushButton("领取"); cb.setFixedSize(56,26)
                cb.setStyleSheet(f"QPushButton{{background:#fff3e0;color:#e65100;border:1px solid #ffcc80;border-radius:8px;font-size:11px;}}"
                                 f"QPushButton:hover{{background:#ffe0b2;}}")
                cb.clicked.connect(lambda _=None,tid=t["id"]:self._claim(tid)); tr.addWidget(cb)
            cl.addLayout(tr)
            cl.addWidget(_lbl(f"{t['desc']}　{t['progress']}/{t['target']}　🪙+{t['reward']}",10,T2))
            bar=GradBar("#f0b060","#f8d090"); bar.set_value(int(t["progress"]/t["target"]*100) if t["target"]>0 else 0)
            cl.addWidget(bar); L.addWidget(c); L.addSpacing(2)
        L.addStretch()

    # ════════════════════  背包页  ════════════════════════════
    def _pg_bag(self):
        L=self._cl; L.addWidget(_lbl("🎒 背包",13,T1,True)); L.addSpacing(8)
        if not self._gs: L.addStretch(); return
        bp=self._gs.get_backpack()
        if not bp:
            L.addWidget(_lbl("背包空空如也~\n去商店买点东西吧！",11,T3)); L.addStretch(); return
        from src.game_systems import SHOP_ITEMS
        im={s["id"]:s for s in SHOP_ITEMS}
        g=QGridLayout(); g.setSpacing(8); col=0; row=0
        for iid,cnt in bp.items():
            s=im.get(iid)
            if not s: continue
            b=QPushButton(f"{s['name']}\n×{cnt}"); b.setFixedSize(90,68); b.setFont(QFont("Microsoft YaHei",10))
            b.setStyleSheet(f"QPushButton{{background:{CARD};color:{T1};border:1.5px solid {BD};border-radius:12px;}}"
                            f"QPushButton:hover{{background:{BGB};border-color:{BD2};}}")
            b.clicked.connect(lambda _=None,i=iid:self._use(i)); g.addWidget(b,row,col)
            col+=1
            if col>=4: col=0; row+=1
        L.addLayout(g); L.addSpacing(10)
        L.addWidget(_lbl("点击物品即可使用",10,T3)); L.addStretch()

    # ════════════════════  商店页  ════════════════════════════
    def _pg_shop(self):
        L=self._cl
        tr=QHBoxLayout(); tr.addWidget(_lbl("🏪 商店",13,T1,True)); tr.addStretch()
        tr.addWidget(_lbl(f"🪙 {self._gs.coins if self._gs else 0}",12,TB,True)); L.addLayout(tr); L.addSpacing(8)
        if not self._gs: L.addStretch(); return
        for s in self._gs.get_shop_items():
            c=QWidget(); c.setStyleSheet(f"background:{CARD};border-radius:12px;border:1px solid {BD};")
            cl=QHBoxLayout(c); cl.setContentsMargins(12,10,12,10); cl.setSpacing(10)
            cl.addWidget(_lbl(s["name"],12,T1))
            cl.addWidget(_lbl(s["desc"],10,T2),1)
            ok=self._gs.coins>=s["price"]
            bb=QPushButton(f"🪙{s['price']}"); bb.setFixedSize(60,30)
            bb.setStyleSheet(f"QPushButton{{background:{'#fff3e0' if ok else CARD2};color:{'#e65100' if ok else T3};"
                             f"border:1px solid {'#ffcc80' if ok else BD};border-radius:8px;font-size:11px;}}"
                             f"QPushButton:hover{{background:#ffe0b2;}}")
            bb.setEnabled(ok); bb.clicked.connect(lambda _=None,i=s["id"]:self._buy(i)); cl.addWidget(bb)
            L.addWidget(c); L.addSpacing(2)
        L.addStretch()

    # ════════════════════  成就页  ════════════════════════════
    def _pg_ach(self):
        L=self._cl
        sa=QScrollArea(); sa.setWidgetResizable(True); sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sa.setStyleSheet(
            f"QScrollArea{{border:none;background:transparent;}}"
            f"QScrollBar:vertical{{width:5px;background:{CARD2};}}"
            f"QScrollBar::handle:vertical{{background:{BD};border-radius:2px;}}"
            f"QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0px;}}")
        sw=QWidget(); sw.setStyleSheet("background:transparent;border:none;")
        sl=QVBoxLayout(sw); sl.setContentsMargins(0,0,4,0); sl.setSpacing(6)
        sl.addWidget(_lbl("成就",13,T1,True)); sl.addSpacing(4)
        if not self._gs or not self._ps:
            sl.addWidget(_lbl("系统未初始化",11,T3)); sl.addStretch()
        else:
            for a in self._gs.get_achievements_status(self._ps):
                c=QWidget(); c.setMinimumHeight(52)
                c.setStyleSheet(f"background:{'#f0faf0' if a['unlocked'] else CARD};border-radius:12px;border:1px solid {BD};")
                cl=QHBoxLayout(c); cl.setContentsMargins(12,8,12,8); cl.setSpacing(10)
                icon_lbl=QLabel("🏆" if a["unlocked"] else "🔒")
                icon_lbl.setFont(QFont("Microsoft YaHei",14)); icon_lbl.setFixedWidth(28)
                icon_lbl.setStyleSheet("background:transparent;border:none;")
                icon_lbl.setAlignment(Qt.AlignCenter)
                cl.addWidget(icon_lbl)
                iv=QVBoxLayout(); iv.setSpacing(2)
                name_l=_lbl(a["name"],11,T1 if a["unlocked"] else T3,True)
                name_l.setMinimumHeight(20)
                iv.addWidget(name_l)
                desc_l=_lbl(f"{a['desc']}  +{a['reward']}币",9,T2 if a["unlocked"] else T3)
                desc_l.setMinimumHeight(18); desc_l.setWordWrap(True)
                iv.addWidget(desc_l)
                cl.addLayout(iv,1); sl.addWidget(c)
            sl.addStretch()
        sa.setWidget(sw); L.addWidget(sa,1)

    # ════════════════════  聊天页  ════════════════════════════
    def _pg_chat(self):
        L=self._cl

        self._chat_scroll=QScrollArea()
        self._chat_scroll.setWidgetResizable(True)
        self._chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._chat_scroll.setStyleSheet(
            f"QScrollArea{{border:1px solid {BD};border-radius:12px;background:{CARD};}}"
            f"QScrollBar:vertical{{width:5px;background:{CARD2};}}"
            f"QScrollBar::handle:vertical{{background:{BD};border-radius:2px;}}"
            f"QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0px;}}")
        self._chat_content=QWidget()
        self._chat_content.setStyleSheet(f"background:{CARD};border:none;")
        self._chat_layout=QVBoxLayout(self._chat_content)
        self._chat_layout.setContentsMargins(8,8,8,8); self._chat_layout.setSpacing(6)
        self._chat_layout.addStretch()
        self._chat_scroll.setWidget(self._chat_content)
        L.addWidget(self._chat_scroll,1)

        self._load_chat_history()

        if not self._cs or not self._cs.enabled:
            if self._cs and self._cs.is_first_launch:
                hint=_lbl("首次使用，请先去「设置」页输入你的 API 地址和 Key",10,"#c4784a")
            else:
                hint=_lbl("请先在「设置」页配置 API 后使用聊天",10,T3)
            hint.setAlignment(Qt.AlignCenter); hint.setWordWrap(True)
            hint.setCursor(Qt.PointingHandCursor)
            hint.mousePressEvent = lambda _: self._go("settings")
            L.addSpacing(4); L.addWidget(hint)

        L.addSpacing(6)
        ir=QHBoxLayout(); ir.setSpacing(6)
        self._chat_input=_MultiLineInput("和我说说话吧~")
        self._chat_input.submitted.connect(self._send_chat)
        ir.addWidget(self._chat_input,1)

        send_btn=QPushButton("发送"); send_btn.setFixedSize(56,36)
        send_btn.setFont(QFont("Microsoft YaHei",11))
        send_btn.setStyleSheet(
            f"QPushButton{{background:#e8d0c0;color:{T1};border:none;border-radius:12px;font-weight:bold;}}"
            f"QPushButton:hover{{background:#dcc0b0;}}"
            f"QPushButton:pressed{{background:{CARD2};}}")
        send_btn.clicked.connect(self._send_chat)
        ir.addWidget(send_btn)
        L.addLayout(ir)

        if self._cs:
            mi=self._cs.get_memory_info()
            mem_text=f"记忆：{mi['facts_count']} 条事实 · {mi['recent_count']//2} 轮对话"
            ml=_lbl(mem_text,9,T3); ml.setAlignment(Qt.AlignCenter)
            L.addSpacing(2); L.addWidget(ml)

    def _load_chat_history(self, scroll_to_bottom: bool = True):
        if not self._cs:
            return
        recent = self._cs._memory.get("recent", [])
        # 显示最近 20 条，记录每条在 recent 中的真实下标
        start = max(0, len(recent) - 20)
        for i in range(start, len(recent)):
            m = recent[i]
            self._add_chat_bubble(m["content"], m["role"] == "user",
                                  msg_index=i, scroll_to_bottom=scroll_to_bottom)

    def _refresh_chat_view(self, keep_scroll: bool = False):
        """清空聊天区域并重新加载历史。keep_scroll=True 时保持当前滚动位置。"""
        saved_pos = 0
        if keep_scroll:
            saved_pos = self._chat_scroll.verticalScrollBar().value()
        # 清除所有气泡（保留末尾的 stretch）
        while self._chat_layout.count() > 1:
            item = self._chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
        self._load_chat_history(scroll_to_bottom=not keep_scroll)
        if keep_scroll:
            QTimer.singleShot(60, lambda: self._chat_scroll.verticalScrollBar().setValue(
                min(saved_pos, self._chat_scroll.verticalScrollBar().maximum())))

    def _clear_layout(self, layout):
        """递归清除 layout 内的所有子项"""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _add_chat_bubble(self, text, is_user, msg_index=-1, scroll_to_bottom=True):
        """
        所有气泡统一用 QLabel + RichText。
        QLabel 会自动根据 setWordWrap+setMaximumWidth 撑开高度，不产生内部滚动。
        URL 通过 setOpenExternalLinks(True) 实现可点击跳转。
        msg_index: 该消息在 recent 中的下标，用于删除（-1 表示实时新增，由当前 recent 长度推算）
        scroll_to_bottom: 是否自动滚动到底部（删除场景中为 False）
        """
        BUBBLE_W = 272
        html_text = (
            f'<span style="font-family:Microsoft YaHei;font-size:10pt;">'
            f'{_text_to_html(text)}</span>'
        )
        bubble = QLabel()
        bubble.setTextFormat(Qt.RichText)
        bubble.setOpenExternalLinks(True)
        bubble.setWordWrap(True)
        bubble.setMaximumWidth(BUBBLE_W)
        bubble.setFont(QFont("Microsoft YaHei", 10))
        bubble.setText(html_text)
        bubble.setTextInteractionFlags(
            Qt.TextBrowserInteraction | Qt.TextSelectableByMouse
        )
        # 存储消息下标和原始文本，用于右键操作（删除、加入记忆）
        bubble.setProperty("msg_index", msg_index)
        bubble.setProperty("is_user", is_user)
        bubble.setProperty("msg_text", text)
        bubble.setContextMenuPolicy(Qt.CustomContextMenu)
        bubble.customContextMenuRequested.connect(
            lambda pos, b=bubble: self._show_bubble_menu(b, pos))

        if is_user:
            bubble.setStyleSheet(
                "background:#dce8fa;color:#2a4a7a;"
                "border-radius:12px;padding:8px 12px;border:none;")
            row = QHBoxLayout(); row.addStretch(); row.addWidget(bubble)
        else:
            bubble.setStyleSheet(
                f"background:#f0e8e0;color:{T1};"
                "border-radius:12px;padding:8px 12px;border:none;")
            row = QHBoxLayout(); row.addWidget(bubble); row.addStretch()

        idx = self._chat_layout.count() - 1
        self._chat_layout.insertLayout(idx, row)
        if scroll_to_bottom:
            QTimer.singleShot(50, lambda: self._chat_scroll.verticalScrollBar().setValue(
                self._chat_scroll.verticalScrollBar().maximum()))

    def _show_bubble_menu(self, bubble, pos):
        """右键气泡 → 弹出操作菜单（删除 / 加入记忆）"""
        from PyQt5.QtWidgets import QMenu, QAction
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu{{background:{CARD};border:1px solid {BD};border-radius:8px;padding:4px 0;"
            f"font-family:'Microsoft YaHei';font-size:12px;}}"
            f"QMenu::item{{padding:5px 18px;color:{T1};border-radius:5px;margin:1px 3px;}}"
            f"QMenu::item:selected{{background:#f5ddd0;color:#a04030;}}")
        # 加入记忆
        mem_action = QAction("📌 加入记忆", self)
        mem_action.triggered.connect(lambda: self._add_bubble_to_memory(bubble))
        menu.addAction(mem_action)
        # 删除
        del_action = QAction("🗑️ 删除这条对话", self)
        del_action.triggered.connect(lambda: self._delete_chat_bubble(bubble))
        menu.addAction(del_action)
        menu.exec_(bubble.mapToGlobal(pos))

    def _add_bubble_to_memory(self, bubble):
        """将气泡文本加入事实记忆数据库"""
        if not self._cs:
            return
        text = bubble.property("msg_text")
        if not text or not text.strip():
            return
        self._cs.manual_add_fact(text.strip())
        # 视觉反馈：短暂高亮气泡边框
        is_user = bubble.property("is_user")
        if is_user:
            bubble.setStyleSheet(
                "background:#dce8fa;color:#2a4a7a;"
                "border-radius:12px;padding:8px 12px;"
                "border:2px solid #b09480;")
        else:
            bubble.setStyleSheet(
                f"background:#f0e8e0;color:{T1};"
                "border-radius:12px;padding:8px 12px;"
                "border:2px solid #b09480;")
        # 1.5 秒后恢复原样
        QTimer.singleShot(1500, lambda: self._reset_bubble_style(bubble, is_user))

    def _reset_bubble_style(self, bubble, is_user):
        """恢复气泡的默认样式"""
        try:
            if is_user:
                bubble.setStyleSheet(
                    "background:#dce8fa;color:#2a4a7a;"
                    "border-radius:12px;padding:8px 12px;border:none;")
            else:
                bubble.setStyleSheet(
                    f"background:#f0e8e0;color:{T1};"
                    "border-radius:12px;padding:8px 12px;border:none;")
        except RuntimeError:
            pass  # Qt 对象可能已销毁

    def _delete_chat_bubble(self, bubble):
        """删除指定气泡对应的消息（连同配对消息一起删除）"""
        if not self._cs:
            return
        msg_idx = bubble.property("msg_index")
        is_user = bubble.property("is_user")
        # 调用 chat_service 删除
        if msg_idx is not None and msg_idx >= 0:
            self._cs.remove_single_message(msg_idx)
        # 刷新聊天界面，保持当前滚动位置
        self._refresh_chat_view(keep_scroll=True)

    def _send_chat(self):
        if not hasattr(self,'_chat_input'):
            return
        msg=self._chat_input.toPlainText().strip()
        if not msg:
            return
        self._chat_input.clear()
        # 实时发送的消息，msg_index 暂设 -1，回复后刷新
        self._add_chat_bubble(msg, True, msg_index=-1)

        if not self._cs or not self._cs.enabled:
            self._add_chat_bubble("还没配置 API 呢~ 去「设置」页填一下吧！", False)
            return

        typing_lbl=_lbl("正在思考...",10,T3)
        typing_lbl.setStyleSheet(f"color:{T3};background:transparent;border:none;padding:4px;")
        idx=self._chat_layout.count()-1
        self._chat_layout.insertWidget(idx, typing_lbl)
        self._pending_typing_lbl=typing_lbl

        def on_reply(reply, error):
            # 从后台线程通过信号安全地发回主线程
            self._chat_reply_signal.emit(reply or "", error or "")

        self._cs.chat(msg, self._ps, callback=on_reply)

    def _on_chat_reply(self, reply, error):
        """信号槽：在主线程中处理 AI 回复"""
        if self._pending_typing_lbl is not None:
            try:
                self._pending_typing_lbl.deleteLater()
            except RuntimeError:
                pass  # Qt C++ 对象已被销毁，忽略
            self._pending_typing_lbl = None
        # 如果用户已切走聊天页，回复已保存在 memory 中，下次进入聊天页会自动加载
        if not hasattr(self, '_chat_layout') or self._tab != "chat":
            return
        if error:
            self._add_chat_bubble(f"出错了：{error[:100]}", False)
        else:
            # 回复完成后刷新整个聊天视图，确保 msg_index 正确
            self._refresh_chat_view()

    # ════════════════════  设置页  ════════════════════════════
    def _pg_settings(self):
        L=self._cl
        is_first = self._cs and self._cs.is_first_launch
        title = "首次使用 — 配置 API" if is_first else "API 设置"
        L.addWidget(_lbl(title,13,T1,True)); L.addSpacing(6)

        if is_first:
            hint = _lbl("欢迎使用桌宠！请先配置你的 AI 接口信息：",10,"#c4784a")
            hint.setWordWrap(True); L.addWidget(hint); L.addSpacing(6)

        config = self._cs.config if self._cs else {"api_url":"","api_key":"","model":""}

        def _input(label, value, placeholder="", is_password=False):
            L.addWidget(_lbl(label,11,T2)); L.addSpacing(2)
            row=QHBoxLayout(); row.setSpacing(4)
            inp=QLineEdit(value)
            inp.setPlaceholderText(placeholder)
            inp.setFixedHeight(36); inp.setFont(QFont("Microsoft YaHei",10))
            if is_password:
                inp.setEchoMode(QLineEdit.Password)
            inp.setStyleSheet(
                f"QLineEdit{{background:{CARD};border:1.5px solid {BD};border-radius:10px;"
                f"padding:4px 12px;color:{T1};}}"
                f"QLineEdit:focus{{border-color:{ACC};}}")
            row.addWidget(inp)
            clr=QPushButton("✕"); clr.setFixedSize(28,36)
            clr.setToolTip("清空此项")
            clr.setStyleSheet(
                f"QPushButton{{background:transparent;color:{T3};border:none;"
                f"font-size:12px;border-radius:8px;}}"
                f"QPushButton:hover{{color:#c06060;background:#fde8e8;}}")
            clr.clicked.connect(inp.clear)
            row.addWidget(clr)
            L.addLayout(row); L.addSpacing(8)
            return inp

        url_ph = "首次使用，请输入你的 API 地址" if is_first else "https://api.openai.com/v1 或中转站地址"
        key_ph = "首次使用，请输入你的 API Key" if is_first else "sk-..."
        self._cfg_url=_input("API 地址", config.get("api_url",""), url_ph)
        self._cfg_key=_input("API Key", config.get("api_key",""), key_ph, is_password=True)
        self._cfg_model=_input("模型名称", config.get("model",""),
                               "gpt-3.5-turbo / deepseek-chat / claude-3.5-sonnet")
        L.addSpacing(4)
        L.addWidget(_lbl("支持官方/中转站/本地兼容接口（自动补全 /v1/chat/completions）",9,T3))

        L.addSpacing(12)
        br=QHBoxLayout(); br.setSpacing(10)
        save_btn=QPushButton("保存设置"); save_btn.setFixedHeight(38)
        save_btn.setFont(QFont("Microsoft YaHei",11,QFont.Bold))
        save_btn.setStyleSheet(
            f"QPushButton{{background:#e8d0c0;color:{T1};border:none;border-radius:12px;padding:0 20px;}}"
            f"QPushButton:hover{{background:#dcc0b0;}}")
        save_btn.clicked.connect(self._save_settings)
        br.addWidget(save_btn)

        test_btn=QPushButton("测试连接"); test_btn.setFixedHeight(38)
        test_btn.setFont(QFont("Microsoft YaHei",11))
        test_btn.setStyleSheet(
            f"QPushButton{{background:{CARD};color:{T2};border:1.5px solid {BD};border-radius:12px;padding:0 20px;}}"
            f"QPushButton:hover{{background:{BGB};}}")
        test_btn.clicked.connect(self._test_api)
        br.addWidget(test_btn)
        L.addLayout(br)

        L.addSpacing(8)
        status = "已配置" if (self._cs and self._cs.enabled) else "未配置"
        self._cfg_status=_lbl(f"当前状态：{status}",10,T2)
        self._cfg_status.setWordWrap(True)
        L.addWidget(self._cfg_status)

        L.addSpacing(20); L.addWidget(_div()); L.addSpacing(16)

        # 记忆管理入口按钮
        mem_btn=QPushButton("📝 记忆管理"); mem_btn.setFixedHeight(42)
        mem_btn.setFont(QFont("Microsoft YaHei",12,QFont.Bold))
        mem_btn.setStyleSheet(
            f"QPushButton{{background:{CARD};color:{T1};border:1.5px solid {BD};border-radius:12px;padding:0 20px;}}"
            f"QPushButton:hover{{background:{BGB};border-color:{BD2};}}"
            f"QPushButton:pressed{{background:{CARD2};}}")
        mem_btn.clicked.connect(self._open_memory_window)
        L.addWidget(mem_btn)
        if self._cs:
            mi=self._cs.get_memory_info()
            L.addSpacing(4)
            L.addWidget(_lbl(f"{mi['facts_count']} 条记忆  ·  {mi['recent_count']//2} 轮对话",9,T3))
        L.addStretch()

    def _open_memory_window(self):
        if not self._cs:
            return
        self.hide()
        from src.knowledge_hub import KnowledgeHub
        self._mem_win = KnowledgeHub(self._cs, parent_panel=self, parent=None)
        self._mem_win.show()

    def _save_settings(self):
        if not self._cs:
            return
        self._cs.update_config(
            self._cfg_url.text(),
            self._cfg_key.text(),
            self._cfg_model.text(),
        )
        status="已配置" if self._cs.enabled else "未配置"
        self._cfg_status.setText(f"当前状态：{status}")

    def _test_api(self):
        if not self._cs:
            return
        self._save_settings()
        if not self._cs.enabled:
            self._cfg_status.setText("请先填写 API 地址和 Key")
            return
        self._cfg_status.setText("测试中...")

        def on_result(success, error):
            if success:
                self._test_result_signal.emit("ok|")
            else:
                self._test_result_signal.emit(f"err|{str(error)}")

        self._cs.test_connection(callback=on_result)

    def _on_test_result(self, text):
        """信号槽：在主线程展示测试结果（更新状态标签 + 聊天气泡）"""
        ok = text.startswith("ok|")
        detail = text[len("ok|"):] if ok else text[len("err|"):]

        # 更新设置页状态标签（可能已因切换 tab 被销毁）
        try:
            if hasattr(self, '_cfg_status') and self._cfg_status:
                self._cfg_status.setText("✅ 连接成功" if ok else "❌ 连接失败")
        except RuntimeError:
            pass

        # 切到聊天页，弹出气泡（面板隐藏时跳过 UI 操作）
        if not self.isVisible():
            return
        self._go("chat")

        def _show_bubble():
            if not self.isVisible():
                return
            if ok:
                self._add_chat_bubble("嗵在这里！", False)
            else:
                reason_html = (
                    f'<span style="font-family:Microsoft YaHei;font-size:10pt;">'
                    f'你的配置'
                    f'<span style="font-size:8pt;color:#a06040;"> ({detail[:80]})</span>'
                    f'有些奇怪，嗵找不到你！</span>'
                )
                self._add_chat_bubble_html(reason_html, False)

        QTimer.singleShot(30, _show_bubble)

    def _add_chat_bubble_html(self, html_text, is_user):
        """直接传入 HTML 内容的气泡（供内部使用）"""
        BUBBLE_W = 272
        bubble = QLabel()
        bubble.setTextFormat(Qt.RichText)
        bubble.setOpenExternalLinks(False)
        bubble.setWordWrap(True)
        bubble.setMaximumWidth(BUBBLE_W)
        bubble.setFont(QFont("Microsoft YaHei", 10))
        bubble.setText(html_text)
        bubble.setContextMenuPolicy(Qt.CustomContextMenu)
        bubble.customContextMenuRequested.connect(
            lambda pos, b=bubble: self._show_bubble_menu(b, pos))
        bubble.setProperty("msg_index", -1)
        bubble.setProperty("is_user", is_user)
        if is_user:
            bubble.setStyleSheet(
                "background:#dce8fa;color:#2a4a7a;"
                "border-radius:12px;padding:8px 12px;border:none;")
            row = QHBoxLayout(); row.addStretch(); row.addWidget(bubble)
        else:
            bubble.setStyleSheet(
                f"background:#f0e8e0;color:{T1};"
                "border-radius:12px;padding:8px 12px;border:none;")
            row = QHBoxLayout(); row.addWidget(bubble); row.addStretch()
        if hasattr(self, '_chat_layout'):
            idx = self._chat_layout.count() - 1
            self._chat_layout.insertLayout(idx, row)
            QTimer.singleShot(50, lambda: self._chat_scroll.verticalScrollBar().setValue(
                self._chat_scroll.verticalScrollBar().maximum()))

    # ════════════════════  回调  ══════════════════════════════
    def _pick_av(self):
        p,_=QFileDialog.getOpenFileName(self,"选择头像","","图片 (*.png *.jpg *.jpeg *.webp *.bmp)")
        if p: self._avatar.load_custom(p)
    def _rename(self):
        n,ok=QInputDialog.getText(self,"修改名字","新名字：",text=self.name_label.text())
        if ok and n.strip(): nm=n.strip()[:12]; self.name_label.setText(nm); self.rename_requested.emit(nm)
    def _sign(self):
        if not self._gs: return
        r=self._gs.do_sign_in(); self._si.setText(r["msg"]); self._upd_sign(); self._coin.setText(f"🪙 {self._gs.coins}")
    def _upd_sign(self):
        if self._gs and not self._gs.can_sign_in(): self._sb.setEnabled(False); self._sb.setText("已签到")
        else: self._sb.setEnabled(True); self._sb.setText("签到")
    def _claim(self,tid):
        if self._gs: self._gs.claim_task(tid); self._coin.setText(f"🪙 {self._gs.coins}"); self._go("tasks")
    def _use(self,iid):
        if self._gs and self._ps:
            msg = self._gs.use_item(iid, self._ps)
            self.item_used.emit(iid, msg)
            self._go("bag")
    def _buy(self,iid):
        if self._gs: self._gs.buy_item(iid); self._coin.setText(f"🪙 {self._gs.coins}"); self._go("shop")

    # ════════════════════  刷新  ══════════════════════════════
    def update_status(self,state):
        self._ps=state
        if self._gs: self._coin.setText(f"🪙 {self._gs.coins}")
        if self._tab!="status": return
        if not hasattr(self,'name_label'): return
        self.name_label.setText(state.name)
        self._lv.setText(f"Lv.{state.level}")
        self.mood_label.setText(state.get_status_text())
        from src.pet_state import PetMood
        mk={PetMood.HAPPY:"happy",PetMood.NORMAL:"normal",PetMood.SAD:"sad",PetMood.HUNGRY:"hungry",PetMood.SLEEPY:"sleepy",PetMood.SLEEPING:"sleeping"}.get(state.current_mood,"normal")
        self._avatar.set_mood(mk)
        em=state.level*100; self._ev.setText(f"{int(state.exp)}/{em}"); self._eb.set_value(int(state.exp/em*100))
        for k,v in [("hunger",state.hunger),("happy",state.happiness),("energy",state.energy),("intimacy",state.intimacy)]:
            self._bars[k].set_value(int(v)); self._vl[k].setText(str(int(v)))
        self.info_label.setText(f"出生 {int(state.age_days)} 天  ·  喂食 {getattr(state,'total_feed_times',0)} 次")
        self._upd_sign()

    def paintEvent(self,_): pass
