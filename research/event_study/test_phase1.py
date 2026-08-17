import unittest
from pathlib import Path

import pandas as pd

from research.event_study.google_news_expansion import (
    QUERIES,
    build_query_url,
    clean_title,
    selected_records,
)
from research.event_study.phase1_coverage import (
    audit_coverage,
    compile_topic_patterns,
    expand_calendar,
    load_json,
    pre_event_window_start,
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
            {value.date().isoformat() for value in dates},
            {"2024-01-08", "2024-01-09"},
        )
        self.assertEqual(
            pre_event_window_start(trading, event, sessions=2),
            pd.Timestamp("2024-01-08T00:00", tz="America/New_York"),
        )

    def test_window_is_continuous_across_weekend(self):
        trading = pd.DatetimeIndex(
            pd.to_datetime(["2024-01-04", "2024-01-05", "2024-01-08"])
        )
        event = pd.Timestamp("2024-01-09T08:30", tz="America/New_York")
        start = pre_event_window_start(trading, event, sessions=2)
        weekend = pd.Timestamp("2024-01-07T12:00", tz="America/New_York")
        self.assertLessEqual(start, weekend)
        self.assertLess(weekend, event)

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
        trading = pd.DatetimeIndex(
            pd.to_datetime(
                [
                    "2024-01-03",
                    "2024-01-04",
                    "2024-01-05",
                    "2024-01-08",
                    "2024-01-09",
                    "2024-01-10",
                ]
            )
        )
        rows, _ = audit_coverage(news, events, trading, self.patterns)
        for row in rows:
            self.assertEqual(row["matched_headlines_raw"], 1)


class GoogleNewsExpansionTests(unittest.TestCase):
    def test_query_has_explicit_historical_bounds(self):
        url = build_query_url(
            '"Federal Reserve"',
            pd.Timestamp("2024-01-01").date(),
            pd.Timestamp("2024-01-10").date(),
        )
        self.assertIn("after%3A2024-01-01", url)
        self.assertIn("before%3A2024-01-10", url)

    def test_employment_query_does_not_use_nested_outer_group(self):
        self.assertFalse(QUERIES["employment"].startswith("(("))

    def test_source_suffix_is_removed_from_title(self):
        self.assertEqual(
            clean_title("Fed Holds Rates - Example News", "Example News"),
            "Fed Holds Rates",
        )

    def test_external_sample_excludes_release_day_and_official_pages(self):
        event = {
            "event_id": "cpi_test",
            "family": "cpi",
            "release_timestamp_et": "2024-01-10T08:30:00-05:00",
        }
        records = [
            {
                "headline": "US inflation report is due tomorrow",
                "headline_key": "valid",
                "published_date": "2024-01-09",
                "source": "Example News",
            },
            {
                "headline": "US inflation report is released",
                "headline_key": "release day",
                "published_date": "2024-01-10",
                "source": "Example News",
            },
            {
                "headline": "Consumer price index release calendar",
                "headline_key": "official",
                "published_date": "2024-01-09",
                "source": "Bureau of Labor Statistics (.gov)",
            },
            {
                "headline": "A completely unrelated story",
                "headline_key": "query false positive",
                "published_date": "2024-01-09",
                "source": "Example News",
            },
        ]
        trading = pd.DatetimeIndex(
            pd.to_datetime(
                [
                    "2024-01-03",
                    "2024-01-04",
                    "2024-01-05",
                    "2024-01-08",
                    "2024-01-09",
                ]
            )
        )
        selected = selected_records(records, event, trading, sessions=3)
        self.assertEqual([item["headline_key"] for item in selected], ["valid"])


if __name__ == "__main__":
    unittest.main()
