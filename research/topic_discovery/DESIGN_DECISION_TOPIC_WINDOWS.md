# Design Decision: Topic-Window Coverage Dispersion

Date: 2026-10-09
Status: adopted for the primary design

## Decision

The primary unit for distributional sentiment will be a **time-bounded broad
topic discourse**, not a cluster restricted to headlines describing the same
specific event.

For a topic such as Russia-Ukraine, COVID, or monetary policy, news outlets may
select different developments, actors, or consequences to emphasize during the
same information window. Those editorial choices are part of the communicated
market implication. A headline about Ukrainian mobilization and a headline
about Russian repression need not report the same incident to contribute to the
distribution of implications associated with Russia-Ukraine coverage.

The primary construct is therefore:

> **Topic-conditioned coverage dispersion:** the distribution of headline-level
> market implications communicated across coverage of the same predeclared
> topic during the same information window.

This construct combines editorial selection, agenda-setting, framing, and
interpretation. It is a distribution of news-implied market implications; it is
not a direct observation of investor beliefs.

## Rationale

Requiring identical underlying events would remove an important mechanism from
the study. Outlets express perspectives not only through wording but through
which aspects of a broader topic they choose to cover. That selection can make
two news environments with the same average sentiment economically different.

The first 100-pair audit supports this decision qualitatively. COVID and major
war coverage were readily recognized as coherent continuing discourses, while
false joins were concentrated in the residual `other_unclear` category. This
suggests that the immediate measurement problem is defensible topic membership,
not exact-event identity.

## Operational Definition

The primary observational cell is `topic x information_window`. Candidate
windows are one trading day, three completed trading sessions, and one week.
One window will be frozen as primary from coverage and reliability diagnostics
before market-outcome estimation; the others will be robustness checks.

Each cell should retain:

- headline-level market-implication labels;
- unique source count and headline count;
- headline-weighted mean and dispersion;
- equally source-weighted mean and dispersion;
- between-source dispersion in source-level mean implication;
- positive, negative, neutral, and unidentifiable mass;
- topic-membership confidence and effective sample size.

The source-balanced measures are essential because the theory explicitly
includes outlet selection and framing. A prolific outlet must not mechanically
dominate the topic distribution.

## Topic Rules

- Topics must be defined and assigned without market outcomes.
- The taxonomy should be broad enough to capture continuing discourse but
  specific enough to have a common economic interpretation. `Geopolitics` alone
  is too broad; Russia-Ukraine, Israel-Gaza, and Iran-Israel are candidate topic
  families.
- Multi-topic headlines may receive pre-specified fractional membership or a
  primary topic plus secondary tags.
- `other_unclear` is not a substantive topic and is excluded from primary
  within-topic dispersion calculations.
- A topic represented by only one eligible headline or source in a window does
  not yield an estimable primary dispersion measure. The headline remains in
  total-news and attention measures.
- Exact duplicates and syndicated copies must not count as independent views.

## Interpretation And Claims

The primary result may be described as topic-conditioned coverage dispersion,
news-implied implication dispersion, or heterogeneity in topic coverage.

It must not automatically be described as:

- disagreement about the same fact;
- dispersion of investor beliefs;
- evidence of source bias without a separate source-comparison design;
- a causal media effect on the market.

Specific-event or story clustering is retained only as a secondary robustness
decomposition. It can isolate common-information interpretation, but it is no
longer the gatekeeper for inclusion in the primary topic-conditioned measure.

## Consequences For Existing Artifacts

The completed first 100 rows of `data/topic_discovery_pair_audit.csv` remain an
exploratory audit, but its `same_story` column should be interpreted according
to the reviewer-used broader notion of a coherent continuing topic. Future
audit files should use the unambiguous field name `same_topic_discourse` and ask
whether both headlines belong to the same predeclared topic family within a
reasonable time window.

The existing chronological story-clustering prototype remains useful for error
analysis, deduplication, and secondary robustness tests. Its pairwise precision
is no longer the primary measurement-validation target.
