#!/usr/bin/env python3
"""Create an outcome-blind human-validation sample from Phase 2 FOMC headlines."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
DEFAULT_INPUT = ROOT / "data/fomc_phase2_headline_review.csv"
DEFAULT_RATER_1 = ROOT / "data/fomc_phase3_validation_rater_1.csv"
DEFAULT_RATER_2 = ROOT / "data/fomc_phase3_validation_rater_2.csv"
DEFAULT_KEY = ROOT / "data/fomc_phase3_validation_key.csv"
DEFAULT_MANIFEST = HERE / "artifacts/phase3_validation_sample_manifest.json"
SAMPLE_SIZE = 150
SAMPLING_SALT = "fomc-phase3-human-validation-v1-20260818"

RATER_COLUMNS = [
    "sample_id",
    "headline",
    "topic_relevance",
    "equity_sentiment",
    "label_confidence",
    "ambiguity_flag",
    "reviewer_notes",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(*values: str) -> str:
    joined = "|".join((SAMPLING_SALT, *values))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def load_candidates(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=str).fillna("")
    required = {"event_id", "published_date", "source", "headline", "headline_key"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Candidate file lacks required columns: {sorted(missing)}")
    if frame.empty:
        raise ValueError("Candidate file is empty")
    if frame[["event_id", "headline", "headline_key"]].eq("").any().any():
        raise ValueError("Candidates contain blank IDs, headlines, or headline keys")
    if frame.duplicated(["event_id", "headline_key"]).any():
        raise ValueError("Candidates contain duplicate event/headline keys")
    frame["event_year"] = frame["event_id"].str.extract(
        r"^fomc_(\d{4})", expand=False
    )
    if frame["event_year"].isna().any():
        raise ValueError("Could not derive a year from every FOMC event ID")
    source_counts = frame["source"].value_counts()
    frame["source_frequency"] = frame["source"].map(source_counts).astype(int)
    frame["source_band"] = pd.cut(
        frame["source_frequency"],
        bins=[0, 1, 4, np.inf],
        labels=["singleton", "2-4", "5+"],
    ).astype(str)
    return frame


def allocate_event_slots(event_counts: pd.Series, sample_size: int) -> pd.Series:
    """Give each event one slot, then allocate the remainder proportionally."""
    counts = event_counts.sort_index().astype(int)
    if (counts < 1).any():
        raise ValueError("Every represented event must contain at least one headline")
    if sample_size < len(counts):
        raise ValueError("Sample is too small to represent every event")
    if sample_size > int(counts.sum()):
        raise ValueError("Sample cannot exceed the candidate population")

    allocation = pd.Series(1, index=counts.index, dtype=int)
    remaining = sample_size - len(counts)
    capacity = counts - 1
    if remaining == 0:
        return allocation
    if int(capacity.sum()) == 0:
        raise ValueError("No capacity remains for proportional allocation")

    quotas = remaining * capacity / capacity.sum()
    floors = np.floor(quotas).astype(int)
    allocation += floors
    leftover = sample_size - int(allocation.sum())
    ranking = pd.DataFrame(
        {
            "fraction": quotas - floors,
            "tie_break": [stable_hash("allocation", value) for value in counts.index],
            "has_capacity": allocation < counts,
        },
        index=counts.index,
    )
    ranking = ranking.loc[ranking["has_capacity"]].sort_values(
        ["fraction", "tie_break"], ascending=[False, True]
    )
    for event_id in ranking.head(leftover).index:
        allocation.loc[event_id] += 1

    if int(allocation.sum()) != sample_size or (allocation > counts).any():
        raise AssertionError("Event allocation failed its size or capacity constraint")
    return allocation


def build_sample(candidates: pd.DataFrame, sample_size: int = SAMPLE_SIZE) -> pd.DataFrame:
    counts = candidates.groupby("event_id").size()
    allocation = allocate_event_slots(counts, sample_size)
    selected: list[pd.DataFrame] = []
    for event_id, group in candidates.groupby("event_id", sort=True):
        ranked = group.copy()
        ranked["selection_hash"] = ranked["headline_key"].map(
            lambda key: stable_hash("select", event_id, key)
        )
        selected.append(
            ranked.sort_values("selection_hash").head(int(allocation.loc[event_id]))
        )
    sample = pd.concat(selected, ignore_index=True)
    sample["display_hash"] = sample.apply(
        lambda row: stable_hash("display", row["event_id"], row["headline_key"]),
        axis=1,
    )
    sample = sample.sort_values("display_hash").reset_index(drop=True)
    sample["sample_id"] = [f"FOMCVAL-{number:03d}" for number in range(1, len(sample) + 1)]
    if len(sample) != sample_size or sample["event_id"].nunique() != counts.size:
        raise AssertionError("Sample size or event representation is incorrect")
    return sample


def rater_frame(sample: pd.DataFrame, rater: int) -> pd.DataFrame:
    frame = sample[["sample_id", "headline", "event_id", "headline_key"]].copy()
    frame["rater_order"] = frame.apply(
        lambda row: stable_hash(
            f"rater-{rater}", row["event_id"], row["headline_key"]
        ),
        axis=1,
    )
    frame = frame.sort_values("rater_order")[["sample_id", "headline"]]
    for column in RATER_COLUMNS[2:]:
        frame[column] = ""
    return frame[RATER_COLUMNS]


def hidden_key(sample: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "sample_id",
        "event_id",
        "event_year",
        "published_date",
        "source",
        "source_band",
        "headline_key",
        "headline",
    ]
    return sample[columns].sort_values("sample_id")


def distribution(series: pd.Series) -> dict[str, int]:
    return {
        str(key): int(value)
        for key, value in series.value_counts(dropna=False).sort_index().items()
    }


def diagnostics(candidates: pd.DataFrame, sample: pd.DataFrame) -> dict[str, Any]:
    event_counts = candidates.groupby("event_id").size()
    sample_event_counts = sample.groupby("event_id").size()
    return {
        "population_headlines": int(len(candidates)),
        "sample_headlines": int(len(sample)),
        "population_events": int(candidates["event_id"].nunique()),
        "sample_events": int(sample["event_id"].nunique()),
        "all_events_represented": set(event_counts.index) == set(sample_event_counts.index),
        "sample_headlines_per_event_min": int(sample_event_counts.min()),
        "sample_headlines_per_event_median": float(sample_event_counts.median()),
        "sample_headlines_per_event_max": int(sample_event_counts.max()),
        "population_by_year": distribution(candidates["event_year"]),
        "sample_by_year": distribution(sample["event_year"]),
        "population_by_source_band": distribution(candidates["source_band"]),
        "sample_by_source_band": distribution(sample["source_band"]),
        "population_distinct_sources": int(candidates["source"].nunique()),
        "sample_distinct_sources": int(sample["source"].nunique()),
        "population_top_source_share": round(
            float(candidates["source"].value_counts(normalize=True).iloc[0]), 4
        ),
        "sample_top_source_share": round(
            float(sample["source"].value_counts(normalize=True).iloc[0]), 4
        ),
    }


def file_metadata(path: Path) -> dict[str, Any]:
    return {
        "path": str(path.relative_to(ROOT)),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--rater-1", type=Path, default=DEFAULT_RATER_1)
    parser.add_argument("--rater-2", type=Path, default=DEFAULT_RATER_2)
    parser.add_argument("--key", type=Path, default=DEFAULT_KEY)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--sample-size", type=int, default=SAMPLE_SIZE)
    args = parser.parse_args()

    candidates = load_candidates(args.input)
    sample = build_sample(candidates, args.sample_size)
    outputs = {
        "rater_1": (args.rater_1, rater_frame(sample, 1)),
        "rater_2": (args.rater_2, rater_frame(sample, 2)),
        "hidden_key": (args.key, hidden_key(sample)),
    }
    for path, frame in outputs.values():
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)

    manifest = {
        "schema_version": 1,
        "generated_on": date.today().isoformat(),
        "sampling_version": "phase3-human-validation-v1",
        "sampling_salt_sha256": hashlib.sha256(
            SAMPLING_SALT.encode("utf-8")
        ).hexdigest(),
        "outcome_blind": True,
        "selection": (
            "one deterministic headline per event, followed by largest-remainder "
            "proportional allocation over remaining event-level capacity"
        ),
        "blinding": (
            "rater files contain only random sample IDs, headlines, and blank label "
            "fields; event/date/source metadata are confined to the hidden key"
        ),
        "input": file_metadata(args.input),
        "outputs": {name: file_metadata(path) for name, (path, _) in outputs.items()},
        "diagnostics": diagnostics(candidates, sample),
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"Selected {len(sample)} headlines from {len(candidates)} candidates "
        f"across {sample['event_id'].nunique()} FOMC events"
    )


if __name__ == "__main__":
    main()

