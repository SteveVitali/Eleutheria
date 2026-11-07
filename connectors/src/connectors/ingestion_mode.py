# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Declared ingestion mode + incrementality (§21.3, SIG-INGEST-006; P37.5a).

Every connector MUST declare its ingestion mode and its incrementality
strategy. The declaration lives on the connector class itself — mode is a
property of *how the adapter acquires*, not of a registry row one source might
share with a differently-acquiring sibling — and the vocabulary is closed to
the §21.3 mode table. An absent or out-of-vocabulary declaration fails the
``sig-connectors validate`` self-checks and the declaration test, never a
guessed default: a connector that cannot honestly say how it acquires is a
registry defect, not a metadata gap to paper over.
"""

from __future__ import annotations

#: The closed §21.3 ingestion-mode vocabulary. ``manual`` covers the
#: human-in-the-loop/upload-event row (SIG-INGEST-008's manual-acquisition
#: dependencies); ``undeclared`` is not a member — a missing declaration is a
#: violation, never a vocabulary value.
INGESTION_MODES: frozenset[str] = frozenset(
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


def ingestion_declaration(connector_cls: type) -> dict[str, str]:
    """The declared ``{mode, incrementality}`` for one connector class.

    ``""`` mode means undeclared — a violation, reported by
    :func:`ingestion_declaration_violations`, never a vocabulary member.
    """
    return {
        "mode": str(getattr(connector_cls, "ingestion_mode", "")),
        "incrementality": str(getattr(connector_cls, "incrementality", "")),
    }


def ingestion_declaration_violations() -> list[str]:
    """One violation per registered connector whose declaration is broken.

    A registered connector MUST declare ``ingestion_mode`` (a member of
    :data:`INGESTION_MODES`) and a non-empty ``incrementality`` strategy
    (SIG-INGEST-006). The check is evaluated lazily over
    :func:`connectors.stages.registered_connectors` so importing this module
    never forces connector registration.
    """
    from .stages import registered_connectors

    violations: list[str] = []
    for name, cls in sorted(registered_connectors().items()):
        declared = ingestion_declaration(cls)
        mode = declared["mode"]
        if not mode:
            violations.append(
                f"connector {name!r}: ingestion_mode undeclared — every connector "
                "MUST declare its ingestion mode (SIG-INGEST-006)"
            )
        elif mode not in INGESTION_MODES:
            violations.append(
                f"connector {name!r}: ingestion_mode {mode!r} not in the closed "
                f"§21.3 vocabulary {sorted(INGESTION_MODES)} (SIG-INGEST-006)"
            )
        if not declared["incrementality"].strip():
            violations.append(
                f"connector {name!r}: incrementality undeclared — every connector "
                "MUST declare its incrementality strategy (SIG-INGEST-006)"
            )
    return violations


__all__ = [
    "INGESTION_MODES",
    "ingestion_declaration",
    "ingestion_declaration_violations",
]
