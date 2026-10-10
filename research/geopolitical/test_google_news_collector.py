import unittest
from datetime import date
from urllib.parse import parse_qs, urlparse

from research.geopolitical.collector import Window
from research.geopolitical.google_news_collector import (
    build_query_url,
    feed_item_count,
    parse_feed,
)


SAMPLE_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss><channel><item>
<title>Iran and Israel exchange warnings - Example News</title>
<link>https://news.google.com/rss/articles/example</link>
<pubDate>Sat, 13 Apr 2024 12:00:00 GMT</pubDate>
<source url="https://example.com">Example News</source>
</item></channel></rss>"""


class GoogleNewsGeopoliticalTests(unittest.TestCase):
    def test_query_uses_explicit_week_bounds(self):
        window = Window(date(2024, 4, 1), date(2024, 4, 8))
        url = build_query_url("Iran Israel", window)
        query = parse_qs(urlparse(url).query)["q"][0]
        self.assertIn("after:2024-04-01", query)
        self.assertIn("before:2024-04-08", query)

    def test_feed_parser_preserves_topic_and_source(self):
        window = Window(date(2024, 4, 8), date(2024, 4, 15))
        rows = parse_feed(SAMPLE_FEED, "iran_test", window, "Iran Israel")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["headline"], "Iran and Israel exchange warnings")
        self.assertEqual(rows[0]["source"], "Example News")
        self.assertEqual(rows[0]["candidate_topic"], "iran_test")
        self.assertEqual(rows[0]["published_utc"], "2024-04-13T12:00:00+00:00")

    def test_feed_parser_rejects_rows_outside_query_window(self):
        window = Window(date(2024, 4, 1), date(2024, 4, 8))
        self.assertEqual(parse_feed(SAMPLE_FEED, "iran_test", window, "Iran Israel"), [])

    def test_raw_feed_count_is_independent_of_date_filter(self):
        self.assertEqual(feed_item_count(SAMPLE_FEED), 1)


if __name__ == "__main__":
    unittest.main()
