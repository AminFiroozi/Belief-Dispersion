# Topic Family V2 Validation Results

Run date: 2026-10-25
Status: human-verified reference derived; production rules not frozen

## Design

One blinded Codex audit was followed by explicit human acceptance, correction,
or unresolved judgment. This is an adjudicated machine-plus-human reference, not
independent inter-rater agreement. The 180-headline sample was deliberately
stratified across machine topics and difficult confidence strata, so aggregate
accuracy is a validation-sample result rather than a corpus-prevalence estimate.

## Headline Assignment

- Resolved reference labels: 178 of 180.
- Codex primary-topic accuracy: 89.3%.
- Production exact primary-topic accuracy: 73.0%.
- Production primary-or-second-candidate accuracy: 78.7%.
- Production macro F1: 75.6%.
- Production weighted F1: 72.7%.

### Accuracy By Production Confidence

| Confidence | Rows | Correct | Accuracy |
| --- | ---: | ---: | ---: |
| `high` | 48 | 47 | 97.9% |
| `low` | 85 | 55 | 64.7% |
| `medium` | 5 | 4 | 80.0% |
| `unassigned` | 40 | 24 | 60.0% |

High-confidence assignments are reliable in this sample. Low-confidence and
unassigned records account for most errors and should not enter confirmatory
topic-conditioned features without revised rules or model adjudication.

## Pair Assignment

- Final same-topic pairs: 46.
- Final different-topic pairs: 54.
- Codex relation accuracy: 98.0%.
- Production relation accuracy: 86.0%.
- Same-topic precision: 82.0%.
- Same-topic recall: 89.1%.
- Same-topic F1: 85.4%.
- Different-topic specificity: 83.3%.

The pair procedure is usable as a candidate generator but still makes 14 errors
in 100 deliberately balanced audit pairs. Exact-event clustering remains
secondary to the adopted topic-window design.

## Decision

Do not freeze the current production headline assigner at a
73.0% exact rate.
Preserve the 18-family taxonomy, including `iran_israel`, and revise assignment
rules from the frozen adjudicated errors. A defensible first production policy
is to accept high-confidence automatic labels, route medium/low/unassigned cases
through model adjudication, and validate that policy on the same reference before
constructing market-outcome features.
