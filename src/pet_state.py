import json
import os
import time
from enum import Enum, auto
from src.user_data import pet_save_path


class PetMood(Enum):
    HAPPY = auto()
    NORMAL = auto()
    SAD = auto()
    HUNGRY = auto()
    SLEEPY = auto()
    SLEEPING = auto()


class PetAction(Enum):
    IDLE = auto()
    WALK_LEFT = auto()
    WALK_RIGHT = auto()
    SLEEP = auto()
    EAT = auto()
    PLAY = auto()
    DRAG = auto()
    FALL = auto()
    DANCE = auto()
    WAVE = auto()
    CLING = auto()
    LAND = auto()
    GET_UP = auto()
    CAT = auto()
    STUDY = auto()


class PetState:
    SAVE_FILE = pet_save_path()

    def __init__(self):
        self.name = "蓝团子"
        self.hunger = 80.0
        self.happiness = 80.0
        self.energy = 80.0
        self.intimacy = 10.0
        self.level = 1
        self.exp = 0
        self.age_days = 0
        self.birth_time = time.time()
        self.last_update = time.time()
        self.current_action = PetAction.IDLE
        self.current_mood = PetMood.NORMAL
        self.is_sleeping = False
        self.is_new = True

        # ── 今日 / 累计统计 ──────────────────────────────────────
        # 全部来自 InputState，由 main.py 在每次 tick 时同步
        self.total_keystrokes: int = 0       # 累计键击数（存档）
        self.total_mouse_clicks: int = 0     # 累计鼠标点击数（存档）
        self.total_pet_times: int = 0        # 累计被摸次数（存档）
        self.total_feed_times: int = 0       # 累计喂食次数（存档）
        self.total_study_times: int = 0      # 累计学习次数（存档）
        self.total_chat_times: int = 0       # 累计聊天次数（存档）
        self.total_online_seconds: float = 0 # 累计在线秒数（存档）

        # 本次会话新增量（不存档，关闭后清零）
        self._session_start = time.time()

        self.load()

    def update(self, dt_seconds):
        if self.is_sleeping:
            # NOTE: 睡眠恢复较快，从 20→80 约 17 分钟，避免桌宠长时间处于睡眠状态
            self.energy = min(100, self.energy + 0.06 * dt_seconds)
            self.hunger = max(0, self.hunger - 0.003 * dt_seconds)
            # NOTE: 自动唤醒由 main.py _tick 统一管理，避免 state 层与 UI 层不同步
        else:
            self.hunger = max(0, self.hunger - 0.01 * dt_seconds)
            # NOTE: 清醒时体力缓慢消耗，从 100→20 约 7.4 小时，一个工作日内基本不会自动入睡
            self.energy = max(0, self.energy - 0.003 * dt_seconds)
            self.happiness = max(0, self.happiness - 0.005 * dt_seconds)
        self._update_mood()
        self.intimacy = min(100, self.intimacy + 0.001 * dt_seconds)
        self.exp += 0.01 * dt_seconds
        if self.exp >= self.level * 100:
            self.exp = 0
            self.level += 1
        self.age_days = (time.time() - self.birth_time) / 86400
        self.last_update = time.time()
        # 累计在线时长
        self.total_online_seconds += dt_seconds

    def _update_mood(self):
        if self.is_sleeping:
            self.current_mood = PetMood.SLEEPING
        elif self.hunger < 20:
            self.current_mood = PetMood.HUNGRY
        elif self.energy < 20:
            self.current_mood = PetMood.SLEEPY
        elif self.happiness > 80:
            self.current_mood = PetMood.HAPPY
        elif self.happiness < 30:
            self.current_mood = PetMood.SAD
        else:
            self.current_mood = PetMood.NORMAL

    def feed(self):
        if self.is_sleeping:
            return "Zzz...正在睡觉呢..."
        self.hunger = min(100, self.hunger + 25)
        self.happiness = min(100, self.happiness + 5)
        self.intimacy = min(100, self.intimacy + 2)
        self.total_feed_times += 1
        return "好饱啊~打嗝~" if self.hunger > 90 else "真好吃！谢谢~"

    def pet_touch(self):
        if self.is_sleeping:
            return "嗯...别闹...在睡觉..."
        self.happiness = min(100, self.happiness + 10)
        self.intimacy = min(100, self.intimacy + 3)
        self.total_pet_times += 1
        return "好开心！最喜欢你了！" if self.happiness > 90 else "摸摸头~舒服~"

    def play(self):
        if self.is_sleeping:
            return "Zzz...让我再睡会儿..."
        if self.energy < 15:
            return "太累了...想休息..."
        self.happiness = min(100, self.happiness + 15)
        self.energy = max(0, self.energy - 10)
        self.hunger = max(0, self.hunger - 5)
        self.intimacy = min(100, self.intimacy + 4)
        return "玩耍好开心！！"

    def sleep(self):
        if self.is_sleeping:
            return "已经在睡觉了哦~"
        self.is_sleeping = True
        self.current_action = PetAction.SLEEP
        self.current_mood = PetMood.SLEEPING
        return "晚安~Zzz..."

    def wake_up(self):
        self.is_sleeping = False
        self.current_action = PetAction.IDLE
        self.happiness = min(100, self.happiness + 10)
        return "睡醒了！精神满满~"

    def get_status_text(self):
        mood_text = {
            PetMood.HAPPY: "😊 开心", PetMood.NORMAL: "😐 一般",
            PetMood.SAD: "😢 难过", PetMood.HUNGRY: "🍖 饿了",
            PetMood.SLEEPY: "😴 困了", PetMood.SLEEPING: "💤 睡觉中",
        }
        return mood_text.get(self.current_mood, "😐 一般")

    def get_online_str(self) -> str:
        """格式化累计在线时长"""
        total = int(self.total_online_seconds)
        h = total // 3600
        m = (total % 3600) // 60
        if h > 0:
            return f"{h}小时{m}分钟"
        return f"{m}分钟"

    def save(self):
        data = {
            "name": self.name, "is_new": self.is_new,
            "hunger": self.hunger, "happiness": self.happiness,
            "energy": self.energy, "intimacy": self.intimacy,
            "level": self.level, "exp": self.exp,
            "birth_time": self.birth_time, "last_update": time.time(),
            # 累计统计
            "total_keystrokes": self.total_keystrokes,
            "total_mouse_clicks": self.total_mouse_clicks,
            "total_pet_times": self.total_pet_times,
            "total_feed_times": self.total_feed_times,
            "total_study_times": self.total_study_times,
            "total_chat_times": self.total_chat_times,
            "total_online_seconds": self.total_online_seconds,
        }
        try:
            with open(self.SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def load(self):
        if not os.path.exists(self.SAVE_FILE):
            self.is_new = True
            return
        try:
            with open(self.SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.name = data.get("name", self.name)
            self.is_new = data.get("is_new", False)
            self.hunger = data.get("hunger", self.hunger)
            self.happiness = data.get("happiness", self.happiness)
            self.energy = data.get("energy", self.energy)
            self.intimacy = data.get("intimacy", self.intimacy)
            self.level = data.get("level", self.level)
            self.exp = data.get("exp", self.exp)
            self.birth_time = data.get("birth_time", self.birth_time)
            elapsed = time.time() - data.get("last_update", time.time())
            hours = elapsed / 3600
            self.hunger = max(0, self.hunger - hours * 2)
            self.happiness = max(0, self.happiness - hours * 1)
            # 累计统计
            self.total_keystrokes = data.get("total_keystrokes", 0)
            self.total_mouse_clicks = data.get("total_mouse_clicks", 0)
            self.total_pet_times = data.get("total_pet_times", 0)
            self.total_feed_times = data.get("total_feed_times", 0)
            self.total_study_times = data.get("total_study_times", 0)
            self.total_chat_times = data.get("total_chat_times", 0)
            self.total_online_seconds = data.get("total_online_seconds", 0.0)
        except Exception:
            self.is_new = True
