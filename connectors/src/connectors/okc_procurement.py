# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `okc_procurement` document connector (LIVE.1a, GL-LIVE-01, P23.5; closes BL-023).

Fetches the cited City of Oklahoma City procurement / contract document (the Flock
Master Agreement C241032 family), captures it to the OCFL evidence store, reads its
vendor / product / contract-number / amount / term as a table via the layer-4
``pdf_table`` engine (:mod:`parsing.tables`), and emits the contract claims the
P06.1 slice fixtures assert — byte-identically under shadow replay.

All the shared machinery (the predicate allowlist as a hard schema gate, the Part
VIII guard, the sig-parsing extractor dispatch) lives in
:mod:`connectors.okc_documents`; this module is the registered connector identity.
The source is green (RIGHTS.1 flipped it to ``ingestion_permitted=true``); replay and
shadow run over the committed fixture under network isolation (SIG-INGEST-018/019).
"""

from __future__ import annotations

from .okc_documents import OkcDocumentConnector
from .stages import register

__all__ = ["OkcProcurementConnector"]


@register
class OkcProcurementConnector(OkcDocumentConnector):
    """The `okc_procurement` connector: OKC executed contracts / procurement records."""

    name = "okc_procurement"
    version = "1.0.0"
