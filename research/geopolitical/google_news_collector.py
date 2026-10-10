#!/usr/bin/env python3
"""Fetch a cached geopolitical headline snapshot from Google News RSS."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from xml.etree import ElementTree as ET

from research.event_study.google_news_expansion import clean_title, fetch_feed
from research.geopolitical.collector import (
    ROOT,
    HERE,
    Window,
    display_path,
    initial_windows,
    load_config,
    normalize_headline,
    sha256_file,
)


BASE_URL = "https://news.google.com/rss/search"
DEFAULT_CONFIG = HERE / "topics.json"
DEFAULT_CACHE = ROOT / "data/google_news_geopolitical_cache"
DEFAULT_OUTPUT = ROOT / "data/geopolitical_news_google.jsonl"
DEFAULT_MANIFEST = HERE / "artifacts/google_news_geopolitical_manifest.json"
RESULT_CAP = 100


def build_query_url(query: str, window: Window) -> str:
    dated_query = (
        f"{query} after:{window.start.isoformat()} before:{window.end.isoformat()}"
    )
    params = {
        "q": dated_query,
        "hl": "en-US",
        "gl": "US",
        "ceid": "US:en",
    }
    return f"{BASE_URL}?{urlencode(params)}"


def cache_path(cache_dir: Path, topic: str, window: Window, url: str) -> Path:
    fingerprint = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    return cache_dir / topic / f"{window.start}_{window.end}_{fingerprint}.xml"


def parse_feed(content: bytes, topic: str, window: Window, query: str) -> list[dict[str, Any]]:
    root = ET.fromstring(content)
    rows: list[dict[str, Any]] = []
    for item in root.findall("./channel/item"):
        source_element = item.find("source")
        source = (source_element.text or "").strip() if source_element is not None else ""
        headline = clean_title(item.findtext("title", default="").strip(), source)
        link = item.findtext("link", default="").strip()
        published = item.findtext("pubDate", default="").strip()
        if not headline or not link or not published:
            continue
        published_utc = parsedate_to_datetime(published).astimezone(timezone.utc)
        if not (window.start <= published_utc.date() < window.end):
            continue
        rows.append(
            {
                "headline": headline,
                "headline_key": normalize_headline(headline),
                "source": source,
                "source_homepage": source_element.get("url", "") if source_element is not None else "",
                "google_news_url": link,
                "published_utc": published_utc.isoformat(),
                "candidate_topic": topic,
                "query": query,
                "query_window_start": window.start.isoformat(),
                "query_window_end_exclusive": window.end.isoformat(),
                "retrieval_source": "Google News RSS",
            }
        )
    return rows


def feed_item_count(content: bytes) -> int:
    return len(ET.fromstring(content).findall("./channel/item"))


def fetch_window(
    topic: str,
    query: str,
    window: Window,
    cache_dir: Path,
    retries: int,
) -> tuple[Window, int, list[dict[str, Any]]]:
    url = build_query_url(query, window)
    content = fetch_feed(url, cache_path(cache_dir, topic, window, url), retries=retries)
    return window, feed_item_count(content), parse_feed(content, topic, window, query)


def collect_topic(
    topic: str,
    query: str,
    start: date,
    end_exclusive: date,
    cache_dir: Path,
    window_days: int,
    workers: int,
    retries: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    windows = initial_windows(start, end_exclusive, window_days)
    rows: list[dict[str, Any]] = []
    capped: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(fetch_window, topic, query, window, cache_dir, retries): window
            for window in windows
        }
        for completed, future in enumerate(as_completed(futures), start=1):
            window, raw_item_count, window_rows = future.result()
            rows.extend(window_rows)
            if raw_item_count >= RESULT_CAP:
                capped.append(
                    {
                        "start": window.start.isoformat(),
                        "end_exclusive": window.end.isoformat(),
                    }
                )
            if completed % 25 == 0 or completed == len(windows):
                print(f"  {topic}: {completed}/{len(windows)} weekly feeds", flush=True)

    deduplicated: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        deduplicated.setdefault((row["google_news_url"], row["headline_key"]), row)
    result = sorted(
        deduplicated.values(),
        key=lambda row: (row["published_utc"], row["source"], row["headline_key"]),
    )
    diagnostics = {
        "windows": len(windows),
        "raw_records": len(rows),
        "unique_records": len(result),
        "distinct_sources": len({row["source"] for row in result if row["source"]}),
        "capped_windows": sorted(capped, key=lambda item: item["start"]),
    }
    return result, diagnostics


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")
    temporary.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--start", type=date.fromisoformat)
    parser.add_argument("--end", type=date.fromisoformat)
    parser.add_argument("--topic", action="append", dest="topics")
    parser.add_argument("--window-days", type=int, default=7)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--retries", type=int, default=4)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    start = args.start or date.fromisoformat(config["sample_start"])
    inclusive_end = args.end or date.fromisoformat(config["sample_end"])
    end_exclusive = inclusive_end + timedelta(days=1)
    selected = args.topics or list(config["topics"])
    unknown = set(selected).difference(config["topics"])
    if unknown:
        raise ValueError(f"Unknown topics: {sorted(unknown)}")
    if args.workers < 1:
        raise ValueError("Worker count must be positive")

    all_rows: list[dict[str, Any]] = []
    diagnostics: dict[str, Any] = {}
    for topic in selected:
        print(f"Collecting {topic} from {start} through {inclusive_end}", flush=True)
        query = config["topics"][topic]["query"]
        rows, topic_diagnostics = collect_topic(
            topic,
            query,
            start,
            end_exclusive,
            args.cache,
            args.window_days,
            args.workers,
            args.retries,
        )
        diagnostics[topic] = topic_diagnostics
        all_rows.extend(rows)
        print(
            f"  {len(rows):,} unique records from "
            f"{topic_diagnostics['distinct_sources']:,} sources; "
            f"{len(topic_diagnostics['capped_windows'])} capped weeks",
            flush=True,
        )

    all_rows.sort(
        key=lambda row: (
            row["published_utc"],
            row["candidate_topic"],
            row["source"],
            row["headline_key"],
        )
    )
    write_jsonl(args.output, all_rows)
    source_counts = Counter(row["source"] or "Unknown" for row in all_rows)
    topic_membership: dict[str, set[str]] = {}
    for row in all_rows:
        topic_membership.setdefault(row["google_news_url"], set()).add(
            row["candidate_topic"]
        )
    parsed_times = [datetime.fromisoformat(row["published_utc"]) for row in all_rows]
    date_like_timestamps = sum(
        value.hour in {7, 8} and value.minute == 0 and value.second == 0
        for value in parsed_times
    )
    manifest = {
        "schema_version": 1,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "sample_start": start.isoformat(),
        "sample_end": inclusive_end.isoformat(),
        "source": BASE_URL,
        "sampling_frame": f"up to {RESULT_CAP} Google News RSS results per topic per {args.window_days}-day interval",
        "config": display_path(args.config),
        "config_sha256": sha256_file(args.config),
        "output": display_path(args.output),
        "output_sha256": sha256_file(args.output),
        "rows": len(all_rows),
        "distinct_normalized_headlines": len({row["headline_key"] for row in all_rows}),
        "distinct_google_news_urls": len({row["google_news_url"] for row in all_rows}),
        "distinct_sources": len(source_counts),
        "cross_topic_urls": sum(len(topics) > 1 for topics in topic_membership.values()),
        "date_like_timestamp_rows": date_like_timestamps,
        "date_like_timestamp_share": round(date_like_timestamps / len(all_rows), 6)
        if all_rows
        else 0.0,
        "top_sources": source_counts.most_common(25),
        "topics": {topic: config["topics"][topic] for topic in selected},
        "diagnostics": diagnostics,
        "limitations": [
            "Google News RSS results are ranked and are not an exhaustive news archive.",
            "Windows returning 100 records are listed as capped_windows.",
            "Historical RSS timestamps may be date-like rather than exact publisher times.",
            "Candidate-topic membership is query based and requires relevance validation.",
            "Google News URLs and source labels require syndication and duplicate auditing.",
            "Retrieval and reuse must comply with Google News and publisher terms.",
        ],
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(all_rows):,} topic-records to {args.output}", flush=True)


if __name__ == "__main__":
    main()
