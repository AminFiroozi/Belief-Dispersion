#!/usr/bin/env python3
"""Optionally create topic-neutral representations with AvalAI DeepSeek."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

try:
    from json_repair import repair_json
except ImportError:  # Strict JSON remains the default and requires no extra package.
    repair_json = None


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "data/topic_discovery_corpus.parquet"
DEFAULT_OUTPUT = ROOT / "data/topic_neutral_llm.jsonl"
DEFAULT_AUDIT = ROOT / "data/topic_neutral_llm_audit.jsonl"
DEFAULT_PROMPT = ROOT / "research/prompts/TOPIC_NEUTRALIZATION_PROMPT.md"
BASE_URL = "https://api.avalai.ir/v1"
DEFAULT_MODEL = "deepseek-v4.1-flash"
REQUIRED_KEYS = {"record_id", "topic_neutral_text", "entities", "event_terms"}


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def json_hash(value: Any) -> str:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def load_existing(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    rows: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                rows[row["record_id"]] = row
    return rows


def validate_items(
    payload: Any, expected: dict[str, str]
) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise ValueError("Response must be an object containing an items array")
    items = payload["items"]
    if len(items) != len(expected):
        raise ValueError("Response item count does not match request")
    validated: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict) or set(item) != REQUIRED_KEYS:
            raise ValueError("Response item has an invalid schema")
        record_id = str(item["record_id"])
        if record_id not in expected or record_id in seen:
            raise ValueError("Response contains an unknown or duplicate record ID")
        neutral = " ".join(str(item["topic_neutral_text"]).split())
        entities = item["entities"]
        event_terms = item["event_terms"]
        if not neutral or not isinstance(entities, list) or not isinstance(event_terms, list):
            raise ValueError("Response contains blank text or non-list annotations")
        validated.append(
            {
                "record_id": record_id,
                "headline": expected[record_id],
                "topic_neutral_text": neutral,
                "entities": [str(value).strip() for value in entities if str(value).strip()],
                "event_terms": [
                    str(value).strip() for value in event_terms if str(value).strip()
                ],
            }
        )
        seen.add(record_id)
    return sorted(validated, key=lambda item: list(expected).index(item["record_id"]))


def parse_response_json(content: str) -> Any:
    cleaned = content.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    try:
        return json.loads(cleaned.strip())
    except json.JSONDecodeError:
        if repair_json is None:
            raise
        return repair_json(content, return_objects=True)


def request_batch(
    client: OpenAI,
    model: str,
    prompt: str,
    batch: list[dict[str, str]],
    retries: int,
) -> tuple[list[dict[str, Any]], str]:
    expected = {item["record_id"]: item["headline"] for item in batch}
    user_payload = json.dumps({"items": batch}, ensure_ascii=False)
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=0,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_payload},
                ],
            )
            content = response.choices[0].message.content or ""
            parsed = parse_response_json(content)
            return validate_items(parsed, expected), content
        except Exception as error:  # Provider errors vary across OpenAI-compatible routes.
            last_error = error
            if attempt + 1 < retries:
                time.sleep(2**attempt)
    raise RuntimeError(f"AvalAI batch failed after {retries} attempts: {type(last_error).__name__}")


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--live", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_dotenv(ROOT / ".env")
    prompt = args.prompt.read_text(encoding="utf-8")
    corpus = pd.read_parquet(args.input, columns=["record_id", "headline"])
    corpus = corpus.sort_values("record_id")
    existing = load_existing(args.output)
    pending = corpus.loc[~corpus["record_id"].isin(existing)].copy()
    if args.limit is not None:
        pending = pending.head(args.limit)
    print(
        json.dumps(
            {
                "provider": "AvalAI",
                "base_url": BASE_URL,
                "model": args.model,
                "prompt_sha256": prompt_hash(prompt),
                "input_rows": len(corpus),
                "completed_rows": len(existing),
                "pending_this_run": len(pending),
                "live": args.live,
            },
            indent=2,
        )
    )
    if not args.live or pending.empty:
        return

    token = os.getenv("AVALAI_TOKEN") or os.getenv("AVALAI_API_KEY")
    if not token:
        raise RuntimeError("Set AVALAI_TOKEN or AVALAI_API_KEY before a live run")
    client = OpenAI(api_key=token, base_url=BASE_URL)
    rows = pending[["record_id", "headline"]].to_dict("records")
    for offset in range(0, len(rows), args.batch_size):
        batch = rows[offset : offset + args.batch_size]
        started = datetime.now(timezone.utc).isoformat()
        items, raw = request_batch(client, args.model, prompt, batch, args.retries)
        append_jsonl(args.output, items)
        append_jsonl(
            args.audit,
            [
                {
                    "started_at_utc": started,
                    "completed_at_utc": datetime.now(timezone.utc).isoformat(),
                    "provider": "AvalAI",
                    "base_url": BASE_URL,
                    "model": args.model,
                    "temperature": 0,
                    "prompt_sha256": prompt_hash(prompt),
                    "request_sha256": json_hash({"items": batch}),
                    "record_ids": [item["record_id"] for item in batch],
                    "parsed_item_count": len(items),
                    "raw_response_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
                    "raw_response": raw,
                    "status": "ok",
                }
            ],
        )
        print(f"Completed {min(offset + len(batch), len(rows))}/{len(rows)}", flush=True)


if __name__ == "__main__":
    main()
