# Phase 3a LLM Validation Notebook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a resumable Jupyter notebook that labels the blinded 150-headline Phase 3a sample with selectable Gemini/Groq backends and API-key rotation.

**Architecture:** The notebook will keep configuration, rubric prompt construction, provider dispatch, parsing/validation, resumable labeling, atomic CSV writing, and audit checks in separate cells. It will read only the blinded rater-1 input and write a separate LLM output plus audit artifacts; API rotation is provider-specific and never logs secrets.

**Tech Stack:** Jupyter notebook, Python, pandas, `google.generativeai`, `groq`, `python-dotenv`, `json_repair`, standard-library JSON/hash/time/path utilities.

---

### Task 1: Create notebook shell and configuration

**Files:**
- Create: `phase3_llm_validation.ipynb`
- Reference: `main.ipynb`, `research/event_study/PHASE3_LABELING_RUBRIC.md`

- [ ] **Step 1: Write the notebook’s local configuration checks first**

Add API-free assertions for the selected provider, paths, output schema, key-list parsing, and default output path. The checks must establish that the hidden key path is not an input and that the human rater paths are never output targets.

- [ ] **Step 2: Run the checks to verify they fail before implementation**

Execute the notebook’s test/configuration cells in a fresh kernel. Expected: the checks fail because the notebook functions/configuration do not exist yet.

- [ ] **Step 3: Implement configuration and imports**

Add `LLM = "GEMINI"` as the provider switch, configurable Gemini/Groq model names, `MAX_API_RETRIES`, `API_CALL_DELAY`, `CIRCULAR_MODEL`, input/output/audit paths, overwrite control, `.env` loading, and provider key parsing with singular-key fallback. Keep all paths relative to the repository root.

- [ ] **Step 4: Run the checks again**

Execute the setup cells. Expected: configuration checks pass, required packages import, and no API request is made.

### Task 2: Implement blinded rubric prompt and response validation

**Files:**
- Modify: `phase3_llm_validation.ipynb`
- Reference: `research/event_study/PHASE3_LABELING_RUBRIC.md`

- [ ] **Step 1: Write API-free tests for payload blinding and label rules**

Test that a prompt contains the sample ID and headline but none of `event_id`, `event_year`, `published_date`, `source`, `source_band`, `headline_key`, market fields, or hidden-key path. Test valid/invalid codes and the relevance/sentiment relationship.

- [ ] **Step 2: Run the tests and confirm the expected failure**

Execute the prompt/validation test cell in a fresh kernel. Expected: failure because prompt and validation helpers are not implemented.

- [ ] **Step 3: Implement the prompt and validators**

Use the frozen A-E rubric text and exact JSON keys: `topic_relevance`, `equity_sentiment`, `label_confidence`, `ambiguity_flag`, and `reviewer_notes`. Require headline-only reasoning, no search, no post-event knowledge, and one JSON object. Parse normal JSON first, then `json_repair` only as a fallback. Reject extra/missing keys and invalid labels without coercion.

- [ ] **Step 4: Run the tests and confirm they pass**

Expected: all payload-blinding, parsing, and code-validation checks pass.

### Task 3: Implement Gemini/Groq dispatch and API rotation

**Files:**
- Modify: `phase3_llm_validation.ipynb`
- Reference: `main.ipynb`

- [ ] **Step 1: Write API-free rotation tests**

Test deterministic key-index advancement, wraparound, retry-attempt accounting, Gemini circular model advancement after key-pool exhaustion, and redaction of key values from audit records.

- [ ] **Step 2: Run the tests and confirm the expected failure**

Expected: failure because provider dispatch and rotation state do not exist.

- [ ] **Step 3: Implement provider dispatch**

Mirror `main.ipynb`: use `genai.configure` and `GenerativeModel` with JSON response configuration for Gemini; use `Groq().chat.completions.create` for Groq. Set temperature to zero. Select the active key from ordered key pools and pass it only to the provider client.

- [ ] **Step 4: Implement bounded rotation and retry behavior**

On request failure, advance to the next provider key, wrap around, apply exponential backoff, and retry through `MAX_API_RETRIES`. When configured, advance Gemini’s model index after a full key-pool cycle. Fail fast if the selected provider has no key. Return structured status for successful, invalid, and exhausted rows.

- [ ] **Step 5: Run the rotation tests and confirm they pass**

Expected: all API-free rotation tests pass without contacting either provider.

### Task 4: Implement resumable row-level labeling and audit artifacts

**Files:**
- Modify: `phase3_llm_validation.ipynb`

- [ ] **Step 1: Write API-free execution tests**

Test 150-row schema validation, unique IDs, canonical row order, retaining valid existing output rows, retrying blank/invalid rows, and refusal to overwrite human rater files or a non-empty output without the explicit flag.

- [ ] **Step 2: Run the tests and confirm the expected failure**

Expected: failure because loading/execution/output helpers do not exist.

- [ ] **Step 3: Implement input loading and canonical frame preparation**

Read `data/fomc_phase3_validation_rater_1.csv`, assert the exact seven-column schema and 150 unique rows, preserve input `sample_id`/`headline`, and initialize blank label columns.

- [ ] **Step 4: Implement resumable one-request-per-headline execution**

Iterate in canonical order, skip existing valid rows by `sample_id`, send only `{sample_id, headline}`, validate each response, retain blank fields after exhausted retries, sleep between requests, and append one audit record per attempt.

- [ ] **Step 5: Implement atomic CSV and metadata writes**

Write the validated LLM CSV to `data/fomc_phase3_validation_llm.csv` through a temporary sibling file replacement. Write JSONL request audit and JSON run metadata with prompt version, provider/model, timestamps, key indexes, counts, and SHA-256 hashes; never include API key values or hidden metadata.

- [ ] **Step 6: Run the execution tests and confirm they pass**

Expected: API-free tests pass using temporary test frames/files; no repository data files are modified.

### Task 5: Add live-run controls and final validation

**Files:**
- Modify: `phase3_llm_validation.ipynb`

- [ ] **Step 1: Add a dry-run preview cell**

Display the first rendered prompt and configuration summary without displaying keys or making an API call.

- [ ] **Step 2: Add an explicit live-run cell**

Require the user to set `RUN_LIVE = True`, verify the selected key pool, and execute the row-level pipeline. Keep provider/model/output path visible before execution.

- [ ] **Step 3: Add final integrity assertions**

Assert output row count, exact IDs and headlines, allowed codes, relevance/sentiment consistency, canonical order, no hidden columns, and zero unprocessed rows before declaring the output ready.

- [ ] **Step 4: Execute notebook validation without live API calls**

Run all cells through dry-run/final API-free checks. Expected: clean completion with no changes to either human rater CSV.

- [ ] **Step 5: Commit the notebook implementation**

```powershell
git add -- phase3_llm_validation.ipynb
git commit -m "feat: add phase3 LLM validation notebook"
```

