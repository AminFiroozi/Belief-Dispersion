#!/usr/bin/env python3
"""Build blinded general-news sentiment sheets and a separate provenance key."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from research.topic_discovery.build_corpus import sha256_file


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
INPUT = ROOT / "data/topic_family_v2_selective_assignments.parquet"
PRIOR_AUDIT = ROOT / "data/topic_family_v2_adjudicated_headlines.csv"
PREFIX = ROOT / "data/general_sentiment_v1"
MANIFEST = HERE / "artifacts/general_sentiment_v1_sample_manifest.json"
ROUTES = ("auto_accept", "model_review", "retain_other_unclear")
RATER_COLUMNS = (
    "sample_id", "headline", "equity_sentiment", "label_confidence",
    "ambiguity_flag", "reviewer_notes",
)
SEED = "general-sentiment-validation-v1-20261030"


def stable_hash(*parts: object) -> str:
    payload = "|".join((SEED, *(str(part) for part in parts)))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def select_sample(frame: pd.DataFrame, prior_ids: set[str], per_route: int) -> pd.DataFrame:
    required = {
        "record_id", "headline", "duplicate_group_id", "year", "source", "origin",
        "published_utc", "selective_route", "topic_family_primary",
    }
    missing = required - set(frame)
    if missing:
        raise ValueError(f"Missing sample fields: {sorted(missing)}")
    if frame["record_id"].duplicated().any():
        raise ValueError("Duplicate record IDs in source corpus")
    eligible = frame.loc[~frame["record_id"].isin(prior_ids)].copy()
    eligible = eligible.loc[eligible["headline"].fillna("").str.strip().ne("")]
    eligible["selection_hash"] = eligible["record_id"].map(lambda value: stable_hash("select", value))
    eligible["topic_stratum"] = eligible["topic_family_primary"].where(
        eligible["selective_route"].ne("retain_other_unclear"), "other_unclear"
    )
    selected = []
    used_groups: set[str] = set()
    for route in ROUTES:
        subset = eligible.loc[eligible["selective_route"].eq(route)].copy()
        if len(subset) < per_route:
            raise ValueError(f"Insufficient rows for {route}: {len(subset)}")
        subset["stratum"] = (
            subset["topic_stratum"].astype(str) + "|" + subset["year"].astype(str)
            + "|" + subset["origin"].astype(str)
        )
        groups = [
            group.sort_values("selection_hash").to_dict("records")
            for _, group in sorted(
                subset.groupby("stratum", sort=False),
                key=lambda item: stable_hash("stratum", route, item[0]),
            )
        ]
        picked = 0
        depth = 0
        while picked < per_route:
            added = False
            for group in groups:
                while depth < len(group):
                    row = group[depth]
                    duplicate_id = str(row["duplicate_group_id"])
                    if duplicate_id in used_groups:
                        break
                    used_groups.add(duplicate_id)
                    selected.append(row)
                    picked += 1
                    added = True
                    break
                if picked == per_route:
                    break
            if not added:
                raise ValueError(f"Could not obtain {per_route} unique groups for {route}")
            depth += 1
    sample = pd.DataFrame(selected).drop(columns=["selection_hash", "stratum", "topic_stratum"])
    sample["sample_id"] = sample["record_id"].map(lambda value: "GENSENT-" + stable_hash("id", value)[:16])
    sample["split"] = ""
    for route in ROUTES:
        indices = sample.index[sample["selective_route"].eq(route)].tolist()
        indices.sort(key=lambda index: stable_hash("split", sample.at[index, "record_id"]))
        sample.loc[indices[: per_route // 2], "split"] = "development"
        sample.loc[indices[per_route // 2 :], "split"] = "holdout"
    if sample["sample_id"].duplicated().any() or sample["duplicate_group_id"].duplicated().any():
        raise AssertionError("Sample IDs or duplicate groups are not unique")
    return sample


def blinded_sheet(sample: pd.DataFrame, role: str) -> pd.DataFrame:
    result = sample[["sample_id", "headline"]].copy()
    result["order"] = result["sample_id"].map(lambda value: stable_hash("order", role, value))
    result = result.sort_values("order").drop(columns="order").reset_index(drop=True)
    for column in RATER_COLUMNS[2:]:
        result[column] = ""
    return result[list(RATER_COLUMNS)]


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = frame.to_csv(index=False, lineterminator="\n")
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise FileExistsError(f"Existing file differs; refusing to overwrite: {path}")
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=INPUT)
    parser.add_argument("--prior-audit", type=Path, default=PRIOR_AUDIT)
    parser.add_argument("--output-prefix", type=Path, default=PREFIX)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--per-route", type=int, default=80)
    args = parser.parse_args()
    if args.per_route <= 0 or args.per_route % 2:
        raise ValueError("--per-route must be a positive even number")
    frame = pd.read_parquet(args.input)
    prior = pd.read_csv(args.prior_audit, usecols=["record_id"], dtype=str)
    sample = select_sample(frame, set(prior["record_id"]), args.per_route)
    key_columns = [
        "sample_id", "record_id", "duplicate_group_id", "split", "source", "origin",
        "published_utc", "year", "topic_family_primary", "topic_assignment_score",
        "topic_assignment_margin", "selective_route", "selective_primary_topic",
    ]
    outputs = {
        "rater_1": args.output_prefix.with_name(args.output_prefix.name + "_rater_1.csv"),
        "rater_2": args.output_prefix.with_name(args.output_prefix.name + "_rater_2.csv"),
        "frontier_input": args.output_prefix.with_name(args.output_prefix.name + "_frontier_input.csv"),
        "hidden_key": args.output_prefix.with_name(args.output_prefix.name + "_key.csv"),
    }
    for role in ("rater_1", "rater_2", "frontier_input"):
        write_csv(blinded_sheet(sample, role), outputs[role])
    write_csv(sample[key_columns].sort_values("sample_id"), outputs["hidden_key"])
    manifest = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "sampling_seed": SEED,
        "sampling": "Deterministic round robin across topic, year, and origin within each route; unique duplicate groups; disjoint from prior topic audit",
        "sample_size": len(sample),
        "route_counts": sample["selective_route"].value_counts().to_dict(),
        "split_counts": {
            split: group["selective_route"].value_counts().to_dict()
            for split, group in sample.groupby("split")
        },
        "year_counts": sample["year"].value_counts().sort_index().to_dict(),
        "origin_counts": sample["origin"].value_counts().to_dict(),
        "topic_counts": sample["topic_family_primary"].value_counts().to_dict(),
        "unique_sources": int(sample["source"].nunique()),
        "input_sha256": sha256_file(args.input),
        "prior_audit_sha256": sha256_file(args.prior_audit),
        "outputs": {role: {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path), "bytes": path.stat().st_size} for role, path in outputs.items()},
        "blinding": "Raters and frontier see only ID, headline, and blank ratings; sources, dates, topics, routes, and split are confined to the key",
        "market_outcomes_used": False,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Built {len(sample)} blinded rows; {args.per_route} per topic route")


if __name__ == "__main__":
    main()
