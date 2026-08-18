# Phase 3 Human Labeling Rubric

Version: 1.0  
Unit: one headline  
Information available to raters: headline text only

## Purpose

This audit evaluates whether candidate FOMC headlines are genuinely relevant
and whether humans can apply the proposed sentiment axis consistently. It does
not test the research hypothesis. Raters must not inspect event dates, sources,
market prices, model labels, the hidden sample key, or each other's answers.

Complete the relevance field first. Label only what the headline conveys; do
not search for the article, reconstruct its publication date, or infer details
that are absent from the text.

## 1. Topic Relevance

Question:

> Is the headline centrally about an approaching Federal Reserve monetary-policy
> decision, policy outlook, interest-rate path, or communication that bears on
> that decision?

Allowed labels:

- `R`: relevant. Monetary policy, rates, an FOMC decision, policy expectations,
  or Powell's policy communication is a central subject.
- `I`: irrelevant/incidental. The Fed is only mentioned incidentally, or the
  story is mainly about appointments, bank supervision, payments, institutional
  administration, an unrelated speech, or another non-policy subject.
- `U`: unclear from the headline alone.

A headline can be relevant even if it is neutral or reports disagreement. Do
not use sentiment to decide relevance.

## 2. Equity-Implication Sentiment

Complete this field only when relevance is `R`. When relevance is `I`, leave it
blank. When relevance is `U`, use sentiment `U` unless the implication is still
unambiguous.

Question:

> What near-term implication for broad U.S. equity-market conditions is conveyed
> by the headline, considered on its own and before the FOMC announcement?

Allowed labels:

- `A`: strongly adverse. The headline clearly conveys severe downside,
  financial stress, sharply restrictive policy, or a strongly unfavorable
  near-term equity environment.
- `B`: moderately adverse. The implication is unfavorable, but not extreme.
- `C`: neutral, balanced, mixed, descriptive, or directionally unclear.
- `D`: moderately favorable. The implication is favorable, but not extreme.
- `E`: strongly favorable. The headline clearly conveys substantial upside,
  relief, strongly supportive policy, or a strongly favorable near-term equity
  environment.
- `U`: insufficient information to assign A-E from the headline alone.

This is not a hawkish/dovish label and not a judgment about whether Federal
Reserve policy is socially desirable. A strong economy and restrictive policy
can pull in opposite directions; label `C` or `U` when the net equity
implication is genuinely mixed or absent. Do not use knowledge of what markets
actually did afterward.

## 3. Confidence

Allowed labels:

- `H`: the labels follow directly from the headline.
- `M`: a reasonable alternative exists, but the chosen labels are more likely.
- `L`: the headline is highly ambiguous or lacks necessary context.

Confidence is a quality-control field and will not be used as a sentiment
feature.

## 4. Ambiguity Flag

Use `Y` when the headline contains materially conflicting implications, depends
on omitted article context, or could reasonably switch between non-adjacent
sentiment classes. Otherwise use `N`.

## 5. Audit Procedure

1. Raters work independently using their separate CSV files.
2. Use only the permitted codes; leave `reviewer_notes` optional and concise.
3. Do not discuss individual headlines until both files are complete and
   checksummed.
4. Agreement is calculated before adjudication.
5. Disagreements are adjudicated afterward without consulting market outcomes.
6. No model is selected according to downstream return or volatility results.

