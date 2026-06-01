"""reminder_data.json 读写(便携持久化,存于 geren/)。
P2 先存番茄钟时长配置;P3 起在同一文件扩展 reminders / memos。
"""
import json
import os

from src.user_data import reminder_data_path


def _load() -> dict:
    path = reminder_data_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}


def _save(data: dict) -> None:
    try:
        with open(reminder_data_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def load_pomodoro_config():
    cfg = _load().get("pomodoro")
    return cfg if isinstance(cfg, dict) else None


def save_pomodoro_config(cfg: dict) -> None:
    data = _load()
    data["pomodoro"] = dict(cfg)
    _save(data)
