import unittest
from pathlib import Path

import pandas as pd

from research.event_study.phase1_coverage import (
    audit_coverage,
    compile_topic_patterns,
    expand_calendar,
    load_json,
    previous_trading_dates,
    topic_mask,
)


HERE = Path(__file__).parent


class CalendarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_json(HERE / "event_calendar.json")
        cls.events = expand_calendar(cls.config)

    def test_expected_event_counts(self):
        counts = self.events.groupby("family").size().to_dict()
        self.assertEqual(counts, {"cpi": 60, "employment": 60, "fomc": 39})

    def test_ids_and_timestamps_are_unique(self):
        self.assertFalse(self.events["event_id"].duplicated().any())
        self.assertFalse(
            self.events[["family", "release_timestamp_et"]].duplicated().any()
        )

    def test_events_stay_in_sample(self):
        dates = self.events["release_timestamp_et"].dt.date
        self.assertGreaterEqual(dates.min().isoformat(), self.config["sample_start"])
        self.assertLessEqual(dates.max().isoformat(), self.config["sample_end"])


class TopicAndTimingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patterns = compile_topic_patterns(load_json(HERE / "topic_rules.json"))

    def test_bare_fed_verb_is_not_a_fomc_match(self):
        text = pd.Series(["The child was fed before school", "Federal Reserve holds rates"])
        matches = topic_mask(text, self.patterns["fomc"])
        self.assertEqual(matches.tolist(), [False, True])

    def test_window_uses_completed_sessions_plus_event_day(self):
        trading = pd.DatetimeIndex(pd.to_datetime(["2024-01-05", "2024-01-08", "2024-01-09"]))
        event = pd.Timestamp("2024-01-10T08:30", tz="America/New_York")
        dates = previous_trading_dates(trading, event, sessions=2)
        self.assertEqual(
            {value.isoformat() for value in dates},
            {"2024-01-08", "2024-01-09", "2024-01-10"},
        )

    def test_release_boundary_is_strict(self):
        event_time = pd.Timestamp("2024-01-10T08:30", tz="America/New_York")
        news = pd.DataFrame(
            {
                "headline": [
                    "Inflation awaits CPI release",
                    "CPI is released",
                    "Consumer prices surprise",
                ],
                "source": ["A", "A", "B"],
                "published_et": [
                    event_time - pd.Timedelta(minutes=1),
                    event_time,
                    event_time + pd.Timedelta(minutes=1),
                ],
                "local_date": [event_time.date()] * 3,
                "headline_key": ["before", "exact", "after"],
            }
        )
        events = pd.DataFrame(
            [
                {
                    "event_id": "cpi_test",
                    "family": "cpi",
                    "release_timestamp_et": event_time,
                    "source_url": "https://www.bls.gov/",
                }
            ]
        )
        trading = pd.DatetimeIndex(pd.to_datetime(["2024-01-08", "2024-01-09", "2024-01-10"]))
        rows, _ = audit_coverage(news, events, trading, self.patterns)
        for row in rows:
            self.assertEqual(row["matched_headlines_raw"], 1)


if __name__ == "__main__":
    unittest.main()
