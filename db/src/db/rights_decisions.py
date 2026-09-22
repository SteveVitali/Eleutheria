# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The append-only rights-resolution writer (P27.2 / ADR-095).

The claim spine is append-only: a claim's recorded ``rights_id`` is the provenance
of what was known at assertion time and is never rewritten. A licence review that
resolves claims asserted under UNDETERMINED rights is therefore recorded as a NEW
``rights_decision`` row — ``(source_id, prior_rights_id) -> resolved rights_record``
— never an ``UPDATE``. Every reader that needs *effective* rights resolves through
the latest matching decision; the recorded record is the fallback.

Semantics a caller can rely on:

* **A decision only lifts unresolved rights.** ``prior_rights_id`` must point at a
  ``rights_record`` whose ``redistributable = 'UNDETERMINED'`` — a decision can
  never relicense an already-resolved claim (e.g. recorded ODbL stays ODbL).
* **Source-scoped, connector-agnostic.** A decision applies to every claim whose
  evidence chain lands on the named source, however it was ingested.
* **Immutable + superseding.** Decision rows are never edited or deleted (a DB
  trigger enforces it); a changed disposition is a NEW row whose later
  ``decided_at`` wins. History is preserved.
* **Fail-closed validation.** A resolution must carry a reviewer role (never a
  personal name — Part VIII §0.7), a written basis, a terms URL, and a recorded
  review date; ``redistributable`` must be decided (``yes``/``no``/``review_required``),
  never ``UNDETERMINED``. ``no`` is a legitimate resolution — it records
  "reviewed, not publishable", which is honest, not a bypass.

The decisions artifact itself is a committed, reviewed file — see
``docs/build/reports/rights/p272_dispositions.json``.
"""

from __future__ import annotations

import hashlib
import json
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from evidence.digest import blake3_hex, multihash

#: `redistributable` values a decision may resolve to — never UNDETERMINED.
DECIDED_VALUES = ("yes", "no", "review_required")

#: The ingest_run identity the terms-capture rows are attributed to.
REVIEW_RUN_CONNECTOR = "rights-review"
REVIEW_RUN_VERSION = "p27.2"

#: artifact_type for the archived terms page (SIG-LIC-002).
TERMS_ARTIFACT_TYPE = "terms_page"

#: Minimal source_registry defaults for a decision targeting a source that was
#: never registered by a claim sink (mirrors PgClaimSink._ensure_source).
_DEFAULT_RELIABILITY = "R2"


class RightsResolutionError(ValueError):
    """A resolution row failed validation or referenced an undecidable state."""


@dataclass(frozen=True)
class RightsResolution:
    """One reviewed source disposition — the reviewer-prepared flip-list row."""

    source_id: str
    spdx: str
    attribution: str
    redistributable: str
    derivative_permitted: str
    terms_url: str
    retrieval_date: date
    reviewed_by: str  # a ROLE (e.g. 'maintainer (delegated)'), never a personal name
    reviewed_on: date
    basis: str
    review_packet: str | None = None


def load_resolutions(path: str | Path) -> list[RightsResolution]:
    """Load a committed dispositions artifact (JSON) into validated rows."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = doc.get("resolutions")
    if not isinstance(rows, list):
        raise RightsResolutionError(f"{path}: no 'resolutions' list")
    out: list[RightsResolution] = []
    errors: list[str] = []
    for i, row in enumerate(rows):
        try:
            res = RightsResolution(
                source_id=str(row["source_id"]),
                spdx=str(row["spdx"]),
                attribution=str(row.get("attribution") or ""),
                redistributable=str(row["redistributable"]),
                derivative_permitted=str(row["derivative_permitted"]),
                terms_url=str(row["terms_url"]),
                retrieval_date=date.fromisoformat(str(row["retrieval_date"])),
                reviewed_by=str(row["reviewed_by"]),
                reviewed_on=date.fromisoformat(str(row["reviewed_on"])),
                basis=str(row["basis"]),
                review_packet=(
                    None if row.get("review_packet") is None else str(row["review_packet"])
                ),
            )
        except (KeyError, ValueError) as exc:
            errors.append(f"row {i} ({row.get('source_id', '?')}): {exc}")
            continue
        errors.extend(f"row {i} ({res.source_id}): {e}" for e in validate_resolution(res))
        out.append(res)
    if errors:
        raise RightsResolutionError("invalid dispositions artifact:\n  " + "\n  ".join(errors))
    return out


def validate_resolution(res: RightsResolution) -> list[str]:
    """Fail-closed validation of one disposition row. Returns a list of problems."""
    errors: list[str] = []
    if not res.source_id.strip():
        errors.append("source_id is empty")
    if not res.spdx.strip():
        errors.append("spdx is empty")
    if res.redistributable not in DECIDED_VALUES:
        errors.append(
            f"redistributable must be one of {DECIDED_VALUES} "
            f"(a decision resolves UNDETERMINED; it never records it), got {res.redistributable!r}"
        )
    if res.derivative_permitted not in DECIDED_VALUES:
        errors.append(
            f"derivative_permitted must be one of {DECIDED_VALUES}, "
            f"got {res.derivative_permitted!r}"
        )
    if not res.terms_url.strip():
        errors.append("terms_url is empty — every basis carries a terms URL (SIG-LIC-002)")
    if not res.reviewed_by.strip():
        errors.append("reviewed_by is empty — a reviewer role is required")
    if not res.basis.strip():
        errors.append("basis is empty — the gate + legal basis citation is required")
    return errors


# --------------------------------------------------------------------------- #
# Spine writes — insert-only                                                  #
# --------------------------------------------------------------------------- #


def _ensure_source(conn: Any, source_id: str, rights_id: str) -> None:
    """Ensure the source exists in source_registry (insert-only, never an update)."""
    conn.execute(
        "INSERT INTO source_registry"
        "(source_id, name, source_kind, default_reliability, reliability_provisional,"
        " reliability_justification, rights_id, custody_posture, compact_status,"
        " ingestion_permitted, robots_policy) "
        "VALUES (%s, %s, 'rights-review', %s, false, %s, %s, 'REFERENCE', 'compact',"
        " false, 'obeyed') ON CONFLICT (source_id) DO NOTHING",
        (
            source_id,
            f"rights-reviewed source {source_id}",
            _DEFAULT_RELIABILITY,
            "rights-resolution source stub (P27.2 rights_decision writer)",
            rights_id,
        ),
    )


def _ensure_rights_record(conn: Any, res: RightsResolution) -> str:
    """Return the rights_id for the reviewed record, inserting it if absent."""
    row = conn.execute(
        "SELECT rights_id FROM rights_record "
        "WHERE spdx_expression = %s AND attribution_text IS NOT DISTINCT FROM %s "
        "AND terms_url IS NOT DISTINCT FROM %s AND redistributable = %s "
        "AND derivative_permitted = %s AND reviewed_by IS NOT DISTINCT FROM %s "
        "ORDER BY rights_id LIMIT 1",
        (
            res.spdx,
            res.attribution,
            res.terms_url,
            res.redistributable,
            res.derivative_permitted,
            res.reviewed_by,
        ),
    ).fetchone()
    if row is not None:
        return str(row[0])
    inserted = conn.execute(
        "INSERT INTO rights_record"
        "(spdx_expression, attribution_text, redistributable, derivative_permitted,"
        " terms_url, reviewed_by, reviewed_at, retrieval_date) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING rights_id",
        (
            res.spdx,
            res.attribution,
            res.redistributable,
            res.derivative_permitted,
            res.terms_url,
            res.reviewed_by,
            f"{res.reviewed_on.isoformat()}T00:00:00Z",
            res.retrieval_date,
        ),
    ).fetchone()
    assert inserted is not None
    return str(inserted[0])


def _undetermined_priors(conn: Any, source_id: str) -> list[str]:
    """The distinct UNDETERMINED rights_ids this source's claims/registry link carry.

    A decision resolves exactly these records — claims recorded under any other
    (already-resolved) rights record are never touched.
    """
    rows = conn.execute(
        "SELECT DISTINCT r.rights_id FROM rights_record r "
        "WHERE r.redistributable = 'UNDETERMINED' AND ("
        "  r.rights_id IN (SELECT sr.rights_id FROM source_registry sr"
        "                  WHERE sr.source_id = %s)"
        "  OR r.rights_id IN (SELECT c.rights_id FROM claim c"
        "    JOIN claim_evidence ce ON ce.claim_id = c.claim_id AND ce.role = 'establishes'"
        "    JOIN evidence_capture ec ON ce.capture_id = ec.capture_id"
        "    JOIN evidence_artifact ea ON ec.artifact_id = ea.artifact_id"
        "    WHERE ea.source_id = %s))",
        (source_id, source_id),
    ).fetchall()
    return sorted(str(r[0]) for r in rows)


def _claims_lifted(conn: Any, source_id: str, prior_rights_id: str) -> int:
    """How many of the source's claims the decision resolves (recorded = prior)."""
    row = conn.execute(
        "SELECT count(*) FROM claim c"
        " JOIN claim_evidence ce ON ce.claim_id = c.claim_id AND ce.role = 'establishes'"
        " JOIN evidence_capture ec ON ce.capture_id = ec.capture_id"
        " JOIN evidence_artifact ea ON ec.artifact_id = ea.artifact_id"
        " WHERE ea.source_id = %s AND c.rights_id = %s",
        (source_id, prior_rights_id),
    ).fetchone()
    return 0 if row is None else int(row[0])


def _insert_decision(
    conn: Any,
    res: RightsResolution,
    rights_id: str,
    prior_rights_id: str,
    terms_capture_id: str | None,
) -> tuple[str, bool]:
    """Append one decision row; idempotent on (source, prior, resolved)."""
    existing = conn.execute(
        "SELECT decision_id FROM rights_decision "
        "WHERE source_id = %s AND prior_rights_id = %s AND rights_id = %s "
        "ORDER BY decided_at DESC, decision_id DESC LIMIT 1",
        (res.source_id, prior_rights_id, rights_id),
    ).fetchone()
    if existing is not None:
        return str(existing[0]), False
    inserted = conn.execute(
        "INSERT INTO rights_decision"
        "(source_id, rights_id, prior_rights_id, basis, reviewer, review_packet,"
        " terms_url, terms_capture_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        " RETURNING decision_id",
        (
            res.source_id,
            rights_id,
            prior_rights_id,
            res.basis,
            res.reviewed_by,
            res.review_packet,
            res.terms_url,
            terms_capture_id,
        ),
    ).fetchone()
    assert inserted is not None
    return str(inserted[0]), True


def apply_resolution(
    conn: Any,
    res: RightsResolution,
    *,
    terms_capture_id: str | None = None,
) -> dict[str, Any]:
    """Record one resolution: reviewed rights_record + decision row(s). Insert-only.

    Returns a per-source report: the resolved rights_id, the priors lifted, and the
    number of claims each decision flips from UNDETERMINED to resolved.
    """
    problems = validate_resolution(res)
    if problems:
        raise RightsResolutionError(f"{res.source_id}: " + "; ".join(problems))
    rights_id = _ensure_rights_record(conn, res)
    _ensure_source(conn, res.source_id, rights_id)
    priors = _undetermined_priors(conn, res.source_id)
    decisions: list[dict[str, Any]] = []
    for prior in priors:
        decision_id, inserted = _insert_decision(conn, res, rights_id, prior, terms_capture_id)
        decisions.append(
            {
                "decision_id": decision_id,
                "prior_rights_id": prior,
                "inserted": inserted,
                "claims_lifted": _claims_lifted(conn, res.source_id, prior),
            }
        )
    return {
        "source_id": res.source_id,
        "spdx": res.spdx,
        "redistributable": res.redistributable,
        "rights_id": rights_id,
        "decisions": decisions,
        "claims_lifted": sum(d["claims_lifted"] for d in decisions),
    }


def apply_resolutions(
    conn: Any,
    resolutions: list[RightsResolution],
    *,
    terms_captures: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Apply a whole dispositions artifact inside the caller's transaction."""
    return [
        apply_resolution(conn, res, terms_capture_id=(terms_captures or {}).get(res.source_id))
        for res in resolutions
    ]


def plan_resolutions(conn: Any, resolutions: list[RightsResolution]) -> list[dict[str, Any]]:
    """Read-only preview: what each resolution WOULD resolve, with claim counts."""
    out: list[dict[str, Any]] = []
    for res in resolutions:
        priors = _undetermined_priors(conn, res.source_id)
        out.append(
            {
                "source_id": res.source_id,
                "spdx": res.spdx,
                "redistributable": res.redistributable,
                "undetermined_priors": priors,
                "claims_lifted": sum(_claims_lifted(conn, res.source_id, p) for p in priors),
            }
        )
    return out


# --------------------------------------------------------------------------- #
# Terms capture (SIG-LIC-002): archive the reviewed terms page as evidence      #
# --------------------------------------------------------------------------- #


def _ensure_review_run(conn: Any, code_commit: str) -> str:
    """The ingest_run the terms captures are attributed to (idempotent)."""
    row = conn.execute(
        "SELECT run_id FROM ingest_run WHERE connector_name = %s "
        "AND connector_version = %s AND code_commit = %s ORDER BY started_at LIMIT 1",
        (REVIEW_RUN_CONNECTOR, REVIEW_RUN_VERSION, code_commit),
    ).fetchone()
    if row is not None:
        return str(row[0])
    inserted = conn.execute(
        "INSERT INTO ingest_run"
        "(connector_name, connector_version, code_commit, ruleset_version,"
        " vocab_version, parameters, environment, input_digests) "
        "VALUES (%s, %s, %s, 'rights-review', '1.0.0', '{}', '{}', '{}') RETURNING run_id",
        (REVIEW_RUN_CONNECTOR, REVIEW_RUN_VERSION, code_commit),
    ).fetchone()
    assert inserted is not None
    return str(inserted[0])


def fetch_terms(url: str, *, timeout: float = 30.0) -> dict[str, Any] | None:
    """Fetch a public terms page once. Returns bytes + response metadata, or None.

    Plain HTTP GET of a documented terms URL — the archival read SIG-LIC-002
    requires; never a content fetch of the source itself. TLS verification is
    always on (the certifi bundle when present, else the platform trust store).
    """
    if not url.startswith(("http://", "https://")):
        return None  # a repo-relative packet path IS the terms record (derived facts)
    import ssl

    try:
        import certifi

        context = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        context = ssl.create_default_context()
    request = urllib.request.Request(
        url, headers={"User-Agent": "SIG-rights-review/0.1 (evidence archival)"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as resp:  # noqa: S310
            return {
                "body": resp.read(),
                "media_type": (resp.headers.get_content_type() or "application/octet-stream"),
                "http_status": int(resp.status),
            }
    except Exception:  # noqa: BLE001 - a failed capture is recorded, never faked
        return None


def capture_terms(
    conn: Any,
    res: RightsResolution,
    rights_id: str,
    fetched: dict[str, Any],
    *,
    code_commit: str,
) -> str:
    """Register a fetched terms page as evidence_artifact + blob + capture.

    Returns the capture_id the decision row links as its archived-terms evidence
    (SIG-LIC-002). Insert-only; the (blob_digest, source_uri) PK dedups a re-fetch
    of unchanged bytes (SIG-EVID-004).
    """
    run_id = _ensure_review_run(conn, code_commit)
    locator_hash = hashlib.sha256(res.terms_url.encode()).hexdigest()[:16]
    stable_locator = f"sig:terms:{res.source_id}:{locator_hash}"
    art = conn.execute(
        "INSERT INTO evidence_artifact"
        "(source_id, url, stable_locator, artifact_type, acquisition_method,"
        " primary_or_secondary, rights_id, capture_status) "
        "VALUES (%s, %s, %s, %s, 'http_get', 'primary', %s, 'captured') "
        "ON CONFLICT (source_id, stable_locator) DO NOTHING RETURNING artifact_id",
        (res.source_id, res.terms_url, stable_locator, TERMS_ARTIFACT_TYPE, rights_id),
    ).fetchone()
    if art is None:
        art = conn.execute(
            "SELECT artifact_id FROM evidence_artifact "
            "WHERE source_id = %s AND stable_locator = %s",
            (res.source_id, stable_locator),
        ).fetchone()
    assert art is not None
    artifact_id = str(art[0])

    body = fetched["body"]
    digest = multihash(body)
    blake3 = blake3_hex(body)
    ocfl_object_id = f"sig:evidence:{artifact_id}"
    conn.execute(
        "INSERT INTO evidence_blob"
        "(blob_digest, source_uri, byte_size, digest_blake3, ocfl_object_id, ocfl_version) "
        "VALUES (%s, %s, %s, %s, %s, 'v1') "
        "ON CONFLICT (blob_digest, source_uri) DO NOTHING",
        (digest, res.terms_url, len(body), blake3, ocfl_object_id),
    )
    cap = conn.execute(
        "SELECT capture_id FROM evidence_capture "
        "WHERE artifact_id = %s AND content_digest = %s AND source_uri = %s "
        "ORDER BY capture_id LIMIT 1",
        (artifact_id, digest, res.terms_url),
    ).fetchone()
    if cap is None:
        cap = conn.execute(
            "INSERT INTO evidence_capture"
            "(artifact_id, content_digest, digest_blake3, byte_size, media_type,"
            " retrieved_at, retrieved_by_run_id, http_status, ocfl_object_id,"
            " ocfl_version, storage_tier, capture_method, capture_tool_version,"
            " source_uri, blob_digest) "
            "VALUES (%s, %s, %s, %s, %s, clock_timestamp(), %s, %s, %s, 'v1',"
            " 'public', 'http_get', %s, %s, %s) RETURNING capture_id",
            (
                artifact_id,
                digest,
                blake3,
                len(body),
                fetched["media_type"],
                run_id,
                fetched["http_status"],
                ocfl_object_id,
                REVIEW_RUN_VERSION,
                res.terms_url,
                digest,
            ),
        ).fetchone()
    assert cap is not None
    return str(cap[0])
