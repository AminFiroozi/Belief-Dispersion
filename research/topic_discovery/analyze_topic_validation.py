#!/usr/bin/env python3
"""Derive adjudicated topic references and score v2 production assignments."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from research.topic_discovery.build_corpus import sha256_file


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
DEFAULT_HEADLINE_REVIEW = ROOT / "data/topic_family_v2_validation_human_verification.csv"
DEFAULT_HEADLINE_KEY = ROOT / "data/topic_family_v2_validation_key.csv"
DEFAULT_PAIR_REVIEW = ROOT / "data/topic_family_v2_pair_human_verification.csv"
DEFAULT_PAIR_KEY = ROOT / "data/topic_family_v2_pair_key.csv"
DEFAULT_HEADLINE_OUTPUT = ROOT / "data/topic_family_v2_adjudicated_headlines.csv"
DEFAULT_PAIR_OUTPUT = ROOT / "data/topic_family_v2_adjudicated_pairs.csv"
DEFAULT_METRICS = HERE / "artifacts/topic_family_v2_validation_metrics.json"
DEFAULT_REPORT = HERE / "artifacts/TOPIC_FAMILY_V2_VALIDATION_REPORT.md"


def normalized(value: Any) -> str:
    return " ".join(str(value).strip().lower().split())


def derive_headline_reference(review: pd.DataFrame) -> pd.DataFrame:
    frame = review.copy()
    frame["human_decision"] = frame["human_decision"].map(normalized)
    invalid = set(frame["human_decision"]) - {"accept", "correct", "unclear"}
    if invalid:
        raise ValueError(f"Invalid headline decisions: {sorted(invalid)}")

    accepted = frame["human_decision"].eq("accept")
    corrected = frame["human_decision"].eq("correct")
    unresolved = frame["human_decision"].eq("unclear")
    correction_columns = [
        "corrected_primary_topic",
        "corrected_topic_centrality",
        "human_confidence",
    ]
    if frame.loc[corrected, correction_columns].eq("").any().any():
        raise ValueError("Every corrected headline requires topic, centrality, and confidence")
    if frame.loc[accepted, [
        "corrected_primary_topic",
        "corrected_secondary_topics",
        "corrected_topic_centrality",
    ]].ne("").any().any():
        raise ValueError("Accepted headlines must not retain correction fields")

    frame["adjudication_status"] = np.select(
        [accepted, corrected, unresolved],
        ["accepted_agent", "human_corrected", "unresolved"],
        default="",
    )
    frame["final_primary_topic"] = np.where(
        accepted,
        frame["agent_primary_topic"],
        np.where(corrected, frame["corrected_primary_topic"], ""),
    )
    frame["final_secondary_topics"] = np.where(
        accepted,
        frame["agent_secondary_topics"],
        np.where(corrected, frame["corrected_secondary_topics"], ""),
    )
    frame["final_topic_centrality"] = np.where(
        accepted,
        frame["agent_topic_centrality"],
        np.where(corrected, frame["corrected_topic_centrality"], "unclear"),
    )
    frame["final_confidence"] = np.where(
        accepted,
        frame["agent_confidence"],
        np.where(corrected | unresolved, frame["human_confidence"], ""),
    )
    return frame


def derive_pair_reference(review: pd.DataFrame) -> pd.DataFrame:
    frame = review.copy()
    frame["human_decision"] = frame["human_decision"].map(normalized)
    invalid = set(frame["human_decision"]) - {"accept", "correct", "unclear"}
    if invalid:
        raise ValueError(f"Invalid pair decisions: {sorted(invalid)}")
    accepted = frame["human_decision"].eq("accept")
    corrected = frame["human_decision"].eq("correct")
    unresolved = frame["human_decision"].eq("unclear")
    if frame.loc[corrected, ["corrected_same_topic_discourse", "human_confidence"]].eq("").any().any():
        raise ValueError("Every corrected pair requires relation and confidence")
    if frame.loc[accepted, "corrected_same_topic_discourse"].ne("").any():
        raise ValueError("Accepted pairs must not retain a correction")
    frame["adjudication_status"] = np.select(
        [accepted, corrected, unresolved],
        ["accepted_agent", "human_corrected", "unresolved"],
        default="",
    )
    frame["final_same_topic_discourse"] = np.where(
        accepted,
        frame["agent_same_topic_discourse"],
        np.where(corrected, frame["corrected_same_topic_discourse"], "unclear"),
    )
    frame["final_confidence"] = np.where(
        accepted,
        frame["human_confidence"].where(frame["human_confidence"].ne(""), frame["agent_confidence"]),
        frame["human_confidence"],
    )
    return frame


def rounded_classification_report(reference: pd.Series, prediction: pd.Series) -> dict[str, Any]:
    report = classification_report(reference, prediction, output_dict=True, zero_division=0)
    rounded: dict[str, Any] = {}
    for label, values in report.items():
        if isinstance(values, dict):
            rounded[label] = {
                key: int(value) if key == "support" else round(float(value), 6)
                for key, value in values.items()
            }
        else:
            rounded[label] = round(float(values), 6)
    return rounded


def grouped_accuracy(frame: pd.DataFrame, group_column: str, correct_column: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group, values in frame.groupby(group_column, dropna=False, sort=True):
        rows.append(
            {
                group_column: str(group),
                "rows": len(values),
                "correct": int(values[correct_column].sum()),
                "accuracy": round(float(values[correct_column].mean()), 6),
            }
        )
    return rows


def calculate_metrics(headlines: pd.DataFrame, pairs: pd.DataFrame) -> dict[str, Any]:
    resolved_headlines = headlines.loc[headlines["adjudication_status"].ne("unresolved")].copy()
    resolved_pairs = pairs.loc[pairs["final_same_topic_discourse"].isin(["yes", "no"])].copy()

    resolved_headlines["agent_primary_correct"] = (
        resolved_headlines["agent_primary_topic"] == resolved_headlines["final_primary_topic"]
    )
    resolved_headlines["production_primary_correct"] = (
        resolved_headlines["topic_family_primary"] == resolved_headlines["final_primary_topic"]
    )
    resolved_headlines["production_top2_correct"] = (
        resolved_headlines["production_primary_correct"]
        | (resolved_headlines["topic_second_candidate"] == resolved_headlines["final_primary_topic"])
    )

    resolved_pairs["agent_relation_correct"] = (
        resolved_pairs["agent_same_topic_discourse"]
        == resolved_pairs["final_same_topic_discourse"]
    )
    resolved_pairs["production_relation"] = resolved_pairs["machine_relation"].map(
        {"same_topic_discourse": "yes", "different_topic_discourse": "no"}
    )
    resolved_pairs["production_relation_correct"] = (
        resolved_pairs["production_relation"]
        == resolved_pairs["final_same_topic_discourse"]
    )

    pair_matrix = confusion_matrix(
        resolved_pairs["final_same_topic_discourse"],
        resolved_pairs["production_relation"],
        labels=["yes", "no"],
    )
    true_positive, false_negative = map(int, pair_matrix[0])
    false_positive, true_negative = map(int, pair_matrix[1])
    precision = true_positive / (true_positive + false_positive)
    recall = true_positive / (true_positive + false_negative)
    specificity = true_negative / (true_negative + false_positive)
    f1 = 2 * precision * recall / (precision + recall)

    return {
        "headline_validation": {
            "rows": len(headlines),
            "resolved_rows": len(resolved_headlines),
            "unresolved_rows": int((headlines["adjudication_status"] == "unresolved").sum()),
            "human_decisions": headlines["human_decision"].value_counts().sort_index().to_dict(),
            "agent_primary_accuracy": round(float(resolved_headlines["agent_primary_correct"].mean()), 6),
            "production_primary_accuracy": round(float(resolved_headlines["production_primary_correct"].mean()), 6),
            "production_top2_accuracy": round(float(resolved_headlines["production_top2_correct"].mean()), 6),
            "production_classification_report": rounded_classification_report(
                resolved_headlines["final_primary_topic"],
                resolved_headlines["topic_family_primary"],
            ),
            "production_accuracy_by_confidence": grouped_accuracy(
                resolved_headlines, "topic_assignment_confidence", "production_primary_correct"
            ),
            "production_accuracy_by_method": grouped_accuracy(
                resolved_headlines, "topic_assignment_method", "production_primary_correct"
            ),
            "production_error_rows": int((~resolved_headlines["production_primary_correct"]).sum()),
        },
        "pair_validation": {
            "rows": len(pairs),
            "resolved_rows": len(resolved_pairs),
            "human_decisions": pairs["human_decision"].value_counts().sort_index().to_dict(),
            "final_relation_counts": resolved_pairs["final_same_topic_discourse"].value_counts().sort_index().to_dict(),
            "agent_relation_accuracy": round(float(resolved_pairs["agent_relation_correct"].mean()), 6),
            "production_relation_accuracy": round(float(resolved_pairs["production_relation_correct"].mean()), 6),
            "production_same_topic_precision": round(precision, 6),
            "production_same_topic_recall": round(recall, 6),
            "production_same_topic_f1": round(f1, 6),
            "production_different_topic_specificity": round(specificity, 6),
            "production_confusion": {
                "true_positive": true_positive,
                "false_negative": false_negative,
                "false_positive": false_positive,
                "true_negative": true_negative,
            },
            "production_error_rows": int((~resolved_pairs["production_relation_correct"]).sum()),
        },
    }


def markdown_report(metrics: dict[str, Any]) -> str:
    headline = metrics["headline_validation"]
    pair = metrics["pair_validation"]
    confidence_rows = "\n".join(
        f"| `{row['topic_assignment_confidence']}` | {row['rows']} | {row['correct']} | {row['accuracy']:.1%} |"
        for row in headline["production_accuracy_by_confidence"]
    )
    return f"""# Topic Family V2 Validation Results

Run date: 2026-10-25
Status: human-verified reference derived; production rules not frozen

## Design

One blinded Codex audit was followed by explicit human acceptance, correction,
or unresolved judgment. This is an adjudicated machine-plus-human reference, not
independent inter-rater agreement. The 180-headline sample was deliberately
stratified across machine topics and difficult confidence strata, so aggregate
accuracy is a validation-sample result rather than a corpus-prevalence estimate.

## Headline Assignment

- Resolved reference labels: {headline['resolved_rows']} of {headline['rows']}.
- Codex primary-topic accuracy: {headline['agent_primary_accuracy']:.1%}.
- Production exact primary-topic accuracy: {headline['production_primary_accuracy']:.1%}.
- Production primary-or-second-candidate accuracy: {headline['production_top2_accuracy']:.1%}.
- Production macro F1: {headline['production_classification_report']['macro avg']['f1-score']:.1%}.
- Production weighted F1: {headline['production_classification_report']['weighted avg']['f1-score']:.1%}.

### Accuracy By Production Confidence

| Confidence | Rows | Correct | Accuracy |
| --- | ---: | ---: | ---: |
{confidence_rows}

High-confidence assignments are reliable in this sample. Low-confidence and
unassigned records account for most errors and should not enter confirmatory
topic-conditioned features without revised rules or model adjudication.

## Pair Assignment

- Final same-topic pairs: {pair['final_relation_counts'].get('yes', 0)}.
- Final different-topic pairs: {pair['final_relation_counts'].get('no', 0)}.
- Codex relation accuracy: {pair['agent_relation_accuracy']:.1%}.
- Production relation accuracy: {pair['production_relation_accuracy']:.1%}.
- Same-topic precision: {pair['production_same_topic_precision']:.1%}.
- Same-topic recall: {pair['production_same_topic_recall']:.1%}.
- Same-topic F1: {pair['production_same_topic_f1']:.1%}.
- Different-topic specificity: {pair['production_different_topic_specificity']:.1%}.

The pair procedure is usable as a candidate generator but still makes 14 errors
in 100 deliberately balanced audit pairs. Exact-event clustering remains
secondary to the adopted topic-window design.

## Decision

Do not freeze the current production headline assigner at a
{headline['production_primary_accuracy']:.1%} exact rate.
Preserve the 18-family taxonomy, including `iran_israel`, and revise assignment
rules from the frozen adjudicated errors. A defensible first production policy
is to accept high-confidence automatic labels, route medium/low/unassigned cases
through model adjudication, and validate that policy on the same reference before
constructing market-outcome features.
"""


def write_csv_atomic(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False, lineterminator="\n")
    temporary.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--headline-review", type=Path, default=DEFAULT_HEADLINE_REVIEW)
    parser.add_argument("--headline-key", type=Path, default=DEFAULT_HEADLINE_KEY)
    parser.add_argument("--pair-review", type=Path, default=DEFAULT_PAIR_REVIEW)
    parser.add_argument("--pair-key", type=Path, default=DEFAULT_PAIR_KEY)
    parser.add_argument("--headline-output", type=Path, default=DEFAULT_HEADLINE_OUTPUT)
    parser.add_argument("--pair-output", type=Path, default=DEFAULT_PAIR_OUTPUT)
    parser.add_argument("--metrics", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    headline_review = pd.read_csv(args.headline_review, dtype=str, keep_default_na=False)
    pair_review = pd.read_csv(args.pair_review, dtype=str, keep_default_na=False)
    headline_key = pd.read_csv(args.headline_key, dtype=str, keep_default_na=False)
    pair_key = pd.read_csv(args.pair_key, dtype=str, keep_default_na=False)

    headline_reference = derive_headline_reference(headline_review).merge(
        headline_key, on="topic_sample_id", validate="one_to_one"
    )
    pair_reference = derive_pair_reference(pair_review).merge(
        pair_key, on="pair_id", validate="one_to_one"
    )
    metrics = calculate_metrics(headline_reference, pair_reference)
    metrics["schema_version"] = 1
    metrics["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    metrics["inputs"] = {
        str(args.headline_review.relative_to(ROOT)): sha256_file(args.headline_review),
        str(args.headline_key.relative_to(ROOT)): sha256_file(args.headline_key),
        str(args.pair_review.relative_to(ROOT)): sha256_file(args.pair_review),
        str(args.pair_key.relative_to(ROOT)): sha256_file(args.pair_key),
    }
    metrics["market_outcomes_used"] = False
    metrics["sample_interpretation"] = (
        "stratified measurement-validation sample; aggregate metrics are not corpus-prevalence estimates"
    )

    write_csv_atomic(headline_reference, args.headline_output)
    write_csv_atomic(pair_reference, args.pair_output)
    metrics["outputs"] = {
        str(args.headline_output.relative_to(ROOT)): sha256_file(args.headline_output),
        str(args.pair_output.relative_to(ROOT)): sha256_file(args.pair_output),
    }
    args.metrics.parent.mkdir(parents=True, exist_ok=True)
    args.metrics.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    args.report.write_text(markdown_report(metrics), encoding="utf-8")
    print(
        f"Headline production accuracy: {metrics['headline_validation']['production_primary_accuracy']:.1%}; "
        f"pair production accuracy: {metrics['pair_validation']['production_relation_accuracy']:.1%}"
    )


if __name__ == "__main__":
    main()
