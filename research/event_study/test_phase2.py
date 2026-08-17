import unittest

import numpy as np
import pandas as pd

from research.event_study.phase2_event_panel import (
    daily_controls,
    expected_minutes,
    minute_window_metrics,
    volume_baseline,
)


def synthetic_bars(start: str, closes: list[float]) -> pd.DataFrame:
    index = pd.date_range(start=start, periods=len(closes), freq="min")
    values = np.asarray(closes, dtype=float)
    return pd.DataFrame(
        {
            "open": values,
            "high": values,
            "low": values,
            "close": values,
            "volume": np.full(len(values), 100.0),
        },
        index=index,
    )


class MinuteWindowTests(unittest.TestCase):
    def setUp(self):
        # The 13:59 bar supplies only the boundary close. The reaction bars begin
        # at 14:00 and represent [14:00, 14:01), [14:01, 14:02), and so on.
        self.bars = synthetic_bars(
            "2024-01-31 13:59", [100.0, 101.0, 99.0, 102.0, 102.5, 103.0]
        )

    def test_expected_window_is_half_open(self):
        start = pd.Timestamp("2024-01-31 14:00")
        expected = expected_minutes(start, 5)
        self.assertEqual(expected[0], start)
        self.assertEqual(expected[-1], pd.Timestamp("2024-01-31 14:04"))
        self.assertNotIn(pd.Timestamp("2024-01-31 14:05"), expected)

    def test_window_uses_prior_close_as_boundary(self):
        start = pd.Timestamp("2024-01-31 14:00")
        result = minute_window_metrics(self.bars, start, 5)
        closes = np.array([101.0, 99.0, 102.0, 102.5, 103.0])
        lagged = np.array([100.0, 101.0, 99.0, 102.0, 102.5])
        returns = np.log(closes / lagged)
        self.assertTrue(result["complete"])
        self.assertEqual(result["bars_present"], 5)
        self.assertAlmostEqual(result["return_pct"], np.log(103.0 / 100.0) * 100)
        self.assertAlmostEqual(
            result["rv_pct"], np.sqrt(np.square(returns).sum()) * 100
        )

    def test_missing_reaction_bar_rejects_entire_window(self):
        bars = self.bars.drop(pd.Timestamp("2024-01-31 14:02"))
        result = minute_window_metrics(bars, pd.Timestamp("2024-01-31 14:00"), 5)
        self.assertFalse(result["complete"])
        self.assertEqual(result["bars_present"], 4)
        self.assertNotIn("rv_pct", result)

    def test_missing_boundary_rejects_entire_window(self):
        bars = self.bars.drop(pd.Timestamp("2024-01-31 13:59"))
        result = minute_window_metrics(bars, pd.Timestamp("2024-01-31 14:00"), 5)
        self.assertFalse(result["complete"])
        self.assertFalse(result["prior_boundary_present"])

    def test_zero_volume_session_is_excluded_from_volume_baseline(self):
        first = synthetic_bars("2024-01-29 13:59", [100.0, 101.0, 102.0])
        second = synthetic_bars("2024-01-30 13:59", [100.0, 101.0, 102.0])
        second.loc[pd.Timestamp("2024-01-30 14:00"), "volume"] = 0
        bars = pd.concat([first, second])
        result = volume_baseline(
            bars,
            pd.DatetimeIndex(pd.to_datetime(["2024-01-29", "2024-01-30"])),
            pd.Timestamp("2024-01-31 14:00", tz="America/New_York"),
            minutes=2,
            sessions=2,
        )
        self.assertEqual(result["baseline_sessions_complete"], 1)
        self.assertEqual(result["baseline_median_volume"], 200.0)


class DailyControlTests(unittest.TestCase):
    def test_only_pre_event_daily_values_are_used(self):
        dates = pd.to_datetime(
            [
                "2024-01-23",
                "2024-01-24",
                "2024-01-25",
                "2024-01-26",
                "2024-01-29",
                "2024-01-30",
                "2024-01-31",
            ]
        )
        market = pd.DataFrame(
            {
                "SPX": [99, 100, 101, 102, 103, 104, 999],
                "Volume": [9, 10, 11, 12, 13, 14, 999],
                "VIX": [21, 20, 19, 18, 17, 16, 999],
            },
            index=dates,
        )
        market["spx_log_return"] = np.log(market["SPX"] / market["SPX"].shift(1))
        controls = daily_controls(
            market, pd.Timestamp("2024-01-31 14:00", tz="America/New_York")
        )
        self.assertTrue(controls["daily_controls_complete"])
        self.assertEqual(controls["control_date"], "2024-01-30")
        self.assertEqual(controls["prior_spx_close"], 104.0)
        self.assertEqual(controls["prior_vix_close"], 16.0)


if __name__ == "__main__":
    unittest.main()
