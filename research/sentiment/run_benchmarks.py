#!/usr/bin/env python3
"""Run blinded DeepSeek or FinBERT sentiment benchmarks with resumable outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from research.topic_discovery.avalai_neutralize import (
    BASE_URL,
    append_jsonl,
    json_hash,
    parse_response_json,
)
from research.topic_discovery.build_corpus import sha256_file


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "data/general_sentiment_v1_frontier_input.csv"
PROMPT = ROOT / "research/prompts/GENERAL_NEWS_DEEPSEEK_RATER_PROMPT.md"
OUTPUT_DIR = ROOT / "data"
MODEL = "deepseek-v4.1-flash"
FINBERT_MODEL = "ProsusAI/finbert"
RATING_KEYS = {"sample_id", "equity_sentiment", "label_confidence", "ambiguity_flag", "reviewer_notes"}


def validate_input(frame: pd.DataFrame) -> None:
    required = {"sample_id", "headline"}
    if not required.issubset(frame.columns):
        raise ValueError("Blinded input lacks sample_id or headline")
    if frame["sample_id"].duplicated().any() or frame[list(required)].eq("").any().any():
        raise ValueError("Blinded input has duplicate IDs or blank ID/headline")
    forbidden = {"source", "published_utc", "split", "topic_family_primary", "selective_route"}
    if forbidden.intersection(frame.columns):
        raise ValueError("Benchmark input exposes hidden metadata")


def validate_deepseek_response(payload: Any, expected: list[str]) -> list[dict[str, str]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise ValueError("Response must contain an items array")
    items = payload["items"]
    if len(items) != len(expected):
        raise ValueError("Response item count differs from request")
    result = []
    for item, sample_id in zip(items, expected):
        if not isinstance(item, dict) or set(item) != RATING_KEYS:
            raise ValueError("Response item schema is invalid")
        if item["sample_id"] != sample_id:
            raise ValueError("Response IDs or order differ from request")
        if item["equity_sentiment"] not in set("ABCDEU"):
            raise ValueError("Invalid sentiment code")
        if item["label_confidence"] not in {"H", "M", "L"}:
            raise ValueError("Invalid confidence code")
        if item["ambiguity_flag"] not in {"Y", "N"}:
            raise ValueError("Invalid ambiguity code")
        if not isinstance(item["reviewer_notes"], str):
            raise ValueError("Reviewer note must be a string")
        result.append({key: str(item[key]) for key in RATING_KEYS})
    return result


def completed_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    seen = set()
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            sample_id = json.loads(line)["sample_id"]
            if sample_id in seen:
                raise ValueError(f"Duplicate completed sample ID: {sample_id}")
            seen.add(sample_id)
    return seen


def validate_resume(audit_path: Path, output_path: Path, input_hash: str, model: str, prompt_hash: str | None) -> None:
    if not output_path.exists():
        return
    if not audit_path.exists():
        raise ValueError("Existing output lacks an audit log")
    with audit_path.open(encoding="utf-8") as handle:
        audits = [json.loads(line) for line in handle if line.strip()]
    if not audits:
        raise ValueError("Existing output has an empty audit log")
    for entry in audits:
        if entry["input_sha256"] != input_hash or entry["model"] != model:
            raise ValueError("Existing output was made with another input or model")
        if prompt_hash is not None and entry["prompt_sha256"] != prompt_hash:
            raise ValueError("Existing output was made with another prompt")


def request_deepseek(client: Any, model: str, prompt: str, batch: list[dict[str, str]], retries: int) -> tuple[list[dict[str, str]], str]:
    expected = [item["sample_id"] for item in batch]
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=0,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": json.dumps({"items": batch}, ensure_ascii=False)},
                ],
            )
            raw = response.choices[0].message.content or ""
            return validate_deepseek_response(parse_response_json(raw), expected), raw
        except Exception as error:
            last_error = error
            if attempt + 1 < retries:
                time.sleep(2**attempt)
    raise RuntimeError(f"DeepSeek batch failed after {retries} attempts: {last_error}")


def run_deepseek(args: argparse.Namespace, pending: pd.DataFrame, input_hash: str) -> None:
    prompt = args.prompt.read_text(encoding="utf-8")
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    validate_resume(args.audit, args.output, input_hash, args.model, prompt_hash)
    if not args.live or pending.empty:
        return
    from dotenv import load_dotenv
    from openai import OpenAI

    load_dotenv(ROOT / ".env")
    token = os.getenv("AVALAI_TOKEN") or os.getenv("AVALAI_API_KEY")
    if not token:
        raise RuntimeError("AVALAI_TOKEN or AVALAI_API_KEY is required for --live")
    client = OpenAI(api_key=token, base_url=BASE_URL)
    rows = pending[["sample_id", "headline"]].to_dict("records")
    for offset in range(0, len(rows), args.batch_size):
        batch = rows[offset : offset + args.batch_size]
        started = datetime.now(timezone.utc).isoformat()
        items, raw = request_deepseek(client, args.model, prompt, batch, args.retries)
        append_jsonl(args.audit, [{
            "started_at_utc": started,
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "model": args.model,
            "base_url": BASE_URL,
            "temperature": 0,
            "prompt_sha256": prompt_hash,
            "input_sha256": input_hash,
            "request_sha256": json_hash({"items": batch}),
            "sample_ids": [item["sample_id"] for item in batch],
            "raw_response": raw,
            "raw_response_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
            "status": "ok",
        }])
        append_jsonl(args.output, items)
        print(f"DeepSeek completed {offset + len(batch)}/{len(rows)}", flush=True)


def finbert_rows(batch: list[dict[str, str]], classifier: Any) -> list[dict[str, Any]]:
    predictions = classifier([item["headline"] for item in batch], top_k=None, truncation=True)
    result = []
    for item, scores in zip(batch, predictions):
        by_label = {entry["label"].lower(): float(entry["score"]) for entry in scores}
        if set(by_label) != {"positive", "neutral", "negative"}:
            raise ValueError(f"Unexpected FinBERT labels: {sorted(by_label)}")
        if not math.isclose(sum(by_label.values()), 1.0, abs_tol=1e-4):
            raise ValueError("FinBERT probabilities do not sum to one")
        result.append({
            "sample_id": item["sample_id"],
            "p_positive": by_label["positive"],
            "p_neutral": by_label["neutral"],
            "p_negative": by_label["negative"],
            "expected_tone": by_label["positive"] - by_label["negative"],
            "tone_entropy": -sum(value * math.log(value) for value in by_label.values() if value > 0),
        })
    if len(result) != len(batch):
        raise ValueError("FinBERT output count differs from request")
    return result


def run_finbert(args: argparse.Namespace, pending: pd.DataFrame, input_hash: str) -> None:
    validate_resume(args.audit, args.output, input_hash, args.model, None)
    if not args.live or pending.empty:
        return
    from transformers import pipeline

    classifier = pipeline("text-classification", model=args.model, tokenizer=args.model, device=-1)
    rows = pending[["sample_id", "headline"]].to_dict("records")
    for offset in range(0, len(rows), args.batch_size):
        batch = rows[offset : offset + args.batch_size]
        outputs = finbert_rows(batch, classifier)
        append_jsonl(args.audit, [{
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "model": args.model,
            "model_revision": getattr(classifier.model.config, "_commit_hash", None),
            "transformers_version": __import__("transformers").__version__,
            "input_sha256": input_hash,
            "sample_ids": [item["sample_id"] for item in batch],
            "request_sha256": json_hash({"items": batch}),
            "status": "ok",
        }])
        append_jsonl(args.output, outputs)
        print(f"FinBERT completed {offset + len(batch)}/{len(rows)}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backend", choices=["deepseek", "finbert"])
    parser.add_argument("--input", type=Path, default=INPUT)
    parser.add_argument("--prompt", type=Path, default=PROMPT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--audit", type=Path)
    parser.add_argument("--model")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    if args.batch_size < 1 or args.retries < 1 or (args.limit is not None and args.limit < 1):
        raise ValueError("Batch size, retries, and limit must be positive")
    args.model = args.model or (MODEL if args.backend == "deepseek" else FINBERT_MODEL)
    args.output = args.output or OUTPUT_DIR / f"general_sentiment_v1_{args.backend}.jsonl"
    args.audit = args.audit or OUTPUT_DIR / f"general_sentiment_v1_{args.backend}_audit.jsonl"
    frame = pd.read_csv(args.input, dtype=str, keep_default_na=False)
    validate_input(frame)
    done = completed_ids(args.output)
    if done - set(frame["sample_id"]):
        raise ValueError("Existing output includes IDs outside the current input")
    pending = frame.loc[~frame["sample_id"].isin(done)]
    if args.limit is not None:
        pending = pending.head(args.limit)
    print(json.dumps({
        "backend": args.backend, "model": args.model,
        "input_sha256": sha256_file(args.input), "rows": len(frame),
        "completed": len(done), "pending_this_run": len(pending),
        "live": args.live, "output": str(args.output), "audit": str(args.audit),
    }, indent=2))
    if args.backend == "deepseek":
        run_deepseek(args, pending, sha256_file(args.input))
    else:
        run_finbert(args, pending, sha256_file(args.input))


if __name__ == "__main__":
    main()
