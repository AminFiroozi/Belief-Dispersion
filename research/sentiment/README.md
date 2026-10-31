# General-News Sentiment Validation v1

This package measures a headline's implied near-term direction for the
S&P 500/SPY under the rubric in `GENERAL_NEWS_RATER_GUIDE.md`. The reference
asset remains provisional; a different asset requires a new validation rubric
and labels.

## Files

- `data/general_sentiment_v1_rater_1.csv` and `..._rater_2.csv`: independent,
  differently ordered blank human sheets.
- `data/general_sentiment_v1_frontier_input.csv`: separate blank sheet for a
  fresh frontier-model session.
- `data/general_sentiment_v1_key.csv`: local hidden key with record IDs,
  source, date, topic route, and development/holdout split. Never send to raters.
- `artifacts/general_sentiment_v1_sample_manifest.json`: sample design, route
  counts, hashes, and blinding record.
- `research/prompts/GENERAL_NEWS_DEEPSEEK_RATER_PROMPT.md`: machine rubric.
- `research/prompts/FRONTIER_GENERAL_NEWS_RATER_PROMPT.md`: fresh-session handoff.

The 240 rows comprise 80 from each route: accepted substantive topic,
substantive topic awaiting review, and retained `other_unclear`. Each route has
40 development and 40 holdout records. Sampling uses topic, year, and origin
strata, excludes the prior 180-headline topic audit, and selects unique
duplicate groups. The split and strata are hidden from raters. The design is
deliberately balanced for measurement; its class or source proportions are not
estimates of the full news population.

## Human Rating

Give each human rater only their own blank sheet and the guide. Do not send the
hidden key, the other rater's sheet, existing sentiment labels, model responses,
or market outcomes. Keep IDs and headlines unchanged. After both sheets are
complete, checksum them, measure agreement before adjudication, then open the
key. Keep the holdout split sealed until prompts and model choice are fixed.

Validate each completed file against its original blank sheet before analysis:

```bash
/home/hamid/.pyenv/versions/fnlp/bin/python -m research.sentiment.validate_ratings COMPLETED.csv ORIGINAL_BLANK.csv
```

The generator refuses to overwrite an edited sheet.

The FOMC 150-headline audit remains separate. It tests a narrower event sample
with an FOMC relevance field and cannot substitute for this broad-news audit.

## Benchmark Runs

All commands are previews by default:

```bash
/home/hamid/.pyenv/versions/fnlp/bin/python -m research.sentiment.build_validation_sample
/home/hamid/.pyenv/versions/fnlp/bin/python -m research.sentiment.run_benchmarks deepseek --limit 8
/home/hamid/.pyenv/versions/fnlp/bin/python -m research.sentiment.run_benchmarks finbert --limit 8
```

Pass `--live` to run a bounded batch. DeepSeek uses `AVALAI_TOKEN` (or
`AVALAI_API_KEY`) from `.env`, the persisted prompt, temperature zero, and an
append-only raw-response audit. FinBERT uses `ProsusAI/finbert`, records its
resolved model revision, and outputs all three class probabilities, their
positive-minus-negative expected tone, and entropy. The benchmark is textual
financial sentiment, so those probabilities are not calibrated probabilities
of A-E market implication. Both runners resume from completed sample IDs.

A two-headline DeepSeek smoke test completed on 2026-10-30 and wrote valid
ratings plus a raw-response audit log. These two machine ratings are a software
check only; no human comparison or model-quality claim follows from them.
The FinBERT transformation has unit coverage, but a live checkpoint test is
pending: the public model download was interrupted before inference completed.

The default outputs and audit logs are local ignored JSONL files in `data/`.
The manifest hashes define the frozen input package.

## Model Decision

DeepSeek is the candidate scalable instrument; FinBERT and a fresh frontier
session are benchmarks. Human agreement and adjudication define the reference.
Evaluate exact and adjacent A-E agreement, weighted kappa, class confusion,
`U` rates, coverage, stability, and failures on development data. Fix prompts
and model choice before viewing holdout outcomes. No market price, return,
volatility, or volume data enters this measurement stage.

The FinBERT checkpoint's [model card](https://huggingface.co/ProsusAI/finbert)
documents its positive, negative, and neutral outputs and Financial PhraseBank
training target.
