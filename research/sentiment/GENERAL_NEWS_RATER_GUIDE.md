# General-News Market-Implication Rating Guide

Version: 1.0 (2026-10-30)

Rate each headline independently using only its text. The common reference
asset for this validation is the S&P 500/SPY. This asset is provisional for
the broader study; any change requires a new rubric and new validation labels.

## Question

Taking the reality described or implied by the headline as true, what
near-term implication does it communicate for broad U.S. equities? Use ordinary
ex ante financial reasoning. Do not look up the article, source, publication
date, actual price movement, other labels, or subsequent events. Do not invent
facts absent from the headline.

The question concerns the news item's implied equity environment, not the
emotion of its wording or whether the event is socially desirable. For example,
hawkishness and conflict escalation can each affect equities through different
mechanisms. A headline that simply reports the market's past move may describe
performance without identifying a new forward implication.

## Sentiment Code

| Code | Meaning |
| --- | --- |
| `A` | Strongly adverse for broad U.S. equities |
| `B` | Moderately adverse |
| `C` | Neutral, descriptive, balanced, or genuinely offsetting |
| `D` | Moderately favorable |
| `E` | Strongly favorable |
| `U` | Insufficient headline information to make a defensible A-E judgment |

Use `C` when the headline itself communicates a balanced or neutral state. Use
`U` when a material missing fact prevents the market mapping. Do not infer
strength from dramatic language alone. A topic may be clear while its equity
implication is `U`.

## Other Fields

- `label_confidence`: `H` when the implication is direct, `M` when a reasonable
  adjacent interpretation exists, or `L` when uncertainty is substantial.
- `ambiguity_flag`: `Y` when reasonable interpretations conflict materially or
  missing context could change the direction; otherwise `N`.
- `reviewer_notes`: optional short rationale based only on the headline.

Keep `sample_id` and `headline` unchanged. Fill every rating field except the
optional note. Do not open the hidden key or discuss rows with another rater
before both files are complete and checksummed. Agreement is measured before
human adjudication; unresolved disagreements remain visible.
