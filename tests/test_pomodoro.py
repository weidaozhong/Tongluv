import unittest
from src.pomodoro import PomodoroTimer, FOCUS, SHORT_BREAK, LONG_BREAK, IDLE


class FakeClock:
    def __init__(self, t=1000.0):
        self.t = t
    def __call__(self):
        return self.t
    def advance(self, dt):
        self.t += dt


# 测试用小配置:专注/短休/长休各 1 分钟,2 轮专注后长休
CFG = {"focus_min": 1, "short_break_min": 1, "long_break_min": 1, "cycles_before_long": 2}


class TestPomodoro(unittest.TestCase):
    def _mk(self):
        clk = FakeClock()
        return PomodoroTimer(config=CFG, now_fn=clk), clk

    def test_idle_before_start(self):
        p, _ = self._mk()
        self.assertFalse(p.active)
        self.assertEqual(p.phase, IDLE)
        self.assertIsNone(p.update())

    def test_start_enters_focus(self):
        p, _ = self._mk()
        p.start()
        self.assertTrue(p.active)
        self.assertEqual(p.phase, FOCUS)
        self.assertEqual(p.label, "专注")
        self.assertAlmostEqual(p.remaining, 60.0)
        self.assertIsNone(p.update())   # 还没到点

    def test_focus_to_short_break(self):
        p, clk = self._mk()
        p.start()
        clk.advance(60)
        self.assertEqual(p.update(), SHORT_BREAK)
        self.assertEqual(p.completed_focus, 1)
        self.assertAlmostEqual(p.remaining, 60.0)

    def test_full_cycle_reaches_long_break(self):
        p, clk = self._mk()
        p.start()
        clk.advance(60); self.assertEqual(p.update(), SHORT_BREAK)   # 专注1 → 短休
        clk.advance(60); self.assertEqual(p.update(), FOCUS)         # 短休 → 专注2
        clk.advance(60); self.assertEqual(p.update(), LONG_BREAK)    # 专注2 → 长休(2%2==0)
        self.assertEqual(p.completed_focus, 2)
        clk.advance(60); self.assertEqual(p.update(), FOCUS)         # 长休 → 专注

    def test_pause_resume(self):
        p, clk = self._mk()
        p.start()
        clk.advance(20); p.pause()
        self.assertTrue(p.paused)
        self.assertAlmostEqual(p.remaining, 40.0)
        clk.advance(1000)                       # 暂停期间时钟走动不影响
        self.assertAlmostEqual(p.remaining, 40.0)
        self.assertIsNone(p.update())           # 暂停时不推进
        p.resume()
        clk.advance(40)
        self.assertEqual(p.update(), SHORT_BREAK)

    def test_reset(self):
        p, clk = self._mk()
        p.start(); clk.advance(10)
        p.reset()
        self.assertFalse(p.active)
        self.assertEqual(p.phase, IDLE)
        self.assertEqual(p.completed_focus, 0)

    def test_default_config_durations(self):
        p = PomodoroTimer()
        p.start()
        self.assertAlmostEqual(p.remaining, 25 * 60, delta=2)


if __name__ == "__main__":
    unittest.main()
