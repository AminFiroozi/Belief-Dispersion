# Phase 3a LLM Validation Notebook Design

## Goal

Create a Jupyter notebook that independently labels the 150 blinded FOMC
validation headlines with the frozen Phase 3a rubric and writes a validated LLM
label file without modifying either human rater file.

## Scope

The notebook labels each row using only `sample_id` and `headline`. It does not
read or expose the hidden provenance key, event metadata, dates, sources,
market data, existing model labels, or downstream outcomes. It produces an
LLM comparison dataset for the two human audits; it does not adjudicate human
disagreements or select a model based on market results.

## Architecture

The notebook has a small configuration section followed by cells for loading,
prompt construction, provider dispatch, response validation, resumable
execution, output writing, and audit checks. Gemini and Groq share the same
labeling interface and prompt. A `LLM` setting selects the provider; provider
specific model names and API keys come from configuration and `.env` variables,
following the mechanism already used in `main.ipynb`.

Each headline is submitted in its own request. The request uses temperature
zero and asks for exactly one JSON object. The response is parsed, repaired only
when necessary using the project’s existing `json_repair` dependency, and
rejected unless every field conforms to the rubric.

## Inputs and outputs

Input:

`data/fomc_phase3_validation_rater_1.csv`

The notebook checks for the expected columns and uses the rows as the canonical
150-headline sample. It may read the rater 2 file only for a non-labeling ID
integrity check if explicitly enabled; the default labeling path does not need
it.

Default output:

`data/fomc_phase3_validation_llm.csv`

The output preserves the input row order and columns, filling the five rubric
fields and retaining `reviewer_notes` for the model’s concise rationale. Human
rater files are never written by the notebook. An optional output path may be
configured for a second provider/model run.

The notebook also writes:

- a JSONL audit log containing request status, provider/model, timestamps,
  response text, parsed labels, and error information;
- a run metadata JSON file containing prompt version, configuration, input and
  output SHA-256 hashes, row counts, and validation summaries.

These artifacts are intended for reproducibility and must not contain hidden
event/source metadata.

## Prompt and labeling protocol

The system/instruction text reproduces the frozen `PHASE3_LABELING_RUBRIC.md`:

1. Determine topic relevance first: `R`, `I`, or `U`.
2. Assign equity implication only for `R`; use blank for `I` and `U` unless
   the implication is unambiguous for `U`, consistent with the rubric.
3. Assign confidence: `H`, `M`, or `L`.
4. Assign ambiguity: `Y` or `N`.
5. Keep notes short and grounded only in the headline.

The prompt explicitly prohibits web search, article lookup, date/source
inference, market-outcome knowledge, and use of any information beyond the
headline. The row payload includes the random ID and headline only. The model
must return a single object with the exact output keys and permitted codes.

## Execution and recovery

The notebook defaults to a dry-run preview of the first prompt and a separate
explicit execution cell. Execution is row-level and resumable:

- Existing valid rows in the configured output can be retained by `sample_id`.
- Failed or invalid rows remain blank and are retried on rerun.
- Retries use bounded exponential backoff and the same provider/model unless
  the user changes configuration.
- A configurable delay protects provider rate limits.
- The notebook refuses to overwrite a non-empty output unless an explicit
  overwrite flag is enabled.

Provider dispatch follows `main.ipynb`: Gemini uses
`google.generativeai.GenerativeModel` with JSON response configuration; Groq
uses `Groq().chat.completions.create`. Both use temperature zero. The notebook
will expose provider-specific model settings and validate required API keys
before making calls.

## Validation and safety checks

Before writing, the notebook verifies:

- exactly 150 input rows and unique `sample_id` values;
- expected input schema and unchanged `sample_id`/`headline` values;
- all five label fields use only permitted values;
- `equity_sentiment` is blank for `I`, and relevance/sentiment consistency is
  reported for `U` cases according to the rubric;
- every output row is present exactly once and remains in canonical order;
- no hidden-key columns were introduced;
- the output is written atomically through a temporary file replacement;
- the input and output hashes and run counts are recorded.

The notebook reports missing, invalid, and retried rows clearly. It does not
silently coerce invalid model output into a label.

## Testing strategy

The notebook includes local, API-free checks for prompt payload blinding,
response parsing, label validation, resume behavior, row-order preservation,
and output schema. A dry-run cell exercises these checks and displays one
redacted prompt preview. A live run is optional and requires the selected
provider key; after a live run, the final validation cell must pass before the
output is considered usable.

## Non-goals

- Filling either human rater file.
- Opening or using the hidden provenance key.
- Human-label agreement calculations or adjudication.
- Downstream market analysis.
- Choosing a provider/model from market outcomes.
- Adding multidimensional sentiment labels beyond the frozen rubric.

