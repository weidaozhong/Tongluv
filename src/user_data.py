"""
用户数据路径管理 — 便携式存储
所有用户数据存放在程序根目录下的 geren/ 文件夹中，
跟着程序走，不占 C 盘空间，解压到哪里数据就在哪里。
"""
import json
import os
import shutil
import sys

# 项目根目录（代码 / 资源所在位置）
if getattr(sys, "frozen", False):
    # PyInstaller 打包后
    PROJECT_ROOT = os.path.dirname(sys.executable)
else:
    # 开发环境：src/ 的父目录
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_user_data_dir() -> str:
    """
    返回用户数据目录：程序根目录下的 geren/ 文件夹。
    用户解压到哪里，数据就跟到哪里，不占 C 盘。
    """
    data_dir = os.path.join(PROJECT_ROOT, "geren")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def get_user_file(filename: str) -> str:
    """返回用户数据目录下的某个文件完整路径"""
    return os.path.join(get_user_data_dir(), filename)


# ── 各数据文件的用户本地路径 ────────────────────────────────────
def config_path() -> str:
    return get_user_file("chat_config.json")

def memory_path() -> str:
    return get_user_file("chat_memory.json")

def pet_save_path() -> str:
    return get_user_file("pet_save.json")

def game_data_path() -> str:
    return get_user_file("game_data.json")

def reminder_data_path() -> str:
    return get_user_file("reminder_data.json")

def avatar_path() -> str:
    return get_user_file("avatar_custom.png")


# ── 项目内置资源路径 ────────────────────────────────────────────
def _assets_root() -> str:
    """
    只读资源根目录（data/、icons/ 等随程序分发的文件）。
    打包后在 sys._MEIPASS（_internal/），开发时在项目根目录。
    """
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return PROJECT_ROOT


def default_persona_path() -> str:
    """内置角色设定文档（随项目分发，所有用户共享）"""
    return os.path.join(_assets_root(), "data", "default_persona.txt")


# ── 数据迁移（从旧版 %APPDATA% 或 data/ 迁移到 geren/）─────────
_OLD_DATA_DIR  = os.path.join(PROJECT_ROOT, "data")

_MIGRATE_MAP = {
    "chat_config.json":  config_path,
    "chat_memory.json":  memory_path,
    "pet_save.json":     pet_save_path,
    "game_data.json":    game_data_path,
}


def _get_old_appdata_dir() -> str | None:
    """获取旧版 %APPDATA%/DesktopPet/ 路径（如果存在）"""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", "")
        if base:
            d = os.path.join(base, "DesktopPet")
            if os.path.isdir(d):
                return d
    return None


def migrate_old_data():
    """
    一次性迁移：将旧版数据移到 geren/ 目录。
    按优先级检查两个旧位置：
      1. %APPDATA%/DesktopPet/（旧版系统目录）
      2. data/（更早期的项目内存储）
    已迁移的标记文件 .migrated 防止重复执行。
    """
    marker = os.path.join(get_user_data_dir(), ".migrated")
    if os.path.exists(marker):
        return

    # 收集旧数据源（AppData 优先于 data/）
    old_appdata = _get_old_appdata_dir()

    for old_name, path_fn in _MIGRATE_MAP.items():
        new_file = path_fn()
        if os.path.exists(new_file):
            continue  # 新位置已有数据，不覆盖

        # 优先从 AppData 迁移
        if old_appdata:
            old_file = os.path.join(old_appdata, old_name)
            if os.path.exists(old_file):
                try:
                    shutil.copy2(old_file, new_file)
                    continue
                except Exception:
                    pass

        # 再尝试从 data/ 迁移
        old_file = os.path.join(_OLD_DATA_DIR, old_name)
        if os.path.exists(old_file):
            try:
                shutil.copy2(old_file, new_file)
            except Exception:
                pass

    # 自定义头像迁移
    if not os.path.exists(avatar_path()):
        for old_avatar in [
            os.path.join(old_appdata, "avatar_custom.png") if old_appdata else "",
            os.path.join(PROJECT_ROOT, "icons", "avatar_custom.png"),
        ]:
            if old_avatar and os.path.exists(old_avatar):
                try:
                    shutil.copy2(old_avatar, avatar_path())
                    break
                except Exception:
                    pass

    # 写入迁移标记
    try:
        with open(marker, "w", encoding="utf-8") as f:
            f.write("migrated")
    except Exception:
        pass
