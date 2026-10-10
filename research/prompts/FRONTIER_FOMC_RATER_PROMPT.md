# Frontier Model Blinded Rater Prompt: FOMC Pilot v1

## Use

Start a fresh model session that has not seen this repository, the existing
machine labels, the hidden sample key, or any market outcomes. Attach one
untouched blinded input file, preferably
`data/fomc_phase3_validation_rater_1.csv`, and send the prompt below.

Save the returned file as `fomc_phase3_validation_frontier.csv`. Also record the
model's exact name/version, the execution date, and any settings exposed by the
interface. Do not use either human rater's completed sheet as the input.

## Prompt To Send

You are an independent blinded research rater. Your task is to annotate every
row in the attached CSV using only `sample_id` and `headline`.

This is a measurement-validation exercise, not a request for investment advice
or market prediction. Work independently. Do not browse the web, retrieve the
articles, infer publication dates or sources, ask for other project files, use
knowledge of subsequent market behavior, or attempt to identify the events
behind the random IDs. Do not use any labels from another human or model.

Return one completed CSV file. Preserve every input row, its exact `sample_id`,
its exact `headline`, its original row order, and the original seven-column
schema:

```text
sample_id,headline,topic_relevance,equity_sentiment,label_confidence,ambiguity_flag,reviewer_notes
```

Do not add columns, delete rows, reorder rows, or alter headline text. Complete
all 150 rows. Do not wrap the CSV in prose or a Markdown code block.

### 1. Topic Relevance

First answer:

> Is the headline centrally about an approaching Federal Reserve monetary-
> policy decision, policy outlook, interest-rate path, or communication that
> bears on that decision?

Use exactly one code:

- `R`: relevant. Monetary policy, rates, an FOMC decision, policy expectations,
  or Powell's policy communication is a central subject.
- `I`: irrelevant or incidental. The Fed is mentioned only incidentally, or the
  story is mainly about appointments, bank supervision, payments,
  administration, an unrelated speech, or another non-policy subject.
- `U`: unclear from the headline alone.

Do not use sentiment to determine relevance. A headline may be relevant while
neutral, mixed, or uncertain.

### 2. Equity-Implication Sentiment

For a relevant headline, answer:

> What near-term implication for broad U.S. equity-market conditions is
> communicated by this headline, considered on its own and before the FOMC
> announcement?

Use exactly one code:

- `A`: strongly adverse. Clear severe downside, financial stress, sharply
  restrictive policy, or a strongly unfavorable near-term equity environment.
- `B`: moderately adverse. Unfavorable, but not extreme.
- `C`: neutral, balanced, mixed, descriptive, or directionally unclear.
- `D`: moderately favorable. Favorable, but not extreme.
- `E`: strongly favorable. Clear substantial upside, relief, strongly
  supportive policy, or a strongly favorable near-term equity environment.
- `U`: the headline lacks enough information to assign A-E.

If `topic_relevance` is `I`, leave `equity_sentiment` empty. If relevance is
`U`, use sentiment `U` unless the equity implication is nevertheless explicit.

This is not a hawkish/dovish label and not a judgment about whether policy is
socially desirable. A strong economy and restrictive policy can have opposing
equity implications. Use `C` or `U` when the net implication is genuinely
mixed or absent.

### 3. Confidence

Use exactly one code:

- `H`: the assigned labels follow directly from the headline.
- `M`: a reasonable alternative exists, but the assigned labels are more
  plausible.
- `L`: the headline is highly ambiguous or lacks necessary context.

Confidence is a quality-control field, not a probability.

### 4. Ambiguity

Use:

- `Y`: materially conflicting implications, omitted context could change the
  label, or reasonable interpretations span non-adjacent sentiment classes.
- `N`: otherwise.

### 5. Reviewer Notes

Give a concise rationale grounded only in words present in the headline. One
short sentence is enough. Do not mention outside facts, dates, sources, market
outcomes, other raters, or hidden context.

### 6. Final Integrity Check

Before returning the file, verify that:

- There are exactly 150 rows and 150 unique `sample_id` values.
- All IDs, headlines, and row positions exactly match the input.
- Relevance contains only `R`, `I`, or `U`.
- Sentiment contains only `A`, `B`, `C`, `D`, `E`, `U`, or blank where required.
- Every `I` row has blank sentiment.
- Confidence contains only `H`, `M`, or `L`.
- Ambiguity contains only `Y` or `N`.
- Every row has a concise reviewer note.

Return only the completed downloadable CSV file.
