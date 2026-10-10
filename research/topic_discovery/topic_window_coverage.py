#!/usr/bin/env python3
"""Compare outcome-blind topic coverage across candidate trading-session windows."""

from __future__ import annotations

import argparse
import json
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from research.topic_discovery.assign_topic_families import (
    DEFAULT_TAXONOMY,
    load_taxonomy_v2,
)
from research.topic_discovery.build_corpus import sha256_file


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
DEFAULT_INPUT = ROOT / "data/topic_family_v2_assignments.parquet"
DEFAULT_MARKET_CALENDAR = ROOT / "data/market_panel.csv"
DEFAULT_OUTPUT = HERE / "artifacts/topic_window_coverage_v2.csv"
DEFAULT_MANIFEST = HERE / "artifacts/topic_window_coverage_v2_manifest.json"


def map_to_next_session(
    published: pd.Series, market_dates: pd.DatetimeIndex
) -> tuple[np.ndarray, np.ndarray]:
    session_values = market_dates.values.astype("datetime64[D]")
    publication_values = (
        pd.to_datetime(published, utc=True).dt.tz_localize(None).values.astype("datetime64[D]")
    )
    positions = np.searchsorted(session_values, publication_values, side="left")
    valid = positions < len(session_values)
    mapped = np.full(len(positions), np.datetime64("NaT"), dtype="datetime64[D]")
    mapped[valid] = session_values[positions[valid]]
    return mapped, valid


def rolling_topic_cells(
    frame: pd.DataFrame,
    market_dates: pd.DatetimeIndex,
    lookback: int,
) -> pd.DataFrame:
    sessions = [pd.Timestamp(value).date().isoformat() for value in market_dates]
    session_position = {value: index for index, value in enumerate(sessions)}
    rows: list[dict[str, Any]] = []
    for topic, topic_frame in frame.groupby("topic_family_primary", sort=True):
        daily: dict[int, list[str]] = {}
        for session, group in topic_frame.groupby("availability_session", sort=False):
            position = session_position.get(str(session))
            if position is not None:
                daily[position] = group["source"].astype(str).tolist()

        active_days: deque[list[str]] = deque()
        source_counts: Counter[str] = Counter()
        headline_count = 0
        for position, session in enumerate(sessions):
            todays_sources = daily.get(position, [])
            active_days.append(todays_sources)
            source_counts.update(todays_sources)
            headline_count += len(todays_sources)
            if len(active_days) > lookback:
                expired = active_days.popleft()
                headline_count -= len(expired)
                source_counts.subtract(expired)
                source_counts += Counter()
            rows.append(
                {
                    "topic_family": topic,
                    "window_sessions": lookback,
                    "window_end": session,
                    "headline_count": headline_count,
                    "source_count": len(source_counts),
                }
            )
    return pd.DataFrame(rows)


def summarize_cells(
    cells: pd.DataFrame, minimum_rules: list[dict[str, int]]
) -> pd.DataFrame:
    summaries: list[dict[str, Any]] = []
    grouped = list(cells.groupby(["window_sessions", "topic_family"], sort=True))
    grouped.extend(
        ((lookback, "__all_topics__"), group)
        for lookback, group in cells.groupby("window_sessions", sort=True)
    )
    for (lookback, topic), group in grouped:
        nonempty = group.loc[group["headline_count"] > 0]
        row: dict[str, Any] = {
            "window_sessions": int(lookback),
            "topic_family": topic,
            "cells": len(group),
            "nonempty_cells": len(nonempty),
            "nonempty_share": round(len(nonempty) / len(group), 6) if len(group) else 0,
            "median_headlines_nonempty": (
                round(float(nonempty["headline_count"].median()), 3)
                if len(nonempty)
                else 0
            ),
            "median_sources_nonempty": (
                round(float(nonempty["source_count"].median()), 3)
                if len(nonempty)
                else 0
            ),
        }
        for rule in minimum_rules:
            headlines = int(rule["headlines"])
            sources = int(rule["sources"])
            eligible = (
                (group["headline_count"] >= headlines)
                & (group["source_count"] >= sources)
            )
            prefix = f"h{headlines}_s{sources}"
            row[f"{prefix}_cells"] = int(eligible.sum())
            row[f"{prefix}_share"] = round(float(eligible.mean()), 6)
        summaries.append(row)
    return pd.DataFrame(summaries).sort_values(
        ["window_sessions", "topic_family"]
    )


def write_csv_atomic(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--market-calendar", type=Path, default=DEFAULT_MARKET_CALENDAR)
    parser.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    taxonomy = load_taxonomy_v2(args.taxonomy)
    columns = ["record_id", "published_utc", "source", "topic_family_primary"]
    frame = pd.read_parquet(args.input, columns=columns)
    frame = frame.loc[frame["topic_family_primary"].ne("other_unclear")].copy()
    market_dates = pd.DatetimeIndex(
        pd.to_datetime(
            pd.read_csv(args.market_calendar, usecols=["Date"])["Date"], errors="raise"
        ).sort_values().unique()
    )
    mapped, valid = map_to_next_session(frame["published_utc"], market_dates)
    frame = frame.loc[valid].copy()
    frame["availability_session"] = mapped[valid].astype(str)

    cell_frames = [
        rolling_topic_cells(frame, market_dates, int(lookback))
        for lookback in taxonomy["window_candidates_trading_sessions"]
    ]
    cells = pd.concat(cell_frames, ignore_index=True)
    summary = summarize_cells(cells, taxonomy["minimum_coverage_candidates"])
    write_csv_atomic(summary, args.output)

    manifest = {
        "schema_version": 2,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            str(args.input.relative_to(ROOT)): sha256_file(args.input),
            str(args.market_calendar.relative_to(ROOT)): sha256_file(args.market_calendar),
            str(args.taxonomy.relative_to(ROOT)): sha256_file(args.taxonomy),
        },
        "output": str(args.output.relative_to(ROOT)),
        "output_sha256": sha256_file(args.output),
        "market_sessions": len(market_dates),
        "eligible_headlines": len(frame),
        "topic_families": int(frame["topic_family_primary"].nunique()),
        "window_candidates": taxonomy["window_candidates_trading_sessions"],
        "minimum_coverage_candidates": taxonomy["minimum_coverage_candidates"],
        "availability_rule": "publication calendar date maps to first market session on or after that date",
        "selection_rule": "coverage and unique-source diagnostics only; no prices, returns, volatility, or volume inspected",
        "market_outcomes_used": False,
        "status": "candidate window coverage; primary window not frozen",
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {len(summary)} topic-window coverage rows across "
        f"{len(taxonomy['window_candidates_trading_sessions'])} candidate windows"
    )


if __name__ == "__main__":
    main()
