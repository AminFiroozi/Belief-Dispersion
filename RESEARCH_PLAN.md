# Distributional Sentiment Research Plan

## 1. Research Objective

This project tests whether the cross-news distribution of sentiment is an
independent and useful market-state indicator in pre-specified high-information
settings.

The primary claim is deliberately conditional rather than universal:

> Before scheduled, consequential information releases, topic-conditioned
> sentiment dispersion predicts the magnitude of the subsequent market
> adjustment after controlling for mean sentiment, news attention, and the
> market state known before the release.

"Independent" means incremental to mean sentiment and controls. "Useful" means
improved out-of-sample forecasts or economically meaningful event
classification, not only an in-sample p-value. "Certain times" will be defined
before observing outcomes through scheduled-event families, not selected after
seeing where dispersion appears successful.

The broad daily analysis remains supporting evidence. The scheduled-event study
will be the primary design because it provides coherent topics, exact timing,
and a substantially cleaner information set.

## 2. Scope Decisions

- Use the existing discrete A-E headline sentiment labels for the first study.
- Keep multidimensional LLM sentiment as a deferred project. Relevance,
  surprise, horizon, uncertainty, and disagreement may be used as filters,
  controls, or exploratory moderators, but they are not the central claim.
- Condition distributions on one event topic at a time. A distribution across
  unrelated headlines is news-flow heterogeneity, not necessarily disagreement.
- Treat the design as event-timed predictive or quasi-experimental evidence.
  Scheduled timing reduces reverse causality but does not randomly assign
  sentiment dispersion.
- Use only information available before each prediction origin in primary
  models. Post-release information belongs only in mechanism analyses.

## 3. Primary Event Sample

The initial sample spans 2020-05-01 through 2025-04-30 and pools three official
U.S. macroeconomic event families:

1. FOMC policy statements, normally released at 14:00 America/New_York.
2. Consumer Price Index releases, normally released at 08:30 America/New_York.
3. Employment Situation/nonfarm payroll releases, normally released at 08:30
   America/New_York.

GDP releases are a pre-specified expansion candidate if the first three
families do not provide enough usable events.

Event dates and timestamps must come from official Federal Reserve and Bureau
of Labor Statistics calendars. Early closes, holidays, unscheduled FOMC
actions, delayed releases, and timestamp exceptions must be recorded explicitly.

### Event Inclusion Rule

The primary article window is the three trading days preceding an event through
the final headline strictly before the official release timestamp. Robustness
windows are one and five trading days.

An event enters the primary article-level sample when it has:

- At least eight topic-relevant headlines before the release.
- At least one valid source and publication timestamp.
- Complete pre-event controls and post-event market outcomes.

Sensitivity analyses will use minimum counts of 5, 10, and 15. A family is
individually viable when at least 25 events pass the primary rule. Families
below that threshold may enter the pooled model with event-family effects but
will not receive standalone conclusions.

## 4. Data Sources And Provenance

### Existing Inputs

- `result.csv`: 142,343 timestamped, LLM-labeled NYTimes and Guardian headlines.
- `news.csv`: corresponding raw headline corpus.
- `data/spy_1min_data`: SPY minute bars covering 2020-03-24 onward.
- `data/market_panel.csv`: daily SPX and VIX cache.
- `distributional_sentiment_v1.ipynb`: current daily proof of concept.
- `news_analysis.ipynb`: student intraday prototype requiring timing repairs.

### Free Official Inputs

- Federal Reserve FOMC calendars and statements.
- BLS release calendars and public data API.
- Cboe daily historical VIX.
- ALFRED vintages when originally released values are required.
- New York Fed market-expectations surveys for FOMC robustness.

### Provenance Requirements

Every derived dataset must record source URL, retrieval date, timezone,
transformation version, and raw-file checksum. The provenance and licensing of
`spy_1min_data` must be established before it is the sole market-data source in
a paper. Free Alpaca IEX bars may be used as an independent price check, but not
as consolidated-volume data.

Raw news and market data remain outside Git. Small official calendars,
configuration, code, checksums, and aggregate audit tables should be versioned.

## 5. Topic Assignment

Topic membership must be determined without market outcomes.

1. Begin with transparent, high-precision keyword rules for each event family.
2. Manually review false positives and false negatives in a stratified sample.
3. Freeze the rules before outcome regressions.
4. Optionally use an LLM relevance adjudicator only for ambiguous headlines,
   with prompt, model, and output archived.
5. Deduplicate exact and near-duplicate headlines before constructing shares.

Primary distributions use only event-relevant headlines. Unrelated headlines
form a placebo distribution rather than entering the event measure.

## 6. Sentiment Representation

Let `p_A, ..., p_E` be the five daily/event-window class shares. Do not include
redundant transformations of these shares in the same regression.

### Required Baseline

- Mean sentiment, using signed scores `[-1, -0.5, 0, 0.5, 1]`.
- Log headline count.
- Source count or source indicators.

### Primary Distribution Measure

Use the mean-orthogonal quadratic contrast over A-E shares, proportional to
weights `[2, -1, -2, -1, 2]`. It captures extreme/U-shaped mass relative to
neutral and moderate mass while being algebraically orthogonal to the linear
mean contrast.

### Secondary Distribution Measures

- Bipolarity: positive mass multiplied by negative mass.
- Entropy over the five classes.
- Mean-orthogonal cubic and quartic contrasts for asymmetry and tail shape.
- Negative and positive tail masses, tested separately only in labeled
  secondary specifications.

Use Dirichlet or empirical-Bayes smoothing when event article counts are small.
Report unsmoothed estimates as a robustness check. Feature definitions and the
single primary contrast must be frozen before outcome testing.

## 7. Outcomes And Information Sets

### Primary Outcome

- SPY realized volatility during the first 60 minutes after the release.

### Secondary Outcomes

- Five- and fifteen-minute realized volatility.
- Absolute five-, fifteen-, and sixty-minute return.
- Post-release volume relative to normal volume for that minute of day.
- Close-to-close absolute return and next-five-day realized volatility.
- Daily VIX change.
- Tail-event indicators, subject to adequate event counts.

### Timing Rules

- Convert every news timestamp from UTC to `America/New_York` before assignment.
- Begin each reaction window strictly after the official release timestamp.
- Never floor an article timestamp and then measure a reaction from before the
  article.
- Normalize minute outcomes for time-of-day seasonality.
- Use market controls measured before the release: pre-event return, pre-event
  realized volatility, latest available VIX, and prior trading volume.
- Do not use actual announcement surprise in the ex-ante primary model. It may
  enter a secondary mechanism model after the total predictive effect is shown.

## 8. Empirical Specifications

### Event-Level Forecast

Baseline:

`post_event_rv ~ mean sentiment + log news count + source controls + pre-event market controls + event-family effects + calendar effects`

Distribution model:

`baseline + primary quadratic dispersion contrast`

Secondary models add one pre-specified shape measure at a time.

### Pre/Post Event Design

Compare matched pre-release and post-release market windows. Estimate whether
the post-event increase in volatility or volume is larger when pre-event
sentiment dispersion is higher. Cluster uncertainty at the event level and
include event-family and intraday-bin effects as appropriate.

### Inference And Predictive Value

- Event-level heteroskedasticity-robust inference.
- Wild or block bootstrap by event.
- Permutations within event family and year.
- Rolling or leave-one-year-out forecasts.
- Nested-model comparison using RMSE, MAE, OOS R2, and Clark-West or an
  appropriate nested forecast test.
- Report effect sizes and confidence intervals, not only significance.
- Correct secondary-feature inference for multiple testing.

## 9. Robustness And Falsification

Required checks:

- One-, three-, and five-trading-day article windows.
- Minimum headline thresholds of 5, 8, 10, and 15.
- NYTimes-only, Guardian-only, and both-source samples.
- Leave-one-event-family-out and leave-one-year-out analyses.
- Exclude COVID crisis months and other pre-specified stress periods.
- Alternative discrete encodings and unsmoothed versus smoothed shares.
- Randomly shifted event dates matched on weekday and release time.
- Unrelated-topic headline distributions around the same events.
- Pre-event pseudo-reaction windows as a pre-trend placebo.
- Label shuffles within source, topic, and year.
- No conclusion based on a hand-selected individual event.

## 10. Measurement Validation

Before final inference, draw a stratified validation sample covering event
families, sources, years, and all sentiment classes.

- Two independent human labels where feasible.
- Weighted kappa and class-specific agreement.
- Repeated LLM labeling on a subset to measure model stability.
- FinBERT probabilities as an alternative measurement benchmark, not assumed
  ground truth.
- Report class imbalance, disagreement cases, and sensitivity to relabeling.

## 11. Execution Phases

### Phase 0 - Repository And Design Freeze

Status: complete when the reconciled branch is on `main`, raw data are ignored,
the roadmap is versioned, and the current proof-of-concept results are preserved.

Deliverables:

- Reconciled `main` branch.
- This research plan.
- Baseline notebook and literature report under version control.
- Data provenance checklist and checksums.

### Phase 1 - Official Calendar And Coverage Audit

Build the FOMC, CPI, and payroll event calendar with exact New York timestamps.
Apply frozen candidate topic rules to the current corpus and calculate headline
coverage in one-, three-, and five-day pre-event windows.

Gate:

- Continue with each standalone family only if at least 25 events have eight or
  more relevant headlines.
- If the pooled sample is also sparse, expand news coverage before modeling.

Deliverables:

- Versioned event calendar and source manifest.
- Event-level coverage table.
- False-positive topic audit sample.
- Written go/no-go recommendation for each event family.

### Phase 2 - Timing-Safe Event Panel

Repair timezone handling, map topic headlines to events, deduplicate stories,
and construct pre- and post-release SPY outcomes without overlapping the
information boundary.

Deliverables:

- One row per event with article counts, sentiment shares, controls, and
  outcomes.
- Timing assertions and missingness audit.
- Independent spot checks against raw minute bars.

### Phase 3 - Measurement And Feature Validation

Validate sentiment labels, implement orthogonal contrasts and smoothing, and
freeze the primary feature before looking at outcome tests.

Deliverables:

- Label agreement report.
- Feature identity/rank tests proving no exact redundancy.
- Final primary and secondary feature registry.

### Phase 4 - Primary Event Models

Estimate baseline and distribution models for 60-minute realized volatility,
then perform the pre/post event analysis.

Deliverables:

- Primary coefficient and effect-size table.
- Baseline-versus-distribution model comparison.
- Event-family heterogeneity table.
- Diagnostic residual and influence checks.

### Phase 5 - Robustness And Out-Of-Sample Validation

Run source, year, family, threshold, smoothing, placebo, bootstrap, and rolling
forecast tests.

Gate:

The central claim advances only if the primary dispersion effect has a stable
direction, survives event-level inference and key placebos, and improves at
least one pre-specified OOS metric without depending on one source, year, or
event family.

### Phase 6 - Broader Daily And Intraday Extensions

Re-estimate the broad daily model using a market-close information set and
repair the second student's general intraday pipeline. These analyses test
external validity and mechanisms; they do not replace the primary event design.

### Phase 7 - Paper Finalization

Lock tables and figures, verify citations, document null results, produce a
reproducibility appendix, and write the paper around the strength of evidence
actually obtained.

## 12. Decision Log

- Primary endpoint: post-event volatility, not directional return.
- Primary setting: topic-conditioned scheduled macro events.
- Primary sentiment measurement: discrete A-E labels.
- Primary distribution feature: mean-orthogonal quadratic contrast.
- Multidimensional sentiment: deferred.
- Existing broad daily and student intraday findings: exploratory until timing
  and inference are repaired.
- Paid data: deferred until the free-data coverage gate is evaluated.

## 13. Progress Log

### 2026-08-17 - Phase 0 Complete

- Reconciled the Claude work and research baseline into local `main`.
- Preserved the existing notebooks and literature report.
- Excluded raw `data/` inputs from Git and recorded checksums in
  `research/PROVENANCE.md`.
- Added the reproducible event-study structure under `research/event_study/`.

### 2026-08-17 - Phase 1 Initial Gate Complete

- Versioned 39 regular FOMC, 60 CPI, and 60 Employment Situation release
  timestamps from official Federal Reserve and BLS calendars.
- Applied outcome-blind candidate topic rules using a strict pre-release time
  boundary and exact-normalized headline deduplication.
- Under the primary three-session/eight-headline rule, 0 FOMC, 10 CPI, and 1
  employment events pass. None reaches the 25-event standalone threshold.
- Decision: do not begin outcome regressions on this event panel yet. First
  expand U.S. macro-news coverage and rerun the unchanged coverage gate.
- Candidate topic rules remain explicitly unfrozen. The manual relevance audit
  must be completed before any broader rule or longer window is adopted.

The generated audit is in
`research/event_study/artifacts/PHASE1_REPORT.md`. Phase 2 is therefore deferred
until the Phase 1 coverage problem is resolved; this is a design gate, not a
null result for the research hypothesis.

### 2026-08-18 - Phase 1b Free-Coverage Expansion

- Corrected the pre-event window to be continuous from the earliest included
  completed session through the release boundary, so weekend headlines are no
  longer discarded.
- Retrieved an outcome-blind historical Google News RSS pilot for all 159
  events. Raw feeds and headline metadata remain under ignored `data/` paths.
- Excluded release-day RSS records because historical entries frequently have
  date-like rather than trustworthy clock timestamps.
- Added transparent title-level relevance filters and excluded official agency
  pages. Under the original three-session/eight-headline gate, FOMC passes on
  31 of 39 events, CPI on 13 of 60, and employment on 6 of 60.
- Decision: prioritize FOMC as the first case study. Defer CPI and employment.
  FOMC outcome modeling remains blocked until manual relevance validation,
  paper-acceptable source/archiving terms, and consistent sentiment labeling
  are complete.

The aggregate expansion report is in
`research/event_study/artifacts/GOOGLE_NEWS_EXPANSION_REPORT.md`.
