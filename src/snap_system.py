from __future__ import annotations

import ctypes
import ctypes.wintypes
import time
from dataclasses import dataclass
from typing import Optional

user32 = ctypes.windll.user32

# Win32 constants
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000

PET_SIZE = 210
PET_WINDOW_MARGIN = 20  # window padding around sprite
TASKBAR_MARGIN = 40     # bottom margin for taskbar


@dataclass
class SnapTarget:
    """A location the pet can snap to."""
    edge_type: str          # "screen_top", "screen_bottom", "screen_left", "screen_right", "window_top"
    hwnd: int | None        # window handle (only for window_top)
    snap_x: float           # snapped pet_x
    snap_y: float           # snapped pet_y
    range_min: float        # min position along the edge (for distance calc)
    range_max: float        # max position along the edge


class SnapSystem:
    """Detects snap targets from screen edges and visible windows."""

    def __init__(self, dpr: float = 1.0):
        self._window_cache: list[dict] = []
        self._cache_time: float = 0.0
        self._cache_interval: float = 0.5  # refresh window list every 500ms
        self._dpr: float = dpr  # device pixel ratio for coordinate conversion

    def set_dpr(self, dpr: float):
        """更新 DPR（设备像素比），高 DPI 缩放启用后需要将
        Win32 物理像素转换为 Qt 逻辑像素。"""
        self._dpr = dpr

    # ------------------------------------------------------------------
    # Internal: coordinate conversion
    # ------------------------------------------------------------------

    def _to_logical(self, *values: int | float) -> tuple[float, ...]:
        """Win32 物理像素 → Qt 逻辑像素"""
        d = self._dpr
        return tuple(v / d for v in values)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_snap_targets(self, self_hwnd: int, screen_geometry) -> list[SnapTarget]:
        """Collect all valid snap targets: visible window top edges."""
        targets: list[SnapTarget] = []

        # Window top edges
        for w in self._get_visible_windows(self_hwnd):
            left, top, right, bottom = w["rect"]
            ww = right - left
            wh = bottom - top
            if ww < 150 or wh < 150:
                continue
            # 截图/浮动预览窗口：桌宠完全在窗口上方；普通窗口：一半一半
            if w.get("is_tool"):
                snap_y = float(top - 148)
                edge_type = "preview_top"
            else:
                snap_y = float(top - PET_SIZE / 2)
                edge_type = "window_top"
            targets.append(SnapTarget(
                edge_type, w["hwnd"],
                snap_x=0,              # placeholder, resolved in find_nearest_snap
                snap_y=snap_y,
                range_min=float(left),
                range_max=float(right),
            ))

        return targets

    def find_nearest_snap(
        self, pet_x: float, pet_y: float,
        self_hwnd: int,
        screen_geometry,
        threshold: float = 20.0,
    ) -> Optional[SnapTarget]:
        """Return the nearest snap target within threshold pixels, or None."""
        targets = self.get_snap_targets(self_hwnd, screen_geometry)

        best_target = None
        best_dist = float("inf")

        for t in targets:
            dist, snapped_x, snapped_y = self._distance_to_target(pet_x, pet_y, t)
            if dist < best_dist and dist <= threshold:
                best_dist = dist
                t.snap_x = snapped_x
                t.snap_y = snapped_y
                best_target = t

        return best_target

    def get_window_rect(self, hwnd: int) -> tuple[float, float, float, float] | None:
        """Get current rect of a window by handle (Qt 逻辑像素).
        Returns None if window is gone."""
        rect = ctypes.wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return None
        if not user32.IsWindowVisible(hwnd):
            return None
        if user32.IsIconic(hwnd):
            return None
        l, t, r, b = self._to_logical(rect.left, rect.top, rect.right, rect.bottom)
        return (l, t, r, b)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_visible_windows(self, self_hwnd: int) -> list[dict]:
        """Enumerate visible, non-minimized windows (cached)."""
        now = time.time()
        if self._window_cache and (now - self._cache_time) < self._cache_interval:
            return self._window_cache

        windows: list[dict] = []
        dpr = self._dpr

        def enum_callback(hwnd: int, _lparam: int) -> bool:
            if hwnd == self_hwnd:
                return True
            if not user32.IsWindowVisible(hwnd):
                return True
            if user32.IsIconic(hwnd):
                return True

            rect = ctypes.wintypes.RECT()
            if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                return True

            ww = rect.right - rect.left
            wh = rect.bottom - rect.top

            if ww < 100 or wh < 100:
                return True

            # Check if window is on the primary screen
            # (simplified: just check if it has non-zero size)
            if ww <= 0 or wh <= 0:
                return True

            ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            is_tool = bool(ex_style & WS_EX_TOOLWINDOW) and not bool(ex_style & WS_EX_APPWINDOW)
            # Win32 物理像素 → Qt 逻辑像素
            windows.append({
                "hwnd": hwnd,
                "rect": (rect.left / dpr, rect.top / dpr,
                         rect.right / dpr, rect.bottom / dpr),
                "is_tool": is_tool,
            })
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
        user32.EnumWindows(WNDENUMPROC(enum_callback), 0)

        self._window_cache = windows
        self._cache_time = now
        return windows

    @staticmethod
    def _distance_to_target(
        pet_x: float, pet_y: float, target: SnapTarget
    ) -> tuple[float, float, float]:
        """Return (distance, snapped_x, snapped_y) for a target."""
        if target.edge_type in ("screen_top", "screen_bottom"):
            # Horizontal edge: snap y is fixed, clamp x to valid range
            snapped_y = target.snap_y
            clamped_x = max(target.range_min, min(target.range_max - PET_SIZE, pet_x))
            dist_sq = (pet_x - clamped_x) ** 2 + (pet_y - snapped_y) ** 2
            return (dist_sq ** 0.5, clamped_x, snapped_y)

        elif target.edge_type in ("screen_left", "screen_right"):
            # Vertical edge: snap x is fixed, clamp y to valid range
            snapped_x = target.snap_x
            clamped_y = max(target.range_min, min(target.range_max - PET_SIZE, pet_y))
            dist_sq = (pet_x - snapped_x) ** 2 + (pet_y - clamped_y) ** 2
            return (dist_sq ** 0.5, snapped_x, clamped_y)

        elif target.edge_type in ("window_top", "preview_top"):
            # 计算桌宠边界框到窗口上边缘的最短距离
            if target.edge_type == "preview_top":
                window_top = target.snap_y + 148  # snap_y = top - 148
            else:
                window_top = target.snap_y + PET_SIZE / 2  # 一半一半: snap_y = top - PET_SIZE/2
            pet_right = pet_x + PET_SIZE
            pet_bottom = pet_y + PET_SIZE

            # X 方向：桌宠 X 范围 [pet_x, pet_right] 与窗口 X 范围 [range_min, range_max] 的最短距离
            if pet_right < target.range_min:
                dist_x = target.range_min - pet_right
            elif pet_x > target.range_max:
                dist_x = pet_x - target.range_max
            else:
                dist_x = 0.0

            # Y 方向：桌宠 Y 范围 [pet_y, pet_bottom] 与窗口上边缘的最短距离
            if pet_bottom < window_top:
                dist_y = window_top - pet_bottom
            elif pet_y > window_top:
                dist_y = pet_y - window_top
            else:
                dist_y = 0.0

            dist = (dist_x ** 2 + dist_y ** 2) ** 0.5
            clamped_x = max(target.range_min, min(target.range_max - PET_SIZE, pet_x))
            return (dist, clamped_x, target.snap_y)

        # Fallback: no valid target
        return (float("inf"), pet_x, pet_y)
