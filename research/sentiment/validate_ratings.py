#!/usr/bin/env python3
"""Validate a completed blinded sentiment sheet against its untouched input."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from research.sentiment.build_validation_sample import RATER_COLUMNS
from research.topic_discovery.build_corpus import sha256_file


def validate_sheet(completed: pd.DataFrame, original: pd.DataFrame) -> None:
    if completed.columns.tolist() != list(RATER_COLUMNS):
        raise ValueError("Completed sheet has a changed schema")
    if original.columns.tolist() != list(RATER_COLUMNS):
        raise ValueError("Original sheet has a changed schema")
    if len(completed) != len(original):
        raise ValueError("Completed sheet has a changed row count")
    if not completed[["sample_id", "headline"]].equals(original[["sample_id", "headline"]]):
        raise ValueError("Sample IDs, headlines, or row order changed")
    if completed["sample_id"].duplicated().any():
        raise ValueError("Duplicate sample ID")
    allowed = {
        "equity_sentiment": set("ABCDEU"),
        "label_confidence": {"H", "M", "L"},
        "ambiguity_flag": {"Y", "N"},
    }
    for column, codes in allowed.items():
        invalid = set(completed[column]) - codes
        if invalid:
            raise ValueError(f"Invalid or blank {column}: {sorted(invalid)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("completed", type=Path)
    parser.add_argument("original", type=Path)
    args = parser.parse_args()
    completed = pd.read_csv(args.completed, dtype=str, keep_default_na=False)
    original = pd.read_csv(args.original, dtype=str, keep_default_na=False)
    validate_sheet(completed, original)
    print(f"Valid: {len(completed)} rows; SHA-256 {sha256_file(args.completed)}")


if __name__ == "__main__":
    main()
