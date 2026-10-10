# Geopolitical News Collection

This module collects outcome-blind, headline-level snapshots for the Russia-
Ukraine war and Iran-centered regional conflicts. It complements the NYTimes/
Guardian corpus; it does not silently merge with or relabel it.

The configured sample runs from 2020-05-01 through 2025-04-30 to match the
current daily news/market panel. The default sampling frame requests up to 75
relevance-ranked English headlines for each topic in each seven-day interval.
Queries are broad candidate filters. Every record still requires topic-
relevance, syndication, and timestamp validation.

The production expansion uses the repository's established Google News RSS
mechanism:

```bash
/home/hamid/.pyenv/versions/fnlp/bin/python -m research.geopolitical.google_news_collector
```

The alternative GDELT collector can be run with:

```bash
/home/hamid/.pyenv/versions/fnlp/bin/python -m research.geopolitical.collector
```

The GDELT collector:

- requests explicit historical intervals from the GDELT DOC 2.0 API;
- uses a bounded worker pool and resumable per-window cache;
- uses the public HTTP endpoint because GDELT's HTTPS listener timed out during
  this collection; no credentials are sent, and raw responses are checksummed;
- caches every raw JSON response under `data/gdelt_geopolitical_cache/`;
- records every result-capped weekly window in the manifest;
- writes normalized topic-records to `data/geopolitical_news_gdelt.jsonl`;
- writes checksums and diagnostics to
  `research/geopolitical/artifacts/geopolitical_collection_manifest.json`.

`gdelt_seen_utc` is the time GDELT saw the article, not a guaranteed publisher
timestamp. Do not use it for minute-level reaction windows until it has been
validated against publisher metadata.
