"""
知识中心 — 统一记忆管理窗口
三种来源: 💬对话提取 / 📄人设文档 / 🌐网页爬取
"""
import os, time
from datetime import datetime
from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QTimer, QEvent
from PyQt5.QtGui import QFont, QColor, QPainter, QCursor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QScrollArea, QMessageBox, QFileDialog,
    QTextEdit, QSizePolicy, QApplication,
)

# ── 色板（与 status_panel 保持一致）──
BG   = "#fdf6f0"; CARD = "#fff8f3"; CARD2 = "#f5ede4"
BD   = "#e8d8cc"; BD2  = "#d4c4b8"
T1   = "#5a4035"; T2   = "#8a7060"; T3   = "#c4a898"
ACC  = "#b09480"; BGB  = "#f0e8e0"

# 来源色标
CLR_CHAT   = "#d4a8c8"   # 紫
CLR_WEB    = "#7aba7a"   # 绿
CLR_MANUAL = "#a0b8d8"   # 蓝
CLR_DOC    = "#7ab8d4"   # 青


def _lbl(t="", sz=12, c=T1, bold=False):
    lb = QLabel(t)
    f = QFont("Microsoft YaHei", _fs(sz)); f.setBold(bold); lb.setFont(f)
    lb.setStyleSheet(f"color:{c};background:transparent;border:none;padding:0;margin:0;")
    return lb


def _btn(text, h=34, primary=False, danger=False):
    b = QPushButton(text)
    b.setFixedHeight(_s(h))
    b.setFont(QFont("Microsoft YaHei", _fs(10)))
    b.setCursor(Qt.PointingHandCursor)
    if danger:
        b.setStyleSheet(
            f"QPushButton{{background:#fbe9e7;color:#c62828;border:1px solid #ef9a9a;"
            f"border-radius:{_s(10)}px;padding:0 {_s(14)}px;}}"
            f"QPushButton:hover{{background:#ffcdd2;}}")
    elif primary:
        b.setStyleSheet(
            f"QPushButton{{background:#e8d0c0;color:{T1};border:none;border-radius:{_s(10)}px;"
            f"padding:0 {_s(14)}px;font-weight:bold;}}"
            f"QPushButton:hover{{background:#dcc0b0;}}")
    else:
        b.setStyleSheet(
            f"QPushButton{{background:{CARD};color:{T2};border:1.5px solid {BD};"
            f"border-radius:{_s(10)}px;padding:0 {_s(14)}px;}}"
            f"QPushButton:hover{{background:{BGB};border-color:{BD2};color:{T1};}}")
    return b


# ── DPI 等比缩放工具 ─────────────────────────────────────────
_ui_scale = 1.0  # KnowledgeHub.__init__ 中设置

def _s(px):
    """缩放像素值 — 面板内部布局尺寸（边距、固定宽高、间距）"""
    return max(1, round(px * _ui_scale))

def _fs(pt):
    """缩放字号 — 保证最小可读性"""
    return max(7, round(pt * _ui_scale))


def _time_ago(ts):
    """时间戳 → 友好的相对时间"""
    if not ts:
        return ""
    diff = time.time() - ts
    if diff < 60:
        return "刚刚"
    elif diff < 3600:
        return f"{int(diff/60)} 分钟前"
    elif diff < 86400:
        return f"{int(diff/3600)} 小时前"
    elif diff < 86400 * 2:
        return "昨天"
    elif diff < 86400 * 7:
        return f"{int(diff/86400)} 天前"
    else:
        return datetime.fromtimestamp(ts).strftime("%m月%d日")


def _source_label(src):
    """来源代码 → 显示标签"""
    return {"chat": "对话提取", "explicit": "对话提取", "freq": "对话提取",
            "web": "信息搜集", "manual": "手动添加"}.get(src, "其他")


def _source_color(src):
    """来源代码 → 色标"""
    if src in ("chat", "explicit", "freq"):
        return CLR_CHAT
    elif src == "web":
        return CLR_WEB
    elif src == "manual":
        return CLR_MANUAL
    return BD


def _source_icon(src):
    if src in ("chat", "explicit", "freq"):
        return "💬"
    elif src == "web":
        return "🌐"
    elif src == "manual":
        return "✏️"
    return "📋"


def _source_tag_style(src):
    if src in ("chat", "explicit", "freq"):
        return "background:#f4e4f4;color:#906090;"
    elif src == "web":
        return "background:#dcf0dc;color:#407040;"
    elif src == "manual":
        return "background:#dce8fa;color:#4060a0;"
    return f"background:{CARD2};color:{T2};"


# ── 自适应高度多行输入框（Enter 提交，Shift+Enter 换行）────────
class _MultiLineInput(QTextEdit):
    """
    空/一行时紧凑（~36px），随输入自动撑高，
    达到 max_h 后内部滚动，不挤占外部布局。
    """
    submitted = pyqtSignal()

    def __init__(self, placeholder="", max_h=140, parent=None):
        super().__init__(parent)
        self._max_h = _s(max_h)
        self.setPlaceholderText(placeholder)
        self.setFont(QFont("Microsoft YaHei", _fs(10)))
        self.setAcceptRichText(False)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet(
            f"QTextEdit{{background:{CARD};border:1.5px solid {BD};"
            f"border-radius:{_s(12)}px;padding:{_s(4)}px {_s(12)}px;color:{T1};}}"
            f"QTextEdit:focus{{border-color:{ACC};}}"
            f"QScrollBar:vertical{{width:{_s(4)}px;background:{CARD2};}}"
            f"QScrollBar::handle:vertical{{background:{BD};border-radius:{_s(2)}px;}}"
            f"QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0px;}}")
        self.document().setDocumentMargin(_s(2))       # 默认 4，压缩省空间
        fm = self.fontMetrics()
        self._single_h = max(fm.height() + _s(22), _s(38))  # 留足 padding+border+docMargin
        self.setFixedHeight(self._single_h)
        self.textChanged.connect(self._auto_resize)

    # ── 核心：根据文档实际高度自动调整控件高度 ──
    def _auto_resize(self):
        doc_h = int(self.document().size().height())
        target = doc_h + _s(12)                       # 上下 padding 补偿
        target = max(self._single_h, min(self._max_h, target))
        if self.height() != target:
            self.setFixedHeight(target)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            if e.modifiers() & Qt.ShiftModifier:
                super().keyPressEvent(e)
            else:
                self.submitted.emit()
        else:
            super().keyPressEvent(e)


# ══════════════════════════════════════════════════════════════
#  爬取结果面板（覆盖弹窗）
# ══════════════════════════════════════════════════════════════
class CrawlOverlay(QWidget):
    """网页爬取浮层"""
    saved = pyqtSignal()  # 保存完毕
    _crawl_done = pyqtSignal(object, str)  # result_dict_or_None, error_str

    def __init__(self, chat_service, parent=None):
        super().__init__(parent)
        self._cs = chat_service
        self.setStyleSheet("background:transparent;")
        self._results = []  # [{"text":..., "checked": bool}]
        self._page_title = ""
        self._page_url = ""
        self._page_source = ""
        self._crawl_thread = None
        self._crawl_cancelled = False
        self._crawl_done.connect(self._handle_result)
        self._build()

    def _build(self):
        self._root = QWidget(self)
        self._root.setObjectName("CO")
        self._root.setStyleSheet(
            f"QWidget#CO{{background:{BG};border-radius:{_s(18)}px;"
            f"border:1.5px solid {BD};}}")
        ml = QVBoxLayout(self._root)
        ml.setContentsMargins(_s(18), _s(16), _s(18), _s(14))
        ml.setSpacing(0)

        # ── 标题
        h = QHBoxLayout()
        h.addWidget(_lbl("🌐 网页信息整理", 13, T1, True))
        h.addStretch()
        cb = QPushButton("✕"); cb.setFixedSize(_s(26), _s(26))
        cb.setStyleSheet(
            f"QPushButton{{background:transparent;color:{T3};border:none;"
            f"font-size:{_fs(13)}px;border-radius:{_s(13)}px;}}"
            f"QPushButton:hover{{background:{CARD2};color:{T2};}}")
        cb.clicked.connect(self._close)
        h.addWidget(cb)
        ml.addLayout(h)
        ml.addSpacing(_s(10))

        # ── URL 输入（多行，Enter 触发抓取）
        ur = QHBoxLayout(); ur.setSpacing(_s(6)); ur.setAlignment(Qt.AlignTop)
        self._url_input = _MultiLineInput("粘贴网址，如 https://…")
        self._url_input.submitted.connect(self._do_crawl)
        ur.addWidget(self._url_input, 1)

        btn_col = QVBoxLayout(); btn_col.setSpacing(_s(4)); btn_col.setAlignment(Qt.AlignTop)

        self._clear_url_btn = QPushButton("✕")
        self._clear_url_btn.setFixedSize(_s(28), _s(28))
        self._clear_url_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{T3};border:none;"
            f"font-size:{_fs(12)}px;border-radius:{_s(14)}px;}}"
            f"QPushButton:hover{{background:{CARD2};color:{T2};}}")
        self._clear_url_btn.setToolTip("清空网址及搜索记录（已保存内容不受影响）")
        self._clear_url_btn.clicked.connect(self._clear_url)
        btn_col.addWidget(self._clear_url_btn)

        self._fetch_btn = _btn("抓取", 34, primary=True)
        self._fetch_btn.setFixedWidth(_s(64))
        self._fetch_btn.clicked.connect(self._do_crawl)
        btn_col.addWidget(self._fetch_btn)

        self._cancel_btn = _btn("取消", 34, danger=True)
        self._cancel_btn.setFixedWidth(_s(64))
        self._cancel_btn.clicked.connect(self._cancel_crawl)
        self._cancel_btn.hide()
        btn_col.addWidget(self._cancel_btn)

        ur.addLayout(btn_col)
        ml.addLayout(ur)
        ml.addSpacing(_s(6))

        # ── 状态行
        self._status_lbl = _lbl("输入网址后点击「抓取」或按 Enter", 10, T3)
        ml.addWidget(self._status_lbl)
        ml.addSpacing(_s(6))

        # ── 文件夹名称（可自定义，抓取后自动填入页面标题）
        fn_row = QHBoxLayout(); fn_row.setSpacing(_s(6))
        fn_row.addWidget(_lbl("📂", 13))
        fn_row.addWidget(_lbl("文件夹名称：", 10, T2))
        self._folder_input = QLineEdit()
        self._folder_input.setPlaceholderText("抓取后自动填入标题，可随时修改…")
        self._folder_input.setFixedHeight(_s(32))
        self._folder_input.setFont(QFont("Microsoft YaHei", _fs(10)))
        self._folder_input.setStyleSheet(
            f"QLineEdit{{background:{CARD};border:1.5px solid {BD};border-radius:{_s(10)}px;"
            f"padding:0 {_s(10)}px;color:{T1};}}"
            f"QLineEdit:focus{{border-color:{ACC};}}")
        fn_row.addWidget(self._folder_input, 1)
        ml.addLayout(fn_row)
        ml.addSpacing(_s(8))

        # ── 抓取结果滚动区
        self._result_widget = QWidget()
        self._result_widget.setStyleSheet("background:transparent;border:none;")
        self._result_layout = QVBoxLayout(self._result_widget)
        self._result_layout.setContentsMargins(_s(4), _s(4), _s(4), _s(4))
        self._result_layout.setSpacing(_s(4))
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sa.setStyleSheet(
            f"QScrollArea{{border:1px solid {BD};border-radius:{_s(12)}px;background:{CARD};}}"
            f"QScrollBar:vertical{{width:{_s(5)}px;background:{CARD2};}}"
            f"QScrollBar::handle:vertical{{background:{BD};border-radius:{_s(2)}px;}}"
            f"QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0px;}}")
        sa.setWidget(self._result_widget)
        ml.addWidget(sa, 1)
        ml.addSpacing(_s(6))

        # ── 手动添加内容行（多行输入）
        ca_row = QHBoxLayout(); ca_row.setSpacing(_s(6)); ca_row.setAlignment(Qt.AlignTop)
        self._custom_input = _MultiLineInput("手动添加内容到此文件夹…")
        self._custom_input.submitted.connect(self._add_custom_item)
        ca_row.addWidget(self._custom_input, 1)
        add_custom_btn = QPushButton("＋ 添加")
        add_custom_btn.setFixedSize(_s(72), _s(34))
        add_custom_btn.setFont(QFont("Microsoft YaHei", _fs(10)))
        add_custom_btn.setCursor(Qt.PointingHandCursor)
        add_custom_btn.setStyleSheet(
            f"QPushButton{{background:{CARD};color:{T2};border:1.5px solid {BD};"
            f"border-radius:{_s(10)}px;}}"
            f"QPushButton:hover{{background:{BGB};color:{T1};}}")
        add_custom_btn.clicked.connect(self._add_custom_item)
        ca_row.addWidget(add_custom_btn)
        ml.addLayout(ca_row)
        ml.addSpacing(_s(6))

        # ── 底部操作
        br = QHBoxLayout()
        self._count_lbl = _lbl("", 10, T2)
        br.addWidget(self._count_lbl)
        br.addStretch()
        cancel_btn = _btn("取消", 30)
        cancel_btn.clicked.connect(self._close)
        br.addWidget(cancel_btn)
        self._save_btn = _btn("保存到记忆", 30, primary=True)
        self._save_btn.clicked.connect(self._save)
        self._save_btn.setEnabled(False)
        br.addWidget(self._save_btn)
        ml.addLayout(br)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        # 浮层居中
        pw, ph = self.width(), self.height()
        rw, rh = min(pw - _s(20), _s(510)), min(ph - _s(20), _s(650))
        self._root.setGeometry((pw - rw) // 2, (ph - rh) // 2, rw, rh)

    def paintEvent(self, e):
        # 半透明遮罩
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(90, 64, 53, 40))
        p.end()

    def _close(self):
        self._cancel_crawl()
        self.hide()

    def _clear_url(self):
        """清空网址输入 + 本次抓取的结果列表（已保存到记忆的内容不受影响）"""
        self._cancel_crawl()
        self._url_input.clear()
        self._folder_input.clear()
        self._custom_input.clear()
        self._results = []
        while self._result_layout.count():
            it = self._result_layout.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        self._status_lbl.setText("输入网址后点击「抓取」或按 Enter")
        self._status_lbl.setStyleSheet(
            f"color:{T3};background:transparent;border:none;padding:0;margin:0;")
        self._count_lbl.setText("")
        self._save_btn.setEnabled(False)
        self._page_title = ""
        self._page_url = ""
        self._page_source = ""
        self._url_input.setFocus()

    def _cancel_crawl(self):
        """取消当前抓取（标记忽略回调结果）"""
        self._crawl_cancelled = True
        self._fetch_btn.show()
        self._cancel_btn.hide()
        self._fetch_btn.setEnabled(True)
        self._status_lbl.setText("已取消抓取")
        self._status_lbl.setStyleSheet(f"color:{T3};background:transparent;border:none;padding:0;margin:0;")

    def _do_crawl(self):
        url = self._url_input.toPlainText().strip().splitlines()[0].strip() \
              if self._url_input.toPlainText().strip() else ""
        if not url:
            return
        if not url.startswith("http"):
            url = "https://" + url
        self._crawl_cancelled = False
        self._status_lbl.setText("正在抓取页面内容…")
        self._status_lbl.setStyleSheet(f"color:{T2};background:transparent;border:none;padding:0;margin:0;")
        self._fetch_btn.hide()
        self._cancel_btn.show()
        self._save_btn.setEnabled(False)

        try:
            from src.web_crawler import crawl_url
        except ImportError:
            self._status_lbl.setText("爬取模块未找到")
            self._fetch_btn.show()
            self._cancel_btn.hide()
            return

        def on_result(result, error):
            # 通过信号安全回到主线程
            self._crawl_done.emit(result, error or "")

        self._crawl_thread = crawl_url(url, callback=on_result)

    def _handle_result(self, result, error):
        self._fetch_btn.show()
        self._cancel_btn.hide()
        self._fetch_btn.setEnabled(True)

        # 如果已取消，忽略结果
        if self._crawl_cancelled:
            return
        # 清空旧结果
        while self._result_layout.count():
            it = self._result_layout.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

        if error:
            self._status_lbl.setText(f"❌ {error}")
            self._status_lbl.setStyleSheet(f"color:#c06060;background:transparent;border:none;padding:0;margin:0;")
            return

        self._page_title = result.get("title", "")
        self._page_url = result.get("url", "")
        self._page_source = result.get("source", "")
        paragraphs = result.get("paragraphs", [])

        # 自动填入文件夹名（用户还没填过才覆盖）
        if not self._folder_input.text().strip():
            auto_name = (self._page_title[:40] if self._page_title
                         else (self._page_source or ""))
            self._folder_input.setText(auto_name)

        self._status_lbl.setText(f"✅ 已读取 · {self._page_title[:28]}  共 {len(paragraphs)} 段")
        self._status_lbl.setStyleSheet(f"color:#408060;background:transparent;border:none;padding:0;margin:0;")

        self._results = []
        for i, para in enumerate(paragraphs):
            item = {"text": para, "checked": False, "deleted": False}
            self._results.append(item)
            row = self._make_result_row(i, para)
            self._result_layout.addWidget(row)
        self._update_count()

    def _make_result_row(self, idx, text):
        w = QWidget()
        w.setStyleSheet(f"background:{CARD};border-radius:{_s(8)}px;border:1px solid {BD};")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(_s(8), _s(6), _s(8), _s(6))
        lay.setSpacing(_s(8))

        # 勾选框
        cb = QPushButton("☐")
        cb.setFixedSize(_s(22), _s(22))
        cb.setFont(QFont("Microsoft YaHei", _fs(12)))
        cb.setStyleSheet(
            f"QPushButton{{background:transparent;color:{T3};border:none;}}"
            f"QPushButton:hover{{color:{T1};}}")
        cb.clicked.connect(lambda checked=False, i=idx, b=cb: self._toggle(i, b))
        lay.addWidget(cb, 0, Qt.AlignTop)

        # 内容
        lbl = QLabel(text)
        lbl.setFont(QFont("Microsoft YaHei", _fs(10)))
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color:{T1};background:transparent;border:none;")
        lay.addWidget(lbl, 1)

        # 从列表移除按钮
        del_btn = QPushButton("✕")
        del_btn.setFixedSize(_s(20), _s(20))
        del_btn.setFont(QFont("Arial", _fs(10)))
        del_btn.setToolTip("从列表移除（已保存记忆不受影响）")
        del_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{BD};border:none;border-radius:{_s(10)}px;}}"
            f"QPushButton:hover{{background:#fde8e8;color:#c06060;}}")
        del_btn.clicked.connect(lambda checked=False, i=idx, ww=w: self._delete_result_row(i, ww))
        lay.addWidget(del_btn, 0, Qt.AlignTop)

        return w

    def _toggle(self, idx, btn):
        if self._results[idx].get("deleted"):
            return
        self._results[idx]["checked"] = not self._results[idx]["checked"]
        btn.setText("☑" if self._results[idx]["checked"] else "☐")
        btn.setStyleSheet(
            f"QPushButton{{background:transparent;"
            f"color:{'#408060' if self._results[idx]['checked'] else T3};border:none;}}"
            f"QPushButton:hover{{color:{T1};}}")
        self._update_count()

    def _delete_result_row(self, idx, widget):
        """从待选列表中移除该条目（不影响已保存的记忆）"""
        if 0 <= idx < len(self._results):
            self._results[idx]["deleted"] = True
            self._results[idx]["checked"] = False
        widget.hide()
        widget.deleteLater()
        self._update_count()

    def _add_custom_item(self):
        """手动向结果列表添加一条自定义内容"""
        txt = self._custom_input.toPlainText().strip()
        if not txt:
            return
        item = {"text": txt, "checked": True, "deleted": False}
        idx = len(self._results)
        self._results.append(item)
        row = self._make_result_row(idx, txt)
        self._result_layout.addWidget(row)
        self._custom_input.clear()
        self._update_count()

    def _update_count(self):
        active = [r for r in self._results if not r.get("deleted")]
        n = sum(1 for r in active if r.get("checked"))
        total = len(active)
        if n:
            self._count_lbl.setText(f"已选中 {n} / {total} 条")
        elif total:
            self._count_lbl.setText(f"共 {total} 条，未选中")
        else:
            self._count_lbl.setText("")
        self._save_btn.setEnabled(n > 0)

    def _save(self):
        # 使用用户填写的文件夹名；未填则回退到页面标题或域名
        origin = self._folder_input.text().strip()
        if not origin:
            origin = (self._page_title[:40] if self._page_title
                      else (self._page_source or "网页内容"))
        for r in self._results:
            if r.get("checked") and not r.get("deleted"):
                self._cs.add_web_fact(r["text"], origin=origin)
        self.saved.emit()
        self._close()


# ══════════════════════════════════════════════════════════════
#  知识中心主窗口
# ══════════════════════════════════════════════════════════════
class KnowledgeHub(QWidget):
    _BASE_KW, _BASE_KH = 900, 850
    _DESIGN_H = 1440

    def __init__(self, chat_service, parent=None, parent_panel=None):
        super().__init__(parent)
        self._cs = chat_service
        self._parent_panel = parent_panel
        self._filter = "all"  # all / chat / web / manual
        self._search_text = ""
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        scr = QApplication.primaryScreen()
        avail_h = scr.availableGeometry().height() if scr else 1080
        logical_h = scr.geometry().height() if scr else 1440
        _scale = min(1.0, logical_h / self._DESIGN_H)
        global _ui_scale
        _ui_scale = _scale
        self.KW = max(480, int(self._BASE_KW * _scale))
        self.KH = max(440, int(self._BASE_KH * _scale))
        self.KH = min(self.KH, avail_h - 60)
        self.setFixedSize(self.KW, self.KH)
        self._dp = QPoint(); self._dg = False
        # 居中
        scr_geo = scr.geometry() if scr else QApplication.primaryScreen().geometry()
        self.move((scr_geo.width() - self.KW) // 2, (scr_geo.height() - self.KH) // 2)
        self._build()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._dg = True
            self._dp = e.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._dg and e.buttons() == Qt.LeftButton:
            self.move(e.globalPos() - self._dp)

    def mouseReleaseEvent(self, _):
        self._dg = False


    def paintEvent(self, _):
        pass

    # ── 构建 ─────────────────────────────────────────────────
    def _build(self):
        root = QWidget(self)
        root.setGeometry(0, 0, self.KW, self.KH)
        root.setObjectName("KH")
        root.setStyleSheet(
            f"QWidget#KH{{background:{BG};border-radius:{_s(22)}px;"
            f"border:1.5px solid {BD};}}")
        self._main_layout = QVBoxLayout(root)
        self._main_layout.setContentsMargins(_s(3), 0, _s(3), 0)
        self._main_layout.setSpacing(0)

        # ── 标题栏
        self._build_titlebar()

        # ── 主体 = 侧栏 + 时间线
        body = QWidget()
        body.setStyleSheet("background:transparent;border:none;")
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(_s(0), _s(0), _s(0), _s(0))
        body_lay.setSpacing(0)

        self._build_sidebar(body_lay)
        self._build_timeline(body_lay)

        self._main_layout.addWidget(body, 1)

        # ── 底部操作栏
        self._build_bottombar()

        # ── 爬取浮层（隐藏）
        self._crawl_overlay = CrawlOverlay(self._cs, self)
        self._crawl_overlay.setGeometry(0, 0, self.KW, self.KH)
        self._crawl_overlay.hide()
        self._crawl_overlay.saved.connect(self._refresh)

        # 加载数据
        self._refresh()

    def _build_titlebar(self):
        tb = QWidget()
        tb.setFixedHeight(_s(48))
        tb.setStyleSheet(f"background:transparent;border-bottom:1px solid {BD};")
        lay = QHBoxLayout(tb)
        lay.setContentsMargins(_s(16), 0, _s(12), 0)
        lay.setSpacing(_s(8))

        lay.addWidget(_lbl("📝", 15))
        lay.addWidget(_lbl("知识中心", 14, T1, True))
        lay.addStretch()

        # 搜索框
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("搜索…")
        self._search_input.setFixedSize(_s(140), _s(30))
        self._search_input.setFont(QFont("Microsoft YaHei", _fs(10)))
        self._search_input.setStyleSheet(
            f"QLineEdit{{background:{CARD};border:1.5px solid {BD};border-radius:{_s(15)}px;"
            f"padding:0 {_s(10)}px 0 {_s(28)}px;color:{T1};font-size:{_fs(10)}px;}}"
            f"QLineEdit:focus{{border-color:{ACC};}}")
        self._search_input.textChanged.connect(self._on_search)
        # 搜索图标叠加在输入框左侧
        search_wrap = QWidget()
        search_wrap.setFixedSize(_s(140), _s(30))
        search_wrap.setStyleSheet("background:transparent;border:none;")
        self._search_input.setParent(search_wrap)
        self._search_input.setGeometry(0, 0, _s(140), _s(30))
        s_icon = QLabel("🔍", search_wrap)
        s_icon.setFont(QFont("Microsoft YaHei", _fs(10)))
        s_icon.setStyleSheet("background:transparent;border:none;color:#c4a898;")
        s_icon.setGeometry(_s(8), _s(5), _s(20), _s(20))
        s_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        lay.addWidget(search_wrap)

        # 总数
        self._total_badge = QLabel()
        self._total_badge.setFont(QFont("Microsoft YaHei", _fs(9)))
        self._total_badge.setFixedHeight(_s(22))
        self._total_badge.setStyleSheet(
            f"background:#e8d0c0;color:{T1};border-radius:{_s(11)}px;"
            f"padding:0 10px;font-weight:bold;")
        lay.addWidget(self._total_badge)

        # 关闭
        cb = QPushButton("✕"); cb.setFixedSize(_s(28), _s(28))
        cb.setStyleSheet(
            f"QPushButton{{background:transparent;color:{T3};border:none;"
            f"font-size:{_s(13)}px;border-radius:{_s(14)}px;}}"
            f"QPushButton:hover{{background:{CARD2};color:{T2};}}")
        cb.clicked.connect(self._close_hub)
        lay.addWidget(cb)

        self._main_layout.addWidget(tb)

    def _close_hub(self):
        self.close()
        if self._parent_panel is not None:
            # NOTE: 关闭知识中心后默认返回个人中心的聊天版块
            self._parent_panel.show()
            self._parent_panel.raise_()
            if hasattr(self._parent_panel, '_go'):
                self._parent_panel._go('chat')

    def _build_sidebar(self, parent_lay):
        sb = QWidget()
        sb.setFixedWidth(_s(140))
        sb.setStyleSheet(f"background:{CARD};border-right:1px solid {BD};")
        lay = QVBoxLayout(sb)
        lay.setContentsMargins(_s(0), _s(12), _s(0), _s(8))
        lay.setSpacing(0)

        lay.addWidget(self._sb_label("来源筛选"))

        self._sb_btns = {}
        for key, icon, label in [
            ("all",    "📋", "全部"),
            ("chat",   "💬", "对话"),
            ("doc",    "📄", "文档"),
            ("web",    "🌐", "网络"),
        ]:
            btn = self._make_sb_item(icon, label, key)
            lay.addWidget(btn)
            self._sb_btns[key] = btn

        # 分隔线
        div = QFrame()
        div.setFixedHeight(_s(1))
        div.setStyleSheet(f"background:{BD};border:none;margin:0 {_s(14)}px;")
        lay.addSpacing(_s(8))
        lay.addWidget(div)
        lay.addSpacing(_s(8))

        lay.addWidget(self._sb_label("快捷操作"))

        import_btn = self._make_sb_action("📂", "导入文档")
        import_btn.clicked.connect(self._import_doc)
        lay.addWidget(import_btn)

        crawl_btn = self._make_sb_action("🌐", "信息搜集")
        crawl_btn.clicked.connect(self._show_crawl)
        lay.addWidget(crawl_btn)

        lay.addStretch()

        # 底部危险操作
        div2 = QFrame()
        div2.setFixedHeight(_s(1))
        div2.setStyleSheet(f"background:{BD};border:none;margin:0 {_s(14)}px;")
        lay.addWidget(div2)
        lay.addSpacing(_s(4))
        clear_btn = self._make_sb_action("🗑", "清除全部")
        clear_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:#c0a0a0;border:none;"
            f"text-align:left;padding:{_s(6)}px {_s(10)}px;}}"
            f"QPushButton:hover{{color:#c06060;background:rgba(192,96,96,15);}}")
        clear_btn.clicked.connect(self._clear_all)
        lay.addWidget(clear_btn)

        parent_lay.addWidget(sb)

    def _sb_label(self, text):
        lbl = QLabel(text)
        lbl.setFont(QFont("Microsoft YaHei", _fs(8)))
        lbl.setStyleSheet(f"color:{ACC};background:transparent;border:none;"
                          f"padding:{_s(4)}px {_s(14)}px {_s(2)}px;letter-spacing:1px;")
        return lbl

    def _make_sb_item(self, icon, label, key):
        btn = QPushButton(f"{icon} {label}")
        btn.setFixedHeight(_s(32))
        btn.setFont(QFont("Microsoft YaHei", _fs(10)))
        btn.setCursor(Qt.PointingHandCursor)
        btn.setProperty("filter_key", key)
        btn.clicked.connect(lambda _, k=key: self._set_filter(k))
        return btn

    def _make_sb_action(self, icon, label):
        btn = QPushButton(f"{icon} {label}")
        btn.setFixedHeight(_s(30))
        btn.setFont(QFont("Microsoft YaHei", _fs(10)))
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{ACC};border:none;"
            f"text-align:left;padding:{_s(6)}px {_s(10)}px;}}"
            f"QPushButton:hover{{background:rgba(176,148,128,20);color:{T1};}}")
        return btn

    def _style_sidebar(self):
        for key, btn in self._sb_btns.items():
            if key == self._filter:
                btn.setStyleSheet(
                    f"QPushButton{{background:rgba(176,148,128,35);color:{T1};"
                    f"border:none;border-left:{_s(3)}px solid {ACC};"
                    f"text-align:left;padding:{_s(6)}px {_s(10)}px;font-weight:bold;}}"
                    f"QPushButton:hover{{background:rgba(176,148,128,35);}}")
            else:
                btn.setStyleSheet(
                    f"QPushButton{{background:transparent;color:{T2};"
                    f"border:none;border-left:{_s(3)}px solid transparent;"
                    f"text-align:left;padding:{_s(6)}px {_s(10)}px;}}"
                    f"QPushButton:hover{{background:rgba(176,148,128,20);}}")

    def _build_timeline(self, parent_lay):
        area = QWidget()
        area.setStyleSheet("background:transparent;border:none;")
        area_lay = QVBoxLayout(area)
        area_lay.setContentsMargins(_s(0), _s(0), _s(0), _s(0))
        area_lay.setSpacing(0)

        self._tl_widget = QWidget()
        self._tl_widget.setStyleSheet("background:transparent;border:none;")
        self._tl_layout = QVBoxLayout(self._tl_widget)
        self._tl_layout.setContentsMargins(_s(0), _s(6), _s(0), _s(6))
        self._tl_layout.setSpacing(0)

        self._tl_scroll = QScrollArea()
        self._tl_scroll.setWidgetResizable(True)
        self._tl_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._tl_scroll.setStyleSheet(
            f"QScrollArea{{border:none;background:transparent;}}"
            f"QScrollBar:vertical{{width:{_s(5)}px;background:transparent;}}"
            f"QScrollBar::handle:vertical{{background:{BD};border-radius:{_s(2)}px;}}"
            f"QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0px;}}")
        self._tl_scroll.setWidget(self._tl_widget)
        area_lay.addWidget(self._tl_scroll, 1)

        parent_lay.addWidget(area, 1)

    def _build_bottombar(self):
        bb = QWidget()
        bb.setStyleSheet(f"background:transparent;border-top:1px solid {BD};")
        lay = QHBoxLayout(bb)
        lay.setContentsMargins(_s(14), _s(10), _s(14), _s(10))
        lay.setSpacing(_s(8))
        lay.setAlignment(Qt.AlignTop)

        self._add_input = _MultiLineInput("输入想让桌宠记住的内容…")
        self._add_input.submitted.connect(self._manual_add)
        lay.addWidget(self._add_input, 1)

        add_btn = _btn("添加", 34, primary=True)
        add_btn.setFixedWidth(_s(60))
        add_btn.clicked.connect(self._manual_add)
        lay.addWidget(add_btn, 0, Qt.AlignTop)

        self._main_layout.addWidget(bb)

    # ── 数据刷新 ─────────────────────────────────────────────
    def _refresh(self):
        """重新加载所有数据并刷新界面"""
        self._style_sidebar()
        self._update_badge_counts()
        self._render_timeline()
        self._keep_open_folder = None

    def _update_badge_counts(self):
        mi = self._cs.get_memory_info()
        total = mi.get("facts_count", 0)
        self._total_badge.setText(f"{total} 条记忆")

    def _render_timeline(self):
        """渲染时间线"""
        # 清空
        while self._tl_layout.count():
            it = self._tl_layout.takeAt(0)
            w = it.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        # ── 置顶文档区
        docs = self._cs.get_persona_docs() if hasattr(self._cs, 'get_persona_docs') else []
        if docs and self._filter in ("all", "doc"):
            self._render_pinned_docs(docs)

        # ── 记忆卡片
        facts = self._cs.get_facts()
        if not facts:
            if not docs:
                empty = _lbl("暂无记忆\n和桌宠聊聊天，或导入文档让它认识你~", 10, T3)
                empty.setAlignment(Qt.AlignCenter)
                empty.setWordWrap(True)
                empty.setStyleSheet(f"color:{T3};background:transparent;border:none;"
                                    f"padding:{_s(40)}px {_s(20)}px;")
                self._tl_layout.addWidget(empty)
            self._tl_layout.addStretch()
            return

        # 过滤
        filtered = self._apply_filter(facts)

        if not filtered:
            empty = _lbl("没有匹配的记忆", 10, T3)
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(f"color:{T3};background:transparent;border:none;padding:{_s(30)}px;")
            self._tl_layout.addWidget(empty)
            self._tl_layout.addStretch()
            return

        # ── "全部" 和 "网络" 都用文件夹分组视图 ──
        if self._filter in ("all", "web"):
            self._render_grouped(filtered, facts)
            self._tl_layout.addStretch()
            return

        # ── 对话 / 手动等单一来源：简洁列表 ──
        filtered.sort(key=lambda f: f.get("ts", 0) if isinstance(f, dict) else 0,
                      reverse=True)
        for fact in filtered:
            text = fact.get("text", "") if isinstance(fact, dict) else str(fact)
            if self._search_text and self._search_text.lower() not in text.lower():
                continue
            idx = facts.index(fact) if fact in facts else -1
            mini = self._make_mini_card(
                text,
                fact.get("source", "chat") if isinstance(fact, dict) else "chat",
                fact.get("ts", 0) if isinstance(fact, dict) else 0,
                idx)
            self._tl_layout.addWidget(mini)

        self._tl_layout.addStretch()

    # ── 分组文件夹视图（"全部" 与 "网络" 通用）────────────────
    def _render_grouped(self, filtered, all_facts):
        """将记忆按来源类型/origin 分成文件夹展示"""
        # 构建分组  folder_key → [fact, ...]
        groups = {}
        order = []
        sorted_f = sorted(filtered,
                          key=lambda f: f.get("ts", 0) if isinstance(f, dict) else 0,
                          reverse=True)
        for f in sorted_f:
            if not isinstance(f, dict):
                continue
            if self._search_text and self._search_text.lower() not in f.get("text", "").lower():
                continue
            src = f.get("source", "chat")
            origin = f.get("origin", "")
            if src == "web":
                key = origin or "未分类"
                icon = "🌐"
            elif src in ("chat", "explicit", "freq"):
                key = "💬 对话提取"
                icon = "💬"
            elif src == "manual":
                key = "✏️ 手动添加"
                icon = "✏️"
            else:
                key = "📋 其他"
                icon = "📋"
            if key not in groups:
                groups[key] = {"facts": [], "icon": icon, "src": src}
                order.append(key)
            groups[key]["facts"].append(f)

        if not groups:
            empty = _lbl("没有匹配的记忆", 10, T3)
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(f"color:{T3};background:transparent;border:none;padding:{_s(30)}px;")
            self._tl_layout.addWidget(empty)
            return

        has_search = bool(self._search_text)
        for key in order:
            g = groups[key]
            # NOTE: 文件夸内只有 1 条时自动解散，直接以普通卡片形式呈现
            if len(g["facts"]) == 1:
                fact = g["facts"][0]
                # 移除 origin 让它脱离文件夹分组
                try:
                    idx = all_facts.index(fact)
                    if isinstance(fact, dict) and fact.get("origin"):
                        self._cs.clear_fact_origin(idx)
                except ValueError:
                    idx = -1
                mini = self._make_mini_card(
                    fact.get("text", "") if isinstance(fact, dict) else str(fact),
                    fact.get("source", "chat") if isinstance(fact, dict) else "chat",
                    fact.get("ts", 0) if isinstance(fact, dict) else 0,
                    idx)
                self._tl_layout.addWidget(mini)
            else:
                self._render_folder(key, g["icon"], g["facts"], all_facts,
                                    editable_name=(g["src"] == "web"),
                                    start_open=has_search)

    # ── 通用文件夹渲染 ─────────────────────────────────────────
    def _render_folder(self, title, icon, group_facts, all_facts,
                       editable_name=False, start_open=False):
        """渲染一个可折叠文件夹（支持名称编辑 / 条目编辑 / 增删）"""
        if getattr(self, '_keep_open_folder', None) == title:
            start_open = True
        wrapper = QWidget()
        wrapper.setStyleSheet("background:transparent;border:none;")
        wl = QVBoxLayout(wrapper)
        wl.setContentsMargins(_s(8), _s(4), _s(8), _s(4))
        wl.setSpacing(0)

        folder = QWidget()
        folder.setStyleSheet(
            f"background:{CARD2};border-radius:{_s(14)}px;border:1px solid {BD};")
        fl = QVBoxLayout(folder)
        fl.setContentsMargins(_s(10), _s(8), _s(10), _s(10))
        fl.setSpacing(_s(4))

        # ── 标题行
        header = QHBoxLayout()
        header.setSpacing(_s(6))

        fold_btn = QPushButton("▼")
        fold_btn.setFixedSize(_s(20), _s(20))
        fold_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{T2};border:none;font-size:{_s(10)}px;}}"
            f"QPushButton:hover{{color:{T1};}}")
        header.addWidget(fold_btn)

        icon_lbl = QLabel("📂")
        icon_lbl.setFont(QFont("Microsoft YaHei", _fs(13)))
        icon_lbl.setStyleSheet("background:transparent;border:none;")
        header.addWidget(icon_lbl)

        # 文件夹名（网络来源可编辑，其他只读）
        if editable_name:
            title_edit = QLineEdit(title)
            title_edit.setFont(QFont("Microsoft YaHei", _fs(11)))
            title_edit.setReadOnly(True)
            title_edit.setStyleSheet(
                f"QLineEdit{{color:{T1};background:transparent;border:none;"
                f"font-weight:bold;padding:0;margin:0;}}"
                f"QLineEdit:!read-only{{background:{CARD};border:1.5px solid {ACC};"
                f"border-radius:{_s(8)}px;padding:{_s(2)}px {_s(6)}px;}}")

            edit_name_btn = QPushButton("✎")
            edit_name_btn.setFixedSize(_s(20), _s(20))
            edit_name_btn.setFont(QFont("Arial", _fs(11)))
            edit_name_btn.setToolTip("修改文件夹名称")
            edit_name_btn.setStyleSheet(
                f"QPushButton{{background:transparent;color:{ACC};border:none;"
                f"border-radius:{_s(10)}px;}}"
                f"QPushButton:hover{{color:{T1};background:{CARD};}}")

            _old_origin = title  # capture for closure

            def _start_rename(chk=False, _e=title_edit):
                _e.setReadOnly(False)
                _e.setFocus()
                _e.selectAll()

            def _finish_rename(_e=title_edit, _old=_old_origin):
                _e.setReadOnly(True)
                new_name = _e.text().strip()
                if new_name and new_name != _old:
                    self._cs.rename_folder(_old, new_name)
                    self._refresh()

            edit_name_btn.clicked.connect(_start_rename)
            title_edit.editingFinished.connect(_finish_rename)
            header.addWidget(title_edit, 1)
            header.addWidget(edit_name_btn)
        else:
            title_lbl = QLabel(title)
            title_lbl.setFont(QFont("Microsoft YaHei", _fs(11)))
            title_lbl.setStyleSheet(
                f"color:{T1};background:transparent;border:none;"
                f"font-weight:bold;padding:0;margin:0;")
            header.addWidget(title_lbl, 1)

        count_lbl = QLabel(f"{len(group_facts)} 条")
        count_lbl.setFont(QFont("Microsoft YaHei", _fs(9)))
        count_lbl.setFixedHeight(_s(18))
        count_lbl.setStyleSheet(
            f"background:{CARD};color:{T2};border-radius:{_s(9)}px;"
            f"padding:0 8px;border:none;")
        header.addWidget(count_lbl)

        add_btn = QPushButton("+")
        add_btn.setFixedSize(_s(22), _s(22))
        add_btn.setFont(QFont("Arial", _fs(13)))
        add_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{ACC};border:none;"
            f"border-radius:{_s(11)}px;font-weight:bold;}}"
            f"QPushButton:hover{{background:{CARD};color:{T1};}}")
        add_btn.setToolTip(f"向「{title}」添加内容")
        header.addWidget(add_btn)

        # ── 一键删除整个文件夹
        del_folder_btn = QPushButton("🗑")
        del_folder_btn.setFixedSize(_s(22), _s(22))
        del_folder_btn.setFont(QFont("Arial", _fs(12)))
        del_folder_btn.setToolTip(f"删除整个「{title}」文件夹")
        del_folder_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{T3};border:none;"
            f"border-radius:{_s(11)}px;}}"
            f"QPushButton:hover{{background:#f5ddd0;color:#a04030;}}")

        _folder_src = group_facts[0].get("source", "manual") if group_facts else "manual"
        _folder_origin = title

        def _del_folder(chk=False, _src=_folder_src, _orig=_folder_origin):
            from PyQt5.QtWidgets import QMessageBox
            r = QMessageBox.question(
                self, "确认删除",
                f"确定要删除「{_orig}」文件夹及其中所有 {len(group_facts)} 条记忆吗？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if r == QMessageBox.Yes:
                self._cs.remove_folder(_src, _orig)
                self._refresh()

        del_folder_btn.clicked.connect(_del_folder)
        header.addWidget(del_folder_btn)

        fl.addLayout(header)

        # ── 内容容器（可折叠）
        content = QWidget()
        content.setStyleSheet("background:transparent;border:none;")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(_s(4), _s(4), _s(4), _s(0))
        cl.setSpacing(_s(3))

        for fact in group_facts:
            try:
                idx = all_facts.index(fact)
            except ValueError:
                idx = -1
            mini = self._make_mini_card(
                fact.get("text", ""),
                fact.get("source", "chat"),
                fact.get("ts", 0),
                idx,
                folder_title=title)
            cl.addWidget(mini)

        # ── 行内添加区（默认隐藏）
        inline_row = QWidget()
        inline_row.setStyleSheet("background:transparent;border:none;")
        inline_row.hide()
        ir = QHBoxLayout(inline_row)
        ir.setContentsMargins(_s(0), _s(4), _s(0), _s(0))
        ir.setSpacing(_s(6))
        ir.setAlignment(Qt.AlignTop)

        inline_edit = _MultiLineInput(f"添加内容到「{title}」…")
        ir.addWidget(inline_edit, 1)

        ok_btn = QPushButton("确认")
        ok_btn.setFixedSize(_s(52), _s(34))
        ok_btn.setFont(QFont("Microsoft YaHei", _fs(9)))
        ok_btn.setStyleSheet(
            f"QPushButton{{background:#e8d0c0;color:{T1};border:none;"
            f"border-radius:{_s(10)}px;font-weight:bold;}}"
            f"QPushButton:hover{{background:#dcc0b0;}}")
        ir.addWidget(ok_btn, 0, Qt.AlignTop)

        # 添加来源取决于文件夹类型
        _src_type = group_facts[0].get("source", "manual") if group_facts else "manual"

        def _do_add(*_args, _orig=title, _src=_src_type):
            txt = inline_edit.toPlainText().strip()
            if not txt:
                return
            if _src == "web":
                self._cs.add_web_fact(txt, origin=_orig)
            else:
                self._cs.manual_add_fact(txt)
            self._keep_open_folder = _orig
            self._refresh()

        inline_edit.submitted.connect(_do_add)
        ok_btn.clicked.connect(_do_add)

        cl.addWidget(inline_row)
        fl.addWidget(content)

        # ── 初始折叠状态（搜索时自动展开）
        if start_open:
            content.show()
            fold_btn.setText("▼")
            icon_lbl.setText("📂")
        else:
            content.hide()
            fold_btn.setText("▶")
            icon_lbl.setText("📁")

        # ── 折叠/展开
        def _toggle_fold(checked=False, _c=content, _b=fold_btn, _i=icon_lbl):
            collapsed = _c.isHidden()
            _c.setVisible(collapsed)
            _b.setText("▼" if collapsed else "▶")
            _i.setText("📂" if collapsed else "📁")

        fold_btn.clicked.connect(_toggle_fold)

        # ── "+" 行内输入显隐
        def _toggle_add(checked=False, _row=inline_row, _edit=inline_edit,
                        _c=content, _b=fold_btn, _i=icon_lbl):
            if _c.isHidden():
                _c.show()
                _b.setText("▼")
                _i.setText("📂")
            if _row.isHidden():
                _row.show()
                _edit.setFocus()
            else:
                _row.hide()
                _edit.clear()

        add_btn.clicked.connect(_toggle_add)

        wl.addWidget(folder)
        self._tl_layout.addWidget(wrapper)

    def _make_mini_card(self, text, src, ts, real_idx, folder_title=None):
        """文件夹内的紧凑卡片 — 支持双击编辑文本"""
        card = QWidget()
        card.setStyleSheet(
            f"background:{CARD};border-radius:{_s(10)}px;"
            f"border:1px solid {BD};border-left:3px solid {_source_color(src)};")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(_s(8), _s(6), _s(6), _s(6))
        lay.setSpacing(_s(6))

        # ── 内容区（Label 显示 / TextEdit 编辑切换）
        body = QWidget()
        body.setStyleSheet("background:transparent;border:none;")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(_s(0), _s(0), _s(0), _s(0))
        bl.setSpacing(_s(2))

        txt_lbl = QLabel()
        txt_lbl.setFont(QFont("Microsoft YaHei", _fs(10)))
        txt_lbl.setWordWrap(True)
        txt_lbl.setStyleSheet(
            f"color:{T1};background:transparent;border:none;padding:0;margin:0;")
        if self._search_text:
            import html as _hl
            safe = _hl.escape(text)
            kw   = _hl.escape(self._search_text)
            highlighted = safe.replace(
                kw, f'<span style="background:#ffe0a0;border-radius:{_s(2)}px;'
                    f'padding:0 2px;">{kw}</span>')
            txt_lbl.setTextFormat(Qt.RichText)
            txt_lbl.setText(highlighted)
        else:
            txt_lbl.setTextFormat(Qt.PlainText)
            txt_lbl.setText(text)
        # 保存原始纯文本用于编辑
        txt_lbl.setProperty("plain_text", text)
        bl.addWidget(txt_lbl)

        # 编辑用 TextEdit（默认隐藏）
        txt_edit = _MultiLineInput("", max_h=120)
        txt_edit.hide()
        bl.addWidget(txt_edit)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(_s(4))
        if ts:
            time_lbl = QLabel(_time_ago(ts))
            time_lbl.setFont(QFont("Microsoft YaHei", _fs(8)))
            time_lbl.setStyleSheet(
                f"color:{T3};background:transparent;border:none;padding:0;margin:0;")
            meta_row.addWidget(time_lbl)
        meta_row.addStretch()
        bl.addLayout(meta_row)

        lay.addWidget(body, 1)

        # ── 按钮列（编辑 / 删除）
        btn_col = QVBoxLayout()
        btn_col.setSpacing(_s(2))
        btn_col.setAlignment(Qt.AlignTop)

        edit_btn = QPushButton("✎")
        edit_btn.setFixedSize(_s(20), _s(20))
        edit_btn.setFont(QFont("Arial", _fs(10)))
        edit_btn.setToolTip("编辑内容")
        edit_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{ACC};border:none;border-radius:{_s(10)}px;}}"
            f"QPushButton:hover{{color:{T1};background:{CARD2};}}")
        btn_col.addWidget(edit_btn)

        del_btn = QPushButton("×")
        del_btn.setFixedSize(_s(20), _s(20))
        del_btn.setFont(QFont("Arial", _fs(11)))
        del_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{BD};border:none;border-radius:{_s(10)}px;}}"
            f"QPushButton:hover{{background:#fde8e8;color:#c06060;}}")
        del_btn.clicked.connect(lambda checked=False, i=real_idx, ft=folder_title: self._delete_fact(i, ft))
        btn_col.addWidget(del_btn)

        lay.addLayout(btn_col)

        # ── 编辑切换逻辑
        def _start_edit(checked=False):
            # 取存储的纯文本（避免取到带高亮 HTML）
            plain = txt_lbl.property("plain_text") or txt_lbl.text()
            txt_edit.setPlainText(plain)
            txt_lbl.hide()
            txt_edit.show()
            txt_edit.setFocus()
            edit_btn.setText("✓")
            edit_btn.setToolTip("保存修改")

        def _save_edit(checked=False):
            new_text = txt_edit.toPlainText().strip()
            if new_text and real_idx >= 0:
                self._cs.update_fact_text(real_idx, new_text)
                txt_lbl.setTextFormat(Qt.PlainText)
                txt_lbl.setText(new_text)
                txt_lbl.setProperty("plain_text", new_text)
            # 无论是否有改动，退出编辑模式
            txt_edit.hide()
            txt_lbl.show()
            edit_btn.setText("✎")
            edit_btn.setToolTip("编辑内容")

        def _on_edit_click(checked=False):
            if txt_edit.isHidden():
                _start_edit()
            else:
                _save_edit()

        edit_btn.clicked.connect(_on_edit_click)
        txt_edit.submitted.connect(_save_edit)

        # 外包装
        ww = QWidget()
        ww.setStyleSheet("background:transparent;border:none;")
        wwl = QVBoxLayout(ww)
        wwl.setContentsMargins(_s(2), _s(1), _s(2), _s(1))
        wwl.addWidget(card)
        return ww

    def _apply_filter(self, facts):
        if self._filter == "all":
            return list(facts)
        elif self._filter == "chat":
            return [f for f in facts if isinstance(f, dict) and
                    f.get("source") in ("chat", "explicit", "freq")]
        elif self._filter == "web":
            return [f for f in facts if isinstance(f, dict) and f.get("source") == "web"]
        elif self._filter == "manual":
            return [f for f in facts if isinstance(f, dict) and f.get("source") == "manual"]
        elif self._filter == "doc":
            return []  # 文档在置顶区显示
        return list(facts)

    def _render_pinned_docs(self, docs):
        """渲染置顶文档区"""
        section = QWidget()
        section.setStyleSheet(
            f"background:{CARD2};border-radius:{_s(14)}px;border:1px solid {BD};")
        sl = QVBoxLayout(section)
        sl.setContentsMargins(_s(12), _s(10), _s(12), _s(10))
        sl.setSpacing(_s(4))

        # 标题
        h = QHBoxLayout()
        h.addWidget(_lbl("📌 角色设定文档（永久生效）", 10, T2, True))
        h.addStretch()
        sl.addLayout(h)
        sl.addSpacing(_s(6))

        # 同步状态
        doc_statuses = self._cs.sync_persona_docs() if hasattr(self._cs, 'sync_persona_docs') else []

        for i, doc in enumerate(docs):
            is_default = doc.get("name", "") == "default_persona.txt"

            # 外层容器（行 + 可折叠编辑区）
            doc_wrap = QWidget()
            doc_wrap.setStyleSheet("background:transparent;border:none;")
            dwl = QVBoxLayout(doc_wrap)
            dwl.setContentsMargins(_s(0), _s(0), _s(0), _s(0))
            dwl.setSpacing(_s(4))

            row = QWidget()
            row.setStyleSheet(
                f"background:{CARD};border-radius:{_s(10)}px;border:1px solid {BD};")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(_s(10), _s(7), _s(8), _s(7))
            rl.setSpacing(_s(8))

            icon_lbl = _lbl("📄", 15)
            rl.addWidget(icon_lbl)

            info = QWidget()
            info.setStyleSheet("background:transparent;border:none;")
            il = QVBoxLayout(info)
            il.setContentsMargins(_s(0), _s(0), _s(0), _s(0))
            il.setSpacing(_s(1))
            name = _lbl(doc.get("name", ""), 11, T1)
            name.setStyleSheet(f"color:{T1};background:transparent;border:none;"
                               f"font-weight:bold;padding:0;margin:0;")
            il.addWidget(name)
            path_text = doc.get("path", "")
            if len(path_text) > 40:
                path_text = "..." + path_text[-37:]
            path_lbl = _lbl(path_text, 9, T3)
            path_lbl.setWordWrap(False)
            il.addWidget(path_lbl)
            # NOTE: 确保 info 区域尽可能占满剩余空间，不被右侧按钮挤压
            info.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            rl.addWidget(info, 1)

            # 同步状态
            status = "synced"
            if doc_statuses:
                for ds in doc_statuses:
                    if ds.get("name") == doc.get("name"):
                        status = ds.get("status", "synced")
                        break

            pill = QLabel()
            pill.setFont(QFont("Microsoft YaHei", _fs(9)))
            pill.setFixedHeight(_s(20))
            if status == "synced":
                pill.setText("✓ 已同步")
                pill.setStyleSheet(
                    "background:#e0f0e4;color:#408060;border-radius:10px;"
                    "padding:0 8px;font-weight:bold;")
            elif status == "modified":
                pill.setText("↻ 同步中")
                pill.setStyleSheet(
                    "background:#fef0d8;color:#a08030;border-radius:10px;"
                    "padding:0 8px;font-weight:bold;")
            else:
                pill.setText("✗ 缺失")
                pill.setStyleSheet(
                    "background:#fde8e8;color:#c06060;border-radius:10px;"
                    "padding:0 8px;font-weight:bold;")
            if is_default:
                # 内置人设：编辑按钮放在状态标签左边
                edit_btn = QPushButton("✎")
                edit_btn.setFixedSize(_s(22), _s(22))
                edit_btn.setFont(QFont("Arial", _fs(12)))
                edit_btn.setToolTip("编辑内置人设内容")
                edit_btn.setStyleSheet(
                    f"QPushButton{{background:transparent;color:{ACC};border:none;"
                    f"border-radius:{_s(11)}px;}}"
                    f"QPushButton:hover{{color:{T1};background:{CARD2};}}")
                rl.addWidget(edit_btn)

            rl.addWidget(pill)

            if not is_default:
                # 用户导入的文档：保留删除按钮
                del_btn = QPushButton("×")
                del_btn.setFixedSize(_s(22), _s(22))
                del_btn.setFont(QFont("Arial", _fs(11)))
                del_btn.setStyleSheet(
                    f"QPushButton{{background:transparent;color:{T3};border:none;"
                    f"border-radius:{_s(11)}px;}}"
                    f"QPushButton:hover{{background:#fde8e8;color:#c06060;}}")
                del_btn.clicked.connect(lambda _, idx=i: self._remove_doc(idx))
                rl.addWidget(del_btn)

            dwl.addWidget(row)

            if is_default:
                # 可折叠编辑区
                edit_area = QWidget()
                edit_area.setStyleSheet(
                    f"background:{CARD};border-radius:{_s(10)}px;border:1px solid {BD};")
                edit_area.hide()
                eal = QVBoxLayout(edit_area)
                eal.setContentsMargins(_s(10), _s(8), _s(10), _s(8))
                eal.setSpacing(_s(6))

                persona_edit = QTextEdit()
                persona_edit.setFont(QFont("Microsoft YaHei", _fs(10)))
                persona_edit.setMinimumHeight(120)
                persona_edit.setMaximumHeight(220)
                persona_edit.setStyleSheet(
                    f"QTextEdit{{background:{BG};border:1.5px solid {BD};"
                    f"border-radius:{_s(8)}px;padding:{_s(6)}px;color:{T1};}}"
                    f"QTextEdit:focus{{border-color:{ACC};}}"
                    f"QScrollBar:vertical{{width:{_s(4)}px;background:{CARD2};}}"
                    f"QScrollBar::handle:vertical{{background:{BD};border-radius:{_s(2)}px;}}"
                    f"QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0px;}}")
                eal.addWidget(persona_edit)

                btn_row = QHBoxLayout()
                btn_row.setSpacing(_s(8))
                btn_row.addStretch()
                # NOTE: 不设 setFixedWidth，让按钮根据内边距+文字自适应宽度，
                # 避免中文字符被截断（原60px = padding28px + 文字32px，空间不足）
                cancel_p_btn = _btn("取消", 30)
                cancel_p_btn.setMinimumWidth(_s(64))
                save_p_btn = _btn("保存", 30, primary=True)
                save_p_btn.setMinimumWidth(_s(64))
                btn_row.addWidget(cancel_p_btn)
                btn_row.addWidget(save_p_btn)
                eal.addLayout(btn_row)

                dwl.addWidget(edit_area)

                _doc_path = doc.get("path", "")

                def _toggle_edit(checked=False, _area=edit_area, _te=persona_edit,
                                 _path=_doc_path):
                    if _area.isHidden():
                        try:
                            with open(_path, "r", encoding="utf-8") as f:
                                _te.setPlainText(f.read())
                        except Exception:
                            _te.setPlainText("")
                        _area.show()
                    else:
                        _area.hide()

                def _save_persona(checked=False, _area=edit_area, _te=persona_edit,
                                  _path=_doc_path, _pill=pill):
                    try:
                        with open(_path, "w", encoding="utf-8") as f:
                            f.write(_te.toPlainText())
                        _pill.setText("✓ 已同步")
                        _pill.setStyleSheet(
                            "background:#e0f0e4;color:#408060;border-radius:10px;"
                            "padding:0 8px;font-weight:bold;")
                    except Exception:
                        pass
                    _area.hide()

                def _cancel_edit(checked=False, _area=edit_area):
                    _area.hide()

                edit_btn.clicked.connect(_toggle_edit)
                save_p_btn.clicked.connect(_save_persona)
                cancel_p_btn.clicked.connect(_cancel_edit)

            sl.addWidget(doc_wrap)

        w_container = QWidget()
        w_container.setStyleSheet("background:transparent;border:none;")
        cl = QVBoxLayout(w_container)
        cl.setContentsMargins(_s(8), _s(6), _s(8), _s(2))
        cl.addWidget(section)
        self._tl_layout.addWidget(w_container)

    def _make_day_label(self, text):
        w = QWidget()
        w.setFixedHeight(_s(28))
        w.setStyleSheet("background:transparent;border:none;")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(_s(14), _s(6), _s(14), _s(0))
        lbl = _lbl(text, 9, ACC)
        lbl.setStyleSheet(f"color:{ACC};background:transparent;border:none;"
                          f"font-weight:bold;letter-spacing:1px;padding:0;margin:0;")
        lay.addWidget(lbl)
        line = QFrame()
        line.setFixedHeight(_s(1))
        line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        line.setStyleSheet(f"background:{BD};border:none;")
        lay.addWidget(line, 1)
        return w

    def _make_card(self, text, src, ts, origin, real_idx):
        card = QWidget()
        card.setStyleSheet(
            f"background:{CARD};border-radius:{_s(12)}px;"
            f"border:1px solid {BD};border-left:3.5px solid {_source_color(src)};")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(_s(10), _s(8), _s(8), _s(8))
        lay.setSpacing(_s(8))

        # 来源图标
        icon = _lbl(_source_icon(src), 14)
        icon.setFixedSize(_s(24), _s(24))
        lay.addWidget(icon, 0, Qt.AlignTop)

        # 内容区
        body = QWidget()
        body.setStyleSheet("background:transparent;border:none;")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(_s(0), _s(0), _s(0), _s(0))
        bl.setSpacing(_s(3))

        # 文本（搜索高亮）
        display_text = text
        if self._search_text:
            kw = self._search_text
            # 简单高亮
            display_text = text.replace(kw, f"【{kw}】")

        txt_lbl = QLabel(display_text)
        txt_lbl.setFont(QFont("Microsoft YaHei", _fs(10)))
        txt_lbl.setWordWrap(True)
        txt_lbl.setStyleSheet(f"color:{T1};background:transparent;border:none;padding:0;margin:0;")
        bl.addWidget(txt_lbl)

        # 元数据行
        meta = QHBoxLayout()
        meta.setSpacing(_s(5))
        if ts:
            time_lbl = _lbl(_time_ago(ts), 9, T3)
            meta.addWidget(time_lbl)

        tag = QLabel(_source_label(src))
        tag.setFont(QFont("Microsoft YaHei", _fs(8)))
        tag.setFixedHeight(_s(16))
        tag.setStyleSheet(f"{_source_tag_style(src)}border-radius:{_s(8)}px;padding:0 6px;"
                          f"border:none;")
        meta.addWidget(tag)

        if origin:
            otag = QLabel(origin)
            otag.setFont(QFont("Microsoft YaHei", _fs(8)))
            otag.setFixedHeight(_s(16))
            otag.setStyleSheet(f"background:{CARD2};color:{T2};border-radius:{_s(8)}px;"
                               f"padding:0 6px;border:none;")
            meta.addWidget(otag)

        meta.addStretch()
        bl.addLayout(meta)
        lay.addWidget(body, 1)

        # 删除按钮
        del_btn = QPushButton("×")
        del_btn.setFixedSize(_s(22), _s(22))
        del_btn.setFont(QFont("Arial", _fs(12)))
        del_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{BD};border:none;"
            f"border-radius:{_s(11)}px;}}"
            f"QPushButton:hover{{background:#fde8e8;color:#c06060;}}")
        del_btn.clicked.connect(lambda _, i=real_idx: self._delete_fact(i))
        lay.addWidget(del_btn, 0, Qt.AlignTop)

        # 外部 margin wrapper
        wrapper = QWidget()
        wrapper.setStyleSheet("background:transparent;border:none;")
        wl = QVBoxLayout(wrapper)
        wl.setContentsMargins(_s(12), _s(2), _s(12), _s(2))
        wl.addWidget(card)
        return wrapper

    # ── 操作 ─────────────────────────────────────────────────
    def _set_filter(self, key):
        self._filter = key
        self._refresh()

    def _on_search(self, text):
        self._search_text = text.strip()
        self._render_timeline()

    def _manual_add(self):
        text = self._add_input.toPlainText().strip()
        if not text:
            return
        self._cs.manual_add_fact(text)
        self._add_input.clear()
        self._keep_open_folder = "✏️ 手动添加"
        self._refresh()

    def _delete_fact(self, idx, folder_title=None):
        if idx >= 0:
            if folder_title:
                self._keep_open_folder = folder_title
            self._cs.manual_remove_fact(idx)
            self._refresh()

    def _import_doc(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择人设/设定文档", "",
            "文本文件 (*.txt);;PDF 文件 (*.pdf);;所有文件 (*)")
        if not path:
            return
        if hasattr(self._cs, 'add_persona_doc'):
            self._cs.add_persona_doc(path)
        self._refresh()

    def _remove_doc(self, idx):
        if hasattr(self._cs, 'remove_persona_doc'):
            self._cs.remove_persona_doc(idx)
        self._refresh()

    def _show_crawl(self):
        self._crawl_overlay.setGeometry(0, 0, self.width(), self.height())
        self._crawl_overlay.show()
        self._crawl_overlay.raise_()

    def _clear_all(self):
        ret = QMessageBox.question(
            self, "清除记忆",
            "确定要清除桌宠的所有记忆吗？\n（人设文档不受影响）",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if ret == QMessageBox.Yes:
            self._cs.clear_memory()
            self._refresh()
