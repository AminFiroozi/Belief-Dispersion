#!/usr/bin/env python3
"""Build a timing-safe FOMC event panel from frozen Phase 1 inputs."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from research.event_study.google_news_expansion import selected_records
from research.event_study.phase1_coverage import (
    expand_calendar,
    load_json,
    previous_trading_dates,
)


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
DEFAULT_CALENDAR = HERE / "event_calendar.json"
DEFAULT_MINUTE_BARS = ROOT / "data/spy_1min_data"
DEFAULT_DAILY_MARKET = ROOT / "data/market_panel.csv"
DEFAULT_HEADLINES = ROOT / "data/google_news_event_headlines.jsonl"
DEFAULT_LOCAL_PANEL = ROOT / "data/fomc_phase2_event_panel.csv"
DEFAULT_REVIEW = ROOT / "data/fomc_phase2_headline_review.csv"
DEFAULT_OUTPUT = HERE / "artifacts"

TIMEZONE = "America/New_York"
FAMILY = "fomc"
NEWS_WINDOW_SESSIONS = 3
NEWS_THRESHOLD = 8
REACTION_MINUTES = (5, 15, 60)
PRIMARY_REACTION_MINUTES = 60
VOLUME_BASELINE_SESSIONS = 20
VOLUME_BASELINE_MIN_SESSIONS = 15


def load_minute_bars(path: Path) -> pd.DataFrame:
    bars = pd.read_csv(path, parse_dates=["date"])
    required = {"date", "open", "high", "low", "close", "volume"}
    missing = required.difference(bars.columns)
    if missing:
        raise ValueError(f"Minute bars lack required columns: {sorted(missing)}")
    if bars["date"].isna().any():
        raise ValueError("Minute bars contain invalid timestamps")
    if bars["date"].duplicated().any():
        raise ValueError("Minute bars contain duplicate timestamps")
    if bars["date"].dt.tz is not None:
        bars["date"] = bars["date"].dt.tz_convert(TIMEZONE).dt.tz_localize(None)
    numeric = ["open", "high", "low", "close", "volume"]
    bars[numeric] = bars[numeric].apply(pd.to_numeric, errors="coerce")
    if bars[numeric].isna().any().any():
        raise ValueError("Minute bars contain invalid OHLCV values")
    return bars.sort_values("date").set_index("date", verify_integrity=True)


def load_daily_market(path: Path) -> pd.DataFrame:
    market = pd.read_csv(path)
    required = {"Date", "SPX", "Volume", "VIX"}
    missing = required.difference(market.columns)
    if missing:
        raise ValueError(f"Daily market data lack required columns: {sorted(missing)}")
    market["Date"] = pd.to_datetime(market["Date"], errors="coerce")
    if market["Date"].isna().any() or market["Date"].duplicated().any():
        raise ValueError("Daily market dates must be valid and unique")
    market = market.sort_values("Date").set_index("Date", verify_integrity=True)
    market["spx_log_return"] = np.log(market["SPX"] / market["SPX"].shift(1))
    return market


def load_headline_records(path: Path) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON on {path}:{line_number}") from error
            grouped[record["event_id"]].append(record)
    return dict(grouped)


def expected_minutes(start: pd.Timestamp, minutes: int) -> pd.DatetimeIndex:
    return pd.date_range(start=start, periods=minutes, freq="min")


def minute_window_metrics(
    bars: pd.DataFrame, start: pd.Timestamp, minutes: int
) -> dict[str, Any]:
    """Measure [start, start + minutes), using the prior close as boundary price."""
    expected = expected_minutes(start, minutes)
    present = bars.index.intersection(expected)
    prior_timestamp = start - pd.Timedelta(minutes=1)
    complete = len(present) == minutes and prior_timestamp in bars.index
    result: dict[str, Any] = {
        "bars_expected": minutes,
        "bars_present": int(len(present)),
        "prior_boundary_present": bool(prior_timestamp in bars.index),
        "complete": bool(complete),
    }
    if not complete:
        return result

    window = bars.loc[expected]
    closes = window["close"].to_numpy(dtype=float)
    prior_close = float(bars.at[prior_timestamp, "close"])
    lagged_closes = np.concatenate(([prior_close], closes[:-1]))
    log_returns = np.log(closes / lagged_closes)
    result.update(
        {
            "start": start.isoformat(),
            "end_exclusive": (start + pd.Timedelta(minutes=minutes)).isoformat(),
            "boundary_close": prior_close,
            "end_close": float(closes[-1]),
            "return_pct": float(log_returns.sum() * 100),
            "abs_return_pct": float(abs(log_returns.sum()) * 100),
            "rv_pct": float(np.sqrt(np.square(log_returns).sum()) * 100),
            "max_abs_minute_return_pct": float(np.abs(log_returns).max() * 100),
            "volume": float(window["volume"].sum()),
            "zero_volume_bars": int((window["volume"] == 0).sum()),
        }
    )
    return result


def flatten_window(prefix: str, metrics: dict[str, Any]) -> dict[str, Any]:
    return {f"{prefix}_{key}": value for key, value in metrics.items()}


def volume_baseline(
    bars: pd.DataFrame,
    trading_dates: pd.DatetimeIndex,
    event_time: pd.Timestamp,
    minutes: int = PRIMARY_REACTION_MINUTES,
    sessions: int = VOLUME_BASELINE_SESSIONS,
) -> dict[str, Any]:
    previous = trading_dates[trading_dates.date < event_time.date()][-sessions:]
    totals: list[float] = []
    start_clock = event_time.tz_localize(None).time()
    for trading_date in previous:
        start = pd.Timestamp.combine(trading_date.date(), start_clock)
        metrics = minute_window_metrics(bars, start, minutes)
        if metrics["complete"] and metrics["zero_volume_bars"] == 0:
            totals.append(float(metrics["volume"]))
    return {
        "baseline_sessions_requested": sessions,
        "baseline_sessions_complete": len(totals),
        "baseline_median_volume": float(np.median(totals)) if totals else None,
    }


def daily_controls(market: pd.DataFrame, event_time: pd.Timestamp) -> dict[str, Any]:
    prior = market.loc[market.index.date < event_time.date()]
    if prior.empty:
        return {"daily_controls_complete": False}
    latest_date = prior.index[-1]
    latest = prior.iloc[-1]
    returns_5d = prior["spx_log_return"].dropna().tail(5)
    complete = pd.notna(latest["spx_log_return"]) and len(returns_5d) == 5
    return {
        "daily_controls_complete": bool(complete),
        "control_date": latest_date.date().isoformat(),
        "prior_spx_close": float(latest["SPX"]),
        "prior_spx_return_pct": (
            float(latest["spx_log_return"] * 100)
            if pd.notna(latest["spx_log_return"])
            else None
        ),
        "prior_5d_spx_rv_pct": (
            float(np.sqrt(np.square(returns_5d).sum()) * 100)
            if len(returns_5d) == 5
            else None
        ),
        "prior_spx_volume": float(latest["Volume"]),
        "prior_vix_close": float(latest["VIX"]),
    }


def future_daily_outcomes(market: pd.DataFrame, event_time: pd.Timestamp) -> dict[str, Any]:
    event_date = pd.Timestamp(event_time.date())
    if event_date not in market.index:
        return {"daily_outcomes_complete": False}
    location = market.index.get_loc(event_date)
    previous = market.iloc[location - 1] if location > 0 else None
    current = market.iloc[location]
    future_returns = market["spx_log_return"].iloc[location + 1 : location + 6].dropna()
    complete = previous is not None and len(future_returns) == 5
    return {
        "daily_outcomes_complete": bool(complete),
        "event_day_spx_return_pct": (
            float(np.log(current["SPX"] / previous["SPX"]) * 100)
            if previous is not None
            else None
        ),
        "event_day_vix_change": (
            float(current["VIX"] - previous["VIX"]) if previous is not None else None
        ),
        "next_5d_spx_rv_pct": (
            float(np.sqrt(np.square(future_returns).sum()) * 100)
            if len(future_returns) == 5
            else None
        ),
    }


def select_fomc_news(
    records_by_event: dict[str, list[dict[str, Any]]],
    events: Iterable[dict[str, Any]],
    trading_dates: pd.DatetimeIndex,
) -> dict[str, list[dict[str, Any]]]:
    selected: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        event_records = records_by_event.get(event["event_id"], [])
        selected[event["event_id"]] = selected_records(
            event_records, event, trading_dates, NEWS_WINDOW_SESSIONS
        )
    return selected


def build_event_row(
    event: dict[str, Any],
    selected_news: list[dict[str, Any]],
    bars: pd.DataFrame,
    market: pd.DataFrame,
    trading_dates: pd.DatetimeIndex,
) -> dict[str, Any]:
    release_aware = pd.Timestamp(event["release_timestamp_et"])
    release = release_aware.tz_localize(None)
    previous_sessions = previous_trading_dates(
        trading_dates, release_aware, NEWS_WINDOW_SESSIONS
    )
    news_dates = [date.fromisoformat(item["published_date"]) for item in selected_news]
    if any(published >= release_aware.date() for published in news_dates):
        raise AssertionError(f"Post-boundary news assigned to {event['event_id']}")

    row: dict[str, Any] = {
        "event_id": event["event_id"],
        "family": FAMILY,
        "release_timestamp_et": release_aware.isoformat(),
        "release_date": release_aware.date().isoformat(),
        "news_window_sessions": NEWS_WINDOW_SESSIONS,
        "news_window_start": previous_sessions[0].date().isoformat(),
        "news_release_day_excluded": True,
        "headline_count": len(selected_news),
        "source_count": len({item["source"] for item in selected_news}),
        "coverage_pass": len(selected_news) >= NEWS_THRESHOLD,
        "sentiment_status": "pending_relevance_validation_and_phase3_labeling",
    }

    pre = minute_window_metrics(bars, release - pd.Timedelta(minutes=60), 60)
    row.update(flatten_window("pre_60m", pre))
    for minutes in REACTION_MINUTES:
        metrics = minute_window_metrics(bars, release, minutes)
        row.update(flatten_window(f"post_{minutes}m", metrics))

    delayed = minute_window_metrics(bars, release + pd.Timedelta(minutes=1), 60)
    row.update(flatten_window("post_delayed_60m", delayed))

    baseline = volume_baseline(bars, trading_dates, release_aware)
    row.update({f"post_60m_volume_{key}": value for key, value in baseline.items()})
    baseline_volume = baseline["baseline_median_volume"]
    current_volume = row.get("post_60m_volume")
    row["post_60m_volume_data_complete"] = bool(
        row["post_60m_complete"]
        and row.get("post_60m_zero_volume_bars") == 0
        and baseline["baseline_sessions_complete"] >= VOLUME_BASELINE_MIN_SESSIONS
    )
    row["post_60m_volume_ratio"] = (
        float(current_volume / baseline_volume)
        if row["post_60m_volume_data_complete"]
        and current_volume is not None
        and baseline_volume not in (None, 0)
        else None
    )

    row.update(daily_controls(market, release_aware))
    row.update(future_daily_outcomes(market, release_aware))
    row["primary_market_complete"] = bool(
        row["pre_60m_complete"]
        and row["post_60m_complete"]
        and row["daily_controls_complete"]
    )
    row["primary_sample_eligible_before_sentiment_validation"] = bool(
        row["coverage_pass"] and row["primary_market_complete"]
    )
    return row


def build_panel(
    events: list[dict[str, Any]],
    selected_news: dict[str, list[dict[str, Any]]],
    bars: pd.DataFrame,
    market: pd.DataFrame,
) -> pd.DataFrame:
    trading_dates = pd.DatetimeIndex(market.index).sort_values()
    rows = [
        build_event_row(event, selected_news[event["event_id"]], bars, market, trading_dates)
        for event in events
    ]
    panel = pd.DataFrame(rows).sort_values("release_timestamp_et").reset_index(drop=True)
    if panel["event_id"].duplicated().any() or len(panel) != len(events):
        raise AssertionError("Event panel must contain exactly one row per event")
    return panel


def json_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    cleaned = frame.astype(object).where(pd.notna(frame), None)
    return cleaned.to_dict(orient="records")


def write_review_file(path: Path, selected: dict[str, list[dict[str, Any]]]) -> None:
    rows: list[dict[str, Any]] = []
    for event_id, records in selected.items():
        for record in records:
            rows.append(
                {
                    "event_id": event_id,
                    "published_date": record["published_date"],
                    "source": record["source"],
                    "headline": record["headline"],
                    "headline_key": record["headline_key"],
                    "manual_relevance": "",
                    "review_notes": "",
                }
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)


def summary_payload(panel: pd.DataFrame) -> dict[str, Any]:
    complete = panel["primary_market_complete"]
    eligible = panel["primary_sample_eligible_before_sentiment_validation"]
    incomplete_rows = panel.loc[~complete]
    return {
        "events_total": int(len(panel)),
        "events_passing_news_coverage": int(panel["coverage_pass"].sum()),
        "events_with_complete_primary_market_data": int(complete.sum()),
        "events_eligible_before_sentiment_validation": int(eligible.sum()),
        "eligible_events_with_complete_volume_outcome": int(
            panel.loc[eligible, "post_60m_volume_data_complete"].sum()
        ),
        "incomplete_market_events": incomplete_rows["event_id"].tolist(),
        "missing_pre_60m_bars": {
            row.event_id: int(row.pre_60m_bars_expected - row.pre_60m_bars_present)
            for row in incomplete_rows.itertuples()
            if not row.pre_60m_complete
        },
        "missing_post_60m_bars": {
            row.event_id: int(row.post_60m_bars_expected - row.post_60m_bars_present)
            for row in incomplete_rows.itertuples()
            if not row.post_60m_complete
        },
    }


def spot_checks(panel: pd.DataFrame) -> list[dict[str, Any]]:
    complete = panel.loc[panel["post_60m_complete"]].copy()
    candidates = pd.concat(
        [
            complete.head(1),
            complete.iloc[[len(complete) // 2]],
            complete.tail(1),
            complete.nlargest(2, "post_60m_rv_pct"),
        ]
    ).drop_duplicates("event_id")
    columns = [
        "event_id",
        "post_60m_start",
        "post_60m_end_exclusive",
        "post_60m_boundary_close",
        "post_60m_end_close",
        "post_60m_return_pct",
        "post_60m_rv_pct",
        "post_60m_bars_present",
    ]
    return json_records(candidates[columns])


def markdown_report(panel: pd.DataFrame, summary: dict[str, Any]) -> str:
    eligible = panel.loc[panel["primary_sample_eligible_before_sentiment_validation"]]
    incomplete = panel.loc[~panel["primary_market_complete"]]
    lines = [
        "# Phase 2 Timing-Safe FOMC Panel",
        "",
        "Generated by `phase2_event_panel.py`. This stage freezes event/news",
        "assignment and market timing before sentiment features or outcome models are",
        "estimated.",
        "",
        "## Timing Definition",
        "",
        "Minute timestamps are interpreted as the start of an America/New_York OHLCV",
        "bar. The primary reaction interval is `[14:00, 15:00)`: returns on bars",
        "labeled 14:00 through 14:59 are measured from the immediately preceding close.",
        "Thus the 13:59 close is a boundary price, not a post-release observation.",
        "Realized volatility is `100 * sqrt(sum(one-minute log return^2))`.",
        "No missing announcement-window bars are interpolated.",
        "",
        "## Sample Audit",
        "",
        f"- Official regular FOMC events: {summary['events_total']}",
        "- Events passing the frozen >=8 headline gate: "
        f"{summary['events_passing_news_coverage']}",
        "- Events with complete primary market inputs: "
        f"{summary['events_with_complete_primary_market_data']}",
        "- Events eligible before sentiment validation: "
        f"{summary['events_eligible_before_sentiment_validation']}",
        "- Eligible events with a complete normalized-volume outcome: "
        f"{summary['eligible_events_with_complete_volume_outcome']}",
        "- Release-day Google RSS headlines remain excluded because their clock "
        "times are unreliable.",
        "- Sentiment fields are intentionally pending; expanded headlines have "
        "not yet been validated or labeled.",
        "",
        "## Market Missingness",
        "",
        "| Event | Pre bars | Post bars | Boundary present | Eligible |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    if incomplete.empty:
        lines.append("| none | 60 | 60 | yes | n/a |")
    else:
        for row in incomplete.itertuples():
            lines.append(
                f"| {row.event_id} | {row.pre_60m_bars_present}/60 | "
                f"{row.post_60m_bars_present}/60 | "
                f"{'yes' if row.post_60m_prior_boundary_present else 'no'} | no |"
            )
    lines.extend(
        [
            "",
            "## Eligible Outcome Distribution",
            "",
            "| Measure | Mean | Median | Min | Max |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for column, label in [
        ("post_60m_rv_pct", "Post 60m realized volatility (%)"),
        ("post_60m_abs_return_pct", "Post 60m absolute return (%)"),
        ("post_60m_volume_ratio", "Post 60m volume / prior-session median"),
        ("pre_60m_rv_pct", "Pre 60m realized volatility (%)"),
    ]:
        values = eligible[column].dropna()
        lines.append(
            f"| {label} | {values.mean():.4f} | {values.median():.4f} | "
            f"{values.min():.4f} | {values.max():.4f} |"
        )
    lines.extend(
        [
            "",
            "## Phase Gate",
            "",
            "The timing-safe outcome scaffold is complete for feasibility work. It is",
            "not yet a model-ready paper sample: the Google RSS corpus requires manual",
            "relevance validation, acceptable archival/use terms, and a documented",
            "sentiment-labeling pass. Phase 3 must complete those tasks and freeze the",
            "distribution feature before any association with these outcomes is tested.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calendar", type=Path, default=DEFAULT_CALENDAR)
    parser.add_argument("--minute-bars", type=Path, default=DEFAULT_MINUTE_BARS)
    parser.add_argument("--daily-market", type=Path, default=DEFAULT_DAILY_MARKET)
    parser.add_argument("--headlines", type=Path, default=DEFAULT_HEADLINES)
    parser.add_argument("--local-panel", type=Path, default=DEFAULT_LOCAL_PANEL)
    parser.add_argument("--review-file", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    calendar = load_json(args.calendar)
    event_frame = expand_calendar(calendar)
    event_frame = event_frame.loc[event_frame["family"] == FAMILY]
    events: list[dict[str, Any]] = []
    for row in event_frame.to_dict(orient="records"):
        row["release_timestamp_et"] = row["release_timestamp_et"].isoformat()
        events.append(row)

    bars = load_minute_bars(args.minute_bars)
    market = load_daily_market(args.daily_market)
    trading_dates = pd.DatetimeIndex(market.index).sort_values()
    records = load_headline_records(args.headlines)
    selected = select_fomc_news(records, events, trading_dates)
    panel = build_panel(events, selected, bars, market)

    args.local_panel.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(args.local_panel, index=False)
    write_review_file(args.review_file, selected)

    summary = summary_payload(panel)
    payload = {
        "schema_version": 1,
        "generated_on": date.today().isoformat(),
        "family": FAMILY,
        "timezone": TIMEZONE,
        "configuration": {
            "news_window_sessions": NEWS_WINDOW_SESSIONS,
            "news_threshold": NEWS_THRESHOLD,
            "release_day_news_excluded": True,
            "reaction_window": "[release, release + 60 minutes)",
            "minute_timestamp_semantics": "bar_start",
            "missing_bar_policy": "reject_window_without_interpolation",
            "volume_baseline_sessions": VOLUME_BASELINE_SESSIONS,
            "volume_baseline_min_clean_sessions": VOLUME_BASELINE_MIN_SESSIONS,
            "zero_volume_policy": "volume_outcome_missing",
            "sentiment_status": "pending_phase3",
        },
        "summary": summary,
        "spot_checks": spot_checks(panel),
        "events": json_records(panel),
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "fomc_event_panel.json").write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    (args.output / "PHASE2_REPORT.md").write_text(
        markdown_report(panel, summary), encoding="utf-8"
    )

    print(
        f"Built {len(panel)} FOMC events; "
        f"{summary['events_eligible_before_sentiment_validation']} are timing/coverage eligible"
    )


if __name__ == "__main__":
    main()
