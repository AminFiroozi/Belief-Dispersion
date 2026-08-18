# Google News Coverage Expansion

This is an outcome-blind feasibility experiment using historical Google
News RSS result metadata. It is not yet an approved paper dataset.

## Conservative Timing Rule

Historical RSS timestamps are frequently date-like rather than reliable
publication clock times. The audit therefore excludes every release-day
headline and counts only unique headlines dated in completed pre-event
sessions. Official Federal Reserve and BLS pages are excluded, and every
headline must pass a transparent family-specific title relevance filter.

- Retrieved event-result records: 5,933
- Raw feeds and headline metadata: local `data/` directory (not in Git)
- Primary gate: three completed sessions and at least eight headlines

## Primary Coverage Gate

| Family | Events with >=8 headlines | Total events | Standalone viable (>=25) |
| --- | ---: | ---: | --- |
| fomc | 31 | 39 | yes |
| cpi | 13 | 60 | no |
| employment | 6 | 60 | no |
| pooled | 50 | 159 | n/a |

## Sensitivity

| Family | Sessions | Mean | Median | Max | >=5 | >=8 | >=10 | >=15 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fomc | 1 | 4.87 | 5.00 | 14 | 22 | 6 | 2 | 0 |
| fomc | 3 | 13.18 | 13.00 | 30 | 35 | 31 | 27 | 17 |
| fomc | 5 | 17.21 | 17.00 | 36 | 37 | 31 | 30 | 27 |
| cpi | 1 | 2.20 | 2.00 | 8 | 7 | 2 | 0 | 0 |
| cpi | 3 | 4.27 | 3.00 | 15 | 24 | 13 | 7 | 1 |
| cpi | 5 | 5.25 | 4.00 | 15 | 28 | 18 | 11 | 1 |
| employment | 1 | 1.95 | 1.00 | 9 | 5 | 1 | 0 | 0 |
| employment | 3 | 3.58 | 3.00 | 11 | 17 | 6 | 3 | 0 |
| employment | 5 | 4.72 | 4.00 | 15 | 29 | 7 | 3 | 2 |

## Source Breadth In Primary Windows

| Family | Accepted event-headlines | Distinct sources | Top source share |
| --- | ---: | ---: | ---: |
| fomc | 514 | 206 | 12.4% |
| cpi | 256 | 114 | 11.3% |
| employment | 215 | 93 | 13.5% |

## Methodological Status

Passing this gate establishes approximate coverage, not validated relevance
or predictive value. The local audit sample must be manually reviewed.
Google News RSS terms restrict reuse, and result rankings are not a stable
sampling frame. A paper should prefer a documented API/archive with
reproducible access.
This source can justify the next data-acquisition step but should not be
silently merged with the student labels.

## Decision

FOMC clears the preliminary title-filtered coverage gate and should be
prioritized as the first case study. CPI and Employment Situation do not
clear the same primary gate and remain deferred. Before outcome modeling,
the FOMC sample still requires manual relevance review, a stable archival
data source or frozen local snapshot with acceptable terms, and new
sentiment labels generated under a documented measurement protocol.
