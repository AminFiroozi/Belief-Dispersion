#!/usr/bin/env python3
"""Build the outcome-blind canonical corpus used for topic discovery."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
DEFAULT_TAXONOMY = HERE / "taxonomy.json"
DEFAULT_NEWS = ROOT / "news.csv"
DEFAULT_GEOPOLITICAL = ROOT / "data/geopolitical_news_google.jsonl"
DEFAULT_OUTPUT = ROOT / "data/topic_discovery_corpus.parquet"
DEFAULT_MANIFEST = HERE / "artifacts/canonical_corpus_manifest.json"

SOURCE_ALIASES = {
    "nytimes": "The New York Times",
    "the new york times": "The New York Times",
    "guardian": "The Guardian",
    "the guardian": "The Guardian",
    "associated press": "AP News",
    "ap news": "AP News",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_text(value: str) -> str:
    return " ".join(
        "".join(character.casefold() if character.isalnum() else " " for character in str(value)).split()
    )


def normalize_source(value: str) -> str:
    cleaned = " ".join(str(value).strip().split())
    return SOURCE_ALIASES.get(cleaned.casefold(), cleaned or "Unknown")


def stable_id(*values: str, length: int = 20) -> str:
    payload = "|".join(str(value) for value in values)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]


def load_taxonomy(path: Path) -> dict[str, Any]:
    taxonomy = json.loads(path.read_text(encoding="utf-8"))
    required = {"topics", "candidate_topic_map", "topic_priority", "neutral_replacements", "clustering"}
    missing = required.difference(taxonomy)
    if missing:
        raise ValueError(f"Taxonomy lacks required fields: {sorted(missing)}")
    unknown = set(taxonomy["topic_priority"]).difference(taxonomy["topics"])
    if unknown:
        raise ValueError(f"Topic priority contains unknown topics: {sorted(unknown)}")
    return taxonomy


def deterministic_neutral_text(headline: str, replacements: dict[str, str]) -> str:
    text = " ".join(str(headline).split())
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return " ".join(text.split())


def assign_topics(
    headline: str,
    candidate_topics: str,
    taxonomy: dict[str, Any],
) -> tuple[str, str, str]:
    scores: dict[str, int] = {}
    matched_rules: list[str] = []
    for topic, patterns in taxonomy["topics"].items():
        hits = [pattern for pattern in patterns if re.search(pattern, headline, flags=re.IGNORECASE)]
        if hits:
            scores[topic] = len(hits)
            matched_rules.extend(f"{topic}:{pattern}" for pattern in hits)

    for candidate in filter(None, str(candidate_topics).split("|")):
        mapped = taxonomy["candidate_topic_map"].get(candidate)
        if mapped:
            scores[mapped] = scores.get(mapped, 0) + 3
            matched_rules.append(f"candidate:{candidate}")

    if not scores:
        return "other_unclear", "other_unclear", ""
    priority = {topic: position for position, topic in enumerate(taxonomy["topic_priority"])}
    ordered = sorted(scores, key=lambda topic: (-scores[topic], priority.get(topic, 10_000), topic))
    return ordered[0], "|".join(ordered), "|".join(matched_rules)


def load_original_news(path: Path) -> pd.DataFrame:
    columns = ["headline", "url", "source", "date", "section_name"]
    frame = pd.read_csv(path, usecols=columns, low_memory=False).fillna("")
    frame["published_utc"] = pd.to_datetime(frame["date"], utc=True, errors="coerce")
    frame = frame.loc[frame["published_utc"].notna() & frame["headline"].ne("")].copy()
    frame["origin"] = "student_news"
    frame["candidate_topics"] = ""
    frame["timestamp_precision"] = "timestamp"
    frame["source_original"] = frame["source"]
    return frame[
        [
            "headline",
            "url",
            "source_original",
            "published_utc",
            "section_name",
            "origin",
            "candidate_topics",
            "timestamp_precision",
        ]
    ]


def load_geopolitical_news(path: Path) -> pd.DataFrame:
    frame = pd.read_json(path, lines=True).fillna("")
    frame["published_utc"] = pd.to_datetime(frame["published_utc"], utc=True, errors="coerce")
    frame = frame.loc[frame["published_utc"].notna() & frame["headline"].ne("")].copy()
    group_columns = ["google_news_url", "headline", "headline_key", "source", "published_utc"]
    grouped = (
        frame.groupby(group_columns, as_index=False, dropna=False)["candidate_topic"]
        .agg(lambda values: "|".join(sorted(set(filter(None, values)))))
        .rename(
            columns={
                "google_news_url": "url",
                "source": "source_original",
                "candidate_topic": "candidate_topics",
            }
        )
    )
    grouped["section_name"] = ""
    grouped["origin"] = "google_geopolitical"
    grouped["timestamp_precision"] = "date"
    return grouped[
        [
            "headline",
            "url",
            "source_original",
            "published_utc",
            "section_name",
            "origin",
            "candidate_topics",
            "timestamp_precision",
        ]
    ]


def build_corpus(
    original: pd.DataFrame,
    geopolitical: pd.DataFrame,
    taxonomy: dict[str, Any],
    sample_start: str,
    sample_end: str,
) -> pd.DataFrame:
    frame = pd.concat([original, geopolitical], ignore_index=True)
    frame["published_date"] = frame["published_utc"].dt.date.astype(str)
    frame = frame.loc[
        frame["published_date"].between(sample_start, sample_end, inclusive="both")
    ].copy()
    frame["source"] = frame["source_original"].map(normalize_source)
    frame["headline_key"] = frame["headline"].map(normalize_text)
    frame = frame.loc[frame["headline_key"].ne("")].copy()

    frame["origin_priority"] = frame["origin"].map(
        {"student_news": 0, "google_geopolitical": 1}
    ).fillna(9)
    frame = frame.sort_values(
        ["source", "published_date", "headline_key", "origin_priority", "url"]
    )
    frame = frame.drop_duplicates(["source", "published_date", "headline_key"], keep="first")
    frame["duplicate_group_id"] = frame["headline_key"].map(
        lambda value: f"DUP-{stable_id(value, length=16)}"
    )
    frame["record_id"] = frame.apply(
        lambda row: f"NEWS-{stable_id(row['origin'], row['url'], row['headline_key'], row['published_date'])}",
        axis=1,
    )

    assigned = frame.apply(
        lambda row: assign_topics(row["headline"], row["candidate_topics"], taxonomy),
        axis=1,
        result_type="expand",
    )
    assigned.columns = ["primary_topic", "broad_topics", "topic_rule_matches"]
    frame = pd.concat([frame, assigned], axis=1)
    frame["neutral_text_baseline"] = frame["headline"].map(
        lambda value: deterministic_neutral_text(value, taxonomy["neutral_replacements"])
    )
    frame["year"] = frame["published_utc"].dt.year.astype(int)
    frame = frame.sort_values(["published_utc", "record_id"]).reset_index(drop=True)
    if frame["record_id"].duplicated().any():
        raise AssertionError("Canonical record IDs are not unique")
    return frame[
        [
            "record_id",
            "headline",
            "headline_key",
            "neutral_text_baseline",
            "url",
            "source",
            "source_original",
            "published_utc",
            "published_date",
            "timestamp_precision",
            "section_name",
            "origin",
            "candidate_topics",
            "primary_topic",
            "broad_topics",
            "topic_rule_matches",
            "duplicate_group_id",
            "year",
        ]
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--news", type=Path, default=DEFAULT_NEWS)
    parser.add_argument("--geopolitical", type=Path, default=DEFAULT_GEOPOLITICAL)
    parser.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--sample-start", default="2020-05-01")
    parser.add_argument("--sample-end", default="2025-04-30")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    taxonomy = load_taxonomy(args.taxonomy)
    original = load_original_news(args.news)
    geopolitical = load_geopolitical_news(args.geopolitical)
    corpus = build_corpus(
        original, geopolitical, taxonomy, args.sample_start, args.sample_end
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(".tmp.parquet")
    corpus.to_parquet(temporary, index=False)
    temporary.replace(args.output)

    duplicate_sizes = corpus.groupby("duplicate_group_id").size()
    manifest = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "sample_start": args.sample_start,
        "sample_end": args.sample_end,
        "inputs": {
            str(args.news.relative_to(ROOT)): sha256_file(args.news),
            str(args.geopolitical.relative_to(ROOT)): sha256_file(args.geopolitical),
            str(args.taxonomy.relative_to(ROOT)): sha256_file(args.taxonomy),
        },
        "output": str(args.output.relative_to(ROOT)),
        "output_sha256": sha256_file(args.output),
        "rows": len(corpus),
        "origins": Counter(corpus["origin"]),
        "sources": int(corpus["source"].nunique()),
        "primary_topics": Counter(corpus["primary_topic"]),
        "exact_duplicate_groups_with_multiple_rows": int((duplicate_sizes > 1).sum()),
        "rows_in_multirow_exact_duplicate_groups": int(duplicate_sizes[duplicate_sizes > 1].sum()),
        "timestamp_precision": Counter(corpus["timestamp_precision"]),
        "status": "outcome-blind candidate corpus; topic rules and duplicate groups are not frozen",
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2, default=dict) + "\n", encoding="utf-8")
    print(f"Wrote {len(corpus):,} canonical records to {args.output}")


if __name__ == "__main__":
    main()
