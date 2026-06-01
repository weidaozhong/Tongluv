import unittest
import os
import json
import tempfile

import src.pomodoro_store as ps


class TestPomodoroStore(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.join(tempfile.gettempdir(), "_test_pomo_cfg.json")
        if os.path.exists(self.tmp):
            os.remove(self.tmp)
        self._orig = ps.pomodoro_config_path
        ps.pomodoro_config_path = lambda: self.tmp   # 重定向到临时文件

    def tearDown(self):
        ps.pomodoro_config_path = self._orig
        if os.path.exists(self.tmp):
            os.remove(self.tmp)

    def _write(self, text):
        with open(self.tmp, "w", encoding="utf-8") as f:
            f.write(text)

    # ── 迁移场景:老用户旧 geren/ 没有这个文件 ──
    def test_missing_file_returns_none(self):
        self.assertIsNone(ps.load_pomodoro_config())

    def test_round_trip(self):
        cfg = {"focus_min": 30, "short_break_min": 8, "long_break_min": 20, "cycles_before_long": 3}
        ps.save_pomodoro_config(cfg)
        self.assertEqual(ps.load_pomodoro_config(), cfg)

    # ── 防御:文件被损坏 / 结构异常 ──
    def test_corrupt_json_returns_none(self):
        self._write("{ this is not json")
        self.assertIsNone(ps.load_pomodoro_config())

    def test_non_dict_returns_none(self):
        self._write("[1, 2, 3]")
        self.assertIsNone(ps.load_pomodoro_config())

    def test_all_illegal_values_returns_none(self):
        self._write(json.dumps({
            "focus_min": -5, "short_break_min": "x",
            "long_break_min": 0, "cycles_before_long": True,
        }))
        self.assertIsNone(ps.load_pomodoro_config())

    def test_partial_valid_keeps_only_valid(self):
        self._write(json.dumps({"focus_min": 40, "short_break_min": -1}))
        self.assertEqual(ps.load_pomodoro_config(), {"focus_min": 40})

    def test_save_drops_unknown_and_bad_keys(self):
        ps.save_pomodoro_config({
            "focus_min": 25, "short_break_min": 5, "long_break_min": 15,
            "cycles_before_long": 4, "junk": 99, "focus_min_typo": 3,
        })
        with open(self.tmp, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(set(data.keys()),
                         {"focus_min", "short_break_min", "long_break_min", "cycles_before_long"})


if __name__ == "__main__":
    unittest.main()
