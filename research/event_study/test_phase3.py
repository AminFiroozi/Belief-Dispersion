import tempfile
import unittest
from pathlib import Path

import pandas as pd

from research.event_study.phase3_validation_sample import (
    RATER_COLUMNS,
    allocate_event_slots,
    build_sample,
    hidden_key,
    rater_frame,
)


class ValidationSamplingTests(unittest.TestCase):
    def setUp(self):
        rows = []
        for event_number, count in enumerate([1, 3, 6], start=1):
            event_id = f"fomc_202{event_number}0101_1400"
            for headline_number in range(count):
                rows.append(
                    {
                        "event_id": event_id,
                        "event_year": f"202{event_number}",
                        "published_date": f"202{event_number}-01-01",
                        "source": f"Source {headline_number % 2}",
                        "source_band": "2-4",
                        "headline": f"Headline {event_number}-{headline_number}",
                        "headline_key": f"key-{event_number}-{headline_number}",
                    }
                )
        self.candidates = pd.DataFrame(rows)

    def test_allocation_represents_every_event_and_respects_capacity(self):
        counts = self.candidates.groupby("event_id").size()
        allocation = allocate_event_slots(counts, sample_size=7)
        self.assertEqual(int(allocation.sum()), 7)
        self.assertTrue((allocation >= 1).all())
        self.assertTrue((allocation <= counts).all())

    def test_sample_is_deterministic_and_represents_every_event(self):
        first = build_sample(self.candidates, sample_size=7)
        second = build_sample(self.candidates, sample_size=7)
        self.assertEqual(first["headline_key"].tolist(), second["headline_key"].tolist())
        self.assertEqual(first["event_id"].nunique(), 3)

    def test_rater_export_contains_no_event_metadata(self):
        sample = build_sample(self.candidates, sample_size=7)
        rater = rater_frame(sample, rater=1)
        self.assertEqual(rater.columns.tolist(), RATER_COLUMNS)
        self.assertNotIn("event_id", rater.columns)
        self.assertNotIn("source", rater.columns)
        self.assertNotIn("published_date", rater.columns)
        self.assertTrue(rater["topic_relevance"].eq("").all())

    def test_hidden_key_retains_provenance(self):
        sample = build_sample(self.candidates, sample_size=7)
        key = hidden_key(sample)
        for column in ["event_id", "published_date", "source", "headline_key"]:
            self.assertIn(column, key.columns)

    def test_csv_round_trip_preserves_blank_label_fields(self):
        sample = build_sample(self.candidates, sample_size=7)
        rater = rater_frame(sample, rater=1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rater.csv"
            rater.to_csv(path, index=False)
            loaded = pd.read_csv(path, keep_default_na=False)
        self.assertEqual(loaded.columns.tolist(), RATER_COLUMNS)
        self.assertTrue(loaded["equity_sentiment"].eq("").all())


if __name__ == "__main__":
    unittest.main()

