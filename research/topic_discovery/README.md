# Topic Discovery Pipeline

This directory implements the outcome-blind topic discovery stage of the
distributional-news-sentiment project. Its purpose is to separate three objects
that should not be conflated:

1. a continuing topic discourse, such as Russia-Ukraine or monetary policy;
2. the time-bounded set of perspectives selected by outlets covering it;
3. the headline's implied direction for the equity market.

The first two are constructed here without using sentiment labels or market
outcomes. Market implication is measured later. This ordering prevents the
topic system from mechanically grouping positive coverage apart from negative
coverage and destroying the topic-conditioned dispersion we want to study.
Editorial selection of different sub-events is part of that dispersion. The
formal decision is recorded in `DESIGN_DECISION_TOPIC_WINDOWS.md`.

## Current Status

This is a pilot, not a frozen measurement system.

- The canonical corpus contains 172,039 records from `news.csv` and the local
  geopolitical expansion.
- A deterministic 5,000-record stratified pilot produced 4,398 candidate story
  clusters and a 200-pair blinded audit.
- The first 100 audit rows have one completed human review. That review used a
  broad continuing-topic interpretation, motivating the adopted topic-window
  design. Exact story clustering is now secondary.
- Taxonomy v2 defines 18 economically coherent topic families, including named
  conflict discourses rather than one generic geopolitics class. The candidate
  assignment run labels 64,347 records and leaves 107,692 as `other_unclear`.
- A fresh blinded v2 validation set contains 180 single-headline assignments and
  100 topic-discourse pairs. The rater-1 files now contain one completed Codex
  machine audit; separate human accept/correct verification sheets are ready.
- Outcome-blind coverage diagnostics compare 1-, 3-, and 5-trading-session
  windows. The primary window remains unfrozen pending human topic validation.
- The broad rules leave 99,627 corpus records as `other_unclear`. That is an
  honest coverage diagnostic, not a class to use as a substantive topic.
- The first cluster inspection found both coherent event threads and some
  actor-driven over-merging. The next primary validation target is topic-family
  assignment rather than exact-story precision.
- AvalAI access with `deepseek-v4.1-flash` has been tested on one record. The
  model is an optional topic-neutralization and entity-extraction instrument;
  it is not permitted to inspect market outcomes or choose clusters according
  to downstream results.

## Files

| Path | Role |
| --- | --- |
| `taxonomy.json` | Versioned candidate broad taxonomy, rules, entities, and clustering parameters |
| `taxonomy_v2.json` | Candidate continuing-topic taxonomy and assignment/window parameters |
| `DESIGN_DECISION_TOPIC_WINDOWS.md` | Adopted construct, rationale, operational rules, and claim boundaries |
| `DESIGN_DECISION_AGENT_TOPIC_AUDIT.md` | Adopted agent-first topic audit and human-verification protocol |
| `build_corpus.py` | Canonicalizes sources, creates stable record IDs, and performs exact deduplication |
| `assign_topic_families.py` | Hybrid transparent-rule and topic-prototype assignment for taxonomy v2 |
| `build_topic_validation.py` | Fresh blinded headline and pair sheets with separate hidden keys |
| `build_human_verification.py` | Validates a completed agent audit and creates explicit accept/correct sheets |
| `topic_window_coverage.py` | Source/headline coverage comparison for candidate windows without outcomes |
| `TOPIC_FAMILY_RATER_GUIDE.md` | Allowed codes and instructions for independent reviewers |
| `avalai_neutralize.py` | Resumable, opt-in LLM neutralization with raw-response audit logging |
| `cluster_stories.py` | Deterministic sampling, baseline embeddings, chronological clustering, and pair-audit creation |
| `test_topic_discovery.py` | Unit tests for normalization, sampling, clustering chronology, blinding, and LLM parsing |
| `artifacts/canonical_corpus_manifest.json` | Corpus counts, input/output hashes, and diagnostics |
| `artifacts/topic_discovery_pilot_manifest.json` | Pilot parameters, counts, and output hashes |
| `artifacts/TOPIC_DISCOVERY_PILOT_REPORT.md` | Interpretation and pre-freeze decision gates |
| `artifacts/TOPIC_FAMILY_V2_REPORT.md` | Human-readable v2 counts, coverage findings, limitations, and next gate |
| `artifacts/topic_family_v2_assignment_manifest.json` | V2 assignment counts, hashes, and representation settings |
| `artifacts/topic_family_v2_validation_manifest.json` | Validation sample hashes and blinding checks |
| `artifacts/topic_family_v2_agent_audit_manifest.json` | Completed Codex audit and blank human-verification hashes |
| `artifacts/topic_window_coverage_v2.csv` | Topic-level candidate-window coverage diagnostics |
| `artifacts/topic_window_coverage_v2_manifest.json` | Coverage inputs, assumptions, and hashes |

Large generated datasets are deliberately ignored by ordinary Git and are
identified by SHA-256 in versioned manifests.

## Method

### 1. Canonical corpus

`build_corpus.py` combines the student news universe with the geopolitical
retrieval snapshot. It preserves original text and provenance, normalizes
publisher names, creates stable IDs, and removes only exact duplicates sharing
source, publication date, and normalized headline. It also attaches provisional
broad-topic candidates using transparent rules.

### 2. Topic-neutral text

The deterministic baseline makes only narrow directional-word substitutions.
The persisted prompt at `research/prompts/TOPIC_NEUTRALIZATION_PROMPT.md` asks
an LLM to preserve actors, actions, objects, locations, institutions, and event
identity while removing evaluative market direction. Both original and
neutralized text are retained.

The LLM stage is optional because it incurs cost and must be audited. Live API
calls require `--live`; a dry run is the default. The script accepts
`AVALAI_TOKEN` or `AVALAI_API_KEY` from `.env`, never writes the credential, and
stores parsed output separately from the append-only raw-response audit log.

### 3. Candidate story clusters, secondary

The baseline representation is TF-IDF over unigrams and bigrams followed by a
fixed-seed truncated SVD and L2 normalization. Headlines are processed in
chronological order within their provisional broad topic. A headline may join
an active story using a predeclared weighted score of semantic similarity,
named-entity overlap, and temporal proximity; otherwise it starts a new story.

This online assignment prevents future headlines from changing historical
cluster assignments. It does not solve every look-ahead concern: the pilot SVD
is fit on the complete pilot sample. Forecasting work must fit the representation
on each training period or verify a separately frozen representation model.

The adopted primary design instead aggregates eligible coverage into
predeclared `topic x information_window` cells. Story clusters remain useful
for deduplication, diagnostics, and a narrower common-information robustness
measure.

### 4. Topic-family assignment, primary

`assign_topic_families.py` assigns the v2 topic families using a weighted
combination of transparent regular-expression evidence and cosine similarity to
versioned topic definitions/examples. Known retrieval queries supply candidate
evidence but do not by themselves receive high-confidence status. Headlines
below the minimum score remain `other_unclear`.

The current TF-IDF representation is fit on the complete outcome-blind corpus
plus frozen topic prototypes. This is acceptable for measurement development,
but forecasting evaluation must refit it on training data or freeze a validated
representation before the test period.

### 5. Exploratory pair audit

`data/topic_discovery_pair_audit.csv` contains only two headlines plus blank
review fields. It mixes candidate same-cluster pairs and hard negatives drawn
from the same broad topic and nearby dates. The pair type, record IDs, dates,
sources, and cluster IDs are kept in `data/topic_discovery_pair_key.csv` and
must remain hidden until independent reviews are complete and checksummed.

The first reviewer interpreted `same_story` as membership in the same continuing
topic discourse, including different selected aspects of COVID or a war. That
interpretation is now part of the study design rather than treated as reviewer
error. The first 100 completed judgments are preserved as an exploratory audit.

Future pair audits will replace the ambiguous field with
`same_topic_discourse` (`yes`, `no`, `unclear`). Reviewers will decide whether
both headlines belong to the same predeclared, economically coherent topic
family during a reasonable time window. Confidence remains `low`, `medium`, or
`high`, with a short note for difficult cases.

### 6. Fresh v2 validation

The v2 files are separate from the opened exploratory audit. The completed
Codex audit is stored in:

- `data/topic_family_v2_validation_rater_1.csv`
- `data/topic_family_v2_pair_rater_1.csv`

The human should review:

- `data/topic_family_v2_validation_human_verification.csv`
- `data/topic_family_v2_pair_human_verification.csv`

Use `TOPIC_FAMILY_RATER_GUIDE.md`. Enter `accept`, `correct`, or `unclear` for
every row and supply corrected fields only when needed. Do not open the
corresponding `*_key.csv` files until both verification sheets are complete and
checksummed. The untouched rater-2 files remain fallback artifacts; they are not
part of the adopted single-agent-plus-human workflow.

## Reproduction

Use the project environment directly:

```bash
/home/hamid/.pyenv/versions/fnlp/bin/python -m research.topic_discovery.build_corpus
/home/hamid/.pyenv/versions/fnlp/bin/python -m research.topic_discovery.cluster_stories
/home/hamid/.pyenv/versions/fnlp/bin/python -m research.topic_discovery.assign_topic_families
/home/hamid/.pyenv/versions/fnlp/bin/python -m research.topic_discovery.build_topic_validation
/home/hamid/.pyenv/versions/fnlp/bin/python -m research.topic_discovery.topic_window_coverage
/home/hamid/.pyenv/versions/fnlp/bin/python -m unittest discover
```

Preview an LLM run without making a network request:

```bash
/home/hamid/.pyenv/versions/fnlp/bin/python -m research.topic_discovery.avalai_neutralize --limit 10
```

Run a deliberately small live batch only after checking the preview:

```bash
/home/hamid/.pyenv/versions/fnlp/bin/python -m research.topic_discovery.avalai_neutralize --limit 10 --live
```

## Freeze Gates

Before topic-aware market models are run:

1. Define candidate topic families and their inclusion/exclusion examples.
2. Create at least two independent reviews of a stratified topic-assignment and
   same-topic-discourse sample.
3. Report topic precision, recall, confusion, ambiguity, and results by source,
   year, and topic family.
4. Inspect `other_unclear` and revise topic coverage using outcome-blind
   examples; do not tune rules using market associations.
5. Compare daily, three-session, and weekly windows using coverage and
   reliability only.
6. Freeze the taxonomy, assignment procedure, primary window, source weighting,
   duplicate rules, prompt/model/version, and artifact hashes before outcome
   modeling.
7. Keep `other_unclear` headlines in total-news measures but exclude them from
   primary topic-conditioned dispersion.

Only after these gates pass should the project estimate topic-conditioned
coverage dispersion against market outcomes.
