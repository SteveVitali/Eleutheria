# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The OSM changeset feed → §7 leverage metric (§7, §35.2; P21.7, ADR-069).

Human mappers apply SIG's suggestions **in their own accounts** (SIG-CONTRIB-015);
the only way SIG learns a contribution landed is to read OSM's **public** changeset
feed and count the accepted changesets that carry the declared hashtag
(:data:`~tasks.contribution.CHANGESET_HASHTAG`, SIG-CONTRIB-016e). That count *is*
the §7 leverage metric, and because the hashtag is public a third party can
reconstruct it — the property that makes the metric credible.

Two invariants, pinned by ``tests/tasks/test_tasks_osm_feed.py``:

* **Never store OSM user data (Part VIII §0.7).** :func:`parse_changesets` reads
  **only** the changeset id, its ``comment`` tag, and whether it is closed. It never
  reads the ``user`` / ``uid`` attributes — the :class:`~tasks.contribution.UpstreamChangeset`
  the ledger stores has no field for them, so an OSM display name cannot be
  persisted even by accident. The metric attributes to the *changeset id*, nothing
  more (defining standard §3.1: cite the changeset, no synthetic certainty).
* **Append-only + idempotent (P1–P3).** :func:`ingest_changesets` folds changesets
  into a :class:`~tasks.contribution.LeverageLedger`, which is keyed by changeset id,
  so re-running over the same feed adds **zero** new attributions.

No live poll runs by default (HG-08): the CLI replays recorded fixtures
(``tests/tasks/fixtures/osm_changesets_*.xml``). :func:`build_feed_url` constructs
the public changeset-API URL a live poll *would* fetch (hashtag filtering is applied
client-side on the ``comment`` tag), but SIG performs **no automated OSM writes** and
this run performs **no live OSM read** (§26 conduct, SIG-INGEST-037).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode

from .contribution import (
    CHANGESET_HASHTAG,
    LeverageLedger,
    UpstreamChangeset,
    carries_hashtag,
)

__all__ = [
    "OSM_CHANGESET_API",
    "DEFAULT_FIXTURE_GLOB",
    "IngestResult",
    "parse_changesets",
    "ingest_changesets",
    "pull_files",
    "leverage_metric_json",
    "build_feed_url",
]

#: The public OSM changeset API (read needs no key; SIG-CONTRIB-016e, §26).
OSM_CHANGESET_API = "https://api.openstreetmap.org/api/0.6/changesets"

#: Where recorded changeset fixtures live for replay (HG-08: no live poll this run).
DEFAULT_FIXTURE_GLOB = "tests/tasks/fixtures/osm_changesets_*.xml"


@dataclass(frozen=True)
class IngestResult:
    """The outcome of folding a changeset feed into the leverage ledger.

    ``added`` is the changeset ids **newly** attributed this run (empty on a re-run —
    the ledger is idempotent by id). ``ledger`` carries the running §7 metric.
    """

    added: tuple[str, ...]
    ledger: LeverageLedger

    @property
    def added_count(self) -> int:
        """How many new hashtag-bearing changesets this run attributed."""
        return len(self.added)


def parse_changesets(
    xml_source: str | bytes,
    *,
    hashtag: str = CHANGESET_HASHTAG,
    since: str | None = None,
) -> list[UpstreamChangeset]:
    """Parse an OSM changeset-API XML document into hashtag-bearing attributions.

    Reads **only** the id, the ``comment`` tag, and the ``open``/``closed_at``
    attributes — never ``user``/``uid`` (Part VIII §0.7). Keeps only changesets whose
    comment carries ``hashtag`` (the feed is hashtag-filtered), optionally dropping
    those closed before ``since`` (an ISO-8601 instant; ISO strings sort correctly).
    A still-open changeset is recorded as not-yet-accepted.
    """
    root = ET.fromstring(xml_source) if isinstance(xml_source, (str, bytes)) else xml_source
    out: list[UpstreamChangeset] = []
    for cs in root.iter("changeset"):
        changeset_id = cs.get("id")
        if not changeset_id:
            continue
        comment = ""
        for tag in cs.findall("tag"):
            if tag.get("k") == "comment":
                comment = tag.get("v", "") or ""
                break
        if not carries_hashtag(comment, hashtag=hashtag):
            # Only SIG-hashtagged edits are SIG-attributable (SIG-CONTRIB-016e); a
            # non-SIG changeset is ignored — and, crucially, never stored.
            continue
        closed_at = cs.get("closed_at")
        if since is not None and (closed_at is None or closed_at < since):
            continue
        # A closed changeset is an accepted (landed) edit; an open one is in flight.
        accepted = (cs.get("open") or "true").strip().lower() == "false"
        out.append(
            UpstreamChangeset(changeset_id=str(changeset_id), comment=comment, accepted=accepted)
        )
    return out


def ingest_changesets(
    ledger: LeverageLedger, changesets: Iterable[UpstreamChangeset]
) -> IngestResult:
    """Fold ``changesets`` into ``ledger`` (append-only, idempotent by id).

    Returns the ids newly attributed this run — empty when the feed has already been
    ingested, which is the idempotency guarantee the AC checks (re-run adds 0).
    """
    before = ledger.attributed_changeset_ids()
    ledger.record_all(changesets)
    after = ledger.attributed_changeset_ids()
    return IngestResult(added=tuple(sorted(after - before)), ledger=ledger)


def pull_files(
    paths: Iterable[str | Path],
    *,
    ledger: LeverageLedger | None = None,
    hashtag: str = CHANGESET_HASHTAG,
    since: str | None = None,
) -> IngestResult:
    """Replay recorded changeset fixtures into a leverage ledger (HG-08: no live poll)."""
    ledger = ledger or LeverageLedger(hashtag=hashtag)
    collected: list[UpstreamChangeset] = []
    for path in paths:
        xml = Path(path).read_bytes()
        collected.extend(parse_changesets(xml, hashtag=hashtag, since=since))
    return ingest_changesets(ledger, collected)


def leverage_metric_json(ledger: LeverageLedger) -> dict[str, object]:
    """The §7 metric as a JSON-serialisable record for the web export (data.ts).

    Carries only the hashtag, the accepted count, and the attributed changeset ids —
    public, auditable, and free of any OSM user data (Part VIII §0.7).
    """
    return {
        "hashtag": ledger.hashtag,
        "accepted_operator_attributions": ledger.accepted_operator_attributions(),
        "attributed_changeset_ids": sorted(ledger.attributed_changeset_ids()),
    }


def build_feed_url(
    *,
    base_url: str = OSM_CHANGESET_API,
    since: str | None = None,
    bbox: str | None = None,
    closed_only: bool = True,
) -> str:
    """Construct the public changeset-API URL a live poll would GET (never called here).

    Hashtag filtering is applied client-side on the ``comment`` tag (the core API has
    no hashtag filter); ``since`` maps to the API ``time`` window and ``bbox`` scopes
    a jurisdiction. Provided so the live URL is testable without any network egress.
    """
    params: dict[str, str] = {}
    if closed_only:
        params["closed"] = "true"
    if since is not None:
        params["time"] = since
    if bbox is not None:
        params["bbox"] = bbox
    query = urlencode(params)
    return f"{base_url}?{query}" if query else base_url
