# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The registry's rights records drive the policy export gate (SIG-LIC-004)."""

from __future__ import annotations

import pytest
from connectors.registry import get, rights_records, sources
from policy.rights import is_undetermined

from policy import licensing


def test_undetermined_registry_row_fails_the_export_gate_closed() -> None:
    # SIG-LIC-004: a source whose rights the research pass did not resolve is
    # UNDETERMINED and MUST fail the export gate closed. haveibeenflocked is one
    # such row (rights "Unknown" in §22.2).
    hibf = get("have_i_been_flocked")
    assert is_undetermined(hibf.rights)
    with pytest.raises(licensing.ExportGateClosed):
        licensing.assert_export_permitted([hibf.rights])


def test_seeded_undetermined_rows_all_fail_the_gate() -> None:
    undetermined = [s.rights for s in sources() if is_undetermined(s.rights)]
    assert undetermined  # the seed genuinely contains unresolved sources
    for rec in undetermined:
        with pytest.raises(licensing.ExportGateClosed):
            licensing.assert_export_permitted([rec])


def test_a_redistributable_registry_row_passes_the_gate() -> None:
    # The Atlas is CC-BY-4.0 and separately reviewed redistributable — it passes.
    atlas = get("eff_atlas_of_surveillance")
    assert atlas.rights.redistributable is True
    licensing.assert_export_permitted([atlas.rights])  # does not raise


def test_agpl_repo_is_redistributable_but_flagged_non_derivative() -> None:
    # Redistribution of AGPL source is permitted; the hazard is *linking* it into
    # SIG's Apache-2.0 code, recorded as derivative_permitted=false.
    app = get("deflock_app_repo")
    assert app.rights.redistributable is True
    assert app.rights.derivative_permitted is False


def test_every_registry_rights_record_is_addressable() -> None:
    recs = rights_records()
    assert len(recs) == len(sources())
    assert all(r.source_id for r in recs)
