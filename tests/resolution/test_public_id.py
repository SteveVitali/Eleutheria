# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Public sig: identifiers: minting, dereference/content-negotiation, and the
stability contract across cluster split/merge (SIG-IDENT-031/032)."""

from __future__ import annotations

from datetime import date

import pytest
from resolution.public_id import (
    PublicIdRegistry,
    dereference_url,
    mint,
    negotiate,
    parse,
    uuid7,
)


def _u(seed: int) -> str:
    return "sig:organization:" + str(uuid7(timestamp_ms=seed, rand_a=0, rand_b=seed))


# --- SIG-IDENT-031: minting + form + dereference + content negotiation -------


def test_uuid7_has_version_7_and_is_time_ordered() -> None:
    earlier = uuid7(timestamp_ms=1000, rand_a=0, rand_b=0)
    later = uuid7(timestamp_ms=2000, rand_a=0, rand_b=0)
    assert earlier.version == 7 and later.version == 7
    assert earlier < later  # k-sortable by embedded timestamp


def test_mint_produces_sig_type_uuidv7_form() -> None:
    pid = mint("organization", value=uuid7(timestamp_ms=1, rand_a=1, rand_b=1))
    assert str(pid).startswith("sig:organization:")
    assert pid.uuid.version == 7
    assert parse(str(pid)) == pid  # round-trips


def test_mint_rejects_non_uuidv7_and_bad_types() -> None:
    import uuid as _uuid

    with pytest.raises(ValueError):
        mint("organization", value=_uuid.uuid4())  # not v7
    with pytest.raises(ValueError):
        mint("bad:type")


def test_dereference_url_uses_the_id_path() -> None:
    pid = mint("deployment", value=uuid7(timestamp_ms=5, rand_a=0, rand_b=5))
    url = dereference_url(pid, host="sig.example")
    assert url == f"https://sig.example/id/deployment/{pid.uuid}"


def test_content_negotiation_covers_html_jsonld_rdf() -> None:
    assert negotiate(None) == "html"
    assert negotiate("*/*") == "html"
    assert negotiate("text/html") == "html"
    assert negotiate("application/ld+json") == "json-ld"
    assert negotiate("application/json") == "json-ld"
    assert negotiate("text/turtle") == "rdf"
    assert negotiate("application/rdf+xml") == "rdf"
    # A quality-weighted header still resolves by its listed media types.
    assert negotiate("application/ld+json;q=0.9, text/html;q=0.8") in {"json-ld", "html"}


# --- SIG-IDENT-032: stability across a split ---------------------------------


def test_public_ids_survive_a_simulated_cluster_split() -> None:
    reg = PublicIdRegistry()
    source = reg.register(_u(1))
    child_a, child_b = _u(2), _u(3)

    event = reg.split(source=source, into=(child_a, child_b), dated=date(2026, 3, 1))

    # The source id is NOT silently reassigned to a successor; it is tombstoned
    # with dated split_into pointers.
    assert reg.is_tombstone(source)
    assert source not in reg.live
    tomb = reg.tombstones[source]
    assert tomb.reason == "split"
    assert tomb.dated == date(2026, 3, 1)
    assert tomb.split_into == (child_a, child_b)

    # The successors are live, and resolving the old id yields an AMBIGUOUS set the
    # reader must disambiguate — never a silent pick.
    assert child_a in reg.live and child_b in reg.live
    res = reg.resolve(source)
    assert res.status == "split"
    assert res.targets == (child_a, child_b)

    # The event log records the dated change.
    assert event in reg.events


def test_split_never_reassigns_the_source_id() -> None:
    reg = PublicIdRegistry()
    source = reg.register(_u(1))
    with pytest.raises(ValueError, match="silent reassignment"):
        reg.split(source=source, into=(source, _u(2)), dated=date(2026, 3, 1))


def test_a_tombstoned_id_cannot_be_re_registered() -> None:
    reg = PublicIdRegistry()
    source = reg.register(_u(1))
    reg.split(source=source, into=(_u(2), _u(3)), dated=date(2026, 3, 1))
    with pytest.raises(ValueError, match="tombstoned"):
        reg.register(source)


# --- SIG-IDENT-032: stability across a merge ---------------------------------


def test_merge_preserves_the_survivor_and_redirects_the_rest() -> None:
    reg = PublicIdRegistry()
    keep, gone = reg.register(_u(1)), reg.register(_u(2))

    reg.merge(sources=(keep, gone), survivor=keep, dated=date(2026, 4, 1))

    # The survivor id is preserved and live; the other is a tombstone redirecting
    # to the survivor, so a citation of it still resolves (SIG-IDENT-032).
    assert keep in reg.live
    assert reg.resolve(keep).status == "active"
    assert reg.is_tombstone(gone)
    redirect = reg.resolve(gone)
    assert redirect.status == "redirect"
    assert redirect.target == keep


def test_merge_requires_the_survivor_to_be_a_source() -> None:
    reg = PublicIdRegistry()
    a, b, other = reg.register(_u(1)), reg.register(_u(2)), _u(3)
    with pytest.raises(ValueError, match="survivor"):
        reg.merge(sources=(a, b), survivor=other, dated=date(2026, 4, 1))


def test_resolve_follows_a_chain_of_merges_to_the_final_survivor() -> None:
    reg = PublicIdRegistry()
    a, b, c = reg.register(_u(1)), reg.register(_u(2)), reg.register(_u(3))
    reg.merge(sources=(b, c), survivor=c, dated=date(2026, 4, 1))  # b -> c
    reg.merge(sources=(a, c), survivor=a, dated=date(2026, 5, 1))  # c -> a
    # b redirects transitively to a, the ultimate survivor.
    assert reg.resolve(b).target == a


def test_resolving_an_unknown_id_raises() -> None:
    reg = PublicIdRegistry()
    with pytest.raises(KeyError):
        reg.resolve(_u(99))
