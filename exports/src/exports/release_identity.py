# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Release-identity v2 — descriptor v2, labels, export ids, clock guards and
promotion refusals (P35.12 / REL-01 — SIG-REL-001/002/003; G3 §3; ADR-161).

This module owns the *identity* half of the G3 release model:

* **`sig.publication-descriptor/2`** — :func:`descriptor_v2_document` emits the
  field layout G3 §3.2 fixes exactly (identity, spine-snapshot, export, code,
  versions, publication-gates, evaluation, disclosures, roots, build blocks),
  and :func:`validate_descriptor` re-checks every required field fail-closed.
  v1 descriptors stay parseable (:data:`DESCRIPTOR_SCHEMA_V1`); only v2 is
  promotable.
* **The human label** ``sig-YYYY-MM-DD.N`` — the UTC date of ``as_of_world``
  plus a per-day ordinal allocated under the registry lock
  (:func:`allocate_label`). The date is *derived* from the snapshot instant,
  never typed; a duplicate label can never be issued.
* **The export id** ``sig-export-<YYYYMMDDTHHMMSSZ>-<key8>`` —
  :func:`export_id` keys the digest over the reproducibility inputs including
  the snapshot instants, the watermark and the commit (the NEW-1 collision
  fix: two same-day exports can no longer collide).
* **The §3.3 clock guards** — the AR-3 frozen-window refusal, the host-clock
  sanity check, the ``as-of ≤ built_at`` / no-future-date rule, the
  ``--replay`` labelling rule and the emitted-date scan.
* **The SIG-REL-002 promotion refusals** — :func:`promotion_refusals` names
  every reason a candidate may not promote: a v1 descriptor, a dirty tree,
  an unpushed commit, a ``0.0.0`` version, a non-sha commit, a date earlier
  than the previous release.
"""

from __future__ import annotations

import email.utils
import fcntl
import re
import subprocess
import urllib.request
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from .manifest import canonical_json, sha256_hex

#: Descriptor schema ids. v1 stays parseable (read/validate paths accept it);
#: only v2 is promotable (SIG-REL-002).
DESCRIPTOR_SCHEMA_V1 = "sig.publication-descriptor/1"
DESCRIPTOR_SCHEMA_V2 = "sig.publication-descriptor/2"

#: The release-label registry document (``registry/labels.json``).
LABELS_SCHEMA = "sig.release-labels/1"

#: The canonical code remote every release's ``code.repository`` names.
CODE_REPOSITORY = "https://github.com/SteveVitali/Eleutheria"

#: The four environments a descriptor may declare (G3 §3.2).
ENVIRONMENTS = frozenset({"production", "staging", "fixture", "replay"})

#: ``sig-YYYY-MM-DD.N`` — the immutable human release label (SIG-REL-001).
LABEL_RE = re.compile(r"^sig-(\d{4})-(\d{2})-(\d{2})\.(\d+)$")
#: ``sig-export-<YYYYMMDDTHHMMSSZ>-<key8>`` — the internal export id (NEW-1 fix).
EXPORT_ID_RE = re.compile(r"^sig-export-\d{8}T\d{6}Z-[0-9a-f]{8}$")
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
SHA64_RE = re.compile(r"^[0-9a-f]{64}$")

#: AR-3 frozen windows (``docs/build/reports/OPERATING_MODE_R11.md``): the
#: monthly batch window runs day 6 00:00Z through day 13 12:00Z and the daily
#: restricted window runs 03:00Z through 06:30Z. Emergency takedowns are
#: exempt — only with a recorded ``--emergency <reason>``.
_MONTHLY_FREEZE = (6, 13, 12, 0)  # day6 00:00Z → day13 12:00Z
_DAILY_FREEZE = ((3, 0), (6, 30))  # 03:00Z → 06:30Z

#: Host-clock sanity bound (G3 §3.3 rule 2): ``|T0 − remote Date| ≤ 120 s``.
HOST_CLOCK_TOLERANCE_S = 120.0
#: The default endpoint whose HTTP ``Date`` header the host clock is checked
#: against (G3 §3.3 rule 2 marks the endpoint choice [unverified]; a Google
#: HTTPS GET is the design's default).
HOST_CLOCK_URL = "https://www.google.com"
#: A typed ``--as-of`` may name this run's cut instant only inside the same
#: UTC day — an earlier day is a historical snapshot and requires ``--replay``.
#: (``export.sh`` stamps ``date -u`` when the operator runs it; the Cloud Run
#: job may start hours later, so a same-day lag is the normal path, never a
#: replay claim.)
_FUTURE_ALLOWANCE = timedelta(minutes=5)

#: Field names whose values may legitimately carry a real-world future date
#: inside an emitted document (B1 §5.4 test 1 allow-list) — the
#: emitted-date scan skips them.
_FUTURE_ALLOWED_FIELDS = frozenset(
    {
        "expiry_date",
        "expires",
        "valid_until",
        "sunset_date",
        "sunset",
        "renewal_date",
        "retention_until",
        "review_by",
        "deadline",
    }
)

_ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_ISO_INSTANT_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


class ClockGuardError(Exception):
    """A §3.3 clock guard refusal — the run names the guard, never continues."""


class LabelRegistryError(Exception):
    """A release-label registry refusal (collision, malformed registry)."""


def parse_instant(value: Any) -> datetime | None:
    """Parse an ISO-8601 instant (``Z`` or offset) to an aware UTC datetime.

    A bare ``YYYY-MM-DD`` date parses as that day's UTC midnight — the
    descriptor's as-of fields are instants, but v1 records carry date-grain
    values the comparison rules still judge.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime(value.year, value.month, value.day)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            text = text + "T00:00:00+00:00"
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- #
# The human label — sig-YYYY-MM-DD.N under the registry lock                   #
# --------------------------------------------------------------------------- #


def label_for(as_of_world: datetime | str, ordinal: int) -> str:
    """``sig-YYYY-MM-DD.N`` for one snapshot instant + ordinal (derived, never typed)."""
    dt = parse_instant(as_of_world)
    if dt is None:
        raise LabelRegistryError(f"label date must derive from an ISO instant, got {as_of_world!r}")
    if ordinal < 1:
        raise LabelRegistryError(f"label ordinal must be ≥ 1, got {ordinal}")
    return f"sig-{dt.date().isoformat()}.{ordinal}"


def _labels_path(registry_root: Path) -> Path:
    return registry_root / "labels.json"


def load_labels(registry_root: Path | str) -> dict[str, Any]:
    """The ``sig.release-labels/1`` registry document (created on first write)."""
    path = _labels_path(Path(registry_root))
    if not path.exists():
        return {"schema": LABELS_SCHEMA, "labels": []}
    import json

    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or doc.get("schema") != LABELS_SCHEMA:
        raise LabelRegistryError(
            f"{path} is not a {LABELS_SCHEMA} document — refusing to allocate against it"
        )
    return doc


def _occupied_ordinals(registry_root: Path, day: date) -> set[int]:
    """Every ``.N`` already issued for ``day`` — the labels ledger plus any
    catalog publication carrying a parseable label of that date (labels the
    registry issued before ``labels.json`` existed stay occupied forever)."""
    import json

    occupied: set[int] = set()
    doc = load_labels(registry_root)
    for entry in doc.get("labels") or []:
        m = LABEL_RE.match(str(entry.get("label") or ""))
        if m and date(int(m[1]), int(m[2]), int(m[3])) == day:
            occupied.add(int(m[4]))
        elif str(entry.get("as_of_world_date") or "") == day.isoformat():
            # a recorded allocation whose label never parses is still a slot —
            # count it by its declared ordinal when present
            n = entry.get("ordinal")
            if isinstance(n, int) and n >= 1:
                occupied.add(n)
    catalog = registry_root / "catalog.json"
    if catalog.exists():
        try:
            cat = json.loads(catalog.read_text(encoding="utf-8"))
        except ValueError:
            cat = {}
        for pub in cat.get("publications") or []:
            label = str(pub.get("label") or pub.get("data_release_id") or "")
            m = LABEL_RE.match(label)
            if m and date(int(m[1]), int(m[2]), int(m[3])) == day:
                occupied.add(int(m[4]))
            else:
                # an unlabeled publication pinned to this as-of date occupies a
                # slot too — count it via the next free ordinal rule
                asof = str((pub.get("compat") or {}).get("as_of_world") or "")
                if asof == day.isoformat():
                    occupied.add(max(occupied) + 1 if occupied else 1)
    return occupied


def allocate_label(
    registry_root: Path | str,
    as_of_world: datetime | str,
    *,
    publication_id: str | None = None,
    allocated_at: datetime | None = None,
    environment: str | None = None,
) -> str:
    """Allocate the next ``sig-YYYY-MM-DD.N`` for ``as_of_world``'s UTC date.

    The allocation is atomic: ``labels.lock`` is flock'd, the occupied
    ordinals re-counted, the entry appended and the file re-written — two
    same-day exports therefore always take different ``.N`` (SIG-REL-001).
    The label's date is derived from the snapshot instant, never from typed
    input (§3.3 rule 6).
    """
    import os

    root = Path(registry_root)
    root.mkdir(parents=True, exist_ok=True)
    day = parse_instant(as_of_world)
    if day is None:
        raise LabelRegistryError(
            f"label allocation needs an ISO as_of_world instant, got {as_of_world!r}"
        )
    allocated = allocated_at or datetime.now(UTC)
    lock_path = root / "labels.lock"
    with lock_path.open("a", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            occupied = _occupied_ordinals(root, day.date())
            ordinal = 1
            while ordinal in occupied:
                ordinal += 1
            label = label_for(day, ordinal)
            doc = load_labels(root)
            if any(e.get("label") == label for e in doc.get("labels") or []):
                raise LabelRegistryError(
                    f"label {label} already issued — refusing reuse (SIG-REL-001)"
                )
            doc.setdefault("labels", []).append(
                {
                    "label": label,
                    "publication_id": publication_id,
                    "as_of_world_date": day.date().isoformat(),
                    "ordinal": ordinal,
                    "allocated_at": _iso(allocated),
                    "environment": environment,
                    "state": "allocated",
                }
            )
            path = _labels_path(root)
            tmp = path.with_name(".labels.json.tmp")
            tmp.write_bytes(canonical_json(doc))
            os.replace(tmp, path)
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    return label


def record_label_publication(registry_root: Path | str, label: str, publication_id: str) -> None:
    """Bind an allocated label to its publication id (post-build fill-in)."""
    import os

    root = Path(registry_root)
    lock_path = root / "labels.lock"
    with lock_path.open("a", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            doc = load_labels(root)
            hit = False
            for entry in doc.get("labels") or []:
                if entry.get("label") == label:
                    entry["publication_id"] = publication_id
                    hit = True
            if hit:
                path = _labels_path(root)
                tmp = path.with_name(".labels.json.tmp")
                tmp.write_bytes(canonical_json(doc))
                os.replace(tmp, path)
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


# --------------------------------------------------------------------------- #
# The export id — sig-export-<ts>-<key8>                                       #
# --------------------------------------------------------------------------- #


def export_id(export_id_inputs: Mapping[str, Any], ts: datetime | str) -> str:
    """``sig-export-<YYYYMMDDTHHMMSSZ>-<key8>`` (G3 §3.1, NEW-1).

    ``key8`` is the leading sha256 hex of the canonical export-id inputs —
    the reproducibility inputs *plus* the snapshot instants, the spine
    watermark and the code commit — so two same-day exports can never share
    an id unless they truly bind identical inputs.
    """
    dt = parse_instant(ts)
    if dt is None:
        raise ValueError(f"export id needs an ISO instant for <ts>, got {ts!r}")
    key = sha256_hex(canonical_json(dict(export_id_inputs)))[:8]
    return f"sig-export-{dt.strftime('%Y%m%dT%H%M%SZ')}-{key}"


# --------------------------------------------------------------------------- #
# §3.3 clock guards                                                            #
# --------------------------------------------------------------------------- #


def freeze_window(t0: datetime) -> str | None:
    """The AR-3 window ``t0`` falls inside, else ``None``.

    Monthly: day 6 00:00Z → day 13 12:00Z. Daily: 03:00Z → 06:30Z (UTC).
    """
    t0 = t0.astimezone(UTC)
    start_day, end_day, end_h, end_m = _MONTHLY_FREEZE
    if t0.day >= start_day and (
        t0.day < end_day or (t0.day == end_day and (t0.hour, t0.minute) < (end_h, end_m))
    ):
        return (
            f"monthly batch window day {start_day} 00:00Z → day {end_day} {end_h:02d}:{end_m:02d}Z"
        )
    (h1, m1), (h2, m2) = _DAILY_FREEZE
    t = t0.hour * 60 + t0.minute
    if h1 * 60 + m1 <= t < h2 * 60 + m2:
        return f"daily restricted window {h1:02d}:{m1:02d}Z → {h2:02d}:{m2:02d}Z"
    return None


def assert_not_frozen(t0: datetime, *, emergency: str | None = None) -> None:
    """Refuse a build inside an AR-3 window unless ``emergency`` names a reason."""
    window = freeze_window(t0)
    if window is None:
        return
    if emergency and emergency.strip():
        return
    raise ClockGuardError(
        f"AR-3 frozen window ({window}) — refusing to start the export; "
        "re-run outside the window or pass --emergency <reason>"
    )


def http_date_fetcher(url: str = HOST_CLOCK_URL, *, timeout: float = 5.0) -> str:
    """The ``Date`` header of an HTTPS GET to ``url`` (the host-clock oracle)."""
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "sig-clock-check/1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - declared endpoint
        return str(resp.headers.get("Date") or "")


def host_clock_report(
    t0: datetime,
    *,
    url: str = HOST_CLOCK_URL,
    timeout: float = 5.0,
    tolerance_s: float = HOST_CLOCK_TOLERANCE_S,
    fetcher: Callable[[], str] | None = None,
) -> dict[str, Any]:
    """Check the host clock against a remote HTTP ``Date`` header.

    Returns the report ``{url, remote_date, skew_seconds, ok}``; raises
    :class:`ClockGuardError` when the fetch fails or the skew exceeds the
    120 s tolerance — a wildly wrong host clock is the B1 failure class and
    a build may never run on it.
    """
    fetch = fetcher or (lambda: http_date_fetcher(url, timeout=timeout))
    try:
        header = fetch()
    except Exception as exc:  # noqa: BLE001 - any fetch failure is a refusal
        raise ClockGuardError(
            f"host-clock check could not read the remote Date header ({url}): {exc} — "
            "refusing (re-run with --skip-host-clock-check to record a declared skip)"
        ) from exc
    remote = None
    if header:
        try:
            remote = email.utils.parsedate_to_datetime(header)
        except (TypeError, ValueError):
            remote = None
    if remote is None:
        raise ClockGuardError(
            f"host-clock check got an unparseable Date header {header!r} from {url}"
        )
    if remote.tzinfo is None:
        remote = remote.replace(tzinfo=UTC)
    skew = abs((t0.astimezone(UTC) - remote.astimezone(UTC)).total_seconds())
    if skew > tolerance_s:
        raise ClockGuardError(
            f"host clock skew {skew:.1f}s exceeds {tolerance_s:.0f}s against {url} "
            f"(T0={_iso(t0)}, remote={_iso(remote)}) — the machine clock is wrong"
        )
    return {
        "url": url,
        "remote_date": _iso(remote),
        "skew_seconds": round(skew, 3),
        "ok": True,
    }


def check_as_of_clock(
    as_of: str | None,
    t0: datetime,
    *,
    replay: str | None = None,
) -> None:
    """The --as-of clock rule for the export path.

    * unparseable → refuse;
    * later than ``t0`` (+5 min skew) → refuse — an export can never emit a
      future as-of (the AC's "future as-of fails");
    * a UTC day *earlier* than ``t0``'s without ``--replay`` → refuse — a
      historical snapshot is a replay and must be labelled Class S;
    * otherwise pass (a same-day typed instant is the normal cut path —
      ``export.sh`` stamps ``date -u`` before the job queues).
    """
    if as_of is None:
        return
    dt = parse_instant(as_of)
    if dt is None:
        raise ClockGuardError(f"--as-of {as_of!r} is not an ISO-8601 date or instant")
    t0u = t0.astimezone(UTC)
    if dt > t0u + _FUTURE_ALLOWANCE:
        raise ClockGuardError(
            f"--as-of {as_of!r} is later than the build instant {_iso(t0u)} — "
            "an export can never name a future snapshot (SIG-REL-003)"
        )
    if dt.date() < t0u.date() and not (replay and replay.strip()):
        raise ClockGuardError(
            f"--as-of {as_of!r} names an earlier UTC day than {_iso(t0u)} — "
            "a historical snapshot is a replay; pass --replay <reason> "
            "(Class S, environment=replay)"
        )


def descriptor_clock_failures(
    descriptor: Mapping[str, Any], *, now: datetime | None = None
) -> list[str]:
    """The §3.3 rule-3 ordering: ``as_of_world ≤ as_of_belief ≤ built_at ≤ now+5m``.

    Reads the v2 snapshot/build blocks (v1 documents are judged by their own
    flat fields where present). Returns one failure line per violation.
    """
    now = now or datetime.now(UTC)
    snap = descriptor.get("snapshot") or {}
    world = parse_instant(snap.get("as_of_world") or descriptor.get("as_of_world"))
    belief = parse_instant(snap.get("as_of_belief") or descriptor.get("as_of_belief"))
    built_at = parse_instant((descriptor.get("build") or {}).get("built_at"))
    failures: list[str] = []
    if world is None:
        failures.append("as_of_world is absent or unparseable")
    if belief is None:
        failures.append("as_of_belief is absent or unparseable")
    if built_at is None:
        failures.append("built_at is absent or unparseable")
    if world is not None and belief is not None and world > belief:
        failures.append(f"as_of_world {_iso(world)} is later than as_of_belief {_iso(belief)}")
    if belief is not None and built_at is not None and belief > built_at:
        failures.append(f"as_of_belief {_iso(belief)} is later than built_at {_iso(built_at)}")
    if built_at is not None and built_at > now.astimezone(UTC) + _FUTURE_ALLOWANCE:
        failures.append(f"built_at {_iso(built_at)} is later than now {_iso(now)} (+5m)")
    return failures


def _iter_date_strings(obj: Any, path: str = "") -> Iterable[tuple[str, str]]:
    """Yield ``(field_path, iso-looking string)`` pairs under ``obj``."""
    if isinstance(obj, Mapping):
        for key, value in obj.items():
            child = f"{path}.{key}" if path else str(key)
            yield from _iter_date_strings(value, child)
    elif isinstance(obj, (list, tuple)):
        for i, value in enumerate(obj):
            yield from _iter_date_strings(value, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, obj


def emitted_date_failures(doc: Any, built_at: datetime, *, _path: str = "") -> list[str]:
    """No emitted date later than ``built_at`` (§3.3 rule 4), scanned over a
    JSON-shaped document. ``_FUTURE_ALLOWED_FIELDS`` names the real-world
    future fields (expiry/sunset/…) the allow-list exempts."""
    failures: list[str] = []
    for field_path, text in _iter_date_strings(doc):
        leaf = field_path.rsplit(".", 1)[-1]
        if leaf in _FUTURE_ALLOWED_FIELDS:
            continue
        for match in _ISO_INSTANT_RE.finditer(text):
            dt = parse_instant(match.group(0))
            if dt is not None and dt > built_at.astimezone(UTC) + _FUTURE_ALLOWANCE:
                failures.append(
                    f"{field_path or '(document)'}: emitted instant {match.group(0)} "
                    f"is later than built_at {_iso(built_at)}"
                )
                break
    return failures


def emitted_file_date_failures(
    files: Iterable[Path], built_at: datetime, *, json_only: bool = False
) -> list[str]:
    """The emitted-date scan over release-metadata files (descriptor,
    catalog entry, build report, landings — §3.3 rule 4's named surfaces:
    descriptor, stamp, landing). Record payload bytes are data, not stamps,
    and carry legitimate future-dated claims — out of this scan's scope."""
    import json

    failures: list[str] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        try:
            doc = json.loads(text)
        except ValueError:
            doc = text
        for fail in emitted_date_failures(doc, built_at):
            failures.append(f"{path.name}: {fail}")
    return failures


# --------------------------------------------------------------------------- #
# The sig.publication-descriptor/2 document                                    #
# --------------------------------------------------------------------------- #


def descriptor_v2_document(
    *,
    label: str,
    environment: str,
    snapshot: Mapping[str, Any],
    export: Mapping[str, Any],
    code: Mapping[str, Any],
    versions: Mapping[str, Any],
    gates: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    disclosures: Sequence[Mapping[str, Any]],
    compartment_projections: Mapping[str, Mapping[str, Any]],
    evidence_root: str | None,
    dossier_root: str | None,
    transparency_root: str | None,
    boundaries_root: str | None,
    built_at: str,
    replay_reason: str | None = None,
) -> dict[str, Any]:
    """The canonical ``sig.publication-descriptor/2`` document.

    Field names follow G3 §3.2 exactly — the layout is the seam the release
    stamp (P35.13), the site and the publish rows consume. Every field is an
    intentional rendering input; the document is ID-free (no publication id,
    no URLs). Declared-empty inputs carry ``None``/``[]`` — populated or
    explicitly declared-empty, never absent.
    """
    return {
        "schema": DESCRIPTOR_SCHEMA_V2,
        "label": label,
        "environment": environment,
        "snapshot": {
            "as_of_world": snapshot.get("as_of_world"),
            "as_of_belief": snapshot.get("as_of_belief"),
            "belief_pinned": bool(snapshot.get("belief_pinned")),
            "spine_watermark": snapshot.get("spine_watermark"),
            "materialize_run": snapshot.get("materialize_run"),
            "sqitch_head": snapshot.get("sqitch_head"),
            "restore_point": snapshot.get("restore_point"),
        },
        "export": {
            "id": export.get("id"),
            "input_manifest_sha256": export.get("input_manifest_sha256"),
            "content_key": export.get("content_key"),
        },
        "code": {
            "commit": code.get("commit"),
            "repository": code.get("repository") or CODE_REPOSITORY,
            "tree": code.get("tree"),
            "images": {"export": code.get("images_export")},
        },
        "renderer": {
            "package": (code.get("renderer") or {}).get("package") or "sig-exports",
            "version": (code.get("renderer") or {}).get("version"),
            "revision": code.get("commit"),
        },
        "site_renderer": {
            "package": "sig-web",
            "version": (code.get("site_renderer") or {}).get("version"),
            "astro_version": (code.get("site_renderer") or {}).get("astro_version"),
            "package_lock_sha256": (code.get("site_renderer") or {}).get("package_lock_sha256"),
        },
        "versions": {
            "ruleset_version": versions.get("ruleset_version"),
            "resolver_version": versions.get("resolver_version"),
            "policy_version": versions.get("policy_version"),
            "projection_version": versions.get("projection_version"),
            "search_index_version": versions.get("search_index_version"),
            "ontology_version": versions.get("ontology_version"),
            "ontology_generated_sha256": versions.get("ontology_generated_sha256"),
            "descriptor_schema": DESCRIPTOR_SCHEMA_V2,
        },
        "gates": {
            "disposition_root": gates.get("disposition_root"),
            "rights_registry_sha256": gates.get("rights_registry_sha256"),
            "attribution_gate": {
                "version": (gates.get("attribution_gate") or {}).get("version")
                or "sig.attribution-gate/1",
                "pass_count": (gates.get("attribution_gate") or {}).get("pass_count"),
            },
        },
        "evaluation": {
            "status": evaluation.get("status") or "deferred",
            "eval_confidence": {
                "mode": (evaluation.get("eval_confidence") or {}).get("mode") or "shadow",
                "applied": list((evaluation.get("eval_confidence") or {}).get("applied") or []),
            },
            "deferral_refs": list(evaluation.get("deferral_refs") or []),
            "review_status_summary": evaluation.get("review_status_summary"),
        },
        "disclosures": [dict(d) for d in disclosures],
        "graph_quality": gates.get("graph_quality"),
        "compartment_projections": {
            comp: dict(proj) for comp, proj in sorted(compartment_projections.items())
        },
        "evidence_root": evidence_root,
        "dossier_root": dossier_root,
        "transparency_root": transparency_root,
        "boundaries_root": boundaries_root,
        "build": {
            "built_at": built_at,
            "publish_class": "S" if environment == "replay" else None,
            "replay_reason": replay_reason if environment == "replay" else None,
        },
    }


def _is_hex(text: Any, n: int) -> bool:
    return isinstance(text, str) and bool(re.fullmatch(rf"[0-9a-f]{{{n}}}", text))


def validate_descriptor(doc: Mapping[str, Any], *, now: datetime | None = None) -> list[str]:
    """Fail-closed field validation for ``sig.publication-descriptor/2``.

    Returns one line per violation; an empty list means the descriptor
    carries every §3.2 field, populated or explicitly declared-empty, with
    the clock ordering enforced.
    """
    failures: list[str] = []
    if doc.get("schema") != DESCRIPTOR_SCHEMA_V2:
        failures.append(
            f"schema {doc.get('schema')!r} != {DESCRIPTOR_SCHEMA_V2!r} — "
            "only v2 descriptors are valid under this validator"
        )
    label = doc.get("label")
    label_match = LABEL_RE.match(label) if isinstance(label, str) else None
    if label_match is None:
        failures.append(f"label {label!r} is not sig-YYYY-MM-DD.N")
    else:
        world = parse_instant((doc.get("snapshot") or {}).get("as_of_world"))
        if world is not None and label != label_for(world, int(label_match[4])):
            failures.append(
                f"label {label!r} does not derive from snapshot.as_of_world "
                "(the label date is the data date, never typed)"
            )
    if doc.get("environment") not in ENVIRONMENTS:
        failures.append(f"environment {doc.get('environment')!r} not in {sorted(ENVIRONMENTS)}")
    snap = doc.get("snapshot") or {}
    for field in (
        "as_of_world",
        "as_of_belief",
        "belief_pinned",
        "spine_watermark",
        "materialize_run",
        "sqitch_head",
        "restore_point",
    ):
        if field not in snap:
            failures.append(f"snapshot.{field} absent — every §3.2 field must exist")
    if parse_instant(snap.get("as_of_world")) is None:
        failures.append("snapshot.as_of_world is not an ISO instant")
    if parse_instant(snap.get("as_of_belief")) is None:
        failures.append("snapshot.as_of_belief is not an ISO instant")
    if not isinstance(snap.get("belief_pinned"), bool):
        failures.append("snapshot.belief_pinned is not a bool")
    export = doc.get("export") or {}
    if not isinstance(export.get("id"), str) or not export["id"]:
        failures.append("export.id absent")
    elif not (EXPORT_ID_RE.match(export["id"]) or export["id"].startswith("sig-")):
        failures.append(f"export.id {export['id']!r} is not a recognised export/release id")
    if not _is_hex(export.get("input_manifest_sha256"), 64):
        failures.append("export.input_manifest_sha256 is not 64-hex")
    if not _is_hex(export.get("content_key"), 64):
        failures.append("export.content_key is not 64-hex")
    code = doc.get("code") or {}
    commit = code.get("commit")
    if not isinstance(commit, str) or not SHA40_RE.match(commit):
        failures.append(f"code.commit {commit!r} is not a 40-hex sha")
    if code.get("repository") != CODE_REPOSITORY:
        failures.append(f"code.repository {code.get('repository')!r} != {CODE_REPOSITORY!r}")
    if code.get("tree") not in ("clean", "dirty", "unknown"):
        failures.append(f"code.tree {code.get('tree')!r} not in clean/dirty/unknown")
    renderer = doc.get("renderer") or {}
    if renderer.get("revision") != commit:
        failures.append("renderer.revision != code.commit (NEW-3: one code identity)")
    for field in ("package", "version"):
        if not renderer.get(field):
            failures.append(f"renderer.{field} absent")
    versions = doc.get("versions") or {}
    for field in (
        "ruleset_version",
        "resolver_version",
        "policy_version",
        "projection_version",
        "search_index_version",
        "ontology_version",
        "ontology_generated_sha256",
        "descriptor_schema",
    ):
        if field not in versions:
            failures.append(f"versions.{field} absent")
        elif field == "ontology_generated_sha256":
            if versions[field] is not None and not _is_hex(versions[field], 64):
                failures.append("versions.ontology_generated_sha256 is not 64-hex")
        elif not versions[field]:
            failures.append(f"versions.{field} empty")
    if versions.get("descriptor_schema") != DESCRIPTOR_SCHEMA_V2:
        failures.append("versions.descriptor_schema != sig.publication-descriptor/2")
    gates = doc.get("gates") or {}
    if not _is_hex(gates.get("disposition_root"), 64):
        failures.append("gates.disposition_root is not 64-hex")
    if gates.get("rights_registry_sha256") is not None and not _is_hex(
        gates["rights_registry_sha256"], 64
    ):
        failures.append("gates.rights_registry_sha256 is not 64-hex")
    gate = gates.get("attribution_gate") or {}
    if not gate.get("version"):
        failures.append("gates.attribution_gate.version absent")
    evaluation = doc.get("evaluation") or {}
    if evaluation.get("status") not in ("deferred", "provisional", "certified"):
        failures.append(
            f"evaluation.status {evaluation.get('status')!r} not in deferred/provisional/certified"
        )
    disclosures = doc.get("disclosures")
    if not isinstance(disclosures, list):
        failures.append("disclosures is not a list")
    else:
        for i, d in enumerate(disclosures):
            if not (isinstance(d, Mapping) and d.get("id") and _is_hex(d.get("text_sha256"), 64)):
                failures.append(f"disclosures[{i}] is not {{id, text_sha256}}")
    for root_field in ("transparency_root", "boundaries_root"):
        value = doc.get(root_field)
        if value is not None and not _is_hex(value, 64):
            failures.append(f"{root_field} is not null-or-64-hex")
    if "boundaries_root" not in doc:
        failures.append("boundaries_root absent — the JUR-01 input field must exist")
    if "transparency_root" not in doc:
        failures.append("transparency_root absent — the J3 TX-13b field must exist")
    build = doc.get("build") or {}
    if parse_instant(build.get("built_at")) is None:
        failures.append("build.built_at is not an ISO instant")
    if doc.get("environment") == "replay" and build.get("publish_class") != "S":
        failures.append("environment=replay must carry build.publish_class 'S'")
    failures.extend(descriptor_clock_failures(doc, now=now))
    return failures


# --------------------------------------------------------------------------- #
# Promotion refusals (SIG-REL-002)                                             #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RepoState:
    """The repo facts promotion re-verifies live (never trusted from the
    descriptor): HEAD, tree cleanliness and the commits pushed to a remote."""

    head: str | None
    clean: bool | None
    pushed: frozenset[str]


def probe_repo_state(repo_root: Path | str) -> RepoState:
    """Read :class:`RepoState` from ``repo_root`` via git (fail-closed: an
    unresolvable fact reads as ``None``/empty, never invented)."""
    root = Path(repo_root)

    def _git(*args: str) -> str | None:
        try:
            out = subprocess.run(
                ["git", *args],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=20,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if out.returncode != 0:
            return None
        return out.stdout.strip()

    head = _git("rev-parse", "HEAD")
    status = _git("status", "--porcelain")
    return RepoState(
        head=head if head and SHA40_RE.match(head) else None,
        clean=(status == "" if status is not None else None),
        # membership is probed per-commit by :func:`commit_is_pushed`; the set
        # stays empty here (a probe over every remote ref is O(n) git calls)
        pushed=frozenset(),
    )


def commit_is_pushed(repo_root: Path | str, commit: str) -> bool | None:
    """Whether ``commit`` is contained in any remote-tracking ref.

    ``git branch -r --contains <sha>`` exits 0 and lists branches only when a
    remote ref reaches the commit; an empty list means unpushed. ``None``
    when git cannot answer.
    """
    try:
        out = subprocess.run(
            ["git", "branch", "-r", "--contains", commit],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return bool(out.stdout.strip())


def _v2_versions_zero(doc: Mapping[str, Any]) -> list[str]:
    """Every version-bearing field reading ``0.0.0`` or empty.

    Core version fields (ruleset/resolver/policy/projection/renderer/ontology)
    must be populated — ``None`` is a refusal, not a declared-empty. Optional
    J3 fields (``site_renderer.*``, ``ontology_generated_sha256``) may be
    declared-empty honestly; a literal ``0.0.0`` is a fake version either way.
    """
    versions = doc.get("versions") or {}
    bad: list[str] = []
    for field, value, required in (
        ("versions.ruleset_version", versions.get("ruleset_version"), True),
        ("versions.resolver_version", versions.get("resolver_version"), True),
        ("versions.policy_version", versions.get("policy_version"), True),
        ("versions.projection_version", versions.get("projection_version"), True),
        ("versions.ontology_version", versions.get("ontology_version"), True),
        ("renderer.version", (doc.get("renderer") or {}).get("version"), True),
        (
            "site_renderer.version",
            (doc.get("site_renderer") or {}).get("version"),
            False,
        ),
    ):
        if value is None:
            if required:
                bad.append(f"{field}={value!r}")
            continue
        if value == "" or str(value).startswith("0.0.0"):
            bad.append(f"{field}={value!r}")
    return bad


def promotion_refusals(
    descriptor: Mapping[str, Any],
    *,
    repo_root: Path | str | None = None,
    previous_as_of_world: str | None = None,
    tree_clean: bool | None = None,
    pushed: bool | None = None,
) -> list[str]:
    """The SIG-REL-002 promotion gate — every refusal reason, named.

    * a v1 (or any non-v2) descriptor → refused (this alone keeps the
      ``p-17b713`` fixture candidate out — the v2-only rule);
    * ``code.commit`` not a 40-hex sha → refused;
    * the descriptor's recorded or the live tree dirty → refused;
    * the commit absent from every remote-tracking ref → refused (unpushed);
    * label ``0.0.0``/missing, or any version field ``0.0.0`` → refused;
    * ``snapshot.as_of_world`` earlier than the previous release's
      → refused (promotion is monotonic; rollback is the older path —
      a same-instant re-cut of the same snapshot may still promote).

    ``tree_clean``/``pushed`` let the caller inject the live repo facts;
    ``repo_root`` makes the function probe them itself. ``None`` (git cannot
    answer) is fail-closed — treated as dirty/unpushed respectively for a
    promotion decision only when the descriptor claims promotion posture
    (a probe failure is itself a refusal: an unverifiable commit is never
    promotable).
    """
    refusals: list[str] = []
    schema = doc_get(descriptor, "schema")
    if schema != DESCRIPTOR_SCHEMA_V2:
        refusals.append(
            f"descriptor schema {schema!r} is not {DESCRIPTOR_SCHEMA_V2} — "
            "only v2 is promotable (SIG-REL-002; v1 candidates such as "
            "p-17b713… are excluded by this rule)"
        )
        return refusals  # nothing else is decidable on a foreign schema

    commit = str((descriptor.get("code") or {}).get("commit") or "")
    if not SHA40_RE.match(commit):
        refusals.append(f"code.commit {commit!r} is not a 40-hex sha")

    recorded_tree = (descriptor.get("code") or {}).get("tree")
    if recorded_tree == "dirty":
        refusals.append("descriptor records a dirty tree at build time")
    live_clean = tree_clean
    if repo_root is not None and tree_clean is None:
        live_clean = probe_repo_state(repo_root).clean
    if live_clean is False:
        refusals.append("the working tree is dirty now — promotion needs a clean tree")
    if live_clean is None and recorded_tree is None:
        refusals.append("tree state unverifiable (descriptor records none and git cannot answer)")

    is_pushed = pushed
    if repo_root is not None and pushed is None and SHA40_RE.match(commit):
        is_pushed = commit_is_pushed(repo_root, commit)
    if is_pushed is False:
        refusals.append(f"commit {commit[:12] or commit!r} is pushed to no remote ref")
    if is_pushed is None and repo_root is not None:
        refusals.append("could not verify the commit is pushed (git cannot answer)")

    label = str(descriptor.get("label") or "")
    if not LABEL_RE.match(label) or label.endswith(".0") or label == "0.0.0":
        refusals.append(f"label {label!r} is not a valid sig-YYYY-MM-DD.N label")
    zeros = _v2_versions_zero(descriptor)
    if zeros:
        refusals.append(f"version fields read 0.0.0 or empty: {', '.join(zeros)}")

    if previous_as_of_world is not None:
        world = (descriptor.get("snapshot") or {}).get("as_of_world")
        w = parse_instant(world)
        p = parse_instant(previous_as_of_world)
        if w is not None and p is not None and w < p:
            refusals.append(
                f"snapshot.as_of_world {world!r} is earlier than the previous "
                f"release's {previous_as_of_world!r} — promotion is monotonic "
                "(rollback is the older path)"
            )
    return refusals


def doc_get(doc: Mapping[str, Any], key: str) -> Any:
    return doc.get(key) if isinstance(doc, Mapping) else None


def descriptor_release_id(doc: Mapping[str, Any]) -> str:
    """The catalog-facing release id — v2 ``label``, v1 ``data_release_id``."""
    if doc.get("schema") == DESCRIPTOR_SCHEMA_V2:
        return str(doc.get("label") or "")
    return str(doc.get("data_release_id") or "")


def descriptor_export_id(doc: Mapping[str, Any]) -> str:
    """The export id — v2 ``export.id``, v1 ``data_release_id``."""
    if doc.get("schema") == DESCRIPTOR_SCHEMA_V2:
        return str((doc.get("export") or {}).get("id") or "")
    return str(doc.get("data_release_id") or "")


def descriptor_as_of_world(doc: Mapping[str, Any]) -> str:
    if doc.get("schema") == DESCRIPTOR_SCHEMA_V2:
        return str((doc.get("snapshot") or {}).get("as_of_world") or "")
    return str(doc.get("as_of_world") or "")


def descriptor_as_of_belief(doc: Mapping[str, Any]) -> str:
    if doc.get("schema") == DESCRIPTOR_SCHEMA_V2:
        return str((doc.get("snapshot") or {}).get("as_of_belief") or "")
    return str(doc.get("as_of_belief") or "")


def descriptor_versions_block(doc: Mapping[str, Any]) -> dict[str, Any]:
    """The flat ruleset/resolver/policy/projection/renderer view the catalog
    entry's ``reproducibility`` block carries — same shape for v1 and v2."""
    if doc.get("schema") == DESCRIPTOR_SCHEMA_V2:
        versions = doc.get("versions") or {}
        return {
            "as_of_world": descriptor_as_of_world(doc),
            "as_of_belief": descriptor_as_of_belief(doc),
            "ruleset_version": versions.get("ruleset_version"),
            "resolver_version": versions.get("resolver_version"),
            "policy_version": versions.get("policy_version"),
            "projection_version": versions.get("projection_version"),
            "renderer": doc.get("renderer") or {},
        }
    return {
        "as_of_world": doc.get("as_of_world"),
        "as_of_belief": doc.get("as_of_belief"),
        "ruleset_version": doc.get("ruleset_version"),
        "resolver_version": doc.get("resolver_version"),
        "policy_version": doc.get("policy_version"),
        "projection_version": doc.get("projection_version"),
        "renderer": doc.get("renderer") or {},
    }


__all__ = [
    "CODE_REPOSITORY",
    "DESCRIPTOR_SCHEMA_V1",
    "DESCRIPTOR_SCHEMA_V2",
    "ENVIRONMENTS",
    "EXPORT_ID_RE",
    "HOST_CLOCK_TOLERANCE_S",
    "HOST_CLOCK_URL",
    "LABEL_RE",
    "LABELS_SCHEMA",
    "ClockGuardError",
    "LabelRegistryError",
    "RepoState",
    "allocate_label",
    "assert_not_frozen",
    "check_as_of_clock",
    "commit_is_pushed",
    "descriptor_as_of_belief",
    "descriptor_as_of_world",
    "descriptor_clock_failures",
    "descriptor_export_id",
    "descriptor_release_id",
    "descriptor_v2_document",
    "descriptor_versions_block",
    "emitted_date_failures",
    "emitted_file_date_failures",
    "export_id",
    "freeze_window",
    "host_clock_report",
    "label_for",
    "load_labels",
    "parse_instant",
    "probe_repo_state",
    "promotion_refusals",
    "record_label_publication",
    "validate_descriptor",
]
