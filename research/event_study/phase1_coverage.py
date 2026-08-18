#!/usr/bin/env python3
"""Audit topic-news coverage around scheduled macroeconomic events."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CALENDAR = Path(__file__).with_name("event_calendar.json")
DEFAULT_RULES = Path(__file__).with_name("topic_rules.json")
DEFAULT_OUTPUT = Path(__file__).with_name("artifacts")
WINDOWS = (1, 3, 5)
THRESHOLDS = (5, 8, 10, 15)
PRIMARY_WINDOW = 3
PRIMARY_THRESHOLD = 8


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def source_key(family: str, year: int) -> str:
    if family == "fomc":
        return "fomc_2020" if year == 2020 else "fomc_2021_2025"
    return f"bls_{year}"


def expand_calendar(config: dict[str, Any]) -> pd.DataFrame:
    timezone = config["timezone"]
    rows: list[dict[str, Any]] = []
    for family, timestamps in config["events"].items():
        for value in timestamps:
            timestamp = pd.Timestamp(value, tz=timezone)
            key = source_key(family, timestamp.year)
            rows.append(
                {
                    "event_id": f"{family}_{timestamp:%Y%m%d_%H%M}",
                    "family": family,
                    "release_timestamp_et": timestamp,
                    "source_url": config["sources"][key],
                }
            )
    return pd.DataFrame(rows).sort_values("release_timestamp_et").reset_index(drop=True)


def compile_topic_patterns(config: dict[str, Any]) -> dict[str, tuple[re.Pattern[str], re.Pattern[str] | None]]:
    flags = 0 if config.get("case_sensitive") else re.IGNORECASE
    compiled: dict[str, tuple[re.Pattern[str], re.Pattern[str] | None]] = {}
    for family, rules in config["rules"].items():
        include = re.compile("(?:" + ")|(?:".join(rules["include"]) + ")", flags)
        exclusions = rules.get("exclude", [])
        exclude = re.compile("(?:" + ")|(?:".join(exclusions) + ")", flags) if exclusions else None
        compiled[family] = (include, exclude)
    return compiled


def topic_mask(text: pd.Series, patterns: tuple[re.Pattern[str], re.Pattern[str] | None]) -> pd.Series:
    include, exclude = patterns
    values = text.fillna("").astype(str)
    mask = values.str.contains(include, regex=True)
    if exclude is not None:
        mask &= ~values.str.contains(exclude, regex=True)
    return mask


def normalize_headline(value: str) -> str:
    value = value.casefold()
    value = re.sub(r"[^\w\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def load_news(path: Path, timezone: str) -> pd.DataFrame:
    columns = ["headline", "source", "date", "sentiment_class"]
    news = pd.read_csv(path, usecols=columns)
    news["published_utc"] = pd.to_datetime(news["date"], utc=True, errors="coerce")
    news["published_et"] = news["published_utc"].dt.tz_convert(timezone)
    news["local_date"] = news["published_et"].dt.date
    news["year"] = news["published_et"].dt.year.astype("Int64")
    news["headline_key"] = news["headline"].fillna("").map(normalize_headline)
    return news


def previous_trading_dates(
    trading_dates: pd.DatetimeIndex, event_date: pd.Timestamp, sessions: int
) -> pd.DatetimeIndex:
    previous = trading_dates[trading_dates.date < event_date.date()][-sessions:]
    if len(previous) != sessions:
        raise ValueError(
            f"Only {len(previous)} completed sessions available before {event_date}"
        )
    return previous


def pre_event_window_start(
    trading_dates: pd.DatetimeIndex, event_time: pd.Timestamp, sessions: int
) -> pd.Timestamp:
    previous = previous_trading_dates(trading_dates, event_time, sessions)
    return pd.Timestamp(previous[0].date(), tz=event_time.tz)


def audit_coverage(
    news: pd.DataFrame,
    events: pd.DataFrame,
    trading_dates: pd.DatetimeIndex,
    patterns: dict[str, tuple[re.Pattern[str], re.Pattern[str] | None]],
) -> tuple[list[dict[str, Any]], dict[str, pd.DataFrame]]:
    topic_frames: dict[str, pd.DataFrame] = {}
    for family, family_patterns in patterns.items():
        topic_frames[family] = news.loc[topic_mask(news["headline"], family_patterns)].copy()

    rows: list[dict[str, Any]] = []
    for event in events.itertuples(index=False):
        candidates = topic_frames[event.family]
        for window in WINDOWS:
            window_start = pre_event_window_start(
                trading_dates, event.release_timestamp_et, window
            )
            selected = candidates.loc[
                (candidates["published_et"] >= window_start)
                & (candidates["published_et"] < event.release_timestamp_et)
            ]
            unique = selected.drop_duplicates("headline_key")
            rows.append(
                {
                    "event_id": event.event_id,
                    "family": event.family,
                    "release_timestamp_et": event.release_timestamp_et.isoformat(),
                    "window_sessions": window,
                    "window_definition": (
                        f"continuous interval from midnight on the earliest of {window} "
                        "completed sessions through the pre-release boundary"
                    ),
                    "matched_headlines_raw": int(len(selected)),
                    "matched_headlines_unique": int(len(unique)),
                    "source_count": int(unique["source"].nunique()),
                    "sources": sorted(unique["source"].dropna().astype(str).unique().tolist()),
                    "source_url": event.source_url,
                }
            )
    return rows, topic_frames


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    frame = pd.DataFrame(rows)
    families = sorted(frame["family"].unique())
    summary: dict[str, Any] = {"by_family": {}, "primary_gate": {}}
    for family in families:
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


def deterministic_audit_sample(
    topic_frames: dict[str, pd.DataFrame], per_family: int = 24
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for family, frame in topic_frames.items():
        candidates = frame.drop_duplicates("headline_key").copy()
        candidates["sample_hash"] = candidates.apply(
            lambda row: hashlib.sha256(
                f"{family}|{row['source']}|{row['year']}|{row['headline_key']}".encode()
            ).hexdigest(),
            axis=1,
        )
        candidates = candidates.sort_values("sample_hash")

        selected_indices: list[int] = []
        for _, group in candidates.groupby(["source", "year"], dropna=False):
            selected_indices.append(int(group.index[0]))
        selected = candidates.loc[selected_indices].sort_values("sample_hash").head(per_family)
        if len(selected) < per_family:
            remaining = candidates.loc[~candidates.index.isin(selected.index)]
            selected = pd.concat([selected, remaining.head(per_family - len(selected))])

        for row in selected.itertuples(index=False):
            output.append(
                {
                    "family": family,
                    "headline": row.headline,
                    "source": row.source,
                    "published_et": row.published_et.isoformat(),
                    "sentiment_class": row.sentiment_class,
                    "manual_relevance": None,
                    "review_notes": "",
                }
            )
    return output


def markdown_report(
    summary: dict[str, Any], news: pd.DataFrame, events: pd.DataFrame
) -> str:
    lines = [
        "# Phase 1 Coverage Audit",
        "",
        "Generated by `phase1_coverage.py`. Counts use exact-normalized unique",
        "headlines published strictly before each official release timestamp.",
        "Each window is continuous from midnight on the earliest included completed",
        "session through the release, including weekends and same-day pre-release news.",
        "",
        "## Inputs",
        "",
        f"- News rows: {len(news):,}",
        f"- Events: {len(events):,}",
        f"- Invalid news timestamps: {int(news['published_et'].isna().sum()):,}",
        f"- Malformed sentiment labels: {int((~news['sentiment_class'].isin(list('ABCDE'))).sum()):,}",
        "",
        "## Primary Coverage Gate",
        "",
        "| Family | Events with >=8 headlines | Total events | Standalone viable (>=25) |",
        "| --- | ---: | ---: | --- |",
    ]
    for family in ("fomc", "cpi", "employment"):
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
            "## Window And Threshold Sensitivity",
            "",
            "| Family | Sessions | Mean | Median | Max | >=5 | >=8 | >=10 | >=15 |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for family in ("fomc", "cpi", "employment"):
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
            "## Interpretation",
            "",
            "The coverage gate assesses feasibility only. It does not use market",
            "outcomes and cannot establish predictive value. The topic audit sample",
            "must be manually reviewed before these rules are frozen for modeling.",
            "",
            "## Go/No-Go Recommendation",
            "",
            "Do not proceed to outcome regressions with the current two-source corpus.",
            "No event family reaches the pre-specified standalone requirement of 25",
            "events with at least eight relevant headlines in the primary window.",
            "The next step is to expand U.S. macro-news coverage, then rerun this same",
            "outcome-blind gate. Broader keywords or a five-session window may be",
            "evaluated as candidate measurement choices, but only after manual",
            "jurisdiction and event-relevance validation; they should not be adopted",
            "merely because they increase the passing count.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--news", type=Path, default=ROOT / "result.csv")
    parser.add_argument("--market", type=Path, default=ROOT / "data/market_panel.csv")
    parser.add_argument("--calendar", type=Path, default=DEFAULT_CALENDAR)
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    calendar_config = load_json(args.calendar)
    rule_config = load_json(args.rules)
    events = expand_calendar(calendar_config)
    patterns = compile_topic_patterns(rule_config)
    news = load_news(args.news, calendar_config["timezone"])
    market = pd.read_csv(args.market, usecols=["Date"])
    trading_dates = pd.DatetimeIndex(pd.to_datetime(market["Date"].dropna().unique())).sort_values()

    rows, topic_frames = audit_coverage(news, events, trading_dates, patterns)
    summary = summarize(rows)
    audit_sample = deterministic_audit_sample(topic_frames)

    args.output.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "calendar_retrieved_on": calendar_config["retrieved_on"],
        "topic_rules_defined_on": rule_config["defined_on"],
        "topic_rules_status": rule_config["status"],
        "summary": summary,
        "events": rows,
    }
    (args.output / "coverage_audit.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    (args.output / "topic_audit_sample.json").write_text(
        json.dumps(audit_sample, indent=2) + "\n", encoding="utf-8"
    )
    (args.output / "PHASE1_REPORT.md").write_text(
        markdown_report(summary, news, events), encoding="utf-8"
    )

    for family, gate in summary["primary_gate"].items():
        print(f"{family}: {gate['events_passing']}/{gate['events_total']} pass primary coverage")


if __name__ == "__main__":
    main()
