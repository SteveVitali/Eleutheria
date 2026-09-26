#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Feed the records-request outcome log from real MuckRock activity (P25.9 / BL-028).

Two feeders, both append-only and both recording only *observed* data:

* ``--spine`` — read the hosted claim spine's ``records_request`` predicate
  surface (the claims the ``records`` connector wrote from real api_v2 pulls,
  e.g. the ``sig-ingest-muckrock`` Cloud Run job) and fold each request into a
  :class:`tasks.request_outcomes.RequestOutcome` (source ``claim_spine``).
* ``--live REQUEST_ID`` — pull one request's current status from MuckRock
  api_v2 through the connector's own machinery (the shared politeness layer +
  the refreshing JWT cache, §23.5 F4.2/F4.3; ``$SIG_MUCKROCK_REFRESH`` env-only)
  and record the outcome (source ``muckrock_api``). A Cloudflare challenge or
  politeness refusal is reported honestly — never defeated, never fabricated.

Secrets are env-only (HG-09): the PG password rides ``$PGPASSWORD`` (or
``$SIG_PG_DSN``); the MuckRock refresh token rides ``$SIG_MUCKROCK_REFRESH``.

Usage:
    uv run python docs/build/tools/records_outcome_feed.py \
        --spine --log docs/build/reports/records_outcomes_<date>.jsonl
    uv run python docs/build/tools/records_outcome_feed.py \
        --live 136412 --log ...
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from tasks.request_outcomes import (
    RequestOutcome,
    RequestOutcomeLog,
    outcome_from_api_payload,
    outcome_from_claims,
)

#: The claim predicates that identify a records-request subject in the spine.
_REQUEST_SURFACE = {"external_id", "response_status", "platform"}


def _connect():
    """Open a spine connection from env ($SIG_PG_DSN or host/port + $PGPASSWORD)."""
    import psycopg

    dsn = os.environ.get("SIG_PG_DSN")
    if dsn:
        return psycopg.connect(dsn)
    host = os.environ.get("SIG_PG_HOST", "127.0.0.1")
    port = os.environ.get("SIG_PG_PORT", "5433")
    user = os.environ.get("SIG_PG_USER", "sig")
    dbname = os.environ.get("SIG_PG_DB", "sig")
    return psycopg.connect(f"host={host} port={port} user={user} dbname={dbname}")


def outcomes_from_spine(*, source_id: str, observed_at: str) -> list[RequestOutcome]:
    """Fold the spine's records_request claims for ``source_id`` into outcomes."""
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT c.subject_id, c.predicate_id, c.value_text
            FROM claim c
            JOIN extraction e ON c.extraction_id = e.extraction_id
            JOIN evidence_capture ec ON e.capture_id = ec.capture_id
            JOIN evidence_artifact ea ON ec.artifact_id = ea.artifact_id
            WHERE ea.source_id = %s
            ORDER BY c.subject_id, c.claim_id
            """,
            (source_id,),
        ).fetchall()
    finally:
        conn.close()
    by_subject: dict[str, list[dict]] = {}
    for subject_id, predicate_id, value_text in rows:
        by_subject.setdefault(str(subject_id), []).append(
            {"predicate_id": predicate_id, "value_text": value_text}
        )
    outcomes = []
    for claims in by_subject.values():
        if _REQUEST_SURFACE & {c["predicate_id"] for c in claims}:
            outcomes.append(
                outcome_from_claims(claims, source="claim_spine", observed_at=observed_at)
            )
    return outcomes


def outcome_from_live_api(request_id: str, *, observed_at: str) -> RequestOutcome:
    """Pull one request live from MuckRock api_v2 through the connector machinery."""
    from connectors.net import PoliteFetcher
    from connectors.records import muckrock_endpoint, vocab
    from connectors.runner import _muckrock_token_cache
    from connectors.transports import HttpxTransport

    transport = HttpxTransport()
    fetcher = PoliteFetcher(
        connector_name="records", connector_version="1.0.0", transport=transport
    )
    cache = _muckrock_token_cache(fetcher)
    try:
        result = fetcher.fetch(
            muckrock_endpoint("requests", request_id),
            headers=cache.authorization_header(),
        )
    finally:
        transport.close()
    if result.status != 200:
        raise RuntimeError(
            f"MuckRock api_v2 returned HTTP {result.status} for request {request_id}; "
            "no outcome recorded (never fabricated)"
        )
    payload = json.loads(result.body)
    return outcome_from_api_payload(
        payload,
        platform="muckrock",
        status_map=vocab().get("muckrock_status_map", {}),
        source="muckrock_api",
        observed_at=observed_at,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--spine", action="store_true", help="fold spine claims into outcomes")
    parser.add_argument("--live", metavar="REQUEST_ID", help="pull one request live via api_v2")
    parser.add_argument(
        "--source-id", default="muckrock", help="spine source_id (default muckrock)"
    )
    parser.add_argument("--log", required=True, help="append-only outcome log (JSONL)")
    parser.add_argument("--observed-at", default=None, help="ISO timestamp (default: now)")
    args = parser.parse_args(argv)

    from datetime import UTC, datetime

    observed_at = args.observed_at or datetime.now(UTC).isoformat()
    log = RequestOutcomeLog(args.log)
    recorded: list[RequestOutcome] = []
    if args.spine:
        outcomes = outcomes_from_spine(source_id=args.source_id, observed_at=observed_at)
        for outcome in outcomes:
            recorded.append(log.record(outcome))
        print(f"spine ({args.source_id}): {len(outcomes)} request(s) folded")
    if args.live:
        try:
            recorded.append(log.record(outcome_from_live_api(args.live, observed_at=observed_at)))
        except Exception as exc:  # the honest recorded-refusal path
            print(f"live pull refused/failed for {args.live}: {type(exc).__name__}: {exc}")
            print("no live outcome recorded (never fabricated)")
    for outcome in recorded:
        print(
            f"  {outcome.key}: {outcome.state} ({outcome.response_status}) "
            f"agency={outcome.agency} filed={outcome.filed_date} "
            f"response={outcome.response_date} via {outcome.source}"
        )
    print(f"log: {log.path} ({len(log.read_all())} observation(s) total)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
