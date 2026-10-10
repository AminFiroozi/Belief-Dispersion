# Topic Discovery Pilot Report

Run date: 2026-10-09

## Purpose

The pilot originally tested whether an outcome-blind, chronological procedure
could discover candidate common-information stories before sentiment was
measured. The human audit prompted a design refinement: the primary construct
is now a time-bounded continuing-topic discourse, with exact stories retained
as a secondary decomposition. This remains a measurement exercise, not a
market-outcome experiment.

## Inputs And Outputs

- Canonical corpus: 172,039 records, 2020-05-01 through 2025-04-30.
- Pilot sample: 5,000 records selected deterministically by origin, year, and
  provisional primary topic.
- Representation: topic-neutral deterministic text, TF-IDF unigrams/bigrams,
  128-dimensional truncated SVD.
- Candidate clusters: 4,398.
- Multi-record clusters: 371.
- Singleton clusters: 4,027.
- Largest cluster: 23 records.
- Blinded audit: 100 candidate same-cluster pairs and 100 nearby same-topic
  different-cluster pairs.

Exact parameters and SHA-256 output hashes are stored in
`topic_discovery_pilot_manifest.json`.

The first 100 data rows received one human review: 45 `yes`, 48 `no`, and 7
`unclear`. The completed file state has SHA-256
`adfd80d06afd5bf616ad37017a158a05471b88675c602ad5ba08b75800864bfe`.
One confidence value is misspelled `meduim` and must be normalized during
analysis without altering the preserved raw response.

## What Worked

Several large clusters describe recognizable evolving event threads, including
the Red Sea shipping attacks, the October 2023 Israel-Hamas outbreak, the 2024
Kursk incursion, and the October 2024 Iran-Israel exchange. The procedure also
leaves most records as singletons instead of forcing complete coverage.

The pipeline is deterministic, keeps market outcomes absent, processes records
chronologically, and creates a genuinely blinded pair-review file separate from
its hidden provenance key.

## Known Failure Modes

Manual inspection found actor-driven chaining. For example, one cluster joined
several 2025 Trump headlines about distinct policies because they shared an
actor and broad vocabulary. The completed audit similarly identified false
joins based on tokens such as `home`, `New York`, `Johnson`, and `New Zealand`.
These errors were concentrated in `other_unclear` rather than the recognizable
COVID and named-conflict discourses.

The broad rule system is deliberately conservative and assigns 99,627 canonical
records to `other_unclear`. Its topic coverage must improve before broad-topic
decomposition. The TF-IDF/SVD representation is a reproducible baseline, but
its 18.1% explained-variance summary and lexical nature are reasons to compare
it with stronger outcome-blind embeddings and LLM-neutral text.

Historical geopolitical timestamps are predominantly date-level. Those records
may support daily or weekly topic windows, but they must not be used to claim
intraday pre/post timing.

## Interpretation

The audit reviewer treated different selected aspects of COVID or a war as
belonging to the same relevant discourse. This is consistent with the project
theory: outlets communicate implications through both wording and editorial
selection. The adopted primary unit is therefore
`topic_family x information_window`, documented in
`../DESIGN_DECISION_TOPIC_WINDOWS.md`.

The measured construct combines selection, agenda-setting, framing, and
interpretation. It will be called topic-conditioned coverage dispersion, not
disagreement about the same fact or directly observed investor-belief
dispersion. Exact-event clustering remains useful for deduplication and a
narrower robustness analysis.

## Next Gate

The next gate is to define economically coherent topic families, especially
named conflict families, and validate headline-to-topic assignment on a new
stratified sample. Future pair audits should ask `same_topic_discourse`, not
`same_story`. Daily, three-session, and weekly windows should then be compared
using coverage, reliability, headline counts, and unique-source counts only.

Freeze the taxonomy, assignment rule, primary window, source weighting, and
duplicate rules from measurement quality and coverage, never from downstream
market coefficients.
