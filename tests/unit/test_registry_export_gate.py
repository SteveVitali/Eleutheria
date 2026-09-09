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


def test_sm_alpr_refused_from_export_with_derivative_permitted_false() -> None:
    # P19.5 / LD-F08 / SIG-INGEST-048b: sm_alpr is AGPL-3.0 — redistributable but
    # derivative_permitted=false. An export bundle is a derived work, so the export
    # gate now fails closed with the machine-stable reason `derivative_permitted=false`.
    sm_alpr = get("sm_alpr")
    assert sm_alpr.rights.redistributable is True
    assert sm_alpr.rights.derivative_permitted is False
    assert licensing.export_refusal_reason(sm_alpr.rights) == "derivative_permitted=false"
    with pytest.raises(licensing.ExportGateClosed) as excinfo:
        licensing.assert_export_permitted([sm_alpr.rights])
    assert "derivative_permitted=false" in str(excinfo.value)


def test_partition_drops_non_derivative_sources_from_an_export_set() -> None:
    # A mixed export set: the CC-BY Atlas is exportable; sm_alpr and deflock_app_repo
    # (both derivative_permitted=false) are partitioned out with the reason, rather
    # than aborting the whole export (Part VIII §0.7 — the gate only withholds).
    atlas = get("eff_atlas_of_surveillance")
    sm_alpr = get("sm_alpr")
    app = get("deflock_app_repo")
    exportable, refused = licensing.partition_exportable([atlas.rights, sm_alpr.rights, app.rights])
    assert atlas.rights in exportable
    refused_ids = {r.source_id: reason for r, reason in refused}
    assert refused_ids["sm_alpr"] == "derivative_permitted=false"
    assert refused_ids["deflock_app_repo"] == "derivative_permitted=false"


def test_derivative_gate_still_admits_derivative_permitted_sources() -> None:
    # Back-compat: a redistributable, derivative-permitted source (the Atlas) still
    # passes the gate unchanged — the new condition can only reduce, never add.
    atlas = get("eff_atlas_of_surveillance")
    assert atlas.rights.derivative_permitted is True
    licensing.assert_export_permitted([atlas.rights])  # does not raise


def test_every_registry_rights_record_is_addressable() -> None:
    recs = rights_records()
    assert len(recs) == len(sources())
    assert all(r.source_id for r in recs)
