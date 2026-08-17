# Data Provenance

Initial inputs were checked on 2026-08-17; the expansion snapshot was added on
2026-08-18. Raw data files are intentionally excluded from Git; only this
manifest, code, official calendars, and aggregate outputs are versioned.

| File | Bytes | SHA-256 | Status |
| --- | ---: | --- | --- |
| `result.csv` | 21,291,011 | `e9dc719c83054a466cd22d96d3073fd1ac472d4d6d88957d5220b27fb8cccac3` | Primary labeled news input |
| `news.csv` | 29,840,992 | `1b3ffac50e7099df3ec4b55bebee8b5586f88b7d6699f707adad2294a988f94e` | Raw news input |
| `data/news_data.csv` | 21,291,011 | `e9dc719c83054a466cd22d96d3073fd1ac472d4d6d88957d5220b27fb8cccac3` | Byte-identical copy of `result.csv` |
| `data/news_daily_data` | 56,531 | `953611e383999d40d4ca1663b6825c2df3491520aaad4d222d6d2258619e62e0` | Second-student daily market/news panel |
| `data/spy_1min_data` | 36,448,727 | `3ddb221e294ceb46194cdf889b06fb96a49fec3f116c7211dc2537cfa3d99ef9` | Second-student SPY minute bars |
| `data/market_panel.csv` | 70,801 | `ab67ec48f22d304b46b5f140ea27a0e65e8f608f0ef61334f2448279bfe541da` | Daily SPX/VIX cache |
| `data/google_news_event_headlines.jsonl` | 6,089,357 | `6cc37f5d4af0d5642d461dbd1945f038ec0d55b9db49908085a1abee89db03a3` | Historical RSS feasibility snapshot; not paper-approved |

## Source Status

- `result.csv` and `news.csv`: derived from NYTimes and Guardian headlines.
  The exact API query, retrieval date, and redistribution terms still need to
  be recovered from the student pipeline before publication.
- `data/spy_1min_data`: source and license are not recorded in the submitted
  files. It is acceptable for a feasibility audit, but it must not be the sole
  market-data source in the paper until provenance is established.
- `data/market_panel.csv`: appears to contain daily S&P 500 and VIX data. Its
  acquisition script and provider metadata still need to be documented.
- `data/google_news_event_headlines.jsonl`: generated on 2026-08-18 from 159
  event-bounded Google News RSS queries. The accepted snapshot contains 5,933
  event-result records. Historical timestamps are often date-like, Google
  rankings can change on rerun, and the RSS terms restrict reuse. Keep this as
  an outcome-blind coverage pilot unless its use and archiving terms are found
  acceptable for publication.
- FOMC dates: official Federal Reserve meeting calendars.
- CPI and Employment Situation dates: official BLS annual release calendars.

## Required Before Paper Freeze

1. Recover the students' raw-data acquisition scripts and API terms.
2. Record column definitions, timezone conventions, and all transformations.
3. Independently verify SPY prices around a random sample of events.
4. Recompute this manifest whenever a raw input changes.
