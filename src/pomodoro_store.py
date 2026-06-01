"""番茄钟配置持久化 —— 独立文件 geren/pomodoro_config.json。

设计目标(兼容老用户迁移):
  - 与其它数据完全独立。老用户把旧版 geren/ 迁移过来时本文件缺失,自动回落默认值。
  - 用户单独删除本文件,只重置番茄钟,不影响聊天记忆/存档/游戏等任何数据。
  - 读取做满防御:文件缺失、JSON 损坏、结构非 dict、字段非法/负数/非数字,
    一律安全回落(load 返回 None → 调用方用内置默认 25/5/15/4),绝不抛异常。
"""
import json
import os

from src.user_data import pomodoro_config_path

_KEYS = ("focus_min", "short_break_min", "long_break_min", "cycles_before_long")


def load_pomodoro_config():
    """读取番茄钟配置;任何异常情况都返回 None(让调用方用默认值)。"""
    path = pomodoro_config_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return None
    if not isinstance(raw, dict):
        return None
    out = {}
    for k in _KEYS:
        v = raw.get(k)
        if isinstance(v, bool):          # 排除 True/False(它们也是 int 子类)
            continue
        if isinstance(v, (int, float)) and v > 0:
            out[k] = int(v)
    return out or None


def save_pomodoro_config(cfg: dict) -> None:
    """只写入已知的合法键,忽略其它内容;写入失败静默(不影响主程序)。"""
    data = {}
    for k in _KEYS:
        v = cfg.get(k)
        if not isinstance(v, bool) and isinstance(v, (int, float)) and v > 0:
            data[k] = int(v)
    try:
        with open(pomodoro_config_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
