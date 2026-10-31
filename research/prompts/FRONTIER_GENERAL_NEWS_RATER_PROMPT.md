# Fresh Frontier Rater: General-News Implication v1

Start a fresh session that has not seen this repository, the sample key,
machine labels, or any human ratings. Attach
`data/general_sentiment_v1_frontier_input.csv` and the guide at
`research/sentiment/GENERAL_NEWS_RATER_GUIDE.md`.

Rate all 240 headlines independently using only `sample_id` and `headline`.
Return a downloadable CSV with the same row order and exactly these columns:

```text
sample_id,headline,equity_sentiment,label_confidence,ambiguity_flag,reviewer_notes
```

Follow the guide's A-E/U, H/M/L, and Y/N definitions. Fill every rating field,
preserve all IDs and headlines exactly, and use a short headline-grounded note.
Do not browse, infer source or date, inspect market outcomes, or view any other
rating sheet. Save the returned file separately and record the exact model name,
run date, and settings. This rating is a machine benchmark, not a human vote.
