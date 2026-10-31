#!/usr/bin/env python3
"""Apply and evaluate the candidate selective topic-classification policy."""

from __future__ import annotations

import argparse
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
from research.topic_discovery.build_corpus import sha256_file


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
DEFAULT_INPUT = ROOT / "data/topic_family_v2_assignments.parquet"
DEFAULT_VALIDATION = ROOT / "data/topic_family_v2_adjudicated_headlines.csv"
DEFAULT_OUTPUT = ROOT / "data/topic_family_v2_selective_assignments.parquet"
DEFAULT_MANIFEST = HERE / "artifacts/topic_family_v2_selective_policy_manifest.json"


def selective_policy_config(taxonomy: dict[str, Any]) -> dict[str, Any]:
    config = taxonomy.get("selective_classification")
    if not isinstance(config, dict):
        raise ValueError("Taxonomy lacks selective_classification configuration")
    required = {"minimum_score", "minimum_margin", "retain_other_unclear"}
    missing = required.difference(config)
    if missing:
        raise ValueError(f"Selective policy lacks fields: {sorted(missing)}")
    if not 0 <= float(config["minimum_score"]) <= 1:
        raise ValueError("minimum_score must be between zero and one")
    if not 0 <= float(config["minimum_margin"]) <= 1:
        raise ValueError("minimum_margin must be between zero and one")
    if config["retain_other_unclear"] is not True:
        raise ValueError("The v2 policy must retain rather than force other_unclear")
    return config


def apply_selective_policy(
    frame: pd.DataFrame, config: dict[str, Any]
) -> pd.DataFrame:
    required = {
        "record_id",
        "topic_family_primary",
        "topic_family_secondary",
        "topic_assignment_score",
        "topic_assignment_margin",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Assignment data lacks fields: {sorted(missing)}")

    result = frame.copy()
    score = pd.to_numeric(result["topic_assignment_score"], errors="raise")
    margin = pd.to_numeric(result["topic_assignment_margin"], errors="raise")
    substantive = result["topic_family_primary"].ne("other_unclear")
    automatic = (
        substantive
        & score.ge(float(config["minimum_score"]))
        & margin.ge(float(config["minimum_margin"]))
    )
    review = substantive & ~automatic

    result["selective_route"] = np.select(
        [automatic, review],
        ["auto_accept", "model_review"],
        default="retain_other_unclear",
    )
    result["selective_primary_topic"] = np.where(
        automatic,
        result["topic_family_primary"],
        np.where(substantive, "", "other_unclear"),
    )
    result["selective_secondary_topics"] = np.where(
        automatic, result["topic_family_secondary"], ""
    )
    result["selective_label_status"] = np.select(
        [automatic, review],
        ["accepted_candidate_gate", "pending_outcome_blind_review"],
        default="retained_outside_topic_analysis",
    )
    return result


def evaluate_development_sample(
    validation: pd.DataFrame, config: dict[str, Any]
) -> dict[str, Any]:
    routed = apply_selective_policy(validation, config)
    resolved = routed.loc[routed["adjudication_status"].ne("unresolved")].copy()
    automatic = resolved["selective_route"].eq("auto_accept")
    automatic_correct = (
        resolved.loc[automatic, "selective_primary_topic"]
        == resolved.loc[automatic, "final_primary_topic"]
    )
    retained_other = resolved["selective_route"].eq("retain_other_unclear")
    retained_other_correct = (
        resolved.loc[retained_other, "final_primary_topic"] == "other_unclear"
    )
    return {
        "resolved_rows": len(resolved),
        "auto_accept_rows": int(automatic.sum()),
        "auto_accept_correct": int(automatic_correct.sum()),
        "auto_accept_accuracy": round(float(automatic_correct.mean()), 6),
        "model_review_rows": int(resolved["selective_route"].eq("model_review").sum()),
        "retained_other_rows": int(retained_other.sum()),
        "retained_other_correct": int(retained_other_correct.sum()),
        "retained_other_accuracy": round(float(retained_other_correct.mean()), 6),
        "selection_warning": (
            "Thresholds were selected on this development sample; accuracy requires "
            "confirmation on a fresh outcome-blind holdout."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--validation", type=Path, default=DEFAULT_VALIDATION)
    parser.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    taxonomy = load_taxonomy_v2(args.taxonomy)
    config = selective_policy_config(taxonomy)
    assignments = pd.read_parquet(args.input)
    validation = pd.read_csv(args.validation, dtype=str, keep_default_na=False)
    routed = apply_selective_policy(assignments, config)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(".tmp.parquet")
    routed.to_parquet(temporary, index=False)
    temporary.replace(args.output)

    route_counts = Counter(routed["selective_route"])
    manifest = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "candidate selective policy; fresh holdout required before freeze",
        "policy": config,
        "inputs": {
            str(args.input.relative_to(ROOT)): sha256_file(args.input),
            str(args.validation.relative_to(ROOT)): sha256_file(args.validation),
            str(args.taxonomy.relative_to(ROOT)): sha256_file(args.taxonomy),
        },
        "output": str(args.output.relative_to(ROOT)),
        "output_sha256": sha256_file(args.output),
        "rows": len(routed),
        "route_counts": dict(route_counts),
        "route_shares": {
            key: round(value / len(routed), 6) for key, value in route_counts.items()
        },
        "development_validation": evaluate_development_sample(validation, config),
        "topic_specific_exclusions_added": False,
        "market_outcomes_used": False,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"route_counts": dict(route_counts)}, indent=2))


if __name__ == "__main__":
    main()
