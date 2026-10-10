#!/usr/bin/env python3
"""Assign outcome-blind v2 topic families to the canonical news corpus."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from research.topic_discovery.build_corpus import sha256_file


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
DEFAULT_INPUT = ROOT / "data/topic_discovery_corpus.parquet"
DEFAULT_TAXONOMY = HERE / "taxonomy_v2.json"
DEFAULT_OUTPUT = ROOT / "data/topic_family_v2_assignments.parquet"
DEFAULT_MANIFEST = HERE / "artifacts/topic_family_v2_assignment_manifest.json"


def load_taxonomy_v2(path: Path) -> dict[str, Any]:
    taxonomy = json.loads(path.read_text(encoding="utf-8"))
    required = {"topic_families", "topic_priority", "candidate_topic_map", "assignment"}
    missing = required.difference(taxonomy)
    if missing:
        raise ValueError(f"Taxonomy lacks required fields: {sorted(missing)}")
    topics = set(taxonomy["topic_families"])
    priority = taxonomy["topic_priority"]
    if set(priority) != topics or len(priority) != len(topics):
        raise ValueError("topic_priority must contain every topic family exactly once")
    for topic, specification in taxonomy["topic_families"].items():
        if not specification.get("definition") or not specification.get("include_patterns"):
            raise ValueError(f"Topic {topic} lacks a definition or include patterns")
        for pattern in specification["include_patterns"]:
            re.compile(pattern, flags=re.IGNORECASE)
    return taxonomy


def topic_prototype(specification: dict[str, Any]) -> str:
    return " ".join(
        [
            specification["label"],
            specification["definition"],
            *specification.get("examples", []),
        ]
    )


def semantic_scores(
    texts: pd.Series,
    taxonomy: dict[str, Any],
) -> tuple[np.ndarray, dict[str, Any]]:
    topics = taxonomy["topic_priority"]
    prototypes = [topic_prototype(taxonomy["topic_families"][topic]) for topic in topics]
    config = taxonomy["assignment"]
    vectorizer = TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        stop_words="english",
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.995,
        sublinear_tf=True,
        max_features=int(config["tfidf_max_features"]),
    )
    combined = pd.concat(
        [texts.fillna("").astype(str), pd.Series(prototypes)], ignore_index=True
    )
    matrix = vectorizer.fit_transform(combined)
    corpus_matrix = matrix[: len(texts)]
    prototype_matrix = matrix[len(texts) :]
    scores = (corpus_matrix @ prototype_matrix.T).toarray().astype(np.float32)
    diagnostics = {
        "backend": "tfidf-word-unigram-bigram-topic-prototypes",
        "vocabulary_size": len(vectorizer.vocabulary_),
        "fit_scope": "complete outcome-blind corpus plus frozen topic prototypes",
    }
    return scores, diagnostics


def rule_scores(
    headlines: pd.Series,
    candidate_topics: pd.Series,
    taxonomy: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    topics = taxonomy["topic_priority"]
    count = len(headlines)
    hits = np.zeros((count, len(topics)), dtype=np.uint8)
    evidence: list[list[str]] = [[] for _ in range(count)]
    for topic_index, topic in enumerate(topics):
        for pattern in taxonomy["topic_families"][topic]["include_patterns"]:
            mask = headlines.str.contains(pattern, case=False, regex=True, na=False).to_numpy()
            hits[:, topic_index] = np.minimum(
                255, hits[:, topic_index].astype(np.uint16) + mask.astype(np.uint16)
            ).astype(np.uint8)
            for row_index in np.flatnonzero(mask):
                evidence[row_index].append(topic)

    candidate_signal = np.zeros_like(hits, dtype=np.float32)
    topic_positions = {topic: index for index, topic in enumerate(topics)}
    for candidate, topic in taxonomy["candidate_topic_map"].items():
        if topic not in topic_positions:
            raise ValueError(f"Candidate map references unknown topic: {topic}")
        mask = candidate_topics.fillna("").map(
            lambda value: candidate in {item for item in str(value).split("|") if item}
        ).to_numpy()
        candidate_signal[mask, topic_positions[topic]] = 1.0
        for row_index in np.flatnonzero(mask):
            evidence[row_index].append(f"candidate:{candidate}")
    evidence_text = ["|".join(sorted(set(values))) for values in evidence]
    return hits, candidate_signal, evidence_text


def combine_assignments(
    semantic: np.ndarray,
    hits: np.ndarray,
    candidate_signal: np.ndarray,
    evidence: list[str],
    taxonomy: dict[str, Any],
) -> pd.DataFrame:
    config = taxonomy["assignment"]
    topics = np.asarray(taxonomy["topic_priority"], dtype=object)
    rule_strength = 1.0 - np.exp(-hits.astype(np.float32))
    scores = (
        float(config["semantic_weight"]) * semantic
        + float(config["rule_weight"]) * rule_strength
    )
    scores = np.maximum(
        scores,
        candidate_signal * float(config["candidate_floor"]),
    )
    order = np.argsort(-scores, axis=1, kind="stable")
    best_index = order[:, 0]
    second_index = order[:, 1]
    row_positions = np.arange(len(scores))
    best_score = scores[row_positions, best_index]
    second_score = scores[row_positions, second_index]
    margin = best_score - second_score
    minimum_score = float(config["minimum_score"])
    is_other = best_score < minimum_score

    primary = topics[best_index].astype(object)
    primary[is_other] = "other_unclear"
    second = topics[second_index].astype(object)
    second[is_other] = ""

    confidence = np.full(len(scores), "low", dtype=object)
    selected_hits = hits[row_positions, best_index]
    selected_candidate = candidate_signal[row_positions, best_index] > 0
    medium = (best_score >= float(config["medium_confidence_score"])) & (
        margin >= float(config["ambiguous_margin"])
    )
    high = (best_score >= float(config["high_confidence_score"])) & (
        margin >= float(config["ambiguous_margin"])
    ) & (
        (selected_hits >= 2) | (selected_candidate & (selected_hits >= 1))
    )
    medium = medium | selected_candidate
    confidence[medium] = "medium"
    confidence[high] = "high"
    confidence[is_other] = "unassigned"

    methods: list[str] = []
    secondary_topics: list[str] = []
    secondary_threshold = float(config["secondary_score"])
    secondary_gap = float(config["secondary_max_gap"])
    for row_index in range(len(scores)):
        if is_other[row_index]:
            methods.append("unassigned")
            secondary_topics.append("")
            continue
        selected = best_index[row_index]
        has_candidate = candidate_signal[row_index, selected] > 0
        has_rule = hits[row_index, selected] > 0
        if has_candidate:
            methods.append("retrieval_candidate")
        elif has_rule and semantic[row_index, selected] > 0:
            methods.append("rule_plus_semantic")
        elif has_rule:
            methods.append("rule")
        else:
            methods.append("semantic")

        alternatives: list[str] = []
        for topic_index in order[row_index, 1:]:
            value = float(scores[row_index, topic_index])
            if value < secondary_threshold or best_score[row_index] - value > secondary_gap:
                break
            if hits[row_index, topic_index] > 0 or semantic[row_index, topic_index] >= secondary_threshold:
                alternatives.append(str(topics[topic_index]))
            if len(alternatives) == 3:
                break
        secondary_topics.append("|".join(alternatives))

    return pd.DataFrame(
        {
            "topic_family_primary": primary,
            "topic_family_secondary": secondary_topics,
            "topic_assignment_score": np.round(best_score, 6),
            "topic_assignment_margin": np.round(margin, 6),
            "topic_assignment_confidence": confidence,
            "topic_assignment_method": methods,
            "topic_second_candidate": second,
            "topic_second_score": np.round(second_score, 6),
            "topic_rule_evidence": evidence,
        }
    )


def assign_topic_families(
    corpus: pd.DataFrame,
    taxonomy: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    required = {"record_id", "headline", "neutral_text_baseline", "candidate_topics"}
    missing = required.difference(corpus.columns)
    if missing:
        raise ValueError(f"Corpus lacks required columns: {sorted(missing)}")
    semantic, diagnostics = semantic_scores(corpus["neutral_text_baseline"], taxonomy)
    hits, candidate_signal, evidence = rule_scores(
        corpus["headline"], corpus["candidate_topics"], taxonomy
    )
    assignment = combine_assignments(
        semantic, hits, candidate_signal, evidence, taxonomy
    )
    result = pd.concat([corpus.reset_index(drop=True), assignment], axis=1)
    if result["record_id"].duplicated().any():
        raise AssertionError("Topic assignment output contains duplicate record IDs")
    return result, diagnostics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    taxonomy = load_taxonomy_v2(args.taxonomy)
    corpus = pd.read_parquet(args.input)
    assignments, semantic_diagnostics = assign_topic_families(corpus, taxonomy)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(".tmp.parquet")
    assignments.to_parquet(temporary, index=False)
    temporary.replace(args.output)

    manifest = {
        "schema_version": 2,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "construct": taxonomy["construct"],
        "inputs": {
            str(args.input.relative_to(ROOT)): sha256_file(args.input),
            str(args.taxonomy.relative_to(ROOT)): sha256_file(args.taxonomy),
        },
        "output": str(args.output.relative_to(ROOT)),
        "output_sha256": sha256_file(args.output),
        "rows": len(assignments),
        "primary_topic_counts": Counter(assignments["topic_family_primary"]),
        "confidence_counts": Counter(assignments["topic_assignment_confidence"]),
        "method_counts": Counter(assignments["topic_assignment_method"]),
        "semantic_representation": semantic_diagnostics,
        "assignment_parameters": taxonomy["assignment"],
        "market_outcomes_used": False,
        "status": "candidate topic-family assignments; human validation required before freeze",
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(manifest, indent=2, default=dict) + "\n", encoding="utf-8"
    )
    print(
        f"Assigned {len(assignments):,} records across "
        f"{assignments['topic_family_primary'].nunique():,} primary labels"
    )


if __name__ == "__main__":
    main()
