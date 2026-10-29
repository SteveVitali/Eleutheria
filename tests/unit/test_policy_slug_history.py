# SPDX-License-Identifier: Apache-2.0
"""Tests for ``policy.slug_history`` — ``sig.slug-history/1`` (P36.29, K2 §3.3/§6.5)."""

from __future__ import annotations

import pytest
from policy.labels import EntityLabel, entity_hash, entity_url, name_slug
from policy.slug_history import (
    ENTITY_SLUG_HISTORY_SCHEMA,
    SlugHistoryRow,
    check_unique_labels,
    freeze_hashes,
    history_doc,
    issued_hashes,
    merge_history,
    resolve_request,
)


def _label(
    entity_id: str,
    label: str,
    *,
    kind: str = "agency",
    url_type: str | None = "agency",
    slug_override: str | None = None,
    hash_override: str | None = None,
) -> EntityLabel:
    """A labelled ``sig.entity-label/1`` row built from the REAL primitives —
    the tests never re-derive a slug or hash by hand."""
    slug = slug_override if slug_override is not None else name_slug(label)
    hash_value = hash_override if hash_override is not None else entity_hash(entity_id)
    url = entity_url(url_type, slug, hash_value) if url_type and slug else None
    return EntityLabel(
        entity_id=entity_id,
        sig_id=f"sig-{entity_id}",
        kind=kind,
        url_type=url_type,
        label=label,
        descriptor=None,
        label_basis="key_name",
        label_source_id="test",
        place_jkey=None,
        slug=slug,
        hash=hash_value,
        url=url,
        disambiguator=None,
        component_id=None,
        part8="pass",
    )


def _rows(doc_or_rows):
    return [r.row() if isinstance(r, SlugHistoryRow) else dict(r) for r in doc_or_rows]


class TestHistoryDoc:
    def test_schema_and_validation(self):
        rows = merge_history((), {"a": _label("a", "Alpha Agency")}, publication="pub1")
        doc = history_doc(rows, publication="pub1", generated_at="2026-09-01T00:00:00Z")
        assert doc["schema"] == ENTITY_SLUG_HISTORY_SCHEMA
        assert doc["publication"] == "pub1"
        assert len(doc["rows"]) == 1

    def test_bad_status_refused(self):
        with pytest.raises(ValueError, match="bad status"):
            history_doc(
                [{"hash": "x", "uuid": "u", "status": "bogus"}],
                publication="p",
                generated_at="t",
            )

    def test_key_retired_twice_refused(self):
        with pytest.raises(ValueError, match="retired twice"):
            history_doc(
                [
                    {"hash": "h", "uuid": "u", "status": "merged"},
                    {"hash": "h", "uuid": "u", "status": "withdrawn"},
                ],
                publication="p",
                generated_at="t",
            )

    def test_two_live_keys_refused(self):
        with pytest.raises(ValueError, match="two live keys"):
            history_doc(
                [
                    {"hash": "h1", "uuid": "u", "status": "current"},
                    {"hash": "h2", "uuid": "u", "status": "current"},
                ],
                publication="p",
                generated_at="t",
            )

    def test_person_row_refused(self):
        """SIG-UI-112: a person row can never appear in the public history."""
        with pytest.raises(ValueError, match="person"):
            history_doc(
                [
                    {
                        "hash": "h",
                        "uuid": "u",
                        "url_type": "person",
                        "status": "current",
                    }
                ],
                publication="p",
                generated_at="t",
            )


class TestMergeHistory:
    def test_first_release_emits_current_only(self):
        labels = {
            "b": _label("b", "Bravo"),
            "a": _label("a", "Alpha"),
        }
        rows = _rows(merge_history((), labels, publication="pub1"))
        assert [r["status"] for r in rows] == ["current", "current"]
        assert {r["uuid"] for r in rows} == {"a", "b"}
        for r in rows:
            assert r["from_pub"] == "pub1"
            assert r["to_pub"] is None
            assert r["hash"] == entity_hash(r["uuid"])

    def test_person_and_unlabelled_emit_nothing(self):
        labels = {
            "p": _label("p", "Jane Doe", kind="person", url_type="person"),
            "w": _label("w", "Withheld", url_type=None),
            "a": _label("a", "Alpha"),
        }
        rows = _rows(merge_history((), labels, publication="pub1"))
        assert [r["uuid"] for r in rows] == ["a"]

    def test_rename_retires_old_key_and_keeps_hash(self):
        prior = _rows(merge_history((), {"e": _label("e", "Old Name")}, publication="pub1"))
        rows = _rows(merge_history(prior, {"e": _label("e", "New Name")}, publication="pub2"))
        by_status = {r["status"]: r for r in rows}
        assert set(by_status) == {"current", "renamed"}
        renamed, current = by_status["renamed"], by_status["current"]
        assert renamed["uuid"] == current["uuid"] == "e"
        assert renamed["hash"] == current["hash"] == entity_hash("e")
        assert renamed["to_pub"] == "pub2"
        current_url = entity_url("agency", name_slug("New Name"), entity_hash("e"))
        assert renamed["target"] == current_url
        assert current["slug"] == name_slug("New Name")
        assert current["from_pub"] == "pub2"

    def test_prior_rows_carry_verbatim(self):
        prior = _rows(merge_history((), {"e": _label("e", "Stable")}, publication="pub1"))
        rows = _rows(merge_history(prior, {"e": _label("e", "Stable")}, publication="pub2"))
        assert rows == prior  # byte-identical — append-only means additive only

    def test_merge_records_survivor(self):
        prior = _rows(
            merge_history(
                (),
                {
                    "gone": _label("gone", "Folded Agency"),
                    "keep": _label("keep", "Surviving Agency"),
                },
                publication="pub1",
            )
        )
        rows = _rows(
            merge_history(
                prior,
                {"keep": _label("keep", "Surviving Agency")},
                publication="pub2",
                merged_into={"gone": "keep"},
                url_types={"gone": "agency", "keep": "agency"},
            )
        )
        merged = [r for r in rows if r["status"] == "merged"]
        assert len(merged) == 1
        assert merged[0]["uuid"] == "gone"
        assert merged[0]["target"] == _label("keep", "Surviving Agency").url
        assert merged[0]["to_pub"] == "pub2"

    def test_split_records_successors(self):
        prior = _rows(merge_history((), {"s": _label("s", "Parent Org")}, publication="pub1"))
        succ = {
            "s1": _label("s1", "Child One"),
            "s2": _label("s2", "Child Two"),
        }
        rows = _rows(
            merge_history(
                prior,
                succ,
                publication="pub2",
                split_into={"s": ["s1", "s2"]},
                url_types={"s": "agency"},
            )
        )
        split = [r for r in rows if r["status"] == "split"]
        assert len(split) == 1
        assert split[0]["uuid"] == "s"
        assert split[0]["target"] == [succ["s1"].url, succ["s2"].url]

    def test_publication_withdrawal_scrubs_every_row(self):
        """P34.19 / F-337: a publication-withdrawn entity's id may not appear
        in any public artifact — all its rows leave the emitted doc, no
        tombstone, nothing emitted."""
        prior = _rows(
            merge_history(
                (),
                {"w": _label("w", "Leaving"), "k": _label("k", "Staying")},
                publication="pub1",
            )
        )
        rows = _rows(
            merge_history(
                prior,
                {"k": _label("k", "Staying")},
                publication="pub2",
                withdrawn={"w"},
                url_types={"w": "agency"},
            )
        )
        assert [r["uuid"] for r in rows] == ["k"]  # "w" is gone entirely

    def test_unexplained_absence_is_honest_withdrawal(self):
        prior = _rows(merge_history((), {"x": _label("x", "Vanished")}, publication="pub1"))
        rows = _rows(merge_history(prior, {}, publication="pub2"))
        gone = [r for r in rows if r["status"] == "withdrawn"]
        assert len(gone) == 1
        assert gone[0]["uuid"] == "x"
        assert gone[0]["target"] is None

    def test_withdrawn_entity_never_keeps_current_key(self):
        """A recorded terminal entity can't hold a live key even when a stale
        registry row still labels it — the record, not the row, governs."""
        labels = {"w": _label("w", "Stale Row")}
        rows = _rows(
            merge_history(
                (),
                labels,
                publication="pub1",
                withdrawn={"w"},
                url_types={"w": "agency"},
            )
        )
        assert rows == []  # scrubbed — no key, no tombstone

    def test_terminal_without_prior_slug_is_none(self):
        rows = _rows(
            merge_history(
                (),
                {"k": _label("k", "Keeper")},
                publication="pub1",
                merged_into={"old": "k"},
                url_types={"old": "agency", "k": "agency"},
            )
        )
        merged = [r for r in rows if r["uuid"] == "old"]
        assert len(merged) == 1
        assert merged[0]["slug"] is None  # never fabricated
        assert merged[0]["hash"] == entity_hash("old")
        assert merged[0]["target"] == _label("k", "Keeper").url

    def test_recorded_terminal_person_emits_nothing(self):
        rows = _rows(
            merge_history(
                (),
                {},
                publication="pub1",
                withdrawn={"p"},
                url_types={"p": "person"},
            )
        )
        assert rows == []

    def test_repeated_merge_is_idempotent(self):
        labels = {"a": _label("a", "Alpha")}
        once = merge_history((), labels, publication="pub1")
        twice = _rows(merge_history(_rows(once), labels, publication="pub2"))
        assert twice == _rows(once)


class TestFreezeHashes:
    def test_no_collision_is_identity(self):
        labels = {"a": _label("a", "Alpha"), "b": _label("b", "Bravo")}
        out = freeze_hashes(labels)
        for eid, lbl in labels.items():
            assert out[eid] is lbl

    def test_collision_extends_the_new_key(self):
        a = _label("a", "Alpha")
        collider = _label("c", "Collider", hash_override=a.hash, slug_override="collider")
        out = freeze_hashes({"a": a, "c": collider})
        assert out["a"].hash == a.hash  # first-come keeps 7 chars
        assert out["c"].hash != a.hash
        assert len(out["c"].hash) == 8  # extended, never rewritten
        assert out["c"].hash == entity_hash("c", length=8)
        assert out["c"].url == entity_url("agency", "collider", out["c"].hash)

    def test_issued_hash_is_never_reissued(self):
        a = _label("a", "Alpha")
        collider = _label("c", "Collider", hash_override=a.hash, slug_override="collider")
        prior = _rows(merge_history((), {"a": a}, publication="pub1"))
        out = freeze_hashes({"c": collider}, prior)
        assert out["c"].hash != a.hash
        assert len(out["c"].hash) == 8

    def test_own_issued_hash_is_reused_not_extended(self):
        """The permanence contract: an entity's own issued hash is reused —
        'already issued' means issued to a DIFFERENT entity."""
        a = _label("a", "Alpha")
        prior = _rows(merge_history((), {"a": a}, publication="pub1"))
        out = freeze_hashes({"a": _label("a", "Alpha Renamed")}, prior)
        assert out["a"].hash == a.hash
        assert len(out["a"].hash) == 7

    def test_issued_set_reads_all_rows(self):
        prior = [
            {"hash": "aaaaaaa", "uuid": "u1", "status": "current"},
            {"hash": "bbbbbbb", "uuid": "u2", "status": "withdrawn"},
        ]
        assert issued_hashes(prior) == {"aaaaaaa", "bbbbbbb"}


class TestUniqueLabels:
    def test_duplicate_label_in_kind_refused(self):
        labels = {
            "a": _label("a", "Same Name"),
            "b": _label("b", "Same Name"),
        }
        with pytest.raises(ValueError, match="SIG-UI-111"):
            check_unique_labels(labels)

    def test_same_label_across_kinds_allowed(self):
        labels = {
            "a": _label("a", "Same Name", kind="agency"),
            "b": _label("b", "Same Name", kind="org"),
        }
        check_unique_labels(labels)  # no raise

    def test_unlabelled_rows_skipped(self):
        labels = {
            "a": _label("a", "Named"),
            "w": _label("w", "Whatever", url_type=None),
        }
        labels["w"] = EntityLabel(
            entity_id="w",
            sig_id=None,
            kind="agency",
            url_type=None,
            label=None,
            descriptor=None,
            label_basis="no_label",
            label_source_id=None,
            place_jkey=None,
            slug=None,
            hash=None,
            url=None,
            disambiguator=None,
            component_id=None,
            part8="pass",
            label_state="withheld",
        )
        check_unique_labels(labels)


class TestResolveRequest:
    def _history(self):
        labels = {
            "okcpd": _label("okcpd", "Oklahoma City Police Department"),
            "oem": _label("oem", "Oklahoma City Emergency Management"),
            "north": _label("north", "North Division"),
            "south": _label("south", "South Division"),
        }
        prior = _rows(
            merge_history(
                (),
                {
                    "okcpd": labels["okcpd"],
                    # The SAME entity under its pub1 label — pub2 renames it.
                    "oem": _label("oem", "OKC OEM Office"),
                    "fusion": _label("fusion", "Fusion Center"),
                    "parent": _label("parent", "Parent Org"),
                    # `feed` is an unexplained absence in pub2 → the K2
                    # lifecycle `withdrawn` tombstone (410); `scrubbed` is
                    # publication-withdrawn → its rows leave the doc entirely.
                    "feed": _label("feed", "Camera Feed", kind="atlas", url_type="atlas"),
                    "scrubbed": _label("scrubbed", "Scrubbed Org"),
                },
                publication="pub1",
            )
        )
        return _rows(
            merge_history(
                prior,
                labels,
                publication="pub2",
                merged_into={"fusion": "okcpd"},
                split_into={"parent": ["north", "south"]},
                withdrawn={"scrubbed"},
                url_types={
                    "fusion": "agency",
                    "parent": "agency",
                    "feed": "atlas",
                    "scrubbed": "agency",
                },
            )
        )

    def test_exact_canonical_serves(self):
        rows = self._history()
        h = entity_hash("okcpd")
        d = resolve_request(rows, f"/entity/agency/oklahoma-city-police-department--{h}/")
        assert d is not None and d.status == 200

    def test_wrong_slug_canonicalises_301(self):
        rows = self._history()
        h = entity_hash("okcpd")
        d = resolve_request(rows, f"/entity/agency/anything-else--{h}/")
        assert d is not None
        assert d.status == 301
        assert d.target == f"/entity/agency/oklahoma-city-police-department--{h}/"

    def test_no_trailing_slash_canonicalises(self):
        rows = self._history()
        h = entity_hash("okcpd")
        d = resolve_request(rows, f"/entity/agency/oklahoma-city-police-department--{h}")
        assert d is not None and d.status == 200

    def test_unknown_hash_is_honest_404(self):
        assert resolve_request(self._history(), "/entity/agency/x--zzzzzzz/") is None

    def test_malformed_paths_are_none(self):
        rows = self._history()
        for bad in (
            "/entity/agency/no-hash-at-all/",
            "/entity/",
            "/other/path/",
            "/id/agency/",
            "",
        ):
            assert resolve_request(rows, bad) is None

    def test_id_url_redirects_to_current(self):
        rows = self._history()
        d = resolve_request(rows, "/id/agency/okcpd")
        assert d is not None
        assert d.status == 302
        okcpd_url = f"/entity/agency/oklahoma-city-police-department--{entity_hash('okcpd')}/"
        assert d.target == okcpd_url

    def test_id_url_for_merged_301s_to_survivor(self):
        rows = self._history()
        d = resolve_request(rows, "/id/agency/fusion")
        assert d is not None
        assert d.status == 301
        okcpd_url = f"/entity/agency/oklahoma-city-police-department--{entity_hash('okcpd')}/"
        assert d.target == okcpd_url

    def test_id_url_for_split_300s_with_successors(self):
        rows = self._history()
        d = resolve_request(rows, "/id/agency/parent")
        assert d is not None
        assert d.status == 300
        assert len(d.targets) == 2

    def test_id_url_for_withdrawn_410s(self):
        rows = self._history()
        d = resolve_request(rows, "/id/atlas/feed")
        assert d is not None and d.status == 410

    def test_publication_withdrawn_uuid_resolves_nothing(self):
        """A publication-withdrawn entity's rows were scrubbed — `/id/` sees
        the honest 404, never the id."""
        rows = self._history()
        assert not any(r["uuid"] == "scrubbed" for r in rows)
        assert resolve_request(rows, "/id/agency/scrubbed") is None

    def test_entity_url_for_retired_key_answers_terminal(self):
        rows = self._history()
        h = entity_hash("fusion")
        d = resolve_request(rows, f"/entity/agency/fusion-center--{h}/")
        assert d is not None and d.status == 301
        d2 = resolve_request(rows, f"/entity/atlas/camera-feed--{entity_hash('feed')}/")
        assert d2 is not None and d2.status == 410
        d3 = resolve_request(rows, f"/entity/agency/parent-org--{entity_hash('parent')}/")
        assert d3 is not None and d3.status == 300

    def test_renamed_old_key_301s_to_new(self):
        rows = self._history()
        h = entity_hash("oem")
        d = resolve_request(rows, f"/entity/agency/okc-oem-office--{h}/")
        assert d is not None
        assert d.status == 301
        assert d.target == (f"/entity/agency/oklahoma-city-emergency-management--{h}/")

    def test_renamed_new_key_serves_and_id_follows(self):
        rows = self._history()
        h = entity_hash("oem")
        d = resolve_request(rows, f"/entity/agency/oklahoma-city-emergency-management--{h}/")
        assert d is not None and d.status == 200
        d2 = resolve_request(rows, "/id/agency/oem")
        assert d2 is not None and d2.status == 302 and d2.target == d.target

    def test_unknown_uuid_is_none(self):
        assert resolve_request(self._history(), "/id/agency/nobody") is None
