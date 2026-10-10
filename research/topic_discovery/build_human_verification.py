#!/usr/bin/env python3
"""Convert a completed agent topic audit into explicit human verification sheets."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from research.topic_discovery.assign_topic_families import (
    DEFAULT_TAXONOMY,
    load_taxonomy_v2,
)
from research.topic_discovery.build_corpus import sha256_file


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
DEFAULT_HEADLINE_AGENT = ROOT / "data/topic_family_v2_validation_rater_1.csv"
DEFAULT_PAIR_AGENT = ROOT / "data/topic_family_v2_pair_rater_1.csv"
DEFAULT_HEADLINE_REVIEW = ROOT / "data/topic_family_v2_validation_human_verification.csv"
DEFAULT_PAIR_REVIEW = ROOT / "data/topic_family_v2_pair_human_verification.csv"
DEFAULT_MANIFEST = HERE / "artifacts/topic_family_v2_agent_audit_manifest.json"


def validate_agent_headlines(frame: pd.DataFrame, allowed_topics: set[str]) -> None:
    required = {
        "topic_sample_id",
        "headline",
        "primary_topic",
        "secondary_topics",
        "topic_centrality",
        "confidence",
        "reviewer_notes",
    }
    if set(frame.columns) != required:
        raise ValueError("Agent headline audit has unexpected columns")
    if frame["topic_sample_id"].duplicated().any() or len(frame) != 180:
        raise ValueError("Agent headline audit must contain 180 unique rows")
    if not set(frame["primary_topic"]).issubset(allowed_topics):
        raise ValueError("Agent headline audit contains an invalid primary topic")
    secondary = {
        item
        for value in frame["secondary_topics"]
        for item in str(value).split("|")
        if item
    }
    if not secondary.issubset(allowed_topics - {"other_unclear"}):
        raise ValueError("Agent headline audit contains an invalid secondary topic")
    if not set(frame["topic_centrality"]).issubset(
        {"central", "material_secondary", "incidental", "unclear"}
    ):
        raise ValueError("Agent headline audit contains invalid centrality values")
    if not set(frame["confidence"]).issubset({"high", "medium", "low"}):
        raise ValueError("Agent headline audit contains invalid confidence values")


def validate_agent_pairs(frame: pd.DataFrame) -> None:
    required = {
        "pair_id",
        "headline_a",
        "headline_b",
        "same_topic_discourse",
        "confidence",
        "reviewer_notes",
    }
    if set(frame.columns) != required:
        raise ValueError("Agent pair audit has unexpected columns")
    if frame["pair_id"].duplicated().any() or len(frame) != 100:
        raise ValueError("Agent pair audit must contain 100 unique rows")
    if not set(frame["same_topic_discourse"]).issubset({"yes", "no", "unclear"}):
        raise ValueError("Agent pair audit contains invalid relation values")
    if not set(frame["confidence"]).issubset({"high", "medium", "low"}):
        raise ValueError("Agent pair audit contains invalid confidence values")


def headline_verification_sheet(frame: pd.DataFrame) -> pd.DataFrame:
    renamed = frame.rename(
        columns={
            "primary_topic": "agent_primary_topic",
            "secondary_topics": "agent_secondary_topics",
            "topic_centrality": "agent_topic_centrality",
            "confidence": "agent_confidence",
            "reviewer_notes": "agent_notes",
        }
    ).copy()
    renamed["human_decision"] = ""
    renamed["corrected_primary_topic"] = ""
    renamed["corrected_secondary_topics"] = ""
    renamed["corrected_topic_centrality"] = ""
    renamed["human_confidence"] = ""
    renamed["human_notes"] = ""
    return renamed


def pair_verification_sheet(frame: pd.DataFrame) -> pd.DataFrame:
    renamed = frame.rename(
        columns={
            "same_topic_discourse": "agent_same_topic_discourse",
            "confidence": "agent_confidence",
            "reviewer_notes": "agent_notes",
        }
    ).copy()
    renamed["human_decision"] = ""
    renamed["corrected_same_topic_discourse"] = ""
    renamed["human_confidence"] = ""
    renamed["human_notes"] = ""
    return renamed


def write_csv_atomic(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--headline-agent", type=Path, default=DEFAULT_HEADLINE_AGENT)
    parser.add_argument("--pair-agent", type=Path, default=DEFAULT_PAIR_AGENT)
    parser.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY)
    parser.add_argument("--headline-review", type=Path, default=DEFAULT_HEADLINE_REVIEW)
    parser.add_argument("--pair-review", type=Path, default=DEFAULT_PAIR_REVIEW)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    taxonomy = load_taxonomy_v2(args.taxonomy)
    allowed_topics = set(taxonomy["topic_families"]) | {"other_unclear"}
    headlines = pd.read_csv(args.headline_agent, dtype=str, keep_default_na=False)
    pairs = pd.read_csv(args.pair_agent, dtype=str, keep_default_na=False)
    validate_agent_headlines(headlines, allowed_topics)
    validate_agent_pairs(pairs)
    headline_review = headline_verification_sheet(headlines)
    pair_review = pair_verification_sheet(pairs)
    write_csv_atomic(headline_review, args.headline_review)
    write_csv_atomic(pair_review, args.pair_review)

    manifest = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "audit_role": "single Codex machine audit followed by explicit human verification",
        "agent_inputs": {
            str(args.headline_agent.relative_to(ROOT)): sha256_file(args.headline_agent),
            str(args.pair_agent.relative_to(ROOT)): sha256_file(args.pair_agent),
            str(args.taxonomy.relative_to(ROOT)): sha256_file(args.taxonomy),
        },
        "verification_outputs": {
            str(args.headline_review.relative_to(ROOT)): sha256_file(args.headline_review),
            str(args.pair_review.relative_to(ROOT)): sha256_file(args.pair_review),
        },
        "headline_rows": len(headline_review),
        "pair_rows": len(pair_review),
        "hidden_keys_opened": False,
        "market_outcomes_used": False,
        "human_decision_values": ["accept", "correct", "unclear"],
        "status": "agent audit complete only when source audits validate; human verification pending",
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {len(headline_review)} headline and {len(pair_review)} pair verification rows"
    )


if __name__ == "__main__":
    main()
