# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `agency_policy` document connector (P36.10 / R11-ACQ-14, I8 §5.7).

The `OkcDocumentConnector` subclass pattern generalized into ONE connector: the
seven ACQ-14 agency-policy publishers (Houston General Orders, the Albuquerque
APD SOP incl. 1-22 ALPR, the Bangor + Little Rock UAS general orders, the
Orange County + Pasadena cell-site-simulator policies, and California Gov.
Code § 53166) ride the shared document pipeline — `document_page` live targets
carrying the reviewed clause→predicate literals (SIG-INGEST-038 data, never
code) and committed JSON-envelope fixtures in replay/shadow.

Every claim still routes through :func:`connectors.okc_documents.okc_claim`, so
the predicate allowlist (SIG-INGEST-033), the Part VIII plate/trip/person guard
and the §43.4 officer-naming default-deny apply unchanged — a policy clause
locates to a section marker, and a policy document NEVER asserts a deployment
(procured ≠ authorized ≠ deployed). All seven rows stay
`ingestion_permitted=false` (HG-03 RB-03 `a`; RB-07 `a` — facts and citations
only — for the two CSS-policy rows); the operator's OP-26 Wave-B flip under
ING-GO-B (P36.12) is the only route to a live fetch.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .okc_documents import OkcDocumentConnector, extract_documents
from .stages import RunContext, register

__all__ = ["AgencyPolicyConnector"]


@register
class AgencyPolicyConnector(OkcDocumentConnector):
    """One connector for the reviewed agency-policy registry seats (P36.10).

    The connector name keys `[connectors.agency_policy]` in
    ``okc_documents_vocab.toml`` — the shared policy/statute clause predicate
    allowlist plus the closed ``source_ids`` seat set. ``extract`` stamps the
    run's own source id on every claim (the seat must be declared, else the
    run fails closed); discover/fetch/parse/normalize/load are inherited
    unchanged — `document_page` targets with reviewed `clauses` read the live
    section slice; fixture envelopes read via the clause locator.
    """

    name = "agency_policy"
    version = "1.0.0"

    def extract(self, ctx: RunContext, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        return extract_documents(self.name, parsed, source_id=ctx.source.id)
