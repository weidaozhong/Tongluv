"""
游戏系统模块 — 签到 / 每日任务 / 成就 / 背包 / 商店
所有数据存储在 game_data.json 中，独立于 pet_save.json。
"""
import json
import os
import time
from datetime import datetime, date, timedelta

from src.user_data import game_data_path

DATA_FILE = game_data_path()

# ══════════════════════════════════════════════════════════════════════
#  🧪 测试开关 — 完成测试后将下面改回 False
# ══════════════════════════════════════════════════════════════════════
_TEST_UNLIMITED_COINS: bool = True   # True = 无限金币测试模式

# ══════════════════════════════════════════════════════════════════════
#  默认数据结构
# ══════════════════════════════════════════════════════════════════════
def _default_data():
    return {
        "coins": 50,                    # 金币（签到/任务奖励，商店消费）
        "sign_in": {
            "last_date": "",            # "2026-04-30"
            "streak": 0,                # 连续签到天数
            "total_days": 0,            # 累计签到天数
        },
        "tasks": {
            "date": "",                 # 任务日期
            "progress": {},             # {"feed_2": 0, "pet_3": 0, ...}
            "claimed": [],              # 已领取的任务 id
        },
        "achievements": [],             # 已解锁的成就 id 列表
        "backpack": {},                 # {"apple": 3, "cake": 1, ...}
    }


# ══════════════════════════════════════════════════════════════════════
#  每日任务定义
# ══════════════════════════════════════════════════════════════════════
DAILY_TASKS = [
    {"id": "feed_2",    "name": "投喂达人",   "desc": "喂食 2 次",     "target": 2, "stat": "feed",  "reward": 15},
    {"id": "pet_3",     "name": "摸摸大师",   "desc": "摸摸头 3 次",   "target": 3, "stat": "pet",   "reward": 15},
    {"id": "play_1",    "name": "游戏时光",   "desc": "玩游戏 1 次",   "target": 1, "stat": "play",  "reward": 10},
    {"id": "online_10", "name": "忠实伙伴",   "desc": "在线 10 分钟",  "target": 10,"stat": "online","reward": 20},
    {"id": "login",     "name": "每日登录",   "desc": "今天打开桌宠",  "target": 1, "stat": "login", "reward": 5},
]


# ══════════════════════════════════════════════════════════════════════
#  成就定义
# ══════════════════════════════════════════════════════════════════════
ACHIEVEMENTS = [
    {"id": "first_feed",    "name": "第一口饭",     "desc": "首次喂食",              "check": lambda s: s.get("total_feed", 0) >= 1,    "reward": 10},
    {"id": "feed_50",       "name": "美食家",       "desc": "累计喂食 50 次",        "check": lambda s: s.get("total_feed", 0) >= 50,   "reward": 30},
    {"id": "pet_100",       "name": "摸摸狂魔",     "desc": "累计摸头 100 次",       "check": lambda s: s.get("total_pet", 0) >= 100,   "reward": 30},
    {"id": "day_7",         "name": "一周之约",     "desc": "陪伴满 7 天",           "check": lambda s: s.get("age_days", 0) >= 7,      "reward": 50},
    {"id": "day_30",        "name": "月之守护",     "desc": "陪伴满 30 天",          "check": lambda s: s.get("age_days", 0) >= 30,     "reward": 100},
    {"id": "lv5",           "name": "小有成就",     "desc": "等级达到 5",            "check": lambda s: s.get("level", 0) >= 5,         "reward": 50},
    {"id": "lv10",          "name": "成长之星",     "desc": "等级达到 10",           "check": lambda s: s.get("level", 0) >= 10,        "reward": 100},
    {"id": "sign_7",        "name": "签到达人",     "desc": "连续签到 7 天",         "check": lambda s: s.get("sign_streak", 0) >= 7,   "reward": 50},
    {"id": "intimacy_max",  "name": "心意相通",     "desc": "亲密度达到 100",        "check": lambda s: s.get("intimacy", 0) >= 100,    "reward": 80},
    {"id": "coins_500",     "name": "小富翁",       "desc": "累计获得 500 金币",     "check": lambda s: s.get("total_coins", 0) >= 500, "reward": 50},
]


# ══════════════════════════════════════════════════════════════════════
#  商店物品定义
# ══════════════════════════════════════════════════════════════════════
SHOP_ITEMS = [
    {"id": "apple",      "name": "🍎 苹果",     "desc": "恢复 15 饱食度",  "price": 10, "effect": ("hunger", 15)},
    {"id": "cake",       "name": "🍰 蛋糕",     "desc": "恢复 30 饱食度",  "price": 20, "effect": ("hunger", 30)},
    {"id": "candy",      "name": "🍬 糖果",     "desc": "心情 +15",       "price": 15, "effect": ("happiness", 15)},
    {"id": "coffee",     "name": "☕ 咖啡",     "desc": "体力 +20",       "price": 15, "effect": ("energy", 20)},
    {"id": "plush",      "name": "🧸 玩偶",     "desc": "亲密度 +10",     "price": 30, "effect": ("intimacy", 10)},
    {"id": "star",       "name": "⭐ 经验星",   "desc": "经验 +50",       "price": 25, "effect": ("exp", 50)},
    {"id": "gift_box",   "name": "🎁 礼物盒",   "desc": "全属性 +10",     "price": 50, "effect": ("all", 10)},
]


# ══════════════════════════════════════════════════════════════════════
#  GameSystems 主类
# ══════════════════════════════════════════════════════════════════════
class GameSystems:
    def __init__(self):
        self._data = _default_data()
        self._today_stats = {
            "feed": 0, "pet": 0, "play": 0,
            "online": 0, "login": 1,
        }
        self._total_coins_earned = 0
        self.load()
        self._init_today_tasks()

    # ── 存取 ─────────────────────────────────────────────────────────
    def load(self):
        if not os.path.exists(DATA_FILE):
            return
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            for k in self._data:
                if k in saved:
                    self._data[k] = saved[k]
            self._total_coins_earned = saved.get("_total_coins_earned", 0)
        except Exception:
            pass

    def save(self):
        d = dict(self._data)
        d["_total_coins_earned"] = self._total_coins_earned
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    @property
    def coins(self) -> int:
        if _TEST_UNLIMITED_COINS:
            return 99999
        return self._data["coins"]

    def _add_coins(self, n: int):
        self._data["coins"] += n
        self._total_coins_earned += n

    # ── 签到 ─────────────────────────────────────────────────────────
    def can_sign_in(self) -> bool:
        return self._data["sign_in"]["last_date"] != str(date.today())

    def do_sign_in(self) -> dict:
        """返回 {"coins": 奖励数, "streak": 连签天数, "msg": 提示}"""
        today = str(date.today())
        si = self._data["sign_in"]
        if si["last_date"] == today:
            return {"coins": 0, "streak": si["streak"], "msg": "今天已经签到过了~"}

        yesterday = str(date.today() - timedelta(days=1))
        if si["last_date"] == yesterday:
            si["streak"] += 1
        else:
            si["streak"] = 1

        si["last_date"] = today
        si["total_days"] += 1

        # 奖励：基础10 + 连签加成
        reward = 10 + min(si["streak"], 7) * 5
        self._add_coins(reward)
        self.save()
        return {"coins": reward, "streak": si["streak"],
                "msg": f"签到成功！连续 {si['streak']} 天，获得 {reward} 金币"}

    # ── 每日任务 ─────────────────────────────────────────────────────
    def _init_today_tasks(self):
        today = str(date.today())
        t = self._data["tasks"]
        if t["date"] != today:
            t["date"] = today
            t["progress"] = {task["id"]: 0 for task in DAILY_TASKS}
            t["claimed"] = []
            # login 任务自动完成
            t["progress"]["login"] = 1

    def record_action(self, action: str, amount: int = 1):
        """记录一次动作，action 是 feed/pet/play/online"""
        self._today_stats[action] = self._today_stats.get(action, 0) + amount
        # 更新任务进度
        for task in DAILY_TASKS:
            if task["stat"] == action:
                self._data["tasks"]["progress"][task["id"]] = self._today_stats[action]

    def get_tasks_status(self) -> list[dict]:
        """返回 [{"id", "name", "desc", "progress", "target", "done", "claimed", "reward"}, ...]"""
        self._init_today_tasks()
        result = []
        for task in DAILY_TASKS:
            tid = task["id"]
            prog = self._data["tasks"]["progress"].get(tid, 0)
            result.append({
                "id": tid,
                "name": task["name"],
                "desc": task["desc"],
                "progress": min(prog, task["target"]),
                "target": task["target"],
                "done": prog >= task["target"],
                "claimed": tid in self._data["tasks"]["claimed"],
                "reward": task["reward"],
            })
        return result

    def claim_task(self, task_id: str) -> str:
        """领取任务奖励，返回提示信息"""
        for task in DAILY_TASKS:
            if task["id"] == task_id:
                prog = self._data["tasks"]["progress"].get(task_id, 0)
                if prog < task["target"]:
                    return "任务还没完成哦~"
                if task_id in self._data["tasks"]["claimed"]:
                    return "奖励已经领过了~"
                self._data["tasks"]["claimed"].append(task_id)
                self._add_coins(task["reward"])
                self.save()
                return f"领取成功！获得 {task['reward']} 金币"
        return "任务不存在"

    # ── 成就 ─────────────────────────────────────────────────────────
    def check_achievements(self, pet_state) -> list[dict]:
        """检查所有成就，返回本次新解锁的列表"""
        stats = {
            "total_feed": getattr(pet_state, "total_feed_times", 0),
            "total_pet": getattr(pet_state, "total_pet_times", 0),
            "age_days": getattr(pet_state, "age_days", 0),
            "level": getattr(pet_state, "level", 1),
            "intimacy": getattr(pet_state, "intimacy", 0),
            "sign_streak": self._data["sign_in"]["streak"],
            "total_coins": self._total_coins_earned,
        }
        newly = []
        for ach in ACHIEVEMENTS:
            if ach["id"] not in self._data["achievements"]:
                try:
                    if ach["check"](stats):
                        self._data["achievements"].append(ach["id"])
                        self._add_coins(ach["reward"])
                        newly.append(ach)
                except Exception:
                    pass
        if newly:
            self.save()
        return newly

    def get_achievements_status(self, pet_state) -> list[dict]:
        stats = {
            "total_feed": getattr(pet_state, "total_feed_times", 0),
            "total_pet": getattr(pet_state, "total_pet_times", 0),
            "age_days": getattr(pet_state, "age_days", 0),
            "level": getattr(pet_state, "level", 1),
            "intimacy": getattr(pet_state, "intimacy", 0),
            "sign_streak": self._data["sign_in"]["streak"],
            "total_coins": self._total_coins_earned,
        }
        result = []
        for ach in ACHIEVEMENTS:
            unlocked = ach["id"] in self._data["achievements"]
            try:
                ready = ach["check"](stats)
            except Exception:
                ready = False
            result.append({
                "id": ach["id"], "name": ach["name"], "desc": ach["desc"],
                "reward": ach["reward"], "unlocked": unlocked or ready,
            })
        return result

    # ── 背包 ─────────────────────────────────────────────────────────
    def get_backpack(self) -> dict:
        return dict(self._data["backpack"])

    def add_item(self, item_id: str, count: int = 1):
        bp = self._data["backpack"]
        bp[item_id] = bp.get(item_id, 0) + count
        self.save()

    def use_item(self, item_id: str, pet_state) -> str:
        """使用背包物品，返回提示信息"""
        bp = self._data["backpack"]
        if bp.get(item_id, 0) <= 0:
            return "背包里没有这个物品~"
        # 找到物品效果
        item = None
        for si in SHOP_ITEMS:
            if si["id"] == item_id:
                item = si
                break
        if item is None:
            return "未知物品"

        attr, val = item["effect"]
        if attr == "all":
            pet_state.hunger    = min(100, pet_state.hunger + val)
            pet_state.happiness = min(100, pet_state.happiness + val)
            pet_state.energy    = min(100, pet_state.energy + val)
            pet_state.intimacy  = min(100, pet_state.intimacy + val)
        elif attr == "exp":
            pet_state.exp += val
        else:
            cur = getattr(pet_state, attr, 0)
            setattr(pet_state, attr, min(100, cur + val))

        bp[item_id] -= 1
        if bp[item_id] <= 0:
            del bp[item_id]
        self.save()
        return f"使用了 {item['name']}！"

    # ── 商店 ─────────────────────────────────────────────────────────
    def get_shop_items(self) -> list[dict]:
        return [dict(si) for si in SHOP_ITEMS]

    def buy_item(self, item_id: str) -> str:
        for si in SHOP_ITEMS:
            if si["id"] == item_id:
                if not _TEST_UNLIMITED_COINS:
                    if self._data["coins"] < si["price"]:
                        return f"金币不足！需要 {si['price']}，当前 {self._data['coins']}"
                    self._data["coins"] -= si["price"]
                self.add_item(item_id)
                return f"购买成功！获得 {si['name']}"
        return "物品不存在"

    # ── 消息提醒 ─────────────────────────────────────────────────────
    def get_reminder(self) -> str | None:
        """每半小时提醒一次（由 main.py 定时调用）"""
        h = datetime.now().hour
        m = datetime.now().minute
        if m not in (0, 30):
            return None
        reminders = {
            (8, 0):  "早上好！新的一天开始了~",
            (12, 0): "中午了，该吃午饭啦！",
            (12, 30):"饭后休息一下吧~",
            (15, 0): "下午茶时间，喝杯水吧~",
            (18, 0): "傍晚了，今天辛苦了！",
            (21, 0): "晚上好~不要太晚睡哦",
            (23, 0): "好晚了！该休息了吧？",
        }
        return reminders.get((h, m), "记得休息一下眼睛哦~" if m == 0 else None)
