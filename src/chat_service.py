"""
聊天服务 — 支持用户自定义 API，长期记忆存储与迭代
记忆策略：
  - 显式声明（含"记住/别忘了/我叫/我喜欢"等）→ 立即入库
  - 普通对话关键词 → 追踪频次，高频（>=2次）自动升级为记忆
  - 不记录URL，只记录有意义的内容
记忆来源：
  - chat: 对话提取
  - web: 网络爬取
  - manual: 用户手动添加
  - explicit: 触发词命中
  - freq: 高频关键词升级
"""
import json
import os
import re
import ssl
import time
import threading
from urllib.request import Request, urlopen

from src.user_data import (
    config_path, memory_path, default_persona_path, get_user_file, PROJECT_ROOT,
)

CONFIG_FILE = config_path()
MEMORY_FILE = memory_path()
MAX_MEMORY_RECENT = 50   # 保留最近轮数
MAX_CONTEXT_MESSAGES = 20
FREQ_THRESHOLD = 2        # 关键词出现几次后升入记忆

# 显式记忆触发词
_EXPLICIT_TRIGGERS = [
    "记住", "别忘了", "我叫", "我是", "我喜欢", "我讨厌",
    "我最喜欢", "我最讨厌", "我住在", "我今年", "我的名字",
]

# 话题提取模式：动词 + 跟随内容（取动词后 2~10 个字）
_TOPIC_PATTERNS = [
    re.compile(p) for p in [
        r"喜欢([^\s，。！？、；：…]{2,10})",
        r"讨厌([^\s，。！？、；：…]{2,10})",
        r"在用([^\s，。！？、；：…]{2,8})",
        r"在玩([^\s，。！？、；：…]{2,8})",
        r"在看([^\s，。！？、；：…]{2,8})",
        r"在学([^\s，。！？、；：…]{2,8})",
        r"喝([^\s，。！？、；：…]{1,6})",
        r"吃([^\s，。！？、；：…]{1,6})",
        r"叫([^\s，。！？、；：…]{1,8})",
        r"用([^\s，。！？、；：…]{2,8})软件",
        r"用([^\s，。！？、；：…]{2,8})工具",
        r"推荐([^\s，。！？、；：…]{2,10})",
    ]
]

# URL 提取（气泡显示用，不写入记忆）
_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_TRAIL  = '.,;:!?\'"），。！？；：、'


def extract_urls(text):
    return [u.rstrip(_TRAIL) for u in _URL_RE.findall(text)]


def _default_config():
    return {"api_url": "", "api_key": "", "model": "", "enabled": False}


def _load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default() if callable(default) else default


def _save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


class ChatService:
    def __init__(self):
        self.config  = _load_json(CONFIG_FILE, _default_config)
        self._memory = _load_json(MEMORY_FILE, self._default_memory)
        self._migrate_memory()
        self._ensure_default_persona()
        # 主动聊天：当日 API 是否成功过
        self._api_confirmed_today = False
        self._api_confirm_date = ""

    @staticmethod
    def _default_memory():
        return {
            "summary":      "",
            "facts":        [],          # 已确认记忆列表 [{text, source, ts, origin?}]
            "recent":       [],          # 近期对话历史
            "kw_freq":      {},          # 候选关键词频次 {word: count}
            "persona_docs": [],          # 人设文档 [{path, name, mtime}]
        }

    def _migrate_memory(self):
        """兼容旧版记忆格式"""
        for key, val in self._default_memory().items():
            if key not in self._memory:
                self._memory[key] = val
        # 旧版有 urls 字段，清除
        self._memory.pop("urls", None)
        # Migrate old string facts to new dict format
        facts = self._memory.get("facts", [])
        if facts and isinstance(facts[0], str):
            self._memory["facts"] = [
                {"text": f, "source": "chat", "ts": 0} for f in facts
            ]
        # Ensure persona_docs exists
        if "persona_docs" not in self._memory:
            self._memory["persona_docs"] = []

    # ── 首次使用检测 ────────────────────────────────────────
    @property
    def is_first_launch(self) -> bool:
        """首次使用：既没有 API Key，也没有任何聊天历史"""
        return (
            not self.config.get("api_key")
            and not self._memory.get("recent")
        )

    def _ensure_default_persona(self):
        """注册内置角色设定文档，并确保用户编辑可持久保存。

        内置 default_persona.txt 捆绑在 EXE 内部（_MEIPASS 临时目录），
        直接写入该路径会在关闭后丢失。因此首次启动时复制到用户数据目录
        geren/default_persona.txt，后续所有读写都指向这个可写副本。
        """
        import shutil
        # 用户数据目录下的可写副本（geren/default_persona.txt）
        user_dp = get_user_file("default_persona.txt")
        # EXE 内捆绑的只读原件（_MEIPASS/data/default_persona.txt）
        bundled_dp = default_persona_path()

        # 首次启动：将内置文档复制到用户目录
        if not os.path.exists(user_dp) and os.path.exists(bundled_dp):
            try:
                shutil.copy2(bundled_dp, user_dp)
            except Exception:
                pass

        # 实际使用的路径：优先用户目录（可写），回退到内置（只读）
        dp = user_dp if os.path.exists(user_dp) else bundled_dp
        if not os.path.exists(dp):
            return

        docs = self._memory.get("persona_docs", [])
        for d in docs:
            if os.path.basename(d.get("path", "")) == "default_persona.txt":
                # 路径可能指向旧的 _MEIPASS 或用户目录，统一刷新
                if d["path"] != dp:
                    d["path"] = dp
                    d["mtime"] = os.path.getmtime(dp)
                    self._save_memory()
                return
        # 全新注册
        mtime = os.path.getmtime(dp)
        docs.insert(0, {"path": dp, "name": "default_persona.txt", "mtime": mtime})
        self._memory["persona_docs"] = docs
        self._save_memory()

    # ── 配置 ─────────────────────────────────────────────────
    @property
    def enabled(self):
        return bool(
            self.config.get("enabled")
            and self.config.get("api_url")
            and self.config.get("api_key")
        )

    def save_config(self):
        _save_json(CONFIG_FILE, self.config)

    def update_config(self, api_url, api_key, model):
        self.config["api_url"] = api_url.strip().rstrip("/")
        self.config["api_key"] = api_key.strip()
        self.config["model"]   = model.strip()
        self.config["enabled"] = bool(api_url and api_key)
        self.save_config()

    def _build_api_url(self):
        """
        根据用户填写的 API 地址智能拼接完整请求 URL。
        支持的格式：
          - https://api.openai.com/v1               → .../v1/chat/completions
          - https://newapi.nekotick.org              → .../v1/chat/completions
          - https://api.klong.lat/v1/chat/completions → 原样使用
          - https://example.com/api/v1               → .../v1/chat/completions
        """
        url = self.config["api_url"].strip().rstrip("/")
        if "/chat/completions" in url:
            return url
        if url.endswith("/v1"):
            return url + "/chat/completions"
        # 如果路径中已经有 /v1/，补上 chat/completions
        if "/v1/" in url:
            return url.rstrip("/") + "/chat/completions"
        # 否则补全 /v1/chat/completions
        return url + "/v1/chat/completions"

    def _save_memory(self):
        _save_json(MEMORY_FILE, self._memory)

    # ── System Prompt ─────────────────────────────────────────
    def _build_system_prompt(self, pet_state=None):
        parts = []

        # 1. Persona docs — ALWAYS FIRST, ALWAYS FULL, never truncated
        persona_content = self._load_persona_content()
        if persona_content:
            parts.append(persona_content)

        # 2. Base pet identity and state
        lines = ["你是一只可爱的桌面宠物，名字叫做"]
        if pet_state:
            lines[0] += f"「{pet_state.name}」。"
            lines.append(
                f"当前状态：等级 Lv.{pet_state.level}，"
                f"饱食度 {int(pet_state.hunger)}，心情 {int(pet_state.happiness)}，"
                f"体力 {int(pet_state.energy)}，亲密度 {int(pet_state.intimacy)}。"
            )
            lines.append(f"已陪伴主人 {int(pet_state.age_days)} 天。")
        else:
            lines[0] += "「桌宠」。"

        lines.append(
            "请用可爱、活泼的语气回复，像一个有感情的小宠物。"
            "回复简短（1-3句话），可以用颜文字。"
            "如果主人问到网站或工具，可以在回复里附上完整的 https:// 网址方便点击。"
        )

        if self._memory.get("summary"):
            lines.append(f"\n关于主人的记忆摘要：{self._memory['summary']}")

        parts.append("\n".join(lines))

        # 3. Conversation facts — subject to 40-item limit (show last 12)
        facts = self._memory.get("facts", [])
        if facts:
            fact_texts = []
            for f in facts[-12:]:
                if isinstance(f, dict):
                    fact_texts.append(f["text"])
                else:
                    fact_texts.append(f)
            parts.append("关于主人记住的事：" + "；".join(fact_texts))

        return "\n".join(parts)

    def _build_messages(self, user_msg, pet_state=None):
        msgs = [{"role": "system", "content": self._build_system_prompt(pet_state)}]
        for m in self._memory.get("recent", [])[-MAX_CONTEXT_MESSAGES:]:
            msgs.append({"role": m["role"], "content": m["content"]})
        msgs.append({"role": "user", "content": user_msg})
        return msgs

    # ── 连接测试（不写入记忆） ──────────────────────────────────
    def test_connection(self, callback=None):
        """轻量连接测试，不写入记忆/对话历史"""
        if not self.enabled:
            if callback:
                callback(None, "API 未配置，请先填写 API 地址和 Key")
            return

        def _do():
            try:
                url = self._build_api_url()
                body = json.dumps({
                    "model":      self.config.get("model") or "gpt-3.5-turbo",
                    "messages":   [{"role": "user", "content": "hi"}],
                    "max_tokens": 10,
                }).encode("utf-8")
                req = Request(url, data=body, method="POST")
                req.add_header("Content-Type", "application/json")
                req.add_header("Authorization", f"Bearer {self.config['api_key']}")
                req.add_header("User-Agent", "DesktopPet/1.0")
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                with urlopen(req, timeout=15, context=ctx) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                result["choices"][0]["message"]["content"]  # 确认字段存在
                if callback:
                    callback(True, None)
            except Exception as e:
                err_msg = str(e)
                body_bytes = getattr(e, 'fp', None) or (e if hasattr(e, 'read') else None)
                if body_bytes is not None:
                    try:
                        raw = body_bytes.read()
                        err_body = json.loads(raw.decode("utf-8"))
                        detail = (err_body.get("error") or {}).get("message", "")
                        if not detail:
                            detail = err_body.get("message", "")
                        if detail:
                            err_msg = detail
                    except Exception:
                        pass
                if callback:
                    callback(None, err_msg)

        threading.Thread(target=_do, daemon=True).start()

    # ── 聊天 ─────────────────────────────────────────────────
    def chat(self, user_msg, pet_state=None, callback=None):
        if not self.enabled:
            if callback:
                callback(None, "API 未配置，请先在设置中填写 API 信息")
            return

        def _do():
            try:
                msgs = self._build_messages(user_msg, pet_state)
                url  = self._build_api_url()
                body = json.dumps({
                    "model":       self.config.get("model") or "gpt-3.5-turbo",
                    "messages":    msgs,
                    "max_tokens":  400,
                    "temperature": 0.8,
                }).encode("utf-8")
                req = Request(url, data=body, method="POST")
                req.add_header("Content-Type", "application/json")
                req.add_header("Authorization", f"Bearer {self.config['api_key']}")
                req.add_header("User-Agent", "DesktopPet/1.0")
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                with urlopen(req, timeout=30, context=ctx) as resp:
                    raw = resp.read().decode("utf-8")
                    result = json.loads(raw)
                reply = result["choices"][0]["message"]["content"].strip()
                self._record(user_msg, reply)
                self._mark_api_ok()
                if callback:
                    callback(reply, None)
            except Exception as e:
                err_msg = str(e)
                # 尝试从响应体中提取更详细的错误信息
                body_bytes = getattr(e, 'fp', None)
                if body_bytes is None and hasattr(e, 'read'):
                    body_bytes = e
                if body_bytes is not None:
                    try:
                        raw = body_bytes.read()
                        err_body = json.loads(raw.decode("utf-8"))
                        detail = (err_body.get("error") or {}).get("message", "")
                        if not detail:
                            detail = err_body.get("message", "")
                        if detail:
                            err_msg = f"{err_msg} — {detail}"
                    except Exception:
                        pass
                if callback:
                    callback(None, f"[{url}]\n{err_msg}")

        threading.Thread(target=_do, daemon=True).start()

    # ── 记忆提取 ─────────────────────────────────────────────
    def _record(self, user_msg, reply):
        recent = self._memory.get("recent", [])
        recent.append({"role": "user",      "content": user_msg, "ts": time.time()})
        recent.append({"role": "assistant", "content": reply,    "ts": time.time()})
        if len(recent) > MAX_MEMORY_RECENT * 2:
            self._summarize_old(recent[:20])
            del recent[:20]
        self._memory["recent"] = recent

        self._process_memory(user_msg)
        self._save_memory()

    def _process_memory(self, user_msg):
        """判断是否将用户消息内容写入记忆"""
        text = user_msg.strip()

        # 1. 显式声明 → 直接入库
        for t in _EXPLICIT_TRIGGERS:
            if t in text:
                self._add_fact(text, source="explicit")
                return

        # 2. 话题提取 → 统计频次，高频升入记忆
        for pat in _TOPIC_PATTERNS:
            m = pat.search(text)
            if m:
                kw = m.group(1).strip()
                if kw:
                    self._track_keyword(kw, context=text)
                    return  # 每条消息只追踪一个关键词

    def _track_keyword(self, kw, context=""):
        freq = self._memory.get("kw_freq", {})
        freq[kw] = freq.get(kw, 0) + 1
        self._memory["kw_freq"] = freq

        if freq[kw] >= FREQ_THRESHOLD:
            # 升级为正式记忆
            fact = context.strip() if context else kw
            self._add_fact(fact, source="freq")
            # 清除频次记录，避免重复升级
            del freq[kw]

    def _add_fact(self, text, source="manual", origin=""):
        facts = self._memory.get("facts", [])
        text = text.strip()
        if not text:
            return
        # Check for duplicate text
        if any(f["text"] == text for f in facts if isinstance(f, dict)):
            return
        entry = {"text": text, "source": source, "ts": time.time()}
        if origin:
            entry["origin"] = origin
        facts.append(entry)
        if len(facts) > 40:
            facts = facts[-40:]
        self._memory["facts"] = facts

    def _summarize_old(self, old_messages):
        texts = []
        for m in old_messages:
            role = "主人" if m["role"] == "user" else "宠物"
            texts.append(f"{role}：{m['content']}")
        old_sum = self._memory.get("summary", "")
        piece   = "；".join(t[:30] for t in texts[:5])
        self._memory["summary"] = (old_sum + "。之后，" + piece if old_sum
                                   else "早期对话摘要：" + piece)
        if len(self._memory["summary"]) > 500:
            self._memory["summary"] = self._memory["summary"][-500:]

    # ── 手动记忆管理 ─────────────────────────────────────────
    def manual_add_fact(self, text):
        """手动添加一条记忆"""
        self._add_fact(text, source="manual")
        self._save_memory()

    def add_web_fact(self, text, origin=""):
        """添加网络爬取的记忆"""
        self._add_fact(text, source="web", origin=origin)
        self._save_memory()

    def manual_remove_fact(self, index):
        """按下标删除一条记忆"""
        facts = self._memory.get("facts", [])
        if 0 <= index < len(facts):
            facts.pop(index)
            self._memory["facts"] = facts
            self._save_memory()

    def remove_folder(self, source: str, origin: str = ""):
        """
        一键删除整个文件夹内的所有记忆条目。
        对于 web 来源按 origin 匹配；对于 chat/manual 等按 source 匹配。
        """
        facts = self._memory.get("facts", [])
        if source == "web":
            new_facts = [
                f for f in facts
                if not (isinstance(f, dict) and f.get("source") == "web"
                        and f.get("origin", "") == origin)
            ]
        else:
            # chat/explicit/freq 归为一组，manual 归为一组
            if source in ("chat", "explicit", "freq"):
                match_sources = {"chat", "explicit", "freq"}
            else:
                match_sources = {source}
            new_facts = [
                f for f in facts
                if not (isinstance(f, dict) and f.get("source") in match_sources)
            ]
        self._memory["facts"] = new_facts
        self._save_memory()

    def clear_fact_origin(self, index: int):
        """移除指定记忆的 origin 字段，使其脱离文件夹显示"""
        facts = self._memory.get("facts", [])
        if 0 <= index < len(facts) and isinstance(facts[index], dict):
            facts[index].pop("origin", None)
            self._memory["facts"] = facts
            self._save_memory()

    def update_fact_text(self, index, new_text):
        """修改指定记忆的文本内容"""
        facts = self._memory.get("facts", [])
        new_text = new_text.strip()
        if 0 <= index < len(facts) and new_text:
            if isinstance(facts[index], dict):
                facts[index]["text"] = new_text
            else:
                facts[index] = new_text
            self._memory["facts"] = facts
            self._save_memory()

    def rename_folder(self, old_origin, new_origin):
        """重命名文件夹（修改所有匹配 origin 的记忆）"""
        new_origin = new_origin.strip()
        if not new_origin or old_origin == new_origin:
            return
        facts = self._memory.get("facts", [])
        changed = False
        for f in facts:
            if isinstance(f, dict) and f.get("origin") == old_origin:
                f["origin"] = new_origin
                changed = True
        if changed:
            self._memory["facts"] = facts
            self._save_memory()

    def remove_recent_pair(self, pair_index):
        """删除第 pair_index 轮对话（一对 user+assistant），同时清除相关记忆"""
        recent = self._memory.get("recent", [])
        # pair_index 对应 recent 中的 [pair_index*2, pair_index*2+1]
        start = pair_index * 2
        if start < 0 or start >= len(recent):
            return
        # 取出被删除的用户消息，用于清除相关记忆
        user_msg = recent[start]["content"] if start < len(recent) else ""
        # 删除这一对消息
        end = min(start + 2, len(recent))
        del recent[start:end]
        self._memory["recent"] = recent
        # 尝试清除由这条用户消息产生的相关记忆
        if user_msg:
            self._remove_related_facts(user_msg)
        self._save_memory()

    def remove_single_message(self, msg_index):
        """删除 recent 中指定下标的单条消息，若为 user 则同时删除紧随其后的 assistant 回复"""
        recent = self._memory.get("recent", [])
        if msg_index < 0 or msg_index >= len(recent):
            return
        msg = recent[msg_index]
        if msg["role"] == "user":
            # 删除 user + 下一条 assistant（若存在）
            end = msg_index + 2 if (msg_index + 1 < len(recent) and
                                     recent[msg_index + 1]["role"] == "assistant") else msg_index + 1
            user_text = msg["content"]
            del recent[msg_index:end]
            self._remove_related_facts(user_text)
        else:
            # 仅删除 assistant 回复
            del recent[msg_index]
        self._memory["recent"] = recent
        self._save_memory()

    _NICK_PATTERNS = [
        # "叫我X" / "称呼我X" / "喊我X"（最常见）
        re.compile(r"(?:叫我|称呼我|喊我|叫我做|叫我为)\s*(\S{1,8})"),
        # "直接叫X" / "就叫X" / "请叫X"（省略"我"的变体）
        re.compile(r"(?:直接|就|请)叫\s*(\S{1,8})"),
        # "我叫X" / "我的名字是X"
        re.compile(r"(?:我叫|我的名字(?:是|叫))\s*(\S{1,8})"),
    ]
    # 提取后需要排除的无效匹配
    _NICK_EXCLUDE = {"主人", "我", "你", "他", "她", "它", "什么", "啥",
                     "你的", "他的", "她的", "我的"}

    def get_user_nickname(self) -> str:
        """
        从记忆和对话中提取用户希望被称呼的名字。
        优先扫描 facts，再扫描 recent 对话。
        未找到则返回 '主人'。
        """
        for f in reversed(self._memory.get("facts", [])):
            text = f["text"] if isinstance(f, dict) else f
            name = self._extract_nick(text)
            if name:
                return name
        for m in reversed(self._memory.get("recent", [])):
            if m.get("role") != "user":
                continue
            name = self._extract_nick(m["content"])
            if name:
                return name
        return "主人"

    def _extract_nick(self, text: str) -> str | None:
        for pat in self._NICK_PATTERNS:
            m = pat.search(text)
            if m:
                name = m.group(1).rstrip("，。！,. 吧呢啊哦呀")
                if name and name not in self._NICK_EXCLUDE:
                    return name
        return None

    def _remove_related_facts(self, user_msg):
        """移除与指定用户消息高度相关的记忆条目"""
        facts = self._memory.get("facts", [])
        if not facts or not user_msg:
            return
        # 提取用户消息中的关键词片段（取前60字符作为匹配依据）
        snippet = user_msg.strip()[:60]
        # 移除 source=="chat" 或 "explicit" 且文本与用户消息高度重合的记忆
        new_facts = []
        for f in facts:
            if not isinstance(f, dict):
                new_facts.append(f)
                continue
            if f.get("source") in ("chat", "explicit", "freq"):
                # 若记忆文本包含用户消息片段，或用户消息包含记忆文本，视为相关
                ft = f.get("text", "")
                if snippet in ft or ft in user_msg:
                    continue  # 移除
            new_facts.append(f)
        self._memory["facts"] = new_facts

    def get_facts(self):
        """返回记忆列表（dict格式）"""
        return list(self._memory.get("facts", []))

    def get_facts_text(self):
        """返回记忆的纯文本列表（向后兼容）"""
        facts = self._memory.get("facts", [])
        result = []
        for f in facts:
            if isinstance(f, dict):
                result.append(f["text"])
            else:
                result.append(f)
        return result

    # ── Persona 文档管理 ───────────────────────────────────────
    def add_persona_doc(self, file_path):
        """注册一个 txt/pdf 文件为人设文档"""
        docs = self._memory.get("persona_docs", [])
        file_path = os.path.abspath(file_path)
        # 避免重复添加同一路径
        if any(d["path"] == file_path for d in docs):
            return
        mtime = os.path.getmtime(file_path) if os.path.exists(file_path) else 0.0
        docs.append({
            "path": file_path,
            "name": os.path.basename(file_path),
            "mtime": mtime,
        })
        self._memory["persona_docs"] = docs
        self._save_memory()

    def remove_persona_doc(self, index):
        """按下标移除一个人设文档"""
        docs = self._memory.get("persona_docs", [])
        if 0 <= index < len(docs):
            docs.pop(index)
            self._memory["persona_docs"] = docs
            self._save_memory()

    def get_persona_docs(self):
        """返回人设文档列表"""
        return list(self._memory.get("persona_docs", []))

    def _load_persona_content(self):
        """读取所有注册的人设文档，返回合并文本"""
        docs = self._memory.get("persona_docs", [])
        if not docs:
            return ""
        parts = []
        for doc in docs:
            path = doc.get("path", "")
            if not os.path.exists(path):
                continue
            # Update mtime if changed
            current_mtime = os.path.getmtime(path)
            if current_mtime != doc.get("mtime"):
                doc["mtime"] = current_mtime
            ext = os.path.splitext(path)[1].lower()
            if ext == ".txt":
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                    if content:
                        parts.append(f"[人设文档: {doc['name']}]\n{content}")
                except Exception:
                    pass
            elif ext == ".pdf":
                # PDF支持需要额外库（如 PyPDF2/pdfplumber），暂时跳过
                parts.append(f"[人设文档: {doc['name']}]（PDF文件，需要额外库解析）")
        return "\n\n".join(parts)

    def sync_persona_docs(self):
        """检查所有人设文档的修改时间变化"""
        docs = self._memory.get("persona_docs", [])
        results = []
        for doc in docs:
            path = doc.get("path", "")
            if not os.path.exists(path):
                results.append({"name": doc.get("name", ""), "status": "missing"})
                continue
            current_mtime = os.path.getmtime(path)
            if current_mtime != doc.get("mtime"):
                doc["mtime"] = current_mtime
                results.append({"name": doc["name"], "status": "modified"})
            else:
                results.append({"name": doc["name"], "status": "synced"})
        self._memory["persona_docs"] = docs
        self._save_memory()
        return results

    # ── 信息查询 ─────────────────────────────────────────────
    def get_memory_info(self):
        facts = self._memory.get("facts", [])
        return {
            "facts_count":  len(facts),
            "chat_count":   sum(1 for f in facts if isinstance(f, dict) and f.get("source") in ("chat", "explicit", "freq")),
            "web_count":    sum(1 for f in facts if isinstance(f, dict) and f.get("source") == "web"),
            "manual_count": sum(1 for f in facts if isinstance(f, dict) and f.get("source") == "manual"),
            "doc_count":    len(self._memory.get("persona_docs", [])),
            "recent_count": len(self._memory.get("recent", [])),
            "pending_kw":   len(self._memory.get("kw_freq", {})),
            "has_summary":  bool(self._memory.get("summary")),
        }

    def clear_memory(self):
        """清除记忆，但保留人设文档（用户显式导入的）"""
        saved_docs = self._memory.get("persona_docs", [])
        self._memory = self._default_memory()
        self._memory["persona_docs"] = saved_docs
        self._save_memory()

    # ── 主动聊天 ─────────────────────────────────────────────
    def _mark_api_ok(self):
        """标记当日 API 已成功（首次对话正常回复后调用）"""
        from datetime import date
        today = date.today().isoformat()
        self._api_confirmed_today = True
        self._api_confirm_date = today

    @property
    def api_ready_today(self) -> bool:
        """当日是否已有过成功的 API 调用"""
        from datetime import date
        if self._api_confirm_date != date.today().isoformat():
            self._api_confirmed_today = False
        return self._api_confirmed_today and self.enabled

    def proactive_chat(self, pet_state=None, callback=None):
        """桌宠主动找用户说话（不需要用户输入）"""
        if not self.api_ready_today:
            return

        def _do():
            try:
                prompt = self._build_system_prompt(pet_state)
                prompt += (
                    "\n\n【特殊指令】现在主人已经很久没有跟你互动了。"
                    "请你主动找主人说话，可以是关心主人、撒娇、分享趣事、"
                    "提醒休息、或者聊聊之前的话题。"
                    "语气自然可爱，像是你忍不住想找主人说话一样。"
                    "简短一两句就好，不要太长。"
                )
                msgs = [{"role": "system", "content": prompt}]
                # 带上最近几轮对话作为上下文
                for m in self._memory.get("recent", [])[-6:]:
                    msgs.append({"role": m["role"], "content": m["content"]})
                msgs.append({"role": "user", "content": "[系统：主人长时间未互动，请主动说话]"})

                url  = self._build_api_url()
                body = json.dumps({
                    "model":       self.config.get("model") or "gpt-3.5-turbo",
                    "messages":    msgs,
                    "max_tokens":  150,
                    "temperature": 0.9,
                }).encode("utf-8")
                req = Request(url, data=body, method="POST")
                req.add_header("Content-Type", "application/json")
                req.add_header("Authorization", f"Bearer {self.config['api_key']}")
                req.add_header("User-Agent", "DesktopPet/1.0")
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                with urlopen(req, timeout=30, context=ctx) as resp:
                    raw = resp.read().decode("utf-8")
                    result = json.loads(raw)
                reply = result["choices"][0]["message"]["content"].strip()
                if callback:
                    callback(reply, None)
            except Exception as e:
                if callback:
                    callback(None, str(e))

        threading.Thread(target=_do, daemon=True).start()
