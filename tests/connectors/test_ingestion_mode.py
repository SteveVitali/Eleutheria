# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Declared ingestion mode + incrementality (SIG-INGEST-006, P37.5a)."""

from __future__ import annotations

from connectors.ingestion_mode import (  # noqa: E402
    INGESTION_MODES,
    ingestion_declaration,
    ingestion_declaration_violations,
)
from connectors.stages import Connector, registered_connectors

import connectors  # noqa: F401 - importing registers every connector (SIG-INGEST-021)


def test_ingestion_mode_vocabulary_is_the_spec_table() -> None:
    # §21.3's mode table, verbatim — the closed vocabulary, not a guess.
    assert INGESTION_MODES == frozenset(
        {
            "bulk_file_download",
            "rest_api",
            "replication_diff",
            "bulk_geodata",
            "html_scraping",
            "headless_browser_capture",
            "manual",
            "partner_feed",
            "alert_stream",
        }
    )


def test_every_registered_connector_declares_mode_and_incrementality() -> None:
    # SIG-INGEST-006: every connector MUST declare its ingestion mode and its
    # incrementality strategy — the self-check reports nothing.
    assert registered_connectors(), "no connectors registered (SIG-INGEST-021)"
    assert ingestion_declaration_violations() == []
    for name, cls in sorted(registered_connectors().items()):
        declared = ingestion_declaration(cls)
        assert declared["mode"] in INGESTION_MODES, f"{name}: {declared['mode']!r}"
        assert declared["incrementality"].strip(), f"{name}: empty incrementality"


def test_undeclared_connector_is_a_violation() -> None:
    # Fail closed: a connector that cannot name its mode is a defect.
    class Undeclared(Connector):
        name = "undeclared-toy"

        def discover(self, ctx):  # type: ignore[no-untyped-def]
            return []

        def fetch(self, ctx, target):  # type: ignore[no-untyped-def]
            raise AssertionError

        def parse(self, ctx, capture):  # type: ignore[no-untyped-def]
            return None

        def extract(self, ctx, parsed):  # type: ignore[no-untyped-def]
            return []

        def normalize(self, ctx, raw_claims):  # type: ignore[no-untyped-def]
            return []

    assert ingestion_declaration(Undeclared) == {"mode": "", "incrementality": ""}


def test_out_of_vocabulary_mode_is_a_violation() -> None:
    # A mode outside §21.3's table fails the self-check the same way an absent
    # one does — the vocabulary is closed.
    class BadMode(Connector):
        name = "bad-mode-toy"
        ingestion_mode = "carrier_pigeon"
        incrementality = "hand-delivered"

        def discover(self, ctx):  # type: ignore[no-untyped-def]
            return []

        def fetch(self, ctx, target):  # type: ignore[no-untyped-def]
            raise AssertionError

        def parse(self, ctx, capture):  # type: ignore[no-untyped-def]
            return None

        def extract(self, ctx, parsed):  # type: ignore[no-untyped-def]
            return []

        def normalize(self, ctx, raw_claims):  # type: ignore[no-untyped-def]
            return []

    assert ingestion_declaration(BadMode)["mode"] == "carrier_pigeon"
    assert "carrier_pigeon" not in INGESTION_MODES
