import unittest
from src.timer_core import Countdown, format_remaining


class FakeClock:
    def __init__(self, t=1000.0):
        self.t = t
    def __call__(self):
        return self.t
    def advance(self, dt):
        self.t += dt


class TestFormatRemaining(unittest.TestCase):
    def test_under_hour(self):
        self.assertEqual(format_remaining(0), "00:00")
        self.assertEqual(format_remaining(65), "01:05")
        self.assertEqual(format_remaining(599), "09:59")
    def test_over_hour(self):
        self.assertEqual(format_remaining(3661), "1:01:01")
    def test_negative_clamps_zero(self):
        self.assertEqual(format_remaining(-5), "00:00")
    def test_rounds(self):
        self.assertEqual(format_remaining(59.6), "01:00")


class TestCountdown(unittest.TestCase):
    def test_start_and_remaining(self):
        clk = FakeClock()
        c = Countdown(now_fn=clk)
        c.start(10, "喝水")
        self.assertEqual(c.label, "喝水")
        self.assertTrue(c.running)
        self.assertAlmostEqual(c.remaining, 10.0)
        self.assertFalse(c.is_done)
        self.assertAlmostEqual(c.fraction, 0.0)

    def test_counts_down(self):
        clk = FakeClock()
        c = Countdown(now_fn=clk)
        c.start(10)
        clk.advance(4)
        self.assertAlmostEqual(c.remaining, 6.0)
        self.assertAlmostEqual(c.fraction, 0.4)
        clk.advance(6)
        self.assertAlmostEqual(c.remaining, 0.0)
        self.assertTrue(c.is_done)
        self.assertAlmostEqual(c.fraction, 1.0)

    def test_remaining_never_negative(self):
        clk = FakeClock()
        c = Countdown(now_fn=clk)
        c.start(5)
        clk.advance(99)
        self.assertEqual(c.remaining, 0.0)

    def test_pause_resume(self):
        clk = FakeClock()
        c = Countdown(now_fn=clk)
        c.start(10)
        clk.advance(3)
        c.pause()
        self.assertFalse(c.running)
        self.assertAlmostEqual(c.remaining, 7.0)
        clk.advance(100)               # 暂停期间时钟走动不影响
        self.assertAlmostEqual(c.remaining, 7.0)
        c.resume()
        self.assertTrue(c.running)
        clk.advance(7)
        self.assertTrue(c.is_done)

    def test_stop(self):
        clk = FakeClock()
        c = Countdown(now_fn=clk)
        c.start(10)
        c.stop()
        self.assertFalse(c.running)
        self.assertFalse(c.is_done)
        self.assertEqual(c.remaining, 0.0)


if __name__ == "__main__":
    unittest.main()
