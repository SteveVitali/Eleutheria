# Live-run fetch records (P21.3, ADR-065)

Each real (`--mode live`) connector run writes one immutable, dated fetch record
here: `<date>_<source>.json`. A record carries **provenance only** — the URL list,
status codes, byte counts, capture digests (the bytes live content-addressed in the
OCFL evidence store, never here), claim count, duration, and the crawler-conduct
evidence (`rate_limit_events` + `robots_decisions`). It contains **no content** and
**no credential** (SIG-INGEST-015, §3.1, RISK-P21-05). Records are append-only: a
re-run writes a new dated file, never edits an existing one (P1–P3).

This directory is **empty** while HG-03 is pending: no source has been flipped to a
green `review-status`, so `run --mode live` refuses (exit 3) and no fetch occurs.
The format is proven over the local stub in `tests/connectors/test_runner.py`.
