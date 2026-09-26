# Live-run fetch records (P21.3, ADR-065)

Each real (`--mode live`) connector run writes one immutable, dated fetch record
here: `<date>_<source>.json`. A record carries **provenance only** — the URL list,
status codes, byte counts, capture digests (the bytes live content-addressed in the
OCFL evidence store, never here), claim count, duration, and the crawler-conduct
evidence (`rate_limit_events` + `robots_decisions`). It contains **no content** and
**no credential** (SIG-INGEST-015, §3.1, RISK-P21-05). Records are append-only: a
re-run writes a new dated file, never edits an existing one (P1–P3).

The format is proven over the local stub in `tests/connectors/test_runner.py`.
Since the HG-03/HG-02/ADR-085 flips (P25.1–P25.5), real dated records live here —
including honest non-fetch outcomes (`ccops_sf` SIG-INGEST-012 robots refusal) and
per-document politeness refusals / `link_rotted` disappearances recorded on the
parent fetch record (P25.5 live-extraction run, 2026-09-16).
