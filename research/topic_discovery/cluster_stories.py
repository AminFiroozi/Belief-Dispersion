#!/usr/bin/env python3
"""Create an outcome-blind pilot of chronological, topic-constrained story clusters."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import Normalizer

from research.topic_discovery.build_corpus import load_taxonomy, sha256_file, stable_id


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
DEFAULT_CORPUS = ROOT / "data/topic_discovery_corpus.parquet"
DEFAULT_TAXONOMY = HERE / "taxonomy.json"
DEFAULT_ASSIGNMENTS = ROOT / "data/topic_discovery_pilot_assignments.csv"
DEFAULT_AUDIT = ROOT / "data/topic_discovery_pair_audit.csv"
DEFAULT_KEY = ROOT / "data/topic_discovery_pair_key.csv"
DEFAULT_MANIFEST = HERE / "artifacts/topic_discovery_pilot_manifest.json"


def stable_hash(*values: str) -> str:
    return hashlib.sha256("|".join(map(str, values)).encode("utf-8")).hexdigest()


def stratified_sample(frame: pd.DataFrame, sample_size: int) -> pd.DataFrame:
    if sample_size >= len(frame):
        return frame.copy()
    working = frame.copy()
    working["sample_hash"] = working["record_id"].map(
        lambda value: stable_hash("topic-discovery-pilot-v1", value)
    )
    strata = ["origin", "year", "primary_topic"]
    counts = working.groupby(strata, dropna=False).size().rename("count").reset_index()
    counts["quota"] = np.floor(sample_size * counts["count"] / len(working)).astype(int)
    counts.loc[(counts["count"] > 0) & (counts["quota"] == 0), "quota"] = 1
    counts["quota"] = counts[["quota", "count"]].min(axis=1)

    while int(counts["quota"].sum()) > sample_size:
        candidates = counts.loc[counts["quota"] > 1].copy()
        if candidates.empty:
            break
        index = candidates.sort_values(["quota", "count"], ascending=False).index[0]
        counts.loc[index, "quota"] -= 1
    while int(counts["quota"].sum()) < sample_size:
        candidates = counts.loc[counts["quota"] < counts["count"]].copy()
        if candidates.empty:
            break
        candidates["shortfall"] = (
            sample_size * candidates["count"] / len(working) - candidates["quota"]
        )
        index = candidates.sort_values(["shortfall", "count"], ascending=False).index[0]
        counts.loc[index, "quota"] += 1

    quotas = counts.set_index(strata)["quota"].to_dict()
    selected: list[pd.DataFrame] = []
    for key, group in working.groupby(strata, dropna=False, sort=True):
        selected.append(group.sort_values("sample_hash").head(int(quotas[key])))
    result = pd.concat(selected, ignore_index=True).drop(columns="sample_hash")
    if len(result) != sample_size:
        raise AssertionError(f"Expected {sample_size} pilot rows, got {len(result)}")
    return result.sort_values(["published_utc", "record_id"]).reset_index(drop=True)


def build_embeddings(texts: pd.Series, dimensions: int) -> tuple[np.ndarray, dict[str, Any]]:
    vectorizer = TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        stop_words="english",
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.97,
        sublinear_tf=True,
        max_features=50_000,
    )
    matrix = vectorizer.fit_transform(texts.fillna("").astype(str))
    maximum_dimensions = min(matrix.shape[0] - 1, matrix.shape[1] - 1)
    selected_dimensions = max(2, min(dimensions, maximum_dimensions))
    reducer = TruncatedSVD(n_components=selected_dimensions, random_state=1729)
    dense = reducer.fit_transform(matrix)
    dense = Normalizer(copy=False).fit_transform(dense).astype(np.float32)
    diagnostics = {
        "backend": "tfidf-bigram-truncated-svd",
        "vocabulary_size": len(vectorizer.vocabulary_),
        "dimensions": selected_dimensions,
        "explained_variance_ratio": round(float(reducer.explained_variance_ratio_.sum()), 6),
    }
    return dense, diagnostics


def compile_entities(taxonomy: dict[str, Any]) -> list[tuple[str, re.Pattern[str]]]:
    return [
        (entity, re.compile(rf"\b{re.escape(entity)}\b", flags=re.IGNORECASE))
        for entity in taxonomy.get("known_entities", [])
    ]


def extract_entities(headline: str, patterns: list[tuple[str, re.Pattern[str]]]) -> set[str]:
    entities = {entity.casefold() for entity, pattern in patterns if pattern.search(headline)}
    entities.update(token.casefold() for token in re.findall(r"\b[A-Z]{2,8}\b", headline))
    return entities


def entity_jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


@dataclass
class StoryCluster:
    cluster_id: str
    topic: str
    first_date: date
    last_date: date
    vector_sum: np.ndarray
    size: int = 1
    entities: set[str] = field(default_factory=set)
    record_ids: list[str] = field(default_factory=list)

    def centroid(self) -> np.ndarray:
        value = self.vector_sum / self.size
        norm = float(np.linalg.norm(value))
        return value / norm if norm else value


def cluster_online(
    frame: pd.DataFrame,
    embeddings: np.ndarray,
    taxonomy: dict[str, Any],
) -> pd.DataFrame:
    config = taxonomy["clustering"]
    max_gap = int(config["max_gap_days"])
    half_life = float(config["time_half_life_days"])
    semantic_weight = float(config["semantic_weight"])
    entity_weight = float(config["entity_weight"])
    time_weight = float(config["time_weight"])
    threshold = float(config["assignment_threshold"])
    entity_patterns = compile_entities(taxonomy)

    clusters: dict[str, StoryCluster] = {}
    by_topic: dict[str, list[str]] = {}
    assignments: list[dict[str, Any]] = []
    for position, row in frame.reset_index(drop=True).iterrows():
        topic = row["primary_topic"]
        current_date = pd.Timestamp(row["published_utc"]).date()
        entities = extract_entities(row["headline"], entity_patterns)
        vector = embeddings[position]
        best: tuple[float, float, float, str] | None = None

        for cluster_id in by_topic.get(topic, []):
            cluster = clusters[cluster_id]
            gap = (current_date - cluster.last_date).days
            if gap < 0 or gap > max_gap:
                continue
            semantic = float(np.dot(vector, cluster.centroid()))
            entity_score = entity_jaccard(entities, cluster.entities)
            time_score = math.exp(-gap / half_life)
            combined = (
                semantic_weight * semantic
                + entity_weight * entity_score
                + time_weight * time_score
            )
            candidate = (combined, semantic, entity_score, cluster_id)
            if best is None or candidate > best:
                best = candidate

        if best is not None and best[0] >= threshold:
            combined, semantic, entity_score, cluster_id = best
            cluster = clusters[cluster_id]
            cluster.vector_sum = cluster.vector_sum + vector
            cluster.size += 1
            cluster.last_date = current_date
            cluster.entities.update(entities)
            cluster.record_ids.append(row["record_id"])
            assignment_type = "existing"
        else:
            cluster_id = f"STORY-{stable_id(topic, row['record_id'], length=16)}"
            clusters[cluster_id] = StoryCluster(
                cluster_id=cluster_id,
                topic=topic,
                first_date=current_date,
                last_date=current_date,
                vector_sum=vector.copy(),
                entities=set(entities),
                record_ids=[row["record_id"]],
            )
            by_topic.setdefault(topic, []).append(cluster_id)
            combined = best[0] if best else np.nan
            semantic = best[1] if best else np.nan
            entity_score = best[2] if best else np.nan
            assignment_type = "new"

        assignments.append(
            {
                "record_id": row["record_id"],
                "story_cluster_id": cluster_id,
                "assignment_type": assignment_type,
                "best_combined_score": combined,
                "best_semantic_score": semantic,
                "best_entity_score": entity_score,
                "entities": "|".join(sorted(entities)),
            }
        )

    assignment_frame = pd.DataFrame(assignments)
    result = frame.merge(assignment_frame, on="record_id", validate="one_to_one")
    sizes = result.groupby("story_cluster_id").size()
    result["story_cluster_size"] = result["story_cluster_id"].map(sizes).astype(int)
    return result.sort_values(["published_utc", "record_id"]).reset_index(drop=True)


def pair_id(kind: str, left: str, right: str) -> str:
    first, second = sorted((left, right))
    return f"PAIR-{stable_id(kind, first, second, length=16)}"


def make_pair_audit(
    assignments: pd.DataFrame, sample_size: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    candidates: list[dict[str, Any]] = []

    for cluster_id, group in assignments.groupby("story_cluster_id"):
        if len(group) < 2:
            continue
        rows = group.sort_values("record_id").to_dict("records")
        pairs = list(combinations(rows, 2))
        pairs.sort(
            key=lambda pair: (
                pair[0]["source"] == pair[1]["source"],
                stable_hash("positive", pair[0]["record_id"], pair[1]["record_id"]),
            )
        )
        left, right = pairs[0]
        candidates.append(
            {
                "kind": "same_cluster",
                "record_a": left,
                "record_b": right,
                "cluster_a": cluster_id,
                "cluster_b": cluster_id,
            }
        )

    ordered = assignments.sort_values(["primary_topic", "published_utc", "record_id"])
    for _, group in ordered.groupby("primary_topic", sort=True):
        rows = group.to_dict("records")
        for index, left in enumerate(rows):
            for right in rows[index + 1 : index + 6]:
                delta = abs(
                    (pd.Timestamp(right["published_utc"]) - pd.Timestamp(left["published_utc"])).days
                )
                if delta <= 7 and left["story_cluster_id"] != right["story_cluster_id"]:
                    candidates.append(
                        {
                            "kind": "same_topic_different_cluster",
                            "record_a": left,
                            "record_b": right,
                            "cluster_a": left["story_cluster_id"],
                            "cluster_b": right["story_cluster_id"],
                        }
                    )

    candidates.sort(
        key=lambda item: stable_hash(
            "pair-audit-v1",
            item["kind"],
            item["record_a"]["record_id"],
            item["record_b"]["record_id"],
        )
    )
    positive_target = sample_size // 2
    positives = [item for item in candidates if item["kind"] == "same_cluster"][:positive_target]
    negatives = [item for item in candidates if item["kind"] != "same_cluster"][
        : sample_size - len(positives)
    ]
    selected = positives + negatives
    selected.sort(
        key=lambda item: stable_hash(
            "pair-display-v1", item["record_a"]["record_id"], item["record_b"]["record_id"]
        )
    )

    audit_rows: list[dict[str, Any]] = []
    key_rows: list[dict[str, Any]] = []
    for item in selected:
        left, right = item["record_a"], item["record_b"]
        identifier = pair_id(item["kind"], left["record_id"], right["record_id"])
        audit_rows.append(
            {
                "pair_id": identifier,
                "headline_a": left["headline"],
                "headline_b": right["headline"],
                "same_story": "",
                "confidence": "",
                "reviewer_notes": "",
            }
        )
        key_rows.append(
            {
                "pair_id": identifier,
                "pair_kind": item["kind"],
                "record_id_a": left["record_id"],
                "record_id_b": right["record_id"],
                "topic_a": left["primary_topic"],
                "topic_b": right["primary_topic"],
                "cluster_a": item["cluster_a"],
                "cluster_b": item["cluster_b"],
                "published_utc_a": left["published_utc"],
                "published_utc_b": right["published_utc"],
                "source_a": left["source"],
                "source_b": right["source"],
            }
        )
    return pd.DataFrame(audit_rows), pd.DataFrame(key_rows)


def write_csv_atomic(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY)
    parser.add_argument("--assignments", type=Path, default=DEFAULT_ASSIGNMENTS)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--key", type=Path, default=DEFAULT_KEY)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--sample-size", type=int, default=5000)
    parser.add_argument("--audit-pairs", type=int, default=200)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    taxonomy = load_taxonomy(args.taxonomy)
    corpus = pd.read_parquet(args.corpus)
    pilot = stratified_sample(corpus, args.sample_size)
    embeddings, embedding_diagnostics = build_embeddings(
        pilot["neutral_text_baseline"], int(taxonomy["clustering"]["svd_dimensions"])
    )
    assignments = cluster_online(pilot, embeddings, taxonomy)
    audit, key = make_pair_audit(assignments, args.audit_pairs)
    write_csv_atomic(assignments, args.assignments)
    write_csv_atomic(audit, args.audit)
    write_csv_atomic(key, args.key)

    cluster_sizes = assignments.groupby("story_cluster_id").size()
    manifest = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "sample_size": len(assignments),
        "sample_rule": "deterministic stratification by origin, year, and primary topic",
        "embedding": embedding_diagnostics,
        "clustering": taxonomy["clustering"],
        "clusters": int(cluster_sizes.size),
        "singletons": int((cluster_sizes == 1).sum()),
        "multi_item_clusters": int((cluster_sizes > 1).sum()),
        "maximum_cluster_size": int(cluster_sizes.max()),
        "median_cluster_size": float(cluster_sizes.median()),
        "audit_pairs": len(audit),
        "audit_same_cluster_pairs": int((key["pair_kind"] == "same_cluster").sum()),
        "audit_different_cluster_pairs": int(
            (key["pair_kind"] == "same_topic_different_cluster").sum()
        ),
        "outputs": {
            "assignments": {
                "path": str(args.assignments.relative_to(ROOT)),
                "sha256": sha256_file(args.assignments),
            },
            "audit": {
                "path": str(args.audit.relative_to(ROOT)),
                "sha256": sha256_file(args.audit),
            },
            "hidden_key": {
                "path": str(args.key.relative_to(ROOT)),
                "sha256": sha256_file(args.key),
            },
        },
        "status": "pilot only; thresholds require blinded pair validation",
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        f"Clustered {len(assignments):,} pilot headlines into {cluster_sizes.size:,} stories; "
        f"wrote {len(audit)} blinded audit pairs"
    )


if __name__ == "__main__":
    main()
