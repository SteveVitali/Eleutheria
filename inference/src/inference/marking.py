# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The cross-surface L4 inference marker contract (§30.4, SIG-RECON-052, P36.14).

Every inference MUST be visually and structurally distinguishable from
observation in the UI, the API, and every export — including derived map
layers. This module is the single Python-side definition of the *structural*
half of that contract: two typed fields every emitted inference record carries,

* ``inferred`` — a boolean, ``True`` exactly when the record is an L4 derived
  fact (``inference.derived_fact``: it lives in the separate namespace, carries
  ``derivation_rule`` + ``derived_at`` + ``input_claim_ids``, per
  SIG-RECON-047/031). An observed or resolved record never carries
  ``inferred: true``; the field is either ``false`` or absent there.
* ``layer`` — the spine layer the record belongs to, ``"L4"`` when
  ``inferred`` is true (``reconcile.model.Inference.layer``). Anything that is
  not an inference carries no layer marker.

A prose note ("L4 inference") supplements but never replaces the typed fields —
a consumer must be able to branch on the field, never parse the sentence
(SIG-ENG-042: an unmarked inference on any surface fails the conformance test).
The *visual* half of the contract — the ``sig-inferred`` epistemic class, its
glyph and text label — lives in ``web/src/lib/epistemic.ts`` +
``web/src/styles/epistemic.css`` and reads exactly these two fields.

``Candidate`` (a lifecycle state) and ``Provisional`` (the unevaluated-method
label, SIG-UI-062) are deliberately NOT this marker: ``inferred``/`layer="L4"`
names *what kind of record this is* — a derived fact, not an observed claim.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

#: The spine layer every inference belongs to (§30, SIG-RECON-047). Kept equal
#: to ``reconcile.model.Inference.layer`` — checked by the conformance test.
INFERRED_LAYER = "L4"

#: The marker field names, in canonical order. Both are required together:
#: ``inferred`` without ``layer`` (or the reverse) is a broken marker.
INFERRED_FIELD = "inferred"
LAYER_FIELD = "layer"


def mark_inferred(record: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy of ``record`` carrying the L4 inference marker (SIG-RECON-052).

    The caller supplies the record's own fields; this stamps the two typed
    marker fields on top. Use it at every seam where a ``derived_fact`` row
    becomes an emitted record, so no path can emit an inference unmarked.
    """
    return {**record, INFERRED_FIELD: True, LAYER_FIELD: INFERRED_LAYER}


def is_inferred_record(record: Mapping[str, Any] | None) -> bool:
    """True exactly when ``record`` carries the complete L4 marker.

    Both fields must agree: ``inferred: true`` alone (or ``layer: "L4"`` alone)
    is not a marker — a half-marked record counts as unmarked, so the
    conformance test fails on a partially-stripped record rather than passing
    on a degraded one.
    """
    if not isinstance(record, Mapping):
        return False
    return record.get(INFERRED_FIELD) is True and record.get(LAYER_FIELD) == INFERRED_LAYER
