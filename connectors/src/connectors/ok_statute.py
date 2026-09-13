# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `ok_statute` document connector (LIVE.1a, GL-LIVE-01, P23.5; closes BL-026).

Fetches the cited Oklahoma statutory text (47 O.S. §7-606.1, which limits ALPR use to
insurance enforcement), captures it to the OCFL evidence store, reads its numbered
sections via the layer-3 ``pdf_text`` clause locator (:mod:`parsing.clauses`), and
emits the legal-instrument claims the P06.1 slice fixtures assert — byte-identically
under shadow replay.

All the shared machinery lives in :mod:`connectors.okc_documents`; this module is the
registered connector identity. Statutory text is an edict of government (public
domain); the source is green (RIGHTS.1); replay and shadow run over the committed
fixture under network isolation (SIG-INGEST-018/019).
"""

from __future__ import annotations

from .okc_documents import OkcDocumentConnector
from .stages import register

__all__ = ["OkStatuteConnector"]


@register
class OkStatuteConnector(OkcDocumentConnector):
    """The `ok_statute` connector: Oklahoma statutory / legal regime (47 O.S. §7-606.1)."""

    name = "ok_statute"
    version = "1.0.0"
