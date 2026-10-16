# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.1b — the Artifact Registry cleanup-policy evaluator (the `sig` repo).

``gcloud artifacts repositories set-cleanup-policies`` applies the committed
policy file (``ops/gcp/ar-cleanup-policy.json``) server-side; this module
re-implements the documented semantics offline so the sweep leg can compute
the candidate delete set BEFORE apply, record it verbatim for the eyeballed
dry-run the contract requires, and fail closed when a version referenced by a
live Cloud Run job/service/revision would be a deletion candidate.

Policy JSON shape (the documented ``--policy`` file format): a list of
``{"name", "action": {"type": "Delete"|"Keep"}, "condition"|"mostRecentVersions"}``
where ``condition`` carries ``tagState`` ("tagged"|"untagged"|"any"),
``tagPrefixes``/``versionNamePrefixes``/``packageNamePrefixes`` and the
``olderThan``/``newerThan`` durations ("30d", "86400s"), and
``mostRecentVersions`` carries ``keepCount`` (+ optional package prefixes).
A keep policy never mixes ``condition`` with ``mostRecentVersions``.

Evaluated rule: a version is a delete candidate iff at least one Delete
policy's condition matches it AND no Keep policy retains it (a keep-by-
condition retains every match; a keep-by-mostRecentVersions retains the N
most recent versions of each matching package). Versions that match no Delete
policy are never candidates. Evaluation is deterministic: candidates sort by
(package, uploaded, version).

``merge_live_referenced`` generates the fourth policy — a Keep keyed on
``versionNamePrefixes`` listing the digests of every image referenced by a
live Cloud Run job, service or revision (the keep rule the committed static
file cannot express). The sweep writes the merged file into its evidence dir
and applies that.

The version input is a normalised record::

    {"package": "sig-api", "version": "sha256:<digest>",
     "tags": ["latest"], "uploaded": "2026-09-22T01:21:00Z"}

``normalize_docker_images`` adapts ``gcloud artifacts docker images list
--include-tags --format=json`` rows (``image``/``digest``/``tags``/
``uploadTime``) into that shape.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = "sig.ar-cleanup-candidates/1"


class CleanupPolicyError(Exception):
    """A malformed policy file or input set — fail closed, never a pass."""


@dataclass(frozen=True)
class ImageVersion:
    """One AR version (= one digest within a package/image name)."""

    package: str
    version: str  # "sha256:<digest>" — the AR version name
    tags: tuple[str, ...] = ()
    uploaded: str = ""  # ISO-8601 creation time (AR "createTime"/uploadTime)


def _parse_duration(text: Any) -> int:
    """``"30d"``/``"86400s"``/``"5m"``/``"12h"`` → seconds. Fail closed."""
    if not isinstance(text, str):
        raise CleanupPolicyError(f"duration must be a string like '30d', got {text!r}")
    m = re.fullmatch(r"(\d+)\s*([smhd])", text.strip())
    if not m:
        raise CleanupPolicyError(f"unparseable duration {text!r} (use e.g. '30d', '86400s')")
    return int(m.group(1)) * {"s": 1, "m": 60, "h": 3600, "d": 86400}[m.group(2)]


def _parse_time(text: str) -> datetime:
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as exc:
        raise CleanupPolicyError(f"unparseable version timestamp {text!r}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def load_policy(path: str | Path) -> list[dict[str, Any]]:
    """Load + validate a ``--policy`` JSON file (schema-checked, fail-closed)."""
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CleanupPolicyError(f"unreadable policy file {path}: {exc}") from exc
    if not isinstance(raw, list):
        raise CleanupPolicyError("cleanup policy file must be a JSON array")
    names: set[str] = set()
    for i, pol in enumerate(raw):
        if not isinstance(pol, dict):
            raise CleanupPolicyError(f"policy[{i}] must be an object")
        name = pol.get("name")
        if not name or not isinstance(name, str):
            raise CleanupPolicyError(f"policy[{i}] missing a name")
        if name in names:
            raise CleanupPolicyError(f"duplicate policy name {name!r}")
        names.add(name)
        action = (pol.get("action") or {}).get("type")
        if action not in {"Delete", "Keep"}:
            raise CleanupPolicyError(f"policy {name!r}: action.type must be Delete or Keep")
        cond, mrv = pol.get("condition"), pol.get("mostRecentVersions")
        if action == "Keep" and cond is not None and mrv is not None:
            raise CleanupPolicyError(
                f"keep policy {name!r} mixes condition and mostRecentVersions — "
                "the documented format forbids the mix"
            )
        if cond is None and mrv is None:
            raise CleanupPolicyError(
                f"policy {name!r} carries neither condition nor mostRecentVersions"
            )
        if isinstance(cond, dict):
            for key in ("olderThan", "newerThan"):
                if key in cond:
                    _parse_duration(cond[key])  # schema-checked at load
            tag_state = str(cond.get("tagState", "any")).lower()
            if tag_state not in {"tagged", "untagged", "any"}:
                raise CleanupPolicyError(f"policy {name!r}: unknown tagState {tag_state!r}")
        elif cond is not None:
            raise CleanupPolicyError(f"policy {name!r}: condition must be an object")
        if mrv is not None:
            if not isinstance(mrv, dict) or not isinstance(mrv.get("keepCount"), int):
                raise CleanupPolicyError(
                    f"policy {name!r}: mostRecentVersions needs an integer keepCount"
                )
    return raw


def _str_list(value: Any, *, policy: str, key: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        raise CleanupPolicyError(f"policy {policy!r}: {key} must be a list of strings")
    return value


def _condition_matches(cond: dict[str, Any], v: ImageVersion, now: datetime) -> bool:
    """True when every present condition field matches the version."""
    name = cond.get("_policy", "?")
    tag_state = str(cond.get("tagState", "any")).lower()
    if tag_state == "tagged" and not v.tags:
        return False
    if tag_state == "untagged" and v.tags:
        return False
    if tag_state not in {"tagged", "untagged", "any"}:
        raise CleanupPolicyError(f"policy {name!r}: unknown tagState {tag_state!r}")
    tag_prefixes = _str_list(cond.get("tagPrefixes"), policy=name, key="tagPrefixes")
    if tag_prefixes and not any(t.startswith(p) for t in v.tags for p in tag_prefixes):
        return False
    ver_prefixes = _str_list(
        cond.get("versionNamePrefixes"), policy=name, key="versionNamePrefixes"
    )
    if ver_prefixes and not any(v.version.startswith(p) for p in ver_prefixes):
        return False
    pkg_prefixes = _str_list(
        cond.get("packageNamePrefixes"), policy=name, key="packageNamePrefixes"
    )
    if pkg_prefixes and not any(v.package.startswith(p) for p in pkg_prefixes):
        return False
    uploaded = _parse_time(v.uploaded) if v.uploaded else None
    if cond.get("olderThan") is not None:
        if uploaded is None:
            return False  # an age-bounded policy cannot match an undated version
        if (now - uploaded).total_seconds() < _parse_duration(cond["olderThan"]):
            return False
    if cond.get("newerThan") is not None:
        if uploaded is None:
            return False
        if (now - uploaded).total_seconds() > _parse_duration(cond["newerThan"]):
            return False
    return True


def _mrv_retains(
    mrv: dict[str, Any], v: ImageVersion, by_package: dict[str, list[ImageVersion]]
) -> bool:
    """True when ``v`` is inside this keep policy's newest-N window for its
    package (``packageNamePrefixes`` restricts which packages get the keep)."""
    pkg_prefixes = _str_list(
        mrv.get("packageNamePrefixes"),
        policy="mostRecentVersions",
        key="packageNamePrefixes",
    )
    if pkg_prefixes and not any(v.package.startswith(p) for p in pkg_prefixes):
        return False
    keep = int(mrv.get("keepCount", 0))
    if keep <= 0:
        return False
    newest = by_package.get(v.package, [])[:keep]
    return v in newest


def normalize_docker_images(raw: Any) -> list[ImageVersion]:
    """Adapt ``gcloud artifacts docker images list --include-tags --format=json``
    rows to :class:`ImageVersion` records. The listed ``image`` is the package
    (e.g. ``…/sig/sig-api`` — shortened to the leaf package name), ``digest`` is
    the version, ``tags`` the tag list, ``uploadTime`` the creation time."""
    if not isinstance(raw, list):
        raise CleanupPolicyError("images input must be a JSON array")
    out: list[ImageVersion] = []
    for i, row in enumerate(raw):
        if not isinstance(row, dict):
            raise CleanupPolicyError(f"images[{i}] must be an object")
        package = str(row.get("package") or str(row.get("image", "")).rsplit("/", 1)[-1])
        version = str(row.get("version") or row.get("digest", ""))
        if not package or not version:
            raise CleanupPolicyError(f"images[{i}] needs package+version (or image+digest)")
        tags = row.get("tags") or []
        if not isinstance(tags, list):
            raise CleanupPolicyError(f"images[{i}].tags must be a list")
        out.append(
            ImageVersion(
                package=package,
                version=version,
                tags=tuple(str(t) for t in tags),
                uploaded=str(
                    row.get("uploaded") or row.get("uploadTime") or row.get("createTime") or ""
                ),
            )
        )
    return out


def merge_live_referenced(
    policies: Sequence[dict[str, Any]], digests: Iterable[str]
) -> list[dict[str, Any]]:
    """Append the generated keep-live-referenced policy: a Keep keyed on
    ``versionNamePrefixes`` covering every digest a live Cloud Run job, service
    or revision references. An empty digest set adds no policy (an empty
    prefix list is ambiguous — the honest shape is omission)."""
    refs = sorted({d.strip() for d in digests if d and d.strip()})
    merged = [dict(p) for p in policies]
    if refs:
        merged.append(
            {
                "name": "keep-live-referenced",
                "action": {"type": "Keep"},
                "condition": {"tagState": "any", "versionNamePrefixes": refs},
            }
        )
    return merged


def evaluate(
    policies: Sequence[dict[str, Any]],
    versions: Sequence[ImageVersion],
    *,
    now: datetime,
) -> dict[str, Any]:
    """Compute the candidate delete set under ``policies`` — deterministic and
    offline. Returns the ``sig.ar-cleanup-candidates/1`` record:
    ``candidates`` (the versions every matching Delete policy would remove and
    no Keep retains) and ``kept`` (with the retaining policy name)."""
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    tagged: list[dict[str, Any]] = []
    for pol in policies:
        pol = dict(pol)
        if isinstance(pol.get("condition"), dict):
            pol["condition"] = dict(pol["condition"])
            pol["condition"]["_policy"] = pol.get("name", "?")
        tagged.append(pol)
    deletes = [p for p in tagged if (p.get("action") or {}).get("type") == "Delete"]
    keeps = [p for p in tagged if (p.get("action") or {}).get("type") == "Keep"]

    by_package: dict[str, list[ImageVersion]] = {}
    for v in versions:
        by_package.setdefault(v.package, []).append(v)
    for pkg in by_package:
        by_package[pkg].sort(
            key=lambda v: (
                _parse_time(v.uploaded) if v.uploaded else datetime.min.replace(tzinfo=UTC)
            ),
            reverse=True,
        )

    candidates: list[dict[str, Any]] = []
    kept: list[dict[str, Any]] = []
    for v in versions:
        matched_deletes = [
            p["name"]
            for p in deletes
            if isinstance(p.get("condition"), dict) and _condition_matches(p["condition"], v, now)
        ]
        if not matched_deletes:
            kept.append(
                {"package": v.package, "version": v.version, "by": "(no delete policy matches)"}
            )
            continue
        retained_by = ""
        for p in keeps:
            cond, mrv = p.get("condition"), p.get("mostRecentVersions")
            if isinstance(mrv, dict) and _mrv_retains(mrv, v, by_package):
                retained_by = p["name"]
                break
            if isinstance(cond, dict) and _condition_matches(cond, v, now):
                retained_by = p["name"]
                break
        if retained_by:
            kept.append({"package": v.package, "version": v.version, "by": retained_by})
        else:
            candidates.append(
                {
                    "package": v.package,
                    "version": v.version,
                    "tags": list(v.tags),
                    "uploaded": v.uploaded,
                    "matchedBy": matched_deletes,
                }
            )
    candidates.sort(key=lambda c: (c["package"], c["uploaded"], c["version"]))
    kept.sort(key=lambda c: (c["package"], c["version"]))
    return {
        "kind": SCHEMA,
        "now": now.isoformat(timespec="seconds"),
        "totalVersions": len(versions),
        "candidates": candidates,
        "kept": kept,
    }


def referenced_digests(*bodies: Any) -> list[str]:
    """Extract ``sha256:…`` digest strings referenced by live Cloud Run bodies —
    ``run jobs list``/``services list``/``revisions list --format=json`` rows.
    Every container image ref carrying ``@sha256:`` contributes its digest; a
    tag (or ``:latest``) reference contributes nothing — it is a SIG-SEC-008
    violation the sweep records, never a digest to protect."""
    found: set[str] = set()
    blob = json.dumps(bodies, default=str)
    found.update(re.findall(r"@(sha256:[0-9a-f]{64})", blob))
    return sorted(found)


__all__ = [
    "SCHEMA",
    "CleanupPolicyError",
    "ImageVersion",
    "evaluate",
    "load_policy",
    "merge_live_referenced",
    "normalize_docker_images",
    "referenced_digests",
]
