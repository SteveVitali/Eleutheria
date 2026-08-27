# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Per-run lineage, mapped to PROV-O (§21.6, SIG-INGEST-015/016).

Every claim a connector run produces is traceable to its ``ingest_run``
(SIG-INGEST-015): the run record (:class:`evidence.ingest_run.IngestRun`) carries
connector name/version, code commit, ruleset and vocabulary versions, input
evidence digests, parameters, and environment. This module assembles the run's
lineage — its source, captures, extraction, and claims — into the project's
PROV-O projection (:mod:`exports.provo`, SIG-INGEST-016), so a run's provenance
exports interoperably: captures and claims are ``prov:Entity``, the run and its
extraction are ``prov:Activity``, and the connector and source are ``prov:Agent``.

The connector framework only *assembles and hands off* lineage here; the PROV-O
mapping and its validation already live in ``exports`` (P02.3) and are reused, not
reimplemented.
"""

from __future__ import annotations

from collections.abc import Sequence

from evidence.ingest_run import IngestRun
from exports.provo import (
    Capture,
    Claim,
    Connector,
    Extraction,
    Lineage,
    Source,
)
from exports.provo import (
    IngestRun as ProvRun,
)

from .stages import CaptureRef


def build_lineage(
    run: IngestRun,
    *,
    run_id: str,
    source_id: str,
    captures: Sequence[CaptureRef],
    claim_ids: Sequence[str],
    extraction_id: str | None = None,
) -> Lineage:
    """Assemble the PROV-O lineage for one connector run (SIG-INGEST-015/016).

    Maps the run's ``ingest_run`` record, the captures it archived, and the claims
    it produced onto the :class:`exports.provo.Lineage` projection. ``run_id`` and
    ``claim_ids`` are the surrogate ids assigned when rows are written; the
    lineage is otherwise a pure function of the run and its artifacts.
    """
    extraction = extraction_id or f"{run_id}:extraction"
    prov_captures = [
        Capture(
            capture_id=ref.digest,
            source_id=source_id,
            run_id=run_id,
            retrieved_at=ref.retrieved_at,
        )
        for ref in captures
    ]
    prov_claims = [
        Claim(claim_id=cid, extraction_id=extraction, run_id=run_id) for cid in claim_ids
    ]
    return Lineage(
        sources=[Source(source_id=source_id)],
        connectors=[Connector(name=run.connector_name, version=run.connector_version)],
        runs=[
            ProvRun(
                run_id=run_id,
                connector_name=run.connector_name,
                connector_version=run.connector_version,
            )
        ],
        extractions=[
            Extraction(extraction_id=extraction, run_id=run_id, connector_name=run.connector_name)
        ],
        captures=prov_captures,
        claims=prov_claims,
    )


__all__ = ["build_lineage"]
