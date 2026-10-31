# Distributional News Sentiment Research Plan

Version: 2.3
Reframed: 2026-10-26

## 1. Research Objective

This project asks whether the distribution of market implications communicated
by financial news contains information beyond their average implication.

The central claim is:

> News items covering the same broad topic in the same information window can
> imply different market directions. The shape of those implications, including
> outlets' choices of which developments and perspectives to cover, may identify
> information states that mean sentiment alone cannot distinguish.

A neutral average can describe very different states: uniformly neutral news,
balanced positive and negative interpretations of one event, or unrelated
topics delivering offsetting signals. The study must distinguish these cases
rather than calling all of them sentiment dispersion.

The primary research question is:

> Does topic-conditioned coverage dispersion in headline-implied market
> direction improve the description or prediction of subsequent market states
> after controlling for mean implication, attention, source mix, topic
> composition, and the market information available at the prediction time?

"Useful" means a stable association, improved out-of-sample prediction, or an
economically interpretable state classification. It does not mean merely an
in-sample p-value. "Independent" means incremental to mean sentiment and the
pre-specified controls.

The defensible primary construct is topic-conditioned coverage dispersion: a
distribution of news-implied market directions that includes editorial
selection, framing, and interpretation. It is not a directly observed
distribution of investor beliefs. The adopted rationale and boundaries are
recorded in `research/topic_discovery/DESIGN_DECISION_TOPIC_WINDOWS.md`.
The common market-implication axis and model roles are recorded in
`research/sentiment/DESIGN_DECISION_MARKET_IMPLICATION.md`.

## 2. Core Decomposition

Every headline receives two conceptually independent measurements:

1. Its expected near-term implication for broad U.S. equities.
2. The broad, predeclared topic discourse to which it belongs.

For headline `i` in information window `t`, let `s_it` denote its market-
implication score and `z_it` its topic assignment.

The total variance of sentiment can be decomposed as:

`Var(s) = sum_k p_k Var(s | z=k) + sum_k p_k (mean_k - mean)^2`

The terms have different interpretations:

- **Total dispersion:** heterogeneity across the complete news environment.
- **Within-topic coverage dispersion:** differing implications produced by the
  selection, framing, and interpretation of developments inside a broad topic.
- **Between-topic dispersion:** different subjects delivering different average
  implications.
- **Between-source dispersion:** differences among source-level mean
  implications within a topic-window.
- **Within-event/story dispersion:** an optional narrower robustness measure
  for headlines concerning the same specific information object.

The primary unit is `topic x information_window`. Within-event dispersion can
help isolate interpretation of common information, but it is not the gatekeeper
for the primary measure because editorial selection of sub-events is part of
the hypothesized signal.

## 3. Hypotheses And Outcomes

### Confirmatory Hypotheses

- **H1, incremental distribution information:** distributional features improve
  on a baseline containing mean market implication, news volume, topic mix,
  source mix, and pre-outcome market controls.
- **H2, topic-conditioned coverage:** within-topic coverage dispersion has
  incremental information beyond total dispersion, topic composition, and
  source composition.
- **H3, source framing and selection:** between-source dispersion in topic-level
  mean implication contributes incremental information beyond the pooled topic
  mean.
- **H4, state rather than direction:** dispersion is more consistently related
  to subsequent volatility, tail risk, or trading volume than to signed return.

H2 is the central test of the adopted theory. Specific-event dispersion remains
a secondary decomposition and supports a narrower common-information claim if
it works, but its failure does not invalidate topic-conditioned coverage
dispersion.

### Primary Outcomes

- Future realized volatility.
- Large absolute-return or tail-event indicators.

### Secondary Outcomes

- Trading volume or abnormal volume.
- Signed return.
- Reversal or continuation.
- VIX level/change when the timing and data source are suitable.

The first FOMC event study retains 60-minute post-announcement SPY realized
volatility as its confirmatory pilot outcome. Broader daily and intraday tests
will be specified separately before they are run.

## 4. Measurement Architecture

### 4.1 Universal Market-Implication Label

The market-implication question must be answerable independently of the topic:

> Taking the reality described or implied by the headline as true, considered
> on its own and using only information available in the headline, what
> near-term implication does it communicate for the S&P 500/SPY as the primary
> proxy for broad U.S. equity-market conditions?

The universal axis is the market mapping, not the topic-native mechanism. A
hawkish monetary-policy state and an escalation in a conflict are different
objects, but each can be mapped to the same bearish/neutral/bullish equity-
implication axis. The label is not a prediction of the observed return and must
not use subsequent market behavior. It is the ex ante implication of the
headline's represented reality, conditional on the headline being true and
holding omitted information unspecified.

The S&P 500/SPY is the provisional primary target because it is the broadest
available U.S. equity benchmark in the project. Interest rates and Nasdaq are
candidate alternative targets for a later design decision. Changing the target
requires a separate rubric and revalidation; the present labels cannot simply
be reinterpreted. The primary horizon is
near term and will be operationalized separately for scheduled-event and daily
designs; raters do not receive or predict the realized outcome window.

Version 1 retains the discrete scale:

- `A`: strongly adverse.
- `B`: moderately adverse.
- `C`: neutral, balanced, mixed, or descriptive.
- `D`: moderately favorable.
- `E`: strongly favorable.
- `U`: insufficient information to infer an A-E implication.

The signed numerical baseline is `[-1, -0.5, 0, 0.5, 1]`. The categories are a
measurement choice, not a claim that sentiment is naturally five-valued.
Robustness work will compare alternative spacings, class shares, tail masses,
probability-based models, and continuous scores if a reliable instrument can
be produced.

Confidence and ambiguity remain quality-control fields. They are not sentiment
features and must not be treated as calibrated probabilities without separate
evidence.

### 4.2 Topic Identity And Windows

The primary topic architecture is:

1. `topic_family`: a continuing economically interpretable discourse, such as
   Russia-Ukraine, COVID, or monetary policy.
2. `primary_topic`: the main topic family for the headline.
3. `secondary_topics`: optional additional families for multi-topic headlines.
4. `information_window`: the predeclared time interval in which coverage is
   aggregated.
5. `topic_centrality`: central, material but secondary, incidental, or unclear.
6. `event_story_cluster`: optional narrower identity used for deduplication and
   robustness analysis, not primary inclusion.

The provisional broad taxonomy is:

- Monetary policy and central banks.
- Inflation and prices.
- Labor markets.
- Growth and macroeconomic activity.
- Fiscal policy and sovereign finance.
- Banking, credit, and financial stability.
- Corporate earnings and firm-specific developments.
- Geopolitics, conflict, and trade, subdivided into named continuing conflicts
  or policy discourses for primary measurement.
- Energy and commodities.
- Technology, competition, and regulation.
- Market structure and observed market performance.
- Other or unclear.

This taxonomy is provisional. It must be audited against the corpus before it
is frozen. Headlines may receive a primary and one or more secondary topics,
but confirmatory within-topic calculations will use a documented primary-topic
rule or pre-specified fractional membership.

### 4.3 Topic-Native Mechanisms

Some topics have a meaningful internal axis, such as hawkish/dovish monetary
policy or escalation/de-escalation in a conflict. These topic-native states are
mechanisms through which a headline maps to the universal equity-implication
axis; they are not separate cross-topic sentiment scales. A later mechanism
analysis may retain them as structured explanatory labels, but the primary
dispersion measure compares the resulting A-E market implications within and
across topics. Topic-native labels are deferred until the universal implication
instrument passes validation.

### 4.4 Sentiment Model Roles

No model is ground truth. The current measurement plan assigns distinct roles:

- Two independent human raters plus blinded adjudication define the reference
  for subjective A-E/U market implication.
- `deepseek-v4.1-flash` through AvalAI is the candidate scalable production
  labeler because it can apply a conditional market-implication rubric across
  heterogeneous topics. It must emit discrete labels, not invented continuous
  precision, and retain complete run provenance.
- FinBERT is a benchmark and robustness instrument. Its class probabilities can
  supply a continuous expected-tone score and entropy, but its positive/neutral/
  negative target may capture textual financial tone rather than the specified
  implication for SPY.
- A fresh frontier-model rating is an additional machine benchmark, not a human
  vote and not an adjudicator.

DeepSeek becomes the production model only if it meets predeclared agreement,
stability, parse-success, and coverage standards on held-out human labels.
FinBERT remains a robustness measure unless it performs better on the same
human reference. Neither model may be chosen because its downstream market
regressions look stronger.

## 5. Topic Discovery And Assignment

Topics must be determined without market outcomes. The preferred procedure is
a hybrid of a predeclared taxonomy and outcome-blind topic discovery. Narrow
story clustering is secondary.

### Step 1: Build Topic-Neutral Representations

Create a concise representation that preserves entities, actions, policy
questions, and topic identity while removing bullish/bearish wording and
observed market-direction language where possible. Store both the original and
neutralized text.

This step is essential because ordinary semantic embeddings can separate
positive and negative coverage of the same topic. Such separation would
mechanically reduce the topic-conditioned dispersion that the study is meant
to measure.

### Step 2: Assign Broad Topics

Use a transparent multi-label classifier combining seed rules, semantic
similarity to topic definitions, and a model adjudicator for ambiguous cases.
The initial taxonomy and examples must be written before inspecting market
outcomes.

### Step 3: Construct Topic-Windows

Within broad topics, construct candidate daily, three-session, and weekly
topic-windows. Preserve:

- all eligible headlines and unique sources;
- primary and secondary topic membership;
- known scheduled-event identity when applicable;
- exact, near-duplicate, and syndicated-copy flags;
- optional event/story clusters for secondary decomposition.

Do not require headlines to describe the same incident. Selection of different
developments within the same topic-window is part of the primary signal. Do not
force `other_unclear` into a substantive topic. Topic assignment must respect
time and prevent future vocabulary from changing historical assignments in
out-of-sample evaluation.

### Step 4: Audit And Freeze

Validate broad-topic labels and pairwise same-topic-discourse decisions on a
stratified human-reviewed sample. Freeze the representation prompt/model,
taxonomy, assignment thresholds, information-window rule, deduplication rule,
and version hashes before testing market outcomes. Validate optional story
clusters separately if they are reported.

For forecasting tests, either fit the topic system on the training period and
assign later observations to frozen topics/centroids, or demonstrate that a
fixed outcome-blind assignment rule produces equivalent results. Unsupervised
does not automatically mean free of look-ahead bias.

## 6. Validation Design

Measurement validation is separate from testing the economic hypothesis.

### 6.1 Rater Panel

For subjective market-implication sentiment, the target validation panel is:

- Human rater 1.
- Human rater 2.
- One fresh frontier-model rater.
- The candidate scalable/production model.

The frontier model is a machine benchmark, not a third human and not ground
truth. Agreement between language models may reflect correlated model errors.

All raters must work independently from headline text alone. They must not see
event dates, sources, hidden keys, other ratings, market outcomes, or article
text. Model runs must preserve the exact model/version, prompt, decoding
settings, timestamp, raw responses, parse failures, input/output hashes, and
software environment.

The reusable fresh-session frontier prompt is stored at:

`research/prompts/FRONTIER_FOMC_RATER_PROMPT.md`

The present conversation must not be used as the independent frontier audit
because it has already inspected and discussed the existing LLM output.

Topic-family and same-topic-discourse validation use a lighter protocol adopted
on 2026-10-10: one blinded Codex machine audit followed by row-level human
`accept`, `correct`, or `unclear` verification. The human sees the agent answer,
so this yields an adjudicated human-verified reference rather than independent
inter-rater agreement. The complete procedure is recorded in
`research/topic_discovery/DESIGN_DECISION_AGENT_TOPIC_AUDIT.md`.

### 6.2 Agreement And Adjudication

Calculate agreement before adjudication:

- Raw exact and adjacent-class agreement.
- Weighted Cohen kappa for ordered A-E labels.
- Krippendorff alpha or an appropriate multi-rater statistic.
- Class-specific precision, recall, and confusion matrices against the
  adjudicated human reference.
- Separate agreement for relevance, topic, market implication, uncertainty,
  and pairwise same-topic-discourse decisions. Optional same-event decisions
  are evaluated separately.

For the agent-plus-human topic workflow, report acceptance, correction, and
unclear rates plus correction confusion by topic. Do not calculate or present
independent-rater kappa for this workflow.

Two human disagreements are adjudicated after both files are complete and
checksummed. The adjudicator must remain blind to market outcomes and, where
feasible, to machine labels. Models are selected for scale according to human
agreement, stability, cost, and coverage, never downstream market performance.

### 6.3 Existing FOMC Pilot

The frozen 150-headline sample remains useful for validating:

- FOMC relevance under the original rubric.
- Headline-only A-E equity implication.
- Confidence and ambiguity behavior.

Its limitations must remain explicit:

- It contains only FOMC candidate headlines and cannot validate the general
  topic taxonomy.
- It was sampled from event-conditioned candidates and cannot estimate label
  quality over the whole news universe.
- The existing LLM response is structurally valid but currently lacks its
  companion run metadata and raw-response audit log.
- Both human sheets remain blank as of this plan revision, so no accuracy or
  agreement claim is yet available.

After the FOMC pilot, create a second stratified general-news validation sample
covering years, sources, broad topics, candidate clusters, sentiment classes,
and difficult/unmatched cases.

## 7. Feature Construction

Construct features only after labels, topic assignment, and deduplication are
frozen. Every information window must retain headline count, source count,
topic count, and effective sample size.

### Required Baseline Features

- Mean market implication.
- Log headline count and source count/mix.
- Topic composition.
- Pre-outcome market controls.
- Calendar and event-family controls where applicable.

### Distribution Features

- Total variance or standard deviation.
- Within-topic coverage dispersion, aggregated with pre-specified topic weights.
- Between-topic dispersion.
- Equally source-weighted within-topic dispersion.
- Between-source dispersion in source-level mean implication.
- Within-event/story dispersion as a narrower robustness measure.
- Entropy over A-E classes.
- Positive and negative tail mass.
- Bipolarity: simultaneous positive and negative mass.
- Neutral and `U`/unidentifiable mass.
- Mean-orthogonal distribution contrasts.

Raw skewness and kurtosis are exploratory when headline counts are small.
Dirichlet or empirical-Bayes smoothing may be used, with unsmoothed estimates
reported as robustness checks. Minimum headline and unique-source counts per
topic-window must be set
before outcome testing; thresholds of 5, 8, 10, and 15 will be evaluated in
coverage audits, not selected by coefficient significance.

Headline-weighted, source-weighted, between-topic, within-topic, between-source,
and optional within-story features must not be entered together without
checking their algebraic relationships and design-matrix rank. The variance
decompositions should be implemented and unit-tested.

## 8. Empirical Designs

### 8.1 FOMC Repeated-Event Pilot

FOMC is the first event family because its timing is scheduled, repeated, and
supports a strict pre/post information boundary. It is an event-timed
observational design with quasi-experimental structure, not a randomized or
fully causal quasi-experiment.

- News window: three completed trading sessions through the last headline
  strictly before the 14:00 America/New_York announcement.
- Robustness windows: one and five completed trading sessions.
- Primary outcome: SPY realized volatility in `[14:00, 15:00)`.
- Primary comparison: mean-only baseline versus baseline plus validated
  within-FOMC-event distribution features.
- Controls: pre-event return/volatility, latest available VIX, prior volume,
  attention, source mix, and calendar controls.

The FOMC pilot tests whether coverage dispersion inside one repeated topic and
event family is measurable and useful. It does not establish external validity
for ordinary days or unrelated topics.

### 8.2 Broad News-Window Design

Construct daily or intraday information windows across the general corpus.
Compare:

1. Controls plus mean implication and attention.
2. Baseline plus total dispersion.
3. Baseline plus headline-weighted within- and between-topic dispersion.
4. Baseline plus source-balanced and between-source topic dispersion.
5. Baseline plus optional within-event/story dispersion where coverage permits.

This nested sequence reveals whether predictive value comes from the shape of
the whole news environment, topic composition, heterogeneous topic coverage,
or the narrower interpretation of common information.

### 8.3 Inference And Prediction

- Strictly lag all features to the prediction origin.
- Use heteroskedasticity-robust or event-clustered inference as appropriate.
- Use block/wild bootstrap and outcome-blind permutations.
- Use rolling, expanding-window, or leave-one-year-out evaluation.
- Compare adjusted R2, AIC/BIC where appropriate, RMSE, MAE, OOS R2, and a
  suitable nested forecast test.
- Report effect sizes and uncertainty, not only significance.
- Correct secondary-feature inference for multiple testing.

## 9. Robustness And Falsification

Required checks include:

- Alternative news windows and minimum cluster sizes.
- Alternative A-E numerical encodings and class-share models.
- Smoothed and unsmoothed distributions.
- Exact and near-duplicate removal.
- Source-only, leave-one-source-out, leave-one-topic-out, and leave-one-year-out
  samples.
- Stress-period exclusions specified before modeling.
- Randomly shifted event dates matched on weekday and release time.
- Pre-outcome pseudo-reaction windows.
- Sentiment shuffles within source, topic, and year.
- Topic-label and story-cluster perturbation/sensitivity tests.
- Comparison of original versus topic-neutral embeddings to detect sentiment-
  driven clustering.
- No conclusion based on a hand-selected topic, year, or individual event.

## 10. Data And Reproducibility

Current evidence includes `news.csv`, `result.csv`, the Google News event
snapshot, SPY minute data, daily market data, the student notebooks, and the
timing-safe FOMC panel under `research/event_study/`.

Every derived dataset must record source, retrieval date, timezone,
transformation version, raw checksum, code version, and licensing status. The
provenance of the student SPY data and original news acquisition must be
resolved before paper freeze.

The repository currently tracks large raw-data files despite the earlier plan
to keep them outside ordinary Git. Before further collection, choose and
document one policy: Git LFS, external immutable storage plus checksums, or a
small versioned analytical extract. Generated labels must not silently
overwrite raw or human-audit files.

## 11. Execution Phases

### Phase 0 - Baseline And Repository Reconciliation

Status: complete.

- Preserved both student analyses and the initial daily proof of concept.
- Reconciled prior development work onto `main`.
- Recorded the first provenance manifest and research roadmap.

### Phase 1 - Event Calendar And Coverage

Status: complete for the first pass.

- Built official FOMC, CPI, and employment calendars for 2020-2025.
- Audited existing-corpus coverage.
- Expanded coverage with an outcome-blind Google News RSS snapshot.
- Selected FOMC as the first viable repeated-event case study: 31 of 39 events
  passed the original three-session/eight-headline coverage rule.

### Phase 2 - Timing-Safe FOMC Panel

Status: scaffold complete.

- Constructed strict pre-announcement headline windows.
- Constructed 5-, 15-, and 60-minute post-announcement outcomes.
- Added pre-event market controls and missingness rules.
- Preserved 30 events with both the primary news gate and complete primary
  market outcome before sentiment validation.

### Phase 3a - Original FOMC Measurement Pilot

Status: in progress.

- Froze a 150-headline, outcome-blind validation sample covering all 39 events.
- Created two independently ordered human sheets and a hidden provenance key.
- Implemented a resumable Gemini/Groq labeling notebook.
- Received one structurally valid 150-row LLM response in `tmp/`.
- Still required: two human audits, a clean frontier-model audit, machine-run
  provenance artifacts, agreement analysis, and adjudication.

### Phase 3b - General Topic-Aware Measurement Design

Status: topic-window prototype, blinded Codex audit, human verification, and
production topic-rule evaluation complete; assignment revision pending.

An initial outcome-blind geopolitical expansion now covers the matched
2020-05-01 through 2025-04-30 daily-panel period. Weekly Google News RSS
queries produced candidate coverage for Russia-Ukraine, direct Iran-Israel,
and Iran-related regional conflict. The snapshot is stored separately from the
existing corpus and has not been treated as validated topic membership or
merged into market features. Historical timestamps are predominantly date-
level, so the data are currently eligible for daily topic-window analysis, not
minute-level reaction measurement.

The first implementation is documented in
`research/topic_discovery/README.md`. It builds a 172,039-record canonical
corpus, assigns transparent provisional broad-topic candidates, creates
topic-neutral baseline text, and performs chronological story clustering on a
deterministic 5,000-record pilot. The pilot produced 4,398 candidate clusters
and a 200-pair exploratory audit. The first 100 rows have one completed human
review and are interpreted using the reviewer's broader continuing-topic
definition. A live one-record AvalAI test confirmed
that `deepseek-v4.1-flash` can return the required neutral-text/entity schema;
bulk LLM processing has not been run.

These are measurement-development results, not substantive findings. The
provisional rules leave 107,692 records as `other_unclear`, and manual inspection
found actor- and token-driven false joins in residual news. The adopted primary
construct is now topic-conditioned coverage dispersion over bounded time
windows; exact story identity is secondary. The taxonomy, topic-assignment
procedure, information window, and source-balancing rules remain unfrozen.
Details are recorded in
`research/topic_discovery/DESIGN_DECISION_TOPIC_WINDOWS.md` and the pilot
report.

Taxonomy v2 now defines 18 continuing topic families and assigns the full
172,039-record canonical corpus using transparent rules plus similarity to
versioned topic prototypes. It assigns 64,347 records and retains 107,692 as
`other_unclear` instead of forcing coverage. A fresh validation package contains
180 single-headline topic assignments and 100 same-topic-discourse pairs,
independently ordered rater sheets, and hidden keys. The rater-1 sheets are
reserved for the blinded Codex audit followed by separate human verification;
rater-2 files remain unused fallback artifacts. Candidate 1-, 3-, and 5-session
windows have been compared using headline and unique-source coverage only; no
market outcomes were consulted and no primary window has been selected yet.

The blinded Codex audit completed all 180 rater-1 headline assignments and 100
rater-1 topic-discourse pairs on 2026-10-10 without inspecting hidden keys,
rater-2 files, source/date metadata, assignments, market data, or web results.
The cleaned human verification accepts 159 headline judgments, corrects 19, and
leaves 2 unclear; it accepts 98 pair judgments and corrects 2. The project keeps
the existing `iran_israel` family rather than adding an Iran-regional family.
This is not independent inter-rater annotation and will be reported accordingly.

Opening the hidden keys after verification produced 178 resolved headline
references and 100 resolved pair references. The Codex audit agreed with the
final headline topic in 89.3% of resolved cases and with the final pair relation
in 98.0%. The current production system reached 73.0% exact headline accuracy
(78.7% when its second candidate counts) and 86.0% pair accuracy. Its 48
high-confidence headline assignments were 97.9% accurate, while low-confidence
and unassigned cases were only 64.7% and 60.0% accurate. These are stratified
validation-sample metrics, not estimates of corpus-wide prevalence or error.
The taxonomy remains useful, but the current headline assigner is not frozen.

A candidate selective-classification policy now automatically accepts any
substantive assignment with score at least 0.28 and margin at least 0.05. It
does not add topic-specific exclusions based on the two observed incidental-
mention errors. On the development sample, the gate accepts 53 resolved cases
with 96.2% accuracy. Applied to the corpus, it accepts 44,991 records (69.9% of
the 64,347 substantively assigned records), routes 19,356 weaker substantive
assignments for outcome-blind review, and retains 107,692 records as
`other_unclear`. The thresholds were selected on the existing adjudicated
sample and therefore require a fresh holdout before freeze. Moreover, only 60%
of the 40 deliberately sampled `other_unclear` cases were truly outside the
taxonomy, so missed-topic recall remains a separate measurement risk.

The coverage audit shows a source-universe asymmetry that must constrain the
design: named geopolitical topics have many Google News sources, whereas most
economic topics currently rely mainly on the New York Times and Guardian.
Between-source inference must therefore be reported by topic and cannot assume
equivalent source breadth without further data expansion.

Deliverables:

1. Universal market-implication rubric independent of FOMC relevance.
2. Versioned broad-topic taxonomy and annotation schema.
3. Topic-neutral representation procedure.
4. Outcome-blind topic-family assignment and topic-window construction.
5. Pairwise same-topic-discourse validation sample.
6. Stratified general-news sentiment/topic validation sample.
7. Agreement report and frozen production labeling decision.

No downstream outcome comparison should be used to tune these components.

### Phase 3c - General Market-Implication Measurement

Status: design and 240-headline blinded validation package implemented;
independent ratings and model benchmark results pending.

The primary sentiment variable is the discrete A-E/U implication of the
headline's represented reality for the S&P 500/SPY. DeepSeek is the candidate
scalable instrument; FinBERT supplies a probability-based benchmark and
continuous-score robustness check. Two independent human ratings, a clean
frontier-model benchmark, and blinded human adjudication are required before a
production model is frozen. Topic-native axes such as hawkish/dovish and
escalation/de-escalation are explanatory mechanisms, not replacements for the
common market axis.

The validation package samples 80 headlines from each selective topic route:
automatic substantive assignment, substantive assignment awaiting review,
and retained `other_unclear`. It excludes the earlier topic audit, removes
duplicate groups, spans all six corpus years and both origin types, and hides
source, date, topic, route, and the 120/120 development/holdout split. Two
independent human sheets, a fresh frontier input, a hidden key, a general
rubric, persisted model prompt, manifest, and resumable DeepSeek/FinBERT
benchmark runners are in `research/sentiment/`. No labels have yet been
collected for this package.

### Phase 4 - Feature Registry And Coverage Gate

Implement and unit-test the total/within/between variance decomposition,
distribution features, effective sample sizes, and smoothing. Produce coverage
tables before inspecting outcome associations. Freeze one primary dispersion
measure for the FOMC pilot and one for the broad design.

### Phase 5 - FOMC Pilot Models

Estimate the mean-only baseline and incremental distribution models for the
pre-specified 60-minute outcome. Run timing, source, count, placebo, influence,
and out-of-sample checks. Interpret results as a repeated-event pilot.

### Phase 6 - Broad Topic-Aware Models

Estimate the nested total/between/within design on daily or timing-safe
intraday windows. Determine whether any result is attributable specifically to
topic-conditioned coverage dispersion or between-source coverage differences
rather than general news mixture. Treat within-story dispersion as secondary.

### Phase 7 - Replication And External Validity

Replicate on additional scheduled-event families and then selected prolonged or
unscheduled stories such as major conflicts, banking stress, or COVID-era news.
These extensions require their own timing and feedback-bias analysis.

### Phase 8 - Paper Freeze

Lock data, prompts, labels, code, tables, and figures. Verify citations and
licenses, disclose null results and specification changes, and write claims at
the level supported by the decomposition and validation evidence.

## 12. Decision Rules

- Call the primary construct topic-conditioned coverage dispersion, not direct
  investor-belief dispersion or disagreement about the same fact.
- Treat editorial selection of different sub-events within one topic-window as
  part of the signal rather than noise.
- Keep topic assignment, window selection, and optional clustering blind to
  market outcomes.
- Exclude `other_unclear` from primary within-topic calculations without
  deleting those headlines from total-news measures.
- Report headline-weighted and equally source-weighted versions.
- Keep mean implication in every incremental distribution specification.
- Keep attention, topic composition, and pre-outcome market state in the
  baseline.
- Do not equate model agreement with human validity.
- Do not use this conversation as a clean frontier audit of the existing sample.
- Do not select labels, topics, clustering parameters, or models because they
  produce favorable market results.
- Treat FOMC as the first controlled case study, not the definition of the
  general theory.
- Treat predictive evidence as associational unless a stronger identification
  strategy is established.

## 13. Immediate Next Steps

1. Complete the two independent broad-news human ratings and one clean
   frontier-model rating using the frozen 240-headline package.
2. Run bounded DeepSeek and FinBERT benchmarks, inspect parse failures and
   class behavior on development rows, and reserve holdout rows for the final
   measurement comparison.
3. Validate the candidate score >= 0.28 and margin >= 0.05 selective gate on a
   fresh outcome-blind holdout, including a dedicated audit of `other_unclear`
   false negatives.
4. Outcome-blindly adjudicate the 19,356 weaker substantive assignments, using
   active sampling before any full model run; do not force general news into a
   topic family.
5. Select the primary 1-, 3-, or 5-session window from validated topic
   reliability, coverage, headline counts, and unique-source counts only.
6. Decide whether to expand non-geopolitical source coverage before treating
   between-source dispersion as confirmatory.
7. Specify and test headline-weighted, equally source-weighted, and
   between-source topic dispersion estimators, including duplicate and minimum-
   coverage rules.
8. In parallel, complete the two human FOMC audits and one clean frontier-model
   audit, then measure and adjudicate A-E market-implication reliability.
9. Proceed to Phase 4 only after both topic identity and market implication pass
   their predeclared measurement gates.
