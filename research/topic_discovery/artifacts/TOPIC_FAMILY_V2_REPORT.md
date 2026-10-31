# Topic Family V2 Implementation Report

Run date: 2026-10-25
Status: adjudicated validation complete; production assignment revision pending

## Implemented Construct

The primary unit is a time-bounded topic discourse. Different sub-events and
perspectives selected by outlets are intentionally retained as part of
topic-conditioned coverage dispersion. Exact-event clustering is secondary.

## Assignment Run

Taxonomy v2 defines 18 topic families. The hybrid rule/topic-prototype pipeline
processed all 172,039 canonical records without sentiment labels or market
outcomes.

| Primary label | Records |
| --- | ---: |
| `other_unclear` | 107,692 |
| `russia_ukraine` | 30,277 |
| `covid_pandemic` | 12,360 |
| `iran_israel` | 7,806 |
| `israel_gaza` | 4,034 |
| `red_sea_houthi` | 1,849 |
| `inflation_prices` | 1,699 |
| `monetary_policy` | 1,302 |
| `trade_tariffs` | 903 |
| `labor_markets` | 686 |
| `growth_recession` | 663 |
| `corporate_earnings_deals` | 571 |
| `market_performance` | 540 |
| `energy_oil_gas` | 406 |
| `technology_ai_chips` | 349 |
| `climate_transition` | 341 |
| `fiscal_tax_debt` | 265 |
| `banking_credit` | 202 |
| `us_china_relations` | 94 |

The assignment confidence distribution is 19,496 high, 25,508 medium, 19,343
low, and 107,692 unassigned. Retrieval-query membership alone is capped at
medium confidence unless headline evidence corroborates the family.

These counts are coverage diagnostics, not validated prevalence estimates.
In particular, the geopolitical counts partly reflect the targeted Google News
retrieval design, while the original student corpus is much broader.

## Fresh Blinded Validation

The generated package originally contained:

- 180 single-headline assignments for each of two raters;
- 100 pairwise same-topic-discourse decisions for each rater;
- independently randomized row order;
- independently swapped A/B pair orientation;
- hidden keys containing machine assignments and provenance.

The rater sheets contain no machine label, source, date, or market information.
On 2026-10-10, one blinded Codex audit completed all 180 rater-1 headline rows
and 100 rater-1 pair rows without opening hidden keys. Headline labels comprise
144 high-, 34 medium-, and 2 low-confidence judgments. Pair judgments comprise
45 `yes`, 54 `no`, and 1 `unclear`.

The cleaned human verification accepts 159 headline judgments, corrects 19, and
leaves 2 unclear. It accepts 98 pair judgments and corrects 2. The taxonomy
retains `iran_israel`; no additional Iran-regional family is introduced. This is
an adjudicated machine-plus-human workflow, not two independent raters.

After verification, the hidden keys were opened. Of 180 headline rows, 178
have resolved adjudicated labels. The Codex audit achieved 89.3% primary-topic
accuracy. The production assigner achieved 73.0% exact accuracy and 78.7%
primary-or-second-candidate accuracy. High-confidence production labels were
47/48 correct (97.9%), compared with 64.7% for low-confidence and 60.0% for
unassigned rows. On the 100 deliberately balanced pairs, the production rule
achieved 86.0% accuracy, 82.0% same-topic precision, and 89.1% same-topic
recall. See `TOPIC_FAMILY_V2_VALIDATION_REPORT.md` for the full interpretation.

## Candidate Selective Policy

The development-sample policy accepts all substantive assignments with score
at least 0.28 and margin at least 0.05. It deliberately adds no topic-specific
COVID or Russia exclusions from the two observed errors. The gate accepts
51/53 development cases correctly (96.2%), 44,991 corpus records in total, and
69.9% of records already assigned to a substantive topic. It routes 19,356
weaker substantive assignments for review and retains 107,692 as
`other_unclear`.

This is a selective-classification candidate, not a frozen estimate. The gate
was chosen on the same adjudicated sample used to report its accuracy. Also,
only 24/40 deliberately sampled `other_unclear` rows were confirmed as such,
so missed substantive topics remain an important recall risk.

## Candidate Window Coverage

Coverage was compared for trailing 1-, 3-, and 5-trading-session windows. A
publication date maps to the first market session on or after that date. Only
headline and unique-source counts were used.

Across all topic-session cells:

| Window | Nonempty cells | Cells with >=3 headlines and >=2 sources | Cells with >=5 headlines and >=3 sources |
| ---: | ---: | ---: | ---: |
| 1 session | 40.5% | 16.8% | 8.5% |
| 3 sessions | 63.9% | 28.6% | 13.3% |
| 5 sessions | 75.3% | 37.9% | 14.6% |

No window is frozen yet. Human assignment reliability and topic-specific
coverage must be considered together before selection.

## Important Limitation

Source breadth is highly uneven. Russia-Ukraine, Iran-Israel, and Red Sea
coverage draw from the multi-source Google News expansion. Most economic topics
come mainly from the New York Times and Guardian, and many cannot satisfy a
three-source threshold regardless of window length.

Therefore:

- headline-weighted estimates are feasible across more topics;
- equally source-weighted two-source comparisons may be feasible for the
  original economic corpus;
- strong between-source inference is currently much better supported for the
  expanded geopolitical topics;
- results must report topic-specific source coverage;
- additional source collection should be considered before making general
  claims about source-level framing.

## Next Gate

Validate the candidate selective gate on a fresh blinded holdout and audit
`other_unclear` recall. Outcome-blindly adjudicate the weaker substantive route
using active sampling before considering a full model run. Freeze the
production assignment procedure only after those checks, and then select the primary
information window using validation reliability and coverage without consulting
market outcomes.
