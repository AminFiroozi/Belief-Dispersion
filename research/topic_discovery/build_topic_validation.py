#!/usr/bin/env python3
"""Build blinded v2 topic-family headline and pair validation files."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from research.topic_discovery.assign_topic_families import (
    DEFAULT_TAXONOMY,
    load_taxonomy_v2,
)
from research.topic_discovery.build_corpus import sha256_file, stable_id


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
DEFAULT_INPUT = ROOT / "data/topic_family_v2_assignments.parquet"
DEFAULT_HEADLINE_1 = ROOT / "data/topic_family_v2_validation_rater_1.csv"
DEFAULT_HEADLINE_2 = ROOT / "data/topic_family_v2_validation_rater_2.csv"
DEFAULT_HEADLINE_KEY = ROOT / "data/topic_family_v2_validation_key.csv"
DEFAULT_PAIR_1 = ROOT / "data/topic_family_v2_pair_rater_1.csv"
DEFAULT_PAIR_2 = ROOT / "data/topic_family_v2_pair_rater_2.csv"
DEFAULT_PAIR_KEY = ROOT / "data/topic_family_v2_pair_key.csv"
DEFAULT_MANIFEST = HERE / "artifacts/topic_family_v2_validation_manifest.json"


def stable_hash(seed: str, *values: str) -> str:
    return hashlib.sha256("|".join([seed, *map(str, values)]).encode("utf-8")).hexdigest()


def allocate_quotas(counts: pd.Series, total: int, minimum: int = 1) -> dict[str, int]:
    counts = counts[counts > 0].sort_index()
    if total > int(counts.sum()):
        raise ValueError("Requested sample exceeds available rows")
    quotas = {str(key): min(minimum, int(value)) for key, value in counts.items()}
    if sum(quotas.values()) > total:
        quotas = {str(key): 0 for key in counts.index}
    weights = np.sqrt(counts.astype(float))
    while sum(quotas.values()) < total:
        candidates = [
            str(key) for key, value in counts.items() if quotas[str(key)] < int(value)
        ]
        if not candidates:
            break
        target = max(
            candidates,
            key=lambda key: (
                float(weights.loc[key]) / (quotas[key] + 1),
                stable_hash("quota-v2", key),
            ),
        )
        quotas[target] += 1
    return quotas


def select_headline_sample(frame: pd.DataFrame, sample_size: int) -> pd.DataFrame:
    counts = frame["topic_family_primary"].value_counts()
    quotas = allocate_quotas(counts, sample_size, minimum=6)
    selected: list[pd.DataFrame] = []
    for topic, quota in quotas.items():
        group = frame.loc[frame["topic_family_primary"].eq(topic)].copy()
        group["selection_hash"] = group["record_id"].map(
            lambda value: stable_hash("headline-validation-v2", topic, value)
        )
        group = group.sort_values(
            ["topic_assignment_confidence", "year", "origin", "selection_hash"]
        )
        # Round-robin across confidence/year/origin blocks before filling by hash.
        blocks = [
            block.sort_values("selection_hash")
            for _, block in group.groupby(
                ["topic_assignment_confidence", "year", "origin"], sort=True
            )
        ]
        rows: list[pd.DataFrame] = []
        position = 0
        while len(rows) < quota:
            added = False
            for block in blocks:
                if position < len(block) and len(rows) < quota:
                    rows.append(block.iloc[[position]])
                    added = True
            if not added:
                break
            position += 1
        selected.append(pd.concat(rows, ignore_index=True))
    result = pd.concat(selected, ignore_index=True).drop(columns="selection_hash")
    if len(result) != sample_size or result["record_id"].duplicated().any():
        raise AssertionError("Headline validation sample is not exact and unique")
    result["topic_sample_id"] = result["record_id"].map(
        lambda value: f"TOPIC-{stable_id('topic-family-v2', value, length=16)}"
    )
    return result


def headline_rater_sheet(sample: pd.DataFrame, seed: str) -> pd.DataFrame:
    sheet = sample[["topic_sample_id", "headline"]].copy()
    sheet["primary_topic"] = ""
    sheet["secondary_topics"] = ""
    sheet["topic_centrality"] = ""
    sheet["confidence"] = ""
    sheet["reviewer_notes"] = ""
    sheet["order"] = sheet["topic_sample_id"].map(lambda value: stable_hash(seed, value))
    return sheet.sort_values("order").drop(columns="order").reset_index(drop=True)


def pair_candidates(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    pair_columns = [
        "record_id",
        "headline",
        "source",
        "published_utc",
        "duplicate_group_id",
        "topic_family_primary",
    ]
    eligible = frame.loc[
        frame["topic_family_primary"].ne("other_unclear"), pair_columns
    ].copy()
    eligible["published_utc"] = pd.to_datetime(eligible["published_utc"], utc=True)
    positives: list[dict[str, Any]] = []
    for topic, group in eligible.groupby("topic_family_primary", sort=True):
        rows = group.sort_values(["published_utc", "record_id"]).to_dict("records")
        for index, left in enumerate(rows[:-1]):
            for right in rows[index + 1 : index + 7]:
                gap = (
                    pd.Timestamp(right["published_utc"])
                    - pd.Timestamp(left["published_utc"])
                ).total_seconds() / 86_400
                if gap > 7:
                    break
                if (
                    left["source"] != right["source"]
                    and left["duplicate_group_id"] != right["duplicate_group_id"]
                ):
                    positives.append(
                        {
                            "machine_relation": "same_topic_discourse",
                            "topic_pair": topic,
                            "record_a": left,
                            "record_b": right,
                            "gap_days": gap,
                        }
                    )
                    break

    negatives: list[dict[str, Any]] = []
    rows = eligible.sort_values(["published_utc", "record_id"]).to_dict("records")
    for index, left in enumerate(rows[:-1]):
        for right in rows[index + 1 : index + 12]:
            gap = (
                pd.Timestamp(right["published_utc"])
                - pd.Timestamp(left["published_utc"])
            ).total_seconds() / 86_400
            if gap > 3:
                break
            if (
                left["topic_family_primary"] != right["topic_family_primary"]
                and left["source"] != right["source"]
                and left["duplicate_group_id"] != right["duplicate_group_id"]
            ):
                topic_pair = "|".join(
                    sorted(
                        [left["topic_family_primary"], right["topic_family_primary"]]
                    )
                )
                negatives.append(
                    {
                        "machine_relation": "different_topic_discourse",
                        "topic_pair": topic_pair,
                        "record_a": left,
                        "record_b": right,
                        "gap_days": gap,
                    }
                )
                break
    return pd.DataFrame(positives), pd.DataFrame(negatives)


def balanced_pairs(candidates: pd.DataFrame, count: int, seed: str) -> pd.DataFrame:
    if len(candidates) < count:
        raise ValueError(f"Only {len(candidates)} pair candidates available for {count} rows")
    working = candidates.copy()
    working["selection_hash"] = working.apply(
        lambda row: stable_hash(
            seed, row["record_a"]["record_id"], row["record_b"]["record_id"]
        ),
        axis=1,
    )
    groups = [
        group.sort_values("selection_hash")
        for _, group in working.groupby("topic_pair", sort=True)
    ]
    selected: list[pd.DataFrame] = []
    position = 0
    while len(selected) < count:
        added = False
        for group in groups:
            if position < len(group) and len(selected) < count:
                selected.append(group.iloc[[position]])
                added = True
        if not added:
            break
        position += 1
    return pd.concat(selected, ignore_index=True).drop(columns="selection_hash")


def build_pair_sample(frame: pd.DataFrame, sample_size: int) -> pd.DataFrame:
    positives, negatives = pair_candidates(frame)
    positive_count = sample_size // 2
    selected = pd.concat(
        [
            balanced_pairs(positives, positive_count, "pair-positive-v2"),
            balanced_pairs(negatives, sample_size - positive_count, "pair-negative-v2"),
        ],
        ignore_index=True,
    )
    selected["pair_id"] = selected.apply(
        lambda row: f"TOPICPAIR-{stable_id('topic-pair-v2', row['record_a']['record_id'], row['record_b']['record_id'], length=16)}",
        axis=1,
    )
    if selected["pair_id"].duplicated().any():
        raise AssertionError("Pair validation sample contains duplicate pair IDs")
    return selected


def pair_rater_sheet(sample: pd.DataFrame, seed: str) -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    for row in sample.to_dict("records"):
        left, right = row["record_a"], row["record_b"]
        if int(stable_hash(seed + "-swap", row["pair_id"])[-1], 16) % 2:
            left, right = right, left
        rows.append(
            {
                "pair_id": row["pair_id"],
                "headline_a": left["headline"],
                "headline_b": right["headline"],
                "same_topic_discourse": "",
                "confidence": "",
                "reviewer_notes": "",
                "order": stable_hash(seed, row["pair_id"]),
            }
        )
    return (
        pd.DataFrame(rows)
        .sort_values("order")
        .drop(columns="order")
        .reset_index(drop=True)
    )


def write_csv_atomic(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY)
    parser.add_argument("--headline-rater-1", type=Path, default=DEFAULT_HEADLINE_1)
    parser.add_argument("--headline-rater-2", type=Path, default=DEFAULT_HEADLINE_2)
    parser.add_argument("--headline-key", type=Path, default=DEFAULT_HEADLINE_KEY)
    parser.add_argument("--pair-rater-1", type=Path, default=DEFAULT_PAIR_1)
    parser.add_argument("--pair-rater-2", type=Path, default=DEFAULT_PAIR_2)
    parser.add_argument("--pair-key", type=Path, default=DEFAULT_PAIR_KEY)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--headline-sample-size", type=int, default=180)
    parser.add_argument("--pair-sample-size", type=int, default=100)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    taxonomy = load_taxonomy_v2(args.taxonomy)
    frame = pd.read_parquet(args.input)
    headline_sample = select_headline_sample(frame, args.headline_sample_size)
    headline_1 = headline_rater_sheet(headline_sample, "headline-rater-1-v2")
    headline_2 = headline_rater_sheet(headline_sample, "headline-rater-2-v2")
    headline_key_columns = [
        "topic_sample_id",
        "record_id",
        "source",
        "published_utc",
        "origin",
        "topic_family_primary",
        "topic_family_secondary",
        "topic_assignment_score",
        "topic_assignment_margin",
        "topic_assignment_confidence",
        "topic_assignment_method",
        "topic_second_candidate",
        "topic_second_score",
    ]
    headline_key = headline_sample[headline_key_columns].copy()

    pair_sample = build_pair_sample(frame, args.pair_sample_size)
    pair_1 = pair_rater_sheet(pair_sample, "pair-rater-1-v2")
    pair_2 = pair_rater_sheet(pair_sample, "pair-rater-2-v2")
    pair_key_rows: list[dict[str, Any]] = []
    for row in pair_sample.to_dict("records"):
        left, right = row["record_a"], row["record_b"]
        pair_key_rows.append(
            {
                "pair_id": row["pair_id"],
                "machine_relation": row["machine_relation"],
                "record_id_a": left["record_id"],
                "record_id_b": right["record_id"],
                "topic_a": left["topic_family_primary"],
                "topic_b": right["topic_family_primary"],
                "published_utc_a": left["published_utc"],
                "published_utc_b": right["published_utc"],
                "source_a": left["source"],
                "source_b": right["source"],
                "gap_days": row["gap_days"],
            }
        )
    pair_key = pd.DataFrame(pair_key_rows)

    outputs = {
        "headline_rater_1": (headline_1, args.headline_rater_1),
        "headline_rater_2": (headline_2, args.headline_rater_2),
        "headline_key": (headline_key, args.headline_key),
        "pair_rater_1": (pair_1, args.pair_rater_1),
        "pair_rater_2": (pair_2, args.pair_rater_2),
        "pair_key": (pair_key, args.pair_key),
    }
    for frame_to_write, path in outputs.values():
        write_csv_atomic(frame_to_write, path)

    manifest_outputs = {
        name: {
            "path": str(path.relative_to(ROOT)),
            "rows": len(frame_to_write),
            "sha256": sha256_file(path),
        }
        for name, (frame_to_write, path) in outputs.items()
    }
    manifest = {
        "schema_version": 2,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            str(args.input.relative_to(ROOT)): sha256_file(args.input),
            str(args.taxonomy.relative_to(ROOT)): sha256_file(args.taxonomy),
        },
        "headline_sample_size": len(headline_sample),
        "headline_machine_topic_counts": Counter(
            headline_sample["topic_family_primary"]
        ),
        "pair_sample_size": len(pair_sample),
        "pair_machine_relation_counts": Counter(pair_sample["machine_relation"]),
        "outputs": manifest_outputs,
        "blinding": {
            "rater_sheets_include_machine_labels": False,
            "rater_sheets_include_source_or_date": False,
            "rater_orders_are_independent": True,
            "pair_headline_order_is_independently_swapped": True,
        },
        "market_outcomes_used": False,
        "status": "fresh blinded candidate validation sample; keys must remain hidden",
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(manifest, indent=2, default=dict) + "\n", encoding="utf-8"
    )
    print(
        f"Wrote {len(headline_sample)} headline assignments and "
        f"{len(pair_sample)} topic-discourse pairs for two raters"
    )


if __name__ == "__main__":
    main()
