#!/usr/bin/env python3
"""Run an outcome-blind historical Google News RSS coverage experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

import pandas as pd

from research.event_study.phase1_coverage import (
    DEFAULT_CALENDAR,
    PRIMARY_THRESHOLD,
    PRIMARY_WINDOW,
    ROOT,
    THRESHOLDS,
    WINDOWS,
    expand_calendar,
    load_json,
    normalize_headline,
    previous_trading_dates,
)


BASE_URL = "https://news.google.com/rss/search"
DEFAULT_CACHE = ROOT / "data/google_news_rss"
DEFAULT_HEADLINES = ROOT / "data/google_news_event_headlines.jsonl"
DEFAULT_OUTPUT = Path(__file__).with_name("artifacts")
USER_AGENT = "Mozilla/5.0 (compatible; academic coverage audit; +local research)"

QUERIES = {
    "fomc": (
        '("Federal Reserve" OR FOMC OR "Jerome Powell" OR "Fed rates" '
        'OR "Fed meeting")'
    ),
    "cpi": (
        '("U.S. inflation" OR "US inflation" OR "consumer price index" '
        'OR "CPI report" OR "inflation report" OR "price pressures")'
    ),
    "employment": (
        '("jobs report" OR payrolls OR "labor market" OR unemployment '
        'OR "jobless claims" OR hiring OR layoffs OR wages) '
        '(US OR "U.S." OR American)'
    ),
}

QUERY_VERSIONS = {"fomc": "v1", "cpi": "v1", "employment": "v2"}

TITLE_FILTERS = {
    "fomc": re.compile(
        r"\bFederal Reserve\b|\bFOMC\b|\b(?:Jerome )?Powell\b|\bFed(?:'s)?\b",
        re.IGNORECASE,
    ),
    "cpi": re.compile(
        r"\bCPI\b|\bconsumer price index\b|\bU\.?S\.? inflation\b|"
        r"\bUS inflation\b|\binflation (?:data|report|figures?|numbers?|reading|rate)\b",
        re.IGNORECASE,
    ),
    "employment": re.compile(
        r"\bjobs report\b|\bpayrolls?\b|\bnonfarm\b|"
        r"\bU\.?S\.? (?:jobs?|employment|unemployment|labou?r market|hiring|wages)\b|"
        r"\blabou?r market\b|\bjobless claims\b|"
        r"\bunemployment (?:rate|claims|benefits)\b",
        re.IGNORECASE,
    ),
}

OFFICIAL_SOURCE_PATTERNS = (
    "bureau of labor statistics",
    "federal reserve board",
    "federal reserve bank",
)


def build_query_url(query: str, start: date, end: date) -> str:
    dated_query = f"{query} after:{start.isoformat()} before:{end.isoformat()}"
    params = {
        "q": dated_query,
        "hl": "en-US",
        "gl": "US",
        "ceid": "US:en",
    }
    return f"{BASE_URL}?{urlencode(params)}"


def fetch_feed(url: str, destination: Path, retries: int = 4) -> bytes:
    if destination.exists():
        return destination.read_bytes()

    destination.parent.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(retries):
        try:
            with urlopen(request, timeout=60) as response:
                content = response.read()
            ET.fromstring(content)
            destination.write_bytes(content)
            return content
        except (HTTPError, URLError, TimeoutError, ET.ParseError) as error:
            if attempt == retries - 1:
                raise RuntimeError(f"Failed to fetch {url}: {error}") from error
            time.sleep(2 ** attempt)
    raise AssertionError("unreachable")


def clean_title(title: str, source: str) -> str:
    suffix = f" - {source}"
    if source and title.endswith(suffix):
        return title[: -len(suffix)].strip()
    return title.strip()


def parse_feed(content: bytes, event: dict[str, Any], query_url: str) -> list[dict[str, Any]]:
    root = ET.fromstring(content)
    records: list[dict[str, Any]] = []
    for item in root.findall("./channel/item"):
        source_element = item.find("source")
        source = (source_element.text or "").strip() if source_element is not None else ""
        raw_title = item.findtext("title", default="").strip()
        published = parsedate_to_datetime(item.findtext("pubDate"))
        title = clean_title(raw_title, source)
        records.append(
            {
                "event_id": event["event_id"],
                "family": event["family"],
                "release_timestamp_et": event["release_timestamp_et"],
                "headline": title,
                "headline_key": normalize_headline(title),
                "source": source,
                "source_homepage": source_element.get("url", "") if source_element is not None else "",
                "google_news_url": item.findtext("link", default="").strip(),
                "published_utc": published.isoformat(),
                "published_date": published.date().isoformat(),
                "query_url": query_url,
            }
        )
    return records


def is_non_news_official_source(source: str) -> bool:
    normalized = source.casefold()
    return any(pattern in normalized for pattern in OFFICIAL_SOURCE_PATTERNS)


def fetch_event(
    event: dict[str, Any], trading_dates: pd.DatetimeIndex, cache_dir: Path
) -> list[dict[str, Any]]:
    release = pd.Timestamp(event["release_timestamp_et"])
    previous = previous_trading_dates(trading_dates, release, max(WINDOWS))
    # One extra calendar day prevents ambiguity in Google's exclusive `after` filter.
    query_start = previous[0].date() - timedelta(days=1)
    query_end = release.date() + timedelta(days=1)
    url = build_query_url(QUERIES[event["family"]], query_start, query_end)
    version = QUERY_VERSIONS[event["family"]]
    suffix = "" if version == "v1" else f"_{version}"
    content = fetch_feed(url, cache_dir / f"{event['event_id']}{suffix}.xml")
    return parse_feed(content, event, url)


def selected_records(
    records: list[dict[str, Any]],
    event: dict[str, Any],
    trading_dates: pd.DatetimeIndex,
    sessions: int,
) -> list[dict[str, Any]]:
    release = pd.Timestamp(event["release_timestamp_et"])
    start = previous_trading_dates(trading_dates, release, sessions)[0].date()
    selected: dict[str, dict[str, Any]] = {}
    for record in records:
        published_date = date.fromisoformat(record["published_date"])
        # Historical RSS frequently supplies date-level rather than true clock time.
        # Excluding the release date prevents post-announcement leakage.
        if not (start <= published_date < release.date()):
            continue
        if is_non_news_official_source(record["source"]):
            continue
        if not TITLE_FILTERS[event["family"]].search(record["headline"]):
            continue
        selected.setdefault(record["headline_key"], record)
    return list(selected.values())


def build_coverage(
    all_records: dict[str, list[dict[str, Any]]],
    events: list[dict[str, Any]],
    trading_dates: pd.DatetimeIndex,
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    rows: list[dict[str, Any]] = []
    primary_samples: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        records = all_records[event["event_id"]]
        for window in WINDOWS:
            selected = selected_records(records, event, trading_dates, window)
            if window == PRIMARY_WINDOW:
                primary_samples[event["event_id"]] = selected
            rows.append(
                {
                    "event_id": event["event_id"],
                    "family": event["family"],
                    "release_timestamp_et": event["release_timestamp_et"],
                    "window_sessions": window,
                    "matched_headlines_unique": len(selected),
                    "source_count": len({item["source"] for item in selected}),
                    "release_day_excluded": True,
                }
            )
    return rows, primary_samples


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    frame = pd.DataFrame(rows)
    summary: dict[str, Any] = {"by_family": {}, "primary_gate": {}}
    for family in QUERIES:
        summary["by_family"][family] = {}
        for window in WINDOWS:
            values = frame.loc[
                (frame["family"] == family) & (frame["window_sessions"] == window),
                "matched_headlines_unique",
            ]
            summary["by_family"][family][str(window)] = {
                "events": int(values.size),
                "mean_unique_headlines": round(float(values.mean()), 2),
                "median_unique_headlines": round(float(values.median()), 2),
                "maximum_unique_headlines": int(values.max()),
                "events_passing": {
                    str(threshold): int((values >= threshold).sum())
                    for threshold in THRESHOLDS
                },
            }
        primary = frame.loc[
            (frame["family"] == family)
            & (frame["window_sessions"] == PRIMARY_WINDOW),
            "matched_headlines_unique",
        ]
        passing = int((primary >= PRIMARY_THRESHOLD).sum())
        summary["primary_gate"][family] = {
            "events_passing": passing,
            "events_total": int(primary.size),
            "standalone_viable": passing >= 25,
        }
    primary_all = frame.loc[
        frame["window_sessions"] == PRIMARY_WINDOW, "matched_headlines_unique"
    ]
    summary["primary_gate"]["pooled"] = {
        "events_passing": int((primary_all >= PRIMARY_THRESHOLD).sum()),
        "events_total": int(primary_all.size),
    }
    return summary


def write_local_headlines(path: Path, records: dict[str, list[dict[str, Any]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for event_records in records.values():
            for record in event_records:
                handle.write(json.dumps(record, ensure_ascii=True) + "\n")


def write_local_audit_sample(
    path: Path, primary_samples: dict[str, list[dict[str, Any]]], per_family: int = 30
) -> None:
    candidates: dict[str, dict[str, dict[str, Any]]] = {family: {} for family in QUERIES}
    for records in primary_samples.values():
        for record in records:
            candidates[record["family"]].setdefault(record["headline_key"], record)

    sample: list[dict[str, Any]] = []
    for family, family_records in candidates.items():
        ranked = sorted(
            family_records.values(),
            key=lambda item: hashlib.sha256(
                f"{family}|{item['source']}|{item['headline_key']}".encode()
            ).hexdigest(),
        )
        for record in ranked[:per_family]:
            sample.append(
                {
                    "family": family,
                    "headline": record["headline"],
                    "source": record["source"],
                    "published_date": record["published_date"],
                    "manual_relevance": None,
                    "review_notes": "",
                }
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sample, indent=2) + "\n", encoding="utf-8")


def source_diagnostics(
    primary_samples: dict[str, list[dict[str, Any]]]
) -> dict[str, dict[str, Any]]:
    diagnostics: dict[str, dict[str, Any]] = {}
    for family in QUERIES:
        records = [
            record
            for event_records in primary_samples.values()
            for record in event_records
            if record["family"] == family
        ]
        source_counts: dict[str, int] = {}
        for record in records:
            source = record["source"] or "Unknown"
            source_counts[source] = source_counts.get(source, 0) + 1
        top_source, top_count = (
            max(source_counts.items(), key=lambda item: item[1])
            if source_counts
            else ("", 0)
        )
        diagnostics[family] = {
            "accepted_event_headlines": len(records),
            "distinct_sources": len(source_counts),
            "top_source": top_source,
            "top_source_share": round(top_count / len(records), 4) if records else 0.0,
        }
    return diagnostics


def report(
    summary: dict[str, Any],
    diagnostics: dict[str, dict[str, Any]],
    total_records: int,
) -> str:
    lines = [
        "# Google News Coverage Expansion",
        "",
        "This is an outcome-blind feasibility experiment using historical Google",
        "News RSS result metadata. It is not yet an approved paper dataset.",
        "",
        "## Conservative Timing Rule",
        "",
        "Historical RSS timestamps are frequently date-like rather than reliable",
        "publication clock times. The audit therefore excludes every release-day",
        "headline and counts only unique headlines dated in completed pre-event",
        "sessions. Official Federal Reserve and BLS pages are excluded, and every",
        "headline must pass a transparent family-specific title relevance filter.",
        "",
        f"- Retrieved event-result records: {total_records:,}",
        "- Raw feeds and headline metadata: local `data/` directory (not in Git)",
        "- Primary gate: three completed sessions and at least eight headlines",
        "",
        "## Primary Coverage Gate",
        "",
        "| Family | Events with >=8 headlines | Total events | Standalone viable (>=25) |",
        "| --- | ---: | ---: | --- |",
    ]
    for family in QUERIES:
        gate = summary["primary_gate"][family]
        lines.append(
            f"| {family} | {gate['events_passing']} | {gate['events_total']} | "
            f"{'yes' if gate['standalone_viable'] else 'no'} |"
        )
    pooled = summary["primary_gate"]["pooled"]
    lines.extend(
        [
            f"| pooled | {pooled['events_passing']} | {pooled['events_total']} | n/a |",
            "",
            "## Sensitivity",
            "",
            "| Family | Sessions | Mean | Median | Max | >=5 | >=8 | >=10 | >=15 |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for family in QUERIES:
        for window in WINDOWS:
            item = summary["by_family"][family][str(window)]
            passed = item["events_passing"]
            lines.append(
                f"| {family} | {window} | {item['mean_unique_headlines']:.2f} | "
                f"{item['median_unique_headlines']:.2f} | {item['maximum_unique_headlines']} | "
                f"{passed['5']} | {passed['8']} | {passed['10']} | {passed['15']} |"
            )
    lines.extend(
        [
            "",
            "## Source Breadth In Primary Windows",
            "",
            "| Family | Accepted event-headlines | Distinct sources | Top source share |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for family in QUERIES:
        item = diagnostics[family]
        lines.append(
            f"| {family} | {item['accepted_event_headlines']} | "
            f"{item['distinct_sources']} | {item['top_source_share']:.1%} |"
        )
    lines.extend(
        [
            "",
            "## Methodological Status",
            "",
            "Passing this gate establishes approximate coverage, not validated relevance",
            "or predictive value. The local audit sample must be manually reviewed.",
            "Google News RSS terms restrict reuse, and result rankings are not a stable",
            "sampling frame. A paper should prefer a documented API/archive with",
            "reproducible access.",
            "This source can justify the next data-acquisition step but should not be",
            "silently merged with the student labels.",
            "",
            "## Decision",
            "",
            "FOMC clears the preliminary title-filtered coverage gate and should be",
            "prioritized as the first case study. CPI and Employment Situation do not",
            "clear the same primary gate and remain deferred. Before outcome modeling,",
            "the FOMC sample still requires manual relevance review, a stable archival",
            "data source or frozen local snapshot with acceptable terms, and new",
            "sentiment labels generated under a documented measurement protocol.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calendar", type=Path, default=DEFAULT_CALENDAR)
    parser.add_argument("--market", type=Path, default=ROOT / "data/market_panel.csv")
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--headlines", type=Path, default=DEFAULT_HEADLINES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    events_frame = expand_calendar(load_json(args.calendar))
    events = []
    for row in events_frame.to_dict(orient="records"):
        row["release_timestamp_et"] = row["release_timestamp_et"].isoformat()
        events.append(row)
    market = pd.read_csv(args.market, usecols=["Date"])
    trading_dates = pd.DatetimeIndex(
        pd.to_datetime(market["Date"].dropna().unique())
    ).sort_values()

    all_records: dict[str, list[dict[str, Any]]] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(fetch_event, event, trading_dates, args.cache): event
            for event in events
        }
        for completed, future in enumerate(as_completed(futures), start=1):
            event = futures[future]
            all_records[event["event_id"]] = future.result()
            if completed % 10 == 0 or completed == len(futures):
                print(f"Fetched or loaded {completed}/{len(futures)} event feeds")

    all_records = dict(sorted(all_records.items()))
    write_local_headlines(args.headlines, all_records)
    rows, primary_samples = build_coverage(all_records, events, trading_dates)
    summary = summarize(rows)
    diagnostics = source_diagnostics(primary_samples)
    write_local_audit_sample(
        ROOT / "data/google_news_topic_audit_sample.json", primary_samples
    )

    args.output.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "retrieved_on": date.today().isoformat(),
        "source": BASE_URL,
        "queries": QUERIES,
        "query_versions": QUERY_VERSIONS,
        "title_filters": {
            family: pattern.pattern for family, pattern in TITLE_FILTERS.items()
        },
        "release_day_excluded": True,
        "summary": summary,
        "source_diagnostics": diagnostics,
        "events": rows,
    }
    (args.output / "google_news_coverage_audit.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    (args.output / "GOOGLE_NEWS_EXPANSION_REPORT.md").write_text(
        report(
            summary,
            diagnostics,
            sum(len(records) for records in all_records.values()),
        ),
        encoding="utf-8",
    )

    for family, gate in summary["primary_gate"].items():
        print(f"{family}: {gate['events_passing']}/{gate['events_total']} pass primary coverage")


if __name__ == "__main__":
    main()
