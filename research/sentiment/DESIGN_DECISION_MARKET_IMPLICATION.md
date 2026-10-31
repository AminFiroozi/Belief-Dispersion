# Design Decision: Universal Market-Implication Axis

Date: 2026-10-26
Status: adopted for measurement development; reference asset provisional

## Decision

The primary sentiment construct is the headline-implied near-term direction for
broad U.S. equities, operationalized with the S&P 500/SPY as the primary market
target.

Raters answer:

> Taking the reality described or implied by the headline as true, considered
> on its own and without using subsequent market behavior, what near-term
> implication does it communicate for the S&P 500/SPY?

This is a conditional implication judgment. The rater does not fact-check the
headline, predict the realized return, or use knowledge of what happened after
publication. Ordinary ex ante financial reasoning is permitted, but missing
facts must not be invented.

## Common Axis And Topic Mechanisms

Topics need not share a native state axis. Monetary-policy news may be hawkish
or dovish, while conflict news may imply escalation or de-escalation. Those
states are different causal mechanisms, but both can map to a common equity-
market implication:

`headline reality -> topic-native mechanism -> S&P 500/SPY implication`

The final implication is coded on the same bearish-to-bullish axis across all
topics. Therefore, topic-conditioned dispersion compares economically aligned
market implications even when the underlying mechanisms differ.

Topic-native states may later be labeled to explain mechanisms. They are not
pooled as if hawkishness and escalation were numerically identical, and they do
not replace the universal market-implication label in the primary analysis.

## Scale

- `A`: strongly bearish or adverse.
- `B`: moderately bearish or adverse.
- `C`: neutral, balanced, mixed, descriptive, or directionally offsetting.
- `D`: moderately bullish or favorable.
- `E`: strongly bullish or favorable.
- `U`: insufficient headline information to infer an A-E implication.

The baseline numerical encoding is `[-1, -0.5, 0, 0.5, 1]`. Distributional
analysis will also use class shares, positive and negative tail mass, entropy,
and alternative encodings. Confidence and ambiguity are quality-control fields,
not sentiment observations.

The target must not change from one headline to another. S&P 500/SPY is the
provisional primary target. Interest rates and Nasdaq remain possible later
targets, but a target change requires new labels and validation.
The event-study and daily designs may use different realized outcome horizons,
but raters label a near-term implication without seeing those outcomes.

## Model Roles

### Human Reference

Two independent human ratings followed by blinded adjudication define the
reference labels. Agreement is measured before adjudication. Human labels are
also fallible, so ambiguity, confidence, and unresolved cases remain visible.

### DeepSeek Candidate

`deepseek-v4.1-flash`, accessed through AvalAI, is the candidate scalable
production labeler. An instruction-following model is appropriate here because
the task requires mapping heterogeneous topic mechanisms to a specified market
target rather than extracting positive or negative wording alone.

DeepSeek will produce discrete A-E/U labels under deterministic settings. It
will not be asked to invent continuous values or probabilities. Exact model,
prompt, decoding parameters, timestamps, input/output hashes, raw responses,
parse failures, and retries must be retained.

### FinBERT Benchmark

FinBERT is a required benchmark and robustness instrument, not the assumed
production model. Its positive/neutral/negative probabilities provide a
continuous expected-tone score and model entropy. However, its training target
may follow textual financial sentiment rather than the conditional implication
for SPY, particularly for geopolitical, public-health, and policy headlines.

### Frontier Benchmark

A fresh frontier-model session supplies an additional blinded machine rating.
It is neither a third human nor the adjudicator. Correlated language-model
errors must not be interpreted as human validity.

## Selection Rule

DeepSeek and FinBERT are evaluated against held-out human-adjudicated labels
using exact and adjacent agreement, weighted kappa, class confusion, `U` rate,
stability, parse success, coverage, and cost. The scalable production method is
selected from those measurement criteria only. Market returns, volatility, or
downstream regression fit may not influence model selection.

## Current Topic-Measurement Context

- Canonical corpus: 172,039 headlines.
- Taxonomy: 18 substantive continuing-topic families plus `other_unclear`.
- Initial substantive assignments: 64,347; retained `other_unclear`: 107,692.
- Adjudicated topic reference: 178 resolved headline labels and 100 pair labels.
- Initial production accuracy: 73.0% exact headline assignment and 86.0% pair
  assignment on deliberately stratified validation samples.
- Candidate selective gate: score at least 0.28 and margin at least 0.05.
- Selective routing: 44,991 auto-accepted, 19,356 weaker substantive assignments
  sent to outcome-blind review, and 107,692 retained as `other_unclear`.
- Development accuracy of the selective gate: 51/53, or 96.2%; a fresh holdout
  remains required because the gate was selected on that same sample.

## Next Measurement Work

1. Collect two independent human ratings, one clean frontier-model rating,
   DeepSeek labels, and FinBERT probabilities.
2. Calculate agreement before adjudication and freeze the production sentiment
   instrument without consulting market outcomes.
3. Label the eligible corpus and construct total, within-topic, between-topic,
   source-balanced, and between-source distribution features.
