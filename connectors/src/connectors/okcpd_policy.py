# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `okcpd_policy` document connector (LIVE.1a, GL-LIVE-01, P23.5; closes BL-024).

Fetches the cited OKCPD Operations Manual policy document (the ALPR clause §5-118),
captures it to the OCFL evidence store, reads its numbered clauses via the layer-3
``pdf_text`` clause locator (:mod:`parsing.clauses`), and emits the agency-policy
claims the P06.1 slice fixtures assert (the sharing restriction) — byte-identically
under shadow replay.

All the shared machinery lives in :mod:`connectors.okc_documents`; this module is the
registered connector identity. The source is green (RIGHTS.1); replay and shadow run
over the committed fixture under network isolation (SIG-INGEST-018/019).
"""

from __future__ import annotations

from .okc_documents import OkcDocumentConnector
from .stages import register

__all__ = ["OkcpdPolicyConnector"]


@register
class OkcpdPolicyConnector(OkcDocumentConnector):
    """The `okcpd_policy` connector: OKCPD agency policy (Operations Manual §5-118)."""

    name = "okcpd_policy"
    version = "1.0.0"
