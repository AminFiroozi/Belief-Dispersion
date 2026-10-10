import tempfile
import unittest
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from research.geopolitical.collector import (
    Window,
    build_query_url,
    cache_path,
    display_path,
    initial_windows,
    normalize_article,
    normalize_headline,
    split_window,
)


class GeopoliticalCollectorTests(unittest.TestCase):
    def test_initial_windows_cover_interval_without_overlap(self):
        windows = initial_windows(date(2024, 1, 1), date(2024, 2, 1), 10)
        self.assertEqual(windows[0], Window(date(2024, 1, 1), date(2024, 1, 11)))
        self.assertEqual(windows[-1], Window(date(2024, 1, 31), date(2024, 2, 1)))
        for previous, current in zip(windows, windows[1:]):
            self.assertEqual(previous.end, current.start)

    def test_split_window_is_contiguous(self):
        original = Window(date(2024, 1, 1), date(2024, 1, 10))
        left, right = split_window(original)
        self.assertEqual(left.start, original.start)
        self.assertEqual(left.end, right.start)
        self.assertEqual(right.end, original.end)
        self.assertEqual(left.days + right.days, original.days)

    def test_query_url_has_explicit_bounds_and_language(self):
        window = Window(date(2024, 4, 1), date(2024, 4, 2))
        url = build_query_url("(Iran OR Iranian) Israel", "english", window)
        params = parse_qs(urlparse(url).query)
        self.assertEqual(params["startdatetime"], ["20240401000000"])
        self.assertEqual(params["enddatetime"], ["20240402000000"])
        self.assertIn("sourcelang:english", params["query"][0])
        self.assertEqual(params["maxrecords"], ["75"])
        self.assertEqual(params["sort"], ["HybridRel"])

    def test_normalization_preserves_provenance(self):
        window = Window(date(2024, 4, 1), date(2024, 4, 2))
        article = {
            "title": "Iran-Israel Tensions Rise",
            "url": "https://example.com/story",
            "domain": "example.com",
            "language": "English",
            "sourcecountry": "United States",
            "seendate": "20240401T121500Z",
        }
        row = normalize_article(article, "iran_test", window, "Iran Israel")
        self.assertIsNotNone(row)
        self.assertEqual(row["headline_key"], "iran israel tensions rise")
        self.assertEqual(row["candidate_topic"], "iran_test")
        self.assertEqual(row["gdelt_seen_utc"], "2024-04-01T12:15:00+00:00")
        self.assertEqual(row["query_window_end_exclusive"], "2024-04-02")

    def test_cache_paths_are_topic_isolated(self):
        window = Window(date(2024, 1, 1), date(2024, 1, 2))
        with tempfile.TemporaryDirectory() as directory:
            first = cache_path(Path(directory), "topic_a", window)
            second = cache_path(Path(directory), "topic_b", window)
        self.assertNotEqual(first, second)

    def test_headline_normalization_is_case_and_punctuation_insensitive(self):
        self.assertEqual(
            normalize_headline("Iran-Israel: Tensions Rise!"),
            normalize_headline("IRAN ISRAEL tensions rise"),
        )

    def test_display_path_accepts_external_outputs(self):
        self.assertEqual(display_path(Path("/tmp/example.jsonl")), "/tmp/example.jsonl")


if __name__ == "__main__":
    unittest.main()
