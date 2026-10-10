#!/usr/bin/env python3
"""Fetch a cached, outcome-blind geopolitical headline snapshot from GDELT."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
# GDELT's HTTPS listener timed out during collection while the documented API
# host served the same public endpoint over HTTP. No credentials are transmitted.
BASE_URL = "http://api.gdeltproject.org/api/v2/doc/doc"
DEFAULT_CONFIG = HERE / "topics.json"
DEFAULT_CACHE = ROOT / "data/gdelt_geopolitical_cache"
DEFAULT_OUTPUT = ROOT / "data/geopolitical_news_gdelt.jsonl"
DEFAULT_MANIFEST = HERE / "artifacts/geopolitical_collection_manifest.json"
USER_AGENT = "Belief-Dispersion academic research collector/1.0"
MAX_RECORDS = 75


@dataclass(frozen=True)
class Window:
    start: date
    end: date

    @property
    def days(self) -> int:
        return (self.end - self.start).days


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def normalize_headline(value: str) -> str:
    return " ".join("".join(character.casefold() if character.isalnum() else " " for character in value).split())


def load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    required = {"sample_start", "sample_end", "language", "topics"}
    missing = required.difference(config)
    if missing:
        raise ValueError(f"Topic config lacks required fields: {sorted(missing)}")
    if not config["topics"]:
        raise ValueError("Topic config contains no topics")
    return config


def initial_windows(start: date, end_exclusive: date, days: int) -> list[Window]:
    if days < 1 or start >= end_exclusive:
        raise ValueError("Collection window and slice length must be positive")
    windows: list[Window] = []
    cursor = start
    while cursor < end_exclusive:
        stop = min(cursor + timedelta(days=days), end_exclusive)
        windows.append(Window(cursor, stop))
        cursor = stop
    return windows


def split_window(window: Window) -> tuple[Window, Window]:
    if window.days <= 1:
        raise ValueError("A one-day window cannot be split")
    midpoint = window.start + timedelta(days=window.days // 2)
    return Window(window.start, midpoint), Window(midpoint, window.end)


def build_query_url(
    query: str,
    language: str,
    window: Window,
    max_records: int = MAX_RECORDS,
    sort: str = "HybridRel",
) -> str:
    qualified_query = f"{query} sourcelang:{language}"
    params = {
        "query": qualified_query,
        "mode": "artlist",
        "maxrecords": str(max_records),
        "format": "json",
        "startdatetime": window.start.strftime("%Y%m%d000000"),
        "enddatetime": window.end.strftime("%Y%m%d000000"),
        "sort": sort,
    }
    return f"{BASE_URL}?{urlencode(params)}"


def cache_path(
    cache_dir: Path, topic: str, window: Window, request_url: str = ""
) -> Path:
    request_hash = hashlib.sha256(request_url.encode("utf-8")).hexdigest()[:12]
    return cache_dir / topic / f"{window.start}_{window.end}_{request_hash}.json"


def fetch_json(
    url: str,
    destination: Path,
    timeout: int,
    retries: int,
    delay: float,
) -> dict[str, Any]:
    if destination.exists():
        return json.loads(destination.read_text(encoding="utf-8"))

    request = Request(url, headers={"User-Agent": USER_AGENT})
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, dict) or not isinstance(payload.get("articles"), list):
                raise ValueError("GDELT response does not contain an article list")
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
            temporary.replace(destination)
            if delay:
                time.sleep(delay)
            return payload
        except HTTPError as error:
            last_error = error
            if attempt + 1 < retries:
                retry_after = error.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else max(delay, 15.0) * (2**attempt)
                time.sleep(wait)
        except (URLError, TimeoutError, ValueError, json.JSONDecodeError) as error:
            last_error = error
            if attempt + 1 < retries:
                time.sleep(max(delay, 2.0) * (2**attempt))
    raise RuntimeError(f"Failed to fetch {url}: {last_error}") from last_error


def parse_seen_date(value: str) -> str:
    value = value.strip()
    for pattern in ("%Y%m%dT%H%M%SZ", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            parsed = datetime.strptime(value, pattern).replace(tzinfo=timezone.utc)
            return parsed.isoformat()
        except ValueError:
            continue
    return value


def normalize_article(
    article: dict[str, Any], topic: str, window: Window, query: str
) -> dict[str, Any] | None:
    headline = str(article.get("title", "")).strip()
    url = str(article.get("url", "")).strip()
    if not headline or not url:
        return None
    return {
        "headline": headline,
        "headline_key": normalize_headline(headline),
        "url": url,
        "domain": str(article.get("domain", "")).strip(),
        "language": str(article.get("language", "")).strip(),
        "source_country": str(article.get("sourcecountry", "")).strip(),
        "gdelt_seen_utc": parse_seen_date(str(article.get("seendate", ""))),
        "candidate_topic": topic,
        "query": query,
        "query_window_start": window.start.isoformat(),
        "query_window_end_exclusive": window.end.isoformat(),
        "retrieval_source": "GDELT DOC 2.0 API",
    }


def collect_topic(
    topic: str,
    query: str,
    language: str,
    start: date,
    end_exclusive: date,
    cache_dir: Path,
    initial_window_days: int,
    minimum_window_days: int,
    max_records: int,
    sort: str,
    timeout: int,
    retries: int,
    delay: float,
    workers: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    queue = deque(initial_windows(start, end_exclusive, initial_window_days))
    accepted_windows: list[Window] = []
    capped_windows: list[dict[str, str]] = []
    records: list[dict[str, Any]] = []
    requests = 0

    if workers < 1:
        raise ValueError("Worker count must be positive")
    with ThreadPoolExecutor(max_workers=workers) as executor:
        while queue:
            batch = [queue.popleft() for _ in range(min(len(queue), workers * 2))]
            futures = {}
            for window in batch:
                url = build_query_url(query, language, window, max_records, sort)
                future = executor.submit(
                    fetch_json,
                    url,
                    cache_path(cache_dir, topic, window, url),
                    timeout,
                    retries,
                    delay,
                )
                futures[future] = window

            for future in as_completed(futures):
                window = futures[future]
                payload = future.result()
                requests += 1
                articles = payload["articles"]
                if len(articles) >= max_records and window.days > minimum_window_days:
                    left, right = split_window(window)
                    queue.extend((left, right))
                    continue

                accepted_windows.append(window)
                if len(articles) >= max_records:
                    capped_windows.append(
                        {
                            "start": window.start.isoformat(),
                            "end_exclusive": window.end.isoformat(),
                        }
                    )
                for article in articles:
                    normalized = normalize_article(article, topic, window, query)
                    if normalized is not None:
                        records.append(normalized)
            if requests % 50 < len(batch):
                print(
                    f"  {topic}: {requests:,} cached/fetched slices, "
                    f"{len(queue):,} queued",
                    flush=True,
                )

    deduplicated: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        key = (record["url"], record["headline_key"])
        deduplicated.setdefault(key, record)
    result = sorted(
        deduplicated.values(),
        key=lambda row: (row["gdelt_seen_utc"], row["domain"], row["headline_key"]),
    )
    diagnostics = {
        "requests": requests,
        "accepted_windows": len(accepted_windows),
        "raw_normalized_records": len(records),
        "unique_records": len(result),
        "distinct_domains": len({row["domain"] for row in result if row["domain"]}),
        "capped_windows": sorted(capped_windows, key=lambda item: item["start"]),
    }
    return result, diagnostics


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
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
    parser.add_argument("--initial-window-days", type=int, default=7)
    parser.add_argument("--minimum-window-days", type=int, default=7)
    parser.add_argument("--max-records", type=int, default=MAX_RECORDS)
    parser.add_argument("--sort", default="HybridRel")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--delay", type=float, default=2.0)
    parser.add_argument("--workers", type=int, default=1)
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

    all_rows: list[dict[str, Any]] = []
    diagnostics: dict[str, Any] = {}
    for topic in selected:
        print(f"Collecting {topic} from {start} through {inclusive_end}", flush=True)
        topic_config = config["topics"][topic]
        rows, topic_diagnostics = collect_topic(
            topic=topic,
            query=topic_config["query"],
            language=config["language"],
            start=start,
            end_exclusive=end_exclusive,
            cache_dir=args.cache,
            initial_window_days=args.initial_window_days,
            minimum_window_days=args.minimum_window_days,
            max_records=args.max_records,
            sort=args.sort,
            timeout=args.timeout,
            retries=args.retries,
            delay=args.delay,
            workers=args.workers,
        )
        diagnostics[topic] = topic_diagnostics
        all_rows.extend(rows)
        print(
            f"  {len(rows):,} unique records from "
            f"{topic_diagnostics['distinct_domains']:,} domains; "
            f"{len(topic_diagnostics['capped_windows'])} capped windows",
            flush=True,
        )

    all_rows.sort(
        key=lambda row: (
            row["gdelt_seen_utc"],
            row["candidate_topic"],
            row["domain"],
            row["headline_key"],
        )
    )
    write_jsonl(args.output, all_rows)
    source_counts = Counter(row["domain"] or "Unknown" for row in all_rows)
    manifest = {
        "schema_version": 1,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "sample_start": start.isoformat(),
        "sample_end": inclusive_end.isoformat(),
        "source": BASE_URL,
        "config": display_path(args.config),
        "config_sha256": sha256_file(args.config),
        "output": display_path(args.output),
        "output_sha256": sha256_file(args.output),
        "rows": len(all_rows),
        "distinct_urls": len({row["url"] for row in all_rows}),
        "distinct_domains": len(source_counts),
        "top_domains": source_counts.most_common(25),
        "topics": {topic: config["topics"][topic] for topic in selected},
        "diagnostics": diagnostics,
        "limitations": [
            "The public GDELT endpoint was retrieved over HTTP because its HTTPS listener timed out.",
            "GDELT article lists are ranked and capped at the configured maximum.",
            "Windows that hit the configured cap are listed under capped_windows.",
            "gdelt_seen_utc is GDELT's seen time and is not guaranteed to be the publisher timestamp.",
            "Candidate-topic membership is query based and requires relevance validation.",
            "Records may include syndicated or near-duplicate stories across domains.",
        ],
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(all_rows):,} topic-records to {args.output}", flush=True)


if __name__ == "__main__":
    main()
