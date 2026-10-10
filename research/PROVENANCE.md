# Data Provenance

Initial inputs were checked on 2026-08-17; the event expansion snapshot was
added on 2026-08-18 and the geopolitical snapshot on 2026-10-09. Some earlier
raw inputs were subsequently committed to Git. New retrieval caches and large
normalized snapshots are kept local while code, configuration, checksums, and
aggregate diagnostics are versioned.

| File | Bytes | SHA-256 | Status |
| --- | ---: | --- | --- |
| `result.csv` | 21,291,011 | `e9dc719c83054a466cd22d96d3073fd1ac472d4d6d88957d5220b27fb8cccac3` | Primary labeled news input |
| `news.csv` | 29,840,992 | `1b3ffac50e7099df3ec4b55bebee8b5586f88b7d6699f707adad2294a988f94e` | Raw news input |
| `data/news_data.csv` | 21,291,011 | `e9dc719c83054a466cd22d96d3073fd1ac472d4d6d88957d5220b27fb8cccac3` | Byte-identical copy of `result.csv` |
| `data/news_daily_data` | 56,531 | `953611e383999d40d4ca1663b6825c2df3491520aaad4d222d6d2258619e62e0` | Second-student daily market/news panel |
| `data/spy_1min_data` | 36,448,727 | `3ddb221e294ceb46194cdf889b06fb96a49fec3f116c7211dc2537cfa3d99ef9` | Second-student SPY minute bars |
| `data/market_panel.csv` | 70,801 | `ab67ec48f22d304b46b5f140ea27a0e65e8f608f0ef61334f2448279bfe541da` | Daily SPX/VIX cache |
| `data/google_news_event_headlines.jsonl` | 6,089,357 | `6cc37f5d4af0d5642d461dbd1945f038ec0d55b9db49908085a1abee89db03a3` | Historical RSS feasibility snapshot; not paper-approved |
| `data/fomc_phase2_event_panel.csv` | 46,693 | `2272a5dcb12fe72f2ff58010784ab686771daf0124b167d73e5d23658119fc1c` | Derived Phase 2 local event panel |
| `data/fomc_phase2_headline_review.csv` | 98,183 | `7ccb6a5dbccd157924ed96cce064dc36911e8d12c10d0bb23d4ccc6422229932` | Derived Phase 2 relevance-review sheet |
| `data/fomc_phase3_validation_rater_1.csv` | 13,630 | `2ef0dad04e0531f902f438ece3f88036093d8c38e71e8dfed2a130ce36fd0f67` | Blinded Phase 3 rater 1 sheet |
| `data/fomc_phase3_validation_rater_2.csv` | 13,630 | `9c1064a7a0c9119f7aca99646656b59c3de7b1bba81ff1ea93acb02520a1f42f` | Blinded Phase 3 rater 2 sheet |
| `data/fomc_phase3_validation_key.csv` | 31,443 | `3a9c38c6a1ffbb752046e4b889acc488de759c63b6ee64669d6d85cf9c97006e` | Hidden Phase 3 provenance key; do not give to raters |
| `data/geopolitical_news_google.jsonl` | 27,396,134 | `fcebe64a1ceac35e93a947995935c03e96b8d961aa9be4f3c7f58be9545b024c` | Local outcome-blind geopolitical expansion; candidate retrieval, not validated topic labels |
| `data/topic_discovery_corpus.parquet` | 48,348,464 | `2f8cad765dfab704385820ec8882b655bb9a38a7db4074bd2badeceeeb7ba67b` | Local canonical topic-discovery corpus; rules and counts in versioned manifest |
| `data/topic_discovery_pair_audit.csv` | 35,304 | `adfd80d06afd5bf616ad37017a158a05471b88675c602ad5ba08b75800864bfe` | First 100 rows completed by one reviewer under the broad continuing-topic interpretation; remaining rows blank |
| `data/topic_family_v2_assignments.parquet` | 50,215,987 | `62155c719042f5bc3917f03c826b0636985e6c71c1214c49c368f4f641d4a413` | Candidate v2 topic-family assignments; not frozen |
| `data/topic_family_v2_validation_rater_1.csv` | 24,761 | `f64bc7f4fce14d8b700ac3c2b079538c8a1789647b18e23b95e3fb7bb9e88c56` | Completed blinded 180-headline Codex topic audit |
| `data/topic_family_v2_validation_rater_2.csv` | 17,823 | `f5996f1639b6c3d94264bc01aa8815e601c470e7857ba7df00ef4c4a66685e40` | Fresh blinded 180-headline topic audit, rater 2 |
| `data/topic_family_v2_validation_key.csv` | 32,805 | `f254f2e1455ac29775cc33806542087932fc0832c4424e3c29acc9463815ec09` | Hidden machine assignment key for the 180-headline audit |
| `data/topic_family_v2_pair_rater_1.csv` | 19,471 | `fff47f1d6805e3379af73cb2ee41771732c3ebe094082c6610d63fe339ac3afa` | Completed blinded 100-pair Codex topic-discourse audit |
| `data/topic_family_v2_pair_rater_2.csv` | 17,134 | `8fe15768d270a742a32ca176ce1aad63bb440ce970a130d76c6f9a19a57f67de` | Fresh blinded 100-pair topic-discourse audit, rater 2 |
| `data/topic_family_v2_pair_key.csv` | 23,997 | `02d35bceeebc19f1315c4246242e4ad8472a180557d9419df88ecea46b0e0860` | Hidden machine relation key for the 100-pair audit |
| `data/topic_family_v2_validation_human_verification.csv` | 25,984 | `775ceddcc63c2fe75bee975d74788ac14ab68c8ebaeb451b816d42b5cc75d872` | Blank human accept/correct review of the completed Codex headline audit |
| `data/topic_family_v2_pair_human_verification.csv` | 19,955 | `c7b4bb0e515db06781354993734fea2ed67c78fb60a275d005575b5164ffd8a8` | Blank human accept/correct review of the completed Codex pair audit |

## Source Status

- `result.csv` and `news.csv`: derived from NYTimes and Guardian headlines.
  The exact API query, retrieval date, and redistribution terms still need to
  be recovered from the student pipeline before publication.
- `data/spy_1min_data`: source and license are not recorded in the submitted
  files. Its regular-session clock and rounded within-bar percentage-change
  field support the working interpretation that naive timestamps are Eastern
  bar-start times, but this is an inference rather than provider documentation.
  Two FOMC dates have incomplete primary windows (`2021-04-28` and
  `2022-01-26`), and one otherwise eligible date (`2023-03-22`) has three
  zero-volume bars. Another (`2021-12-15`) lacks the required 15 clean volume
  baseline sessions. It is acceptable for a feasibility audit, but it must not
  be the sole market-data source in the paper until provenance is established.
- `data/market_panel.csv`: appears to contain daily S&P 500 and VIX data. Its
  acquisition script and provider metadata still need to be documented.
- `data/google_news_event_headlines.jsonl`: generated on 2026-08-18 from 159
  event-bounded Google News RSS queries. The accepted snapshot contains 5,933
  event-result records. Historical timestamps are often date-like, Google
  rankings can change on rerun, and the RSS terms restrict reuse. Keep this as
  an outcome-blind coverage pilot unless its use and archiving terms are found
  acceptable for publication.
- `data/fomc_phase2_event_panel.csv` and
  `data/fomc_phase2_headline_review.csv`: reproducible ignored working files
  generated by `research/event_study/phase2_event_panel.py`. The first contains
  event-level aggregates; the second contains the 514 selected FOMC
  event-headline occurrences and blank manual-review fields.
- `data/fomc_phase3_validation_rater_1.csv` and
  `data/fomc_phase3_validation_rater_2.csv`: separate outcome-blind audit files
  generated by `phase3_validation_sample.py`. They contain only random sample
  IDs, headline text, and blank human-label fields, in different orders.
- `data/fomc_phase3_validation_key.csv`: maps the 150 sample IDs back to event,
  date, source, and normalized headline metadata. Keep it hidden until both
  independent audits are checksummed and complete.
- `data/geopolitical_news_google.jsonl`: generated on 2026-10-09 from 783
  explicit seven-day Google News RSS queries spanning 2020-05-01 through
  2025-04-30. It contains 30,751 topic-records, 29,947 distinct normalized
  headlines, and 2,074 reported sources across Russia-Ukraine, direct
  Iran-Israel, and Iran-related regional-conflict queries. Google results are
  ranked rather than exhaustive; 169 Russia-Ukraine, 15 direct Iran-Israel,
  and 2 regional-conflict weeks hit the 100-result feed cap. Almost all
  historical timestamps are date-like 07:00/08:00 UTC values, so this snapshot
  is suitable for topic discovery and daily analysis only until publisher
  timestamps are verified. Query relevance, source identity, syndication, and
  near-duplicate stories remain unaudited. Raw feeds and the normalized local
  output are ignored from ordinary Git; the code, topic definitions, checksum,
  and diagnostic manifest are versioned.
- `data/topic_discovery_corpus.parquet`: generated by
  `research/topic_discovery/build_corpus.py` from `news.csv` and
  `data/geopolitical_news_google.jsonl`. It contains 172,039 canonical records,
  stable identifiers, source normalization, exact duplicate-group identifiers,
  provisional rule-based topic candidates, and deterministic topic-neutral
  baseline text. It is a local measurement-development artifact, not a labeled
  paper dataset. The input hashes, row counts, date coverage, and topic counts
  are recorded in
  `research/topic_discovery/artifacts/canonical_corpus_manifest.json`.
- `data/topic_discovery_pilot_assignments.csv`,
  `data/topic_discovery_pair_audit.csv`, and
  `data/topic_discovery_pair_key.csv`: ignored local outputs of the deterministic
  5,000-record clustering pilot. Their hashes and exact parameters are stored in
  `research/topic_discovery/artifacts/topic_discovery_pilot_manifest.json`.
  The key was opened programmatically after the first 100 judgments were saved
  in order to diagnose the pilot; this file is therefore exploratory and should
  not be reused as an independent blinded validation sample.
  The pilot manifest identifies the originally generated blank audit; the table
  above separately records the reviewed file state. The first review used
  `same_story` to mean a coherent continuing topic discourse, an interpretation
  formally adopted and bounded in
  `research/topic_discovery/DESIGN_DECISION_TOPIC_WINDOWS.md`.
- `data/topic_family_v2_assignments.parquet`: generated by
  `research/topic_discovery/assign_topic_families.py` from the canonical corpus
  and `taxonomy_v2.json`. It combines transparent headline rules with similarity
  to versioned topic definitions/examples. No sentiment labels or market
  outcomes are inputs. The representation is fit on the complete outcome-blind
  corpus for measurement development and must be frozen or train-period fit for
  forecasting evaluation. Counts, parameters, and hashes are recorded in
  `research/topic_discovery/artifacts/topic_family_v2_assignment_manifest.json`.
- The six `topic_family_v2_*rater*` and `*_key.csv` files are generated by
  `research/topic_discovery/build_topic_validation.py`. Rater files contain no
  source, date, or machine answer and use independent row order; pair files also
  independently swap headline A/B order. Keep both key files hidden until both
  reviews are complete and checksummed. Full blinding diagnostics and hashes are
  recorded in
  `research/topic_discovery/artifacts/topic_family_v2_validation_manifest.json`.
- On 2026-10-10, the rater-1 headline and pair files were completed as a single
  blinded Codex machine audit using only the persisted guide and headline text.
  The hidden keys, rater-2 files, assignments, sources, dates, market data, and
  web search were not inspected by the auditing agent. The separate human-
  verification files were generated by `build_human_verification.py`; they
  preserve the agent labels and require explicit `accept`, `correct`, or
  `unclear` decisions. This workflow is not independent inter-rater annotation.
  Its hashes and protocol are recorded in
  `research/topic_discovery/artifacts/topic_family_v2_agent_audit_manifest.json`.
- `research/topic_discovery/artifacts/topic_window_coverage_v2.csv`: generated
  from v2 topic assignments and the date column of `data/market_panel.csv`.
  Publication dates map to the first market session on or after publication.
  The comparison uses headline and unique-source counts only; no prices,
  returns, volatility, volume, or other market outcomes are inspected.
- FOMC dates: official Federal Reserve meeting calendars.
- CPI and Employment Situation dates: official BLS annual release calendars.

## Required Before Paper Freeze

1. Recover the students' raw-data acquisition scripts and API terms.
2. Record column definitions, timezone conventions, and all transformations.
3. Independently verify SPY prices around a random sample of events.
4. Recompute this manifest whenever a raw input changes.
