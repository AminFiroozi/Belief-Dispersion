# Geopolitical News Collection Report

Retrieved: 2026-10-09  
Sample: 2020-05-01 through 2025-04-30  
Source: Google News RSS historical search results

## Purpose

This outcome-blind expansion adds multi-source candidate headlines for the
Russia-Ukraine war and Iran-centered conflicts. It complements the existing
NYTimes/Guardian corpus. It has not been merged into that corpus, assigned
sentiment, or used with market outcomes.

## Sampling Frame

- Three versioned topic queries.
- One query per topic per seven-day interval.
- 261 intervals per topic and 783 cached RSS feeds in total.
- Up to 100 ranked Google News results per topic-week.
- Local post-parse enforcement of every requested date boundary.

## Output Audit

| Measure | Value |
| --- | ---: |
| Topic-records | 30,751 |
| Distinct normalized headlines | 29,947 |
| Distinct Google News URLs | 30,162 |
| Distinct reported sources | 2,074 |
| URLs returned under multiple topic queries | 588 |
| Exact normalized headlines also in `news.csv` | 425 |

| Candidate topic | Records | Distinct headlines | Sources | Capped weeks |
| --- | ---: | ---: | ---: | ---: |
| Russia-Ukraine war | 17,699 | 17,553 | 1,416 | 169 |
| Direct Iran-Israel conflict | 7,472 | 7,441 | 760 | 15 |
| Iran-related regional conflict | 5,580 | 5,550 | 775 | 2 |

The largest source is Reuters with 1,913 topic-records, or 6.2% of the output.
The next largest sources are Al Jazeera, BBC, Atlantic Council, Radio Free
Europe/Radio Liberty, and PBS. Source names are Google-provided labels and have
not yet been normalized into source families.

## Integrity Checks

- No missing or unparseable timestamps.
- No retained record falls outside 2020-05-01 through 2025-04-30.
- The collector rejected 946 results that Google returned outside their
  requested weekly interval.
- Per-topic URL duplicates are removed.
- Raw weekly feeds are cached and the normalized output is written atomically.
- Output SHA-256:
  `fcebe64a1ceac35e93a947995935c03e96b8d961aa9be4f3c7f58be9545b024c`.

## Limitations And Use Gate

- Google News rankings are not an exhaustive or stable sampling frame.
- Capped weeks, especially Russia-Ukraine weeks, are incomplete ranked samples.
- 99.1% of timestamps are exactly 07:00 or 08:00 UTC and should be treated as
  publication dates rather than reliable publication times.
- Query membership is a candidate topic label, not validated relevance.
- Syndicated copies, near-duplicate stories, opinion pieces, and source-family
  identities still require auditing.
- Google News URLs and publisher material remain subject to applicable access
  and reuse terms.

The dataset may now be used for topic-taxonomy discovery, source-diversity
audits, and daily coverage analysis. It must not enter intraday reaction models
or final sentiment distributions until relevance, deduplication, source, and
timestamp validation are complete.
