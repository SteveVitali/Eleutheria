# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""``sig-ops release`` — the one release-pipeline command family (P35.53 /
REL-03a; SIG-REL-004 single writer, SIG-REL-005 immutable-after-staging;
G3 §4.1/§4.4/§5.1–5.2).

Everything in this module is a *shell* over machinery that already landed:
the immutable namespace builder is ``exports.release.build_release``, the
integrity re-verifier is ``exports.release.validate_release``, the §3.3
clock guards are ``exports.release_identity``'s, the withdrawal barrier is
``ops.release_serving``'s and the bounded publish proof is
``ops.release_publish_verify``'s. This module adds what the G3 model puts
around them and nothing else:

* **The registry** — an object store rooted at a ``gs://…-sig-release``
  bucket (or a local directory in tests/dry-runs) laid out exactly as G3
  §4.1 fixes it: ``registry/{catalog.json, compat_index.json,
  withdrawals.json, activations/, events/, LOCK}``, ``registry/conf/<gen>/``
  (P35.54's), ``staged/{r,v,s,releases}/<pub>/`` and ``status/**``.
* **The lock** — ``registry/LOCK`` is a create-if-absent object
  (``if-generation-match=0``). A second writer gets a refusal, never a
  queue; a dead run's lock clears only through ``--break-lock <reason>``
  and the reason is recorded. The lock carries a digest of the registry
  state (``catalog.json``, ``compat_index.json``, ``withdrawals.json``,
  ``latest.json``) taken at acquisition; a verb re-checks it before its
  writes and *refuses a stale generation* — somebody else wrote registry
  state under the held lock.
* **The journal** — every verb under ``--apply`` appends one
  ``sig.release-event/1`` object at
  ``registry/events/<ts>-<verb>-<pub8>.json``, created if-absent. ``status``
  folds the journal into the §3.4 state machine
  (``cut → built → staged → verified|failed → promoted →
  superseded|rolled-back-from|withdrawn-whole``, ``never-promoted``).
* **The write gate** — ``--dry-run`` is the default and performs no write
  (the lock is *planned*, never taken); ``--apply`` is required for any
  write, exactly as §5.1 fixes it.
* **Immutability** — ``stage`` inserts every object with
  ``if-generation-match=0``: a name collision refuses and no staged byte is
  ever overwritten. An object already present with identical bytes is a
  *resume* (skip + count), which is what makes a crashed stage safe to
  re-run.

The verbs whose behaviour other rows own (``promote`` → P35.54's conf
generations, ``rollback``/``clear-latest``/``withdraw`` → P35.55,
``classify`` → P35.60's classifier, the V1–V14 suite in ``verify`` →
P35.56/P35.58) are still *declared here*: they take the lock, honour
``--dry-run``/``--apply``, journal a ``refused`` outcome naming the owner
row, and never pretend to do work they do not. ``classify`` is landed
(P35.60 / ``ops.release_classify``) and still answers Class S whenever a
check is unevaluable — RM-6 fail-closed.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Protocol

from exports.release_identity import (
    assert_not_frozen,
    check_as_of_clock,
    host_clock_report,
)

from . import gcs as _gcs

#: The §4.1 staged namespaces — ``staged/<ns>/<pub>/`` — verbatim.
STAGED_NAMESPACES: tuple[str, ...] = ("r", "v", "s", "releases")
#: The §4.1 registry objects whose bytes define "registry state" for the
#: stale-generation check (labels.json is included: build rewrites it under
#: the lock, and drift on it must refuse too).
REGISTRY_STATE_FILES: tuple[str, ...] = (
    "catalog.json",
    "compat_index.json",
    "withdrawals.json",
    "latest.json",
    "labels.json",
)
#: The §4.1 top-level layout the bucket carries (the IaC + tests pin it).
NAMESPACE_LAYOUT: dict[str, tuple[str, ...]] = {
    "staged": STAGED_NAMESPACES,
    "registry": (
        "catalog.json",
        "compat_index.json",
        "withdrawals.json",
        "activations/",
        "events/",
        "LOCK",
        "conf/",
    ),
    "status": ("**",),
}
LOCK_OBJECT = "registry/LOCK"
EVENTS_PREFIX = "registry/events/"
LABELS_OBJECT = "registry/labels.json"

#: Journal schema id — one object per applied verb.
EVENT_SCHEMA = "sig.release-event/1"

#: §3.4 lifecycle kinds (the fold order status prints).
LIFECYCLE_KINDS: tuple[str, ...] = (
    "cut",
    "built",
    "staged",
    "verified",
    "failed",
    "promoted",
    "superseded",
    "rolled-back-from",
    "withdrawn-whole",
    "never-promoted",
)


class PipelineError(Exception):
    """A release-pipeline refusal — carries a machine-readable ``code``."""

    def __init__(self, code: str, message: str, detail: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.detail = detail


class LockHeld(PipelineError):
    def __init__(self, held: dict[str, Any]) -> None:
        super().__init__(
            "lock-held",
            f"registry/LOCK is held ({held.get('verb')}, "
            f"{held.get('acquired_at')}, holder {held.get('holder')}) — a "
            "stale lock clears only with --break-lock <reason>",
            held,
        )


class StaleGeneration(PipelineError):
    def __init__(self, recorded: str, current: str) -> None:
        super().__init__(
            "stale-generation",
            "registry state moved under the held lock "
            f"(recorded {recorded[:16]}…, current {current[:16]}…) — "
            "refusing to write; re-read and re-run",
            {"recorded": recorded, "current": current},
        )


class NameCollision(PipelineError):
    def __init__(self, name: str) -> None:
        super().__init__(
            "name-collision",
            f"{name} already exists with different bytes — stage refuses: "
            "nothing staged is ever overwritten (SIG-REL-005)",
            name,
        )


class VerbDeferred(PipelineError):
    """A declared verb whose behaviour a later row owns — journaled, then
    refused with the owning row named."""

    def __init__(self, verb: str, owner: str) -> None:
        super().__init__(
            "verb-deferred",
            f"`release {verb}` is declared but its behaviour lands at "
            f"{owner} — nothing was mutated",
            {"verb": verb, "owner": owner},
        )


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _md5_b64(data: bytes) -> str:
    return base64.b64encode(hashlib.md5(data).digest()).decode()  # noqa: S324 - GCS md5Hash contract


# --------------------------------------------------------------------------- #
# The store abstraction — a gs:// bucket or a local dir, one contract         #
# --------------------------------------------------------------------------- #


class Store(Protocol):
    """The release-bucket contract. ``insert`` is create-if-absent;
    ``replace`` is metageneration-matched conditional write; ``delete`` is
    for ``registry/LOCK`` release only — nothing else in the layout is ever
    deleted (RM-2)."""

    def read(self, name: str) -> bytes | None: ...
    def stat(self, name: str) -> dict[str, Any] | None: ...
    def insert(
        self, name: str, body: bytes, *, content_type: str = "application/octet-stream"
    ) -> dict[str, Any]: ...
    def replace(
        self,
        name: str,
        body: bytes,
        *,
        generation: int,
        content_type: str = "application/octet-stream",
    ) -> dict[str, Any]: ...
    def delete(self, name: str) -> None: ...
    def list(self, prefix: str) -> list[str]: ...
    def describe(self) -> str: ...


class LocalDirStore:
    """The store over a plain directory — tests and local dry-runs.

    ``insert`` opens with ``O_EXCL`` (the local create-if-absent);
    generation is the file's mtime-counter surrogate — every create bumps
    it, so ``replace``'s precondition behaves like GCS generations.
    """

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def describe(self) -> str:
        return f"dir:{self.root}"

    def _path(self, name: str) -> Path:
        p = (self.root / name).resolve()
        if not str(p).startswith(str(self.root.resolve())):
            raise PipelineError("bad-name", f"object name escapes the registry root: {name!r}")
        return p

    def read(self, name: str) -> bytes | None:
        p = self._path(name)
        return p.read_bytes() if p.is_file() else None

    def stat(self, name: str) -> dict[str, Any] | None:
        p = self._path(name)
        if not p.is_file():
            return None
        data = p.read_bytes()
        return {
            "generation": int(p.stat().st_mtime_ns),
            "md5Hash": _md5_b64(data),
            "size": len(data),
        }

    def insert(
        self, name: str, body: bytes, *, content_type: str = "application/octet-stream"
    ) -> dict[str, Any]:
        p = self._path(name)
        p.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        except FileExistsError as exc:
            raise _gcs.GcsPreconditionFailed(f"{name} exists") from exc
        with os.fdopen(fd, "wb") as fh:
            fh.write(body)
        return {"name": name, "generation": int(p.stat().st_mtime_ns)}

    def replace(
        self,
        name: str,
        body: bytes,
        *,
        generation: int,
        content_type: str = "application/octet-stream",
    ) -> dict[str, Any]:
        p = self._path(name)
        meta = self.stat(name)
        if meta is None:
            return self.insert(name, body, content_type=content_type)
        if int(meta["generation"]) != int(generation):
            raise _gcs.GcsPreconditionFailed(
                f"{name} generation {meta['generation']} != expected {generation}"
            )
        p.write_bytes(body)
        return {"name": name, "generation": int(p.stat().st_mtime_ns)}

    def delete(self, name: str) -> None:
        self._path(name).unlink(missing_ok=True)

    def list(self, prefix: str) -> list[str]:
        base = self._path(prefix)
        root = self.root.resolve()
        if base.is_file():
            return [prefix]
        if not base.is_dir():
            return []
        return sorted(str(p.relative_to(root)) for p in base.rglob("*") if p.is_file())


class GcsStore:
    """The store over ``gs://<bucket>[/<prefix>]`` — the production path."""

    def __init__(
        self, bucket: str, prefix: str = "", *, client: _gcs.GcsBucket | None = None
    ) -> None:
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self.client = client or _gcs.GcsBucket(bucket=bucket)

    def describe(self) -> str:
        return f"gs://{self.bucket}/{self.prefix}".rstrip("/")

    def _name(self, name: str) -> str:
        return f"{self.prefix}/{name}" if self.prefix else name

    def read(self, name: str) -> bytes | None:
        try:
            return self.client.get_object(self._name(name))
        except _gcs.GcsError as exc:
            if "HTTP 404" in str(exc):
                return None
            raise

    def stat(self, name: str) -> dict[str, Any] | None:
        return self.client.get_object_meta(self._name(name))

    def insert(
        self, name: str, body: bytes, *, content_type: str = "application/octet-stream"
    ) -> dict[str, Any]:
        return self.client.insert_object(
            self._name(name), body, if_generation_match=0, content_type=content_type
        )

    def replace(
        self,
        name: str,
        body: bytes,
        *,
        generation: int,
        content_type: str = "application/octet-stream",
    ) -> dict[str, Any]:
        return self.client.insert_object(
            self._name(name),
            body,
            if_generation_match=int(generation),
            content_type=content_type,
        )

    def delete(self, name: str) -> None:
        self.client.delete_object(self._name(name))

    def list(self, prefix: str) -> list[str]:
        return self.client.list_objects(self._name(prefix))


def open_store(registry: str) -> Store:
    """``--registry gs://<bucket>[/<prefix>]`` → :class:`GcsStore`; any other
    value is a local directory → :class:`LocalDirStore`. Empty → refuse:
    the pipeline never guesses a registry."""
    if not registry:
        raise PipelineError(
            "no-registry",
            "--registry (or SIG_RELEASE_REGISTRY) must name the release "
            "registry — a local dir or gs://<bucket>; it is never defaulted",
        )
    if registry.startswith("gs://"):
        rest = registry[5:]
        bucket, _, prefix = rest.partition("/")
        if not bucket:
            raise PipelineError("bad-registry", f"unparseable registry {registry!r}")
        return GcsStore(bucket, prefix)
    return LocalDirStore(registry)


# --------------------------------------------------------------------------- #
# Registry state digest + the lock                                          #
# --------------------------------------------------------------------------- #


def registry_state_digest(store: Store) -> str:
    """sha256 over the registry-state objects (the §3.4 "generation" the
    stage-time guard judges). Missing objects hash as their name — an absent
    file still contributes deterministically."""
    h = hashlib.sha256()
    for name in REGISTRY_STATE_FILES:
        body = store.read(f"registry/{name}")
        h.update(name.encode())
        h.update(b"\0")
        h.update(body if body is not None else b"")
        h.update(b"\0")
    return h.hexdigest()


@dataclass
class Lock:
    """A held ``registry/LOCK`` — refresh before writes, release after."""

    store: Store
    record: dict[str, Any]
    state_digest: str
    released: bool = False

    def refresh(self) -> None:
        """Refuse when registry state drifted under the held lock."""
        current = registry_state_digest(self.store)
        if current != self.state_digest:
            raise StaleGeneration(self.state_digest, current)

    def release(self) -> None:
        if self.released:
            return
        self.refresh()  # refuse to close on a silently-drifted registry
        self.store.delete(LOCK_OBJECT)
        self.released = True

    def __enter__(self) -> Lock:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: Any,
    ) -> Literal[False]:
        # On refusal the lock stays held — the journal that wrote it is the
        # forensic record; --break-lock is the recorded override.
        if exc_type is None:
            self.release()
        return False


def acquire_lock(
    store: Store,
    verb: str,
    *,
    break_lock: str | None = None,
    now: datetime | None = None,
    holder: str | None = None,
) -> Lock:
    """Create ``registry/LOCK`` if-absent; refuse a held lock unless
    ``break_lock`` names a reason (recorded into the fresh lock)."""
    now = now or _now()
    existing = store.read(LOCK_OBJECT)
    if existing is not None:
        held: dict[str, Any] = {}
        try:
            held = json.loads(existing)
        except ValueError:
            held = {"verb": "<unreadable>"}
        if not break_lock:
            raise LockHeld(held)
        held["broke_by"] = verb
        held["broke_at"] = _iso(now)
        held["break_reason"] = break_lock
        store.delete(LOCK_OBJECT)
    state_digest = registry_state_digest(store)
    record: dict[str, Any] = {
        "schema": "sig.release-lock/1",
        "verb": verb,
        "holder": holder or os.environ.get("SIG_RELEASE_HOLDER") or "local",
        "acquired_at": _iso(now),
        "registry_state_sha256": state_digest,
    }
    if existing is not None:
        record["broke_lock"] = held
    try:
        store.insert(LOCK_OBJECT, _canonical(record), content_type="application/json")
    except _gcs.GcsPreconditionFailed as exc:
        raise LockHeld({"verb": "<raced>", "acquired_at": "just now"}) from exc
    return Lock(store=store, record=record, state_digest=state_digest)


# --------------------------------------------------------------------------- #
# The event journal                                                          #
# --------------------------------------------------------------------------- #


def emit_event(
    store: Store,
    verb: str,
    publication_id: str | None,
    payload: dict[str, Any],
    *,
    now: datetime | None = None,
) -> str:
    """Append one ``sig.release-event/1`` object (create-if-absent). Returns
    the object name."""
    now = now or _now()
    short = (publication_id or "root")[:10] if publication_id else "root"
    # The seq prefix makes the journal's name order IS its append order —
    # name-sort alone would order same-instant events alphabetically by
    # verb, a wrong fold for the §3.4 state machine (found by P35.54's
    # same-instant fixture). The seq counts the append-only journal's
    # objects; a create-if-absent collision (a racing writer) retries with
    # the next seq — under the registry lock there is exactly one writer.
    seq = len(store.list(EVENTS_PREFIX))
    stem = f"{now.strftime('%Y%m%dT%H%M%S')}-{verb}-{short}"
    doc = {
        "schema": EVENT_SCHEMA,
        "verb": verb,
        "publication_id": publication_id,
        "recorded_at": _iso(now),
        "utc_instant": _iso(now),
        **payload,
    }
    # Two same-instant same-verb events are legal (a verb may run twice);
    # the if-absent write gets the next counter — always two digits and
    # always present, so `stem-00` sorts before `stem-01` and the journal's
    # name order IS the append order (`stem-1` would sort BEFORE `stem.json`,
    # '-' < '.', breaking the fold).
    for n in range(1000):
        name = f"{EVENTS_PREFIX}{seq + n:06d}-{stem}.json"
        try:
            store.insert(name, _canonical(doc), content_type="application/json")
            return name
        except _gcs.GcsPreconditionFailed:
            continue
    raise PipelineError("journal-full", f"no free event name under {stem}")


_EVENT_SEQ_NAME = re.compile(r"^events/(\d{6})-")


def list_events(store: Store, publication_id: str | None = None) -> list[dict[str, Any]]:
    """Every event in journal order — the seq-prefixed names (P35.54) sort
    by their append counter; the older timestamp-led names (P35.53, all
    appended before the scheme existed) keep name order and sort first."""

    def _key(name: str) -> tuple[int, str]:
        m = _EVENT_SEQ_NAME.match(name)
        return (1, m.group(1)) if m else (0, name)

    events: list[dict[str, Any]] = []
    for name in sorted(store.list(EVENTS_PREFIX), key=_key):
        body = store.read(name)
        if body is None:
            continue
        try:
            doc = json.loads(body)
        except ValueError:
            doc = {"schema": "unreadable", "object": name}
        doc["object"] = name
        if publication_id and doc.get("publication_id") not in (publication_id, None):
            continue
        events.append(doc)
    return events


def fold_state(
    events: Iterable[dict[str, Any]], publication_id: str | None = None
) -> dict[str, Any]:
    """Fold the journal into the §3.4 state machine for one publication."""
    state = "none"
    history: list[str] = []
    for ev in events:
        verb = str(ev.get("verb") or "")
        if publication_id and ev.get("publication_id") != publication_id:
            continue
        history.append(verb)
        if verb in LIFECYCLE_KINDS:
            state = verb
        elif verb == "classified":
            state = "classified"
    return {"state": state, "history": history}


# --------------------------------------------------------------------------- #
# The verbs                                                                  #
# --------------------------------------------------------------------------- #

#: Rows that own the deferred verb bodies (the honest refusal text).
#: P35.55 (REL-08) landed rollback/clear-latest/withdraw + import-floor in
#: ``release_reversal.py`` — none remain deferred here.
VERB_OWNERS: dict[str, str] = {}


def _stage_plan(release_dir: Path, pub: str) -> list[tuple[str, Path]]:
    """``(object_name, local_path)`` for every byte under
    ``{r,v,s,releases}/<pub>/`` in ``release_dir``."""
    plan: list[tuple[str, Path]] = []
    for ns in STAGED_NAMESPACES:
        root = release_dir / ns / pub
        if not root.is_dir():
            continue
        for p in sorted(root.rglob("*")):
            if p.is_file():
                plan.append((f"staged/{ns}/{pub}/{p.relative_to(root)}", p))
    return plan


def _publication_id_of(release_dir: Path) -> str:
    """The publication id a built tree declares — the lone
    ``releases/<pub>/`` dir, verified against the descriptor."""
    pubs = (
        sorted(p.name for p in (release_dir / "releases").iterdir() if p.is_dir())
        if (release_dir / "releases").is_dir()
        else []
    )
    if len(pubs) != 1:
        raise PipelineError(
            "no-release",
            f"{release_dir} does not hold exactly one releases/<pub>/ tree "
            f"(found {pubs or 'none'}) — stage/verify name one built release",
        )
    pub = pubs[0]
    descriptor = release_dir / "releases" / pub / "descriptor.json"
    if descriptor.is_file():
        doc = json.loads(descriptor.read_text(encoding="utf-8"))
        from exports.release import descriptor_sha256 as _dsha

        if _dsha(doc) != pub.removeprefix("p-"):
            raise PipelineError(
                "bad-tree",
                f"{descriptor}'s digest does not equal the namespace name {pub}",
            )
    return pub


def verb_cut(
    store: Store,
    *,
    apply_: bool,
    as_of: str | None = None,
    replay: str | None = None,
    emergency: str | None = None,
    skip_host_clock: bool = False,
    break_lock: str | None = None,
    now: datetime | None = None,
    clock_fetcher: Any = None,
) -> dict[str, Any]:
    """``cut`` — the §3.3 guards + the cut event. The hosted legs (AR-2
    on-demand backup → ``sig-materialize`` → ``export.sh run`` with
    ``SIG_EXPORT_AS_OF=T0`` → fetch) are the job's chained script calls
    (``ops/gcp/restore-point.sh``, ``materialize.sh``, ``export.sh``) — this
    verb fixes and records T0 and proves the clock, never re-implements the
    steps."""
    t0 = now or _now()
    assert_not_frozen(t0, emergency=emergency)
    check_as_of_clock(as_of, t0, replay=replay)
    clock = {"skipped": True} if skip_host_clock else host_clock_report(t0, fetcher=clock_fetcher)
    plan = [
        "ops/gcp/restore-point.sh --apply sqlpoint   # AR-2 restore point",
        "ops/gcp/materialize.sh run                  # derived tables",
        f"SIG_EXPORT_AS_OF={_iso(t0)} ops/gcp/export.sh run --wait  # the cut export",
        "ops/gcp/export.sh fetch                    # export → the job's disk",
    ]
    result: dict[str, Any] = {
        "verb": "cut",
        "t0": _iso(t0),
        "as_of": as_of,
        "clock": clock,
        "plan": plan,
        "applied": False,
    }
    if not apply_:
        result["dry_run"] = True
        return result
    with acquire_lock(store, "cut", break_lock=break_lock, now=t0):
        name = emit_event(
            store,
            "cut",
            None,
            {
                "outcome": "recorded",
                "t0": _iso(t0),
                "as_of": as_of,
                "replay": replay,
                "emergency": emergency,
                "host_clock": clock,
                "legs": [p.split("#")[0].strip() for p in plan],
            },
            now=t0,
        )
        result["applied"] = True
        result["event"] = name
    return result


def _allocate_label(store: Store, as_of: str, *, environment: str | None) -> str:
    """Allocate ``sig-YYYY-MM-DD.N`` under the already-held registry lock.

    The allocator is ``release_identity.allocate_label`` over a *mirror* of
    the registry's label-bearing files — for a dir store the mirror is the
    registry itself; for a bucket the mirror is a scratch dir the labels
    document is written back from under a metageneration-matched replace.
    """
    from exports.release_identity import allocate_label

    if isinstance(store, LocalDirStore):
        return allocate_label(store.root / "registry", as_of, environment=environment)
    with tempfile.TemporaryDirectory(prefix="sig-labels-") as td:
        mirror = Path(td)
        for name in ("labels.json", "catalog.json"):
            body = store.read(f"registry/{name}")
            if body is not None:
                (mirror / name).write_bytes(body)
        label = allocate_label(mirror, as_of, environment=environment)
        new_doc = (mirror / "labels.json").read_bytes()
        meta = store.stat(LABELS_OBJECT)
        if meta is None:
            store.insert(LABELS_OBJECT, new_doc, content_type="application/json")
        else:
            store.replace(
                LABELS_OBJECT,
                new_doc,
                generation=int(meta["generation"]),
                content_type="application/json",
            )
        return label


def verb_build(
    store: Store,
    *,
    apply_: bool,
    export_dir: str | Path,
    work_dir: str | Path,
    environment: str | None = None,
    label: str | None = None,
    boundaries_root: str | None = None,
    descriptor_version: int = 2,
    renderer_revision: str | None = None,
    break_lock: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """``build`` — wrap ``exports.release.build_release`` (v2 descriptor by
    default — the only promotable shape; v1 stays selectable for parity /
    replay) + allocate the human label under the registry lock. The built
    tree stays local (``work_dir``); nothing is staged by build."""
    from exports.release import build_release

    export_dir = Path(export_dir)
    work_dir = Path(work_dir)
    if not export_dir.is_dir():
        raise PipelineError("bad-input", f"--export-dir {export_dir} does not exist")
    result: dict[str, Any] = {
        "verb": "build",
        "export_dir": str(export_dir),
        "work_dir": str(work_dir),
        "applied": False,
    }
    if not apply_:
        result["dry_run"] = True
        result["plan"] = [
            f"allocate label under {store.describe()}/registry (lock)",
            f"exports.release.build_release({export_dir} → {work_dir})",
            "journal `built` event",
        ]
        return result
    now = now or _now()
    with acquire_lock(store, "build", break_lock=break_lock, now=now) as lock:
        manifest = json.loads((export_dir / "manifest.json").read_bytes())
        as_of = str(manifest.get("as_of_world") or manifest.get("as_of") or _iso(now))
        label = label or _allocate_label(store, as_of, environment=environment)
        build = build_release(
            export_dir,
            work_dir,
            renderer_revision=renderer_revision,  # v1-only input; v2 binds code.commit itself
            descriptor_version=descriptor_version,
            labels_registry=None,
            label=label,
            environment=environment,
            boundaries_root=boundaries_root,
        )
        lock.refresh()
        name = emit_event(
            store,
            "built",
            build.publication_id,
            {
                "outcome": "recorded",
                "label": label,
                "descriptor_sha256": build.publication_id.removeprefix("p-"),
                "environment": environment,
                "export_manifest_sha256": hashlib.sha256(
                    (export_dir / "manifest.json").read_bytes()
                ).hexdigest(),
            },
            now=now,
        )
        result.update(
            applied=True,
            publication_id=build.publication_id,
            label=label,
            event=name,
        )
    return result


def verb_stage(
    store: Store,
    *,
    apply_: bool,
    work_dir: str | Path,
    publication_id: str | None = None,
    break_lock: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """``stage`` — upload ``staged/{r,v,s,releases}/<pub>/`` create-if-absent.

    Resume contract: an existing object with identical bytes is skipped;
    a same-named object with different bytes is a name-collision refusal —
    nothing staged is overwritten (SIG-REL-005)."""
    work_dir = Path(work_dir)
    pub = publication_id or _publication_id_of(work_dir)
    plan = _stage_plan(work_dir, pub)
    result: dict[str, Any] = {
        "verb": "stage",
        "publication_id": pub,
        "objects": len(plan),
        "applied": False,
    }
    if not plan:
        raise PipelineError("empty-plan", f"nothing under {work_dir}/{{r,v,s,releases}}/{pub}/")
    if not apply_:
        result["dry_run"] = True
        result["plan"] = [f"insert {len(plan)} objects under staged/*/{pub}/ (if-absent)"]
        return result
    now = now or _now()
    staged = 0
    skipped = 0
    nbytes = 0
    with acquire_lock(store, "stage", break_lock=break_lock, now=now) as lock:
        for name, path in plan:
            body = path.read_bytes()
            try:
                store.insert(name, body, content_type=_media_type(name))
                staged += 1
                nbytes += len(body)
            except _gcs.GcsPreconditionFailed as exc:
                meta = store.stat(name) or {}
                if meta.get("md5Hash") == _md5_b64(body):
                    skipped += 1  # identical bytes already there — a resume
                    continue
                raise NameCollision(name) from exc
            lock.refresh()
        event_name = emit_event(
            store,
            "staged",
            pub,
            {
                "outcome": "recorded",
                "objects_staged": staged,
                "objects_resumed": skipped,
                "bytes": nbytes,
                "namespaces": [ns for ns in STAGED_NAMESPACES if (work_dir / ns / pub).is_dir()],
            },
            now=now,
        )
    result.update(applied=True, staged=staged, resumed=skipped, bytes=nbytes, event=event_name)
    return result


def _git_root(cwd: Path) -> Path | None:
    """The worktree root ``cwd`` sits inside, or ``None`` when not a repo —
    V2's default ``--repo-root`` probe target (never a guessed fact)."""
    import subprocess

    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0 or not out.stdout.strip():
        return None
    return Path(out.stdout.strip())


def _declared_410s(store: Store) -> frozenset[str]:
    """The route set the current conf generation's ``withdrawn.conf`` denies
    — V5's "declared 410" allowance: a same-origin link may resolve to 410
    only when the barrier records the denial."""
    from . import release_conf as _rc

    gen = _rc.current_generation(store)
    if gen < 1:
        return frozenset()
    body = store.read(_rc._conf_name(gen, "withdrawn.conf"))
    if body is None:
        return frozenset()
    out: set[str] = set()
    for m in re.finditer(r"location\s*=\s*(\S+)\s*\{([^}]*)}", body.decode("utf-8", "replace")):
        if "410" in m.group(2):
            out.add(m.group(1))
    return frozenset(out)


def _verify_suite_contexts(
    store: Store,
    work_dir: Path,
    pub: str,
    *,
    mode: str,
    origins: tuple[str, ...],
    origin_headers: tuple[str, ...],
    tree_origin: bool,
    release_class: str | None,
    waivers: tuple[str, ...],
    repo_root: Path | None,
    pushed: bool | None,
    tree_clean: bool | None,
    axe_runner: Any,
    site_kwargs: dict[str, Any],
    now: datetime | None,
    api_origin: str | None = None,
    api_headers: tuple[str, ...] = (),
    api_fetcher: Any = None,
    covers: Any = None,
    quality_report: Any = None,
    cadence_path: Path | None = None,
) -> list[Any]:
    """Build the per-origin :class:`release_verify.VerifyContext` set.

    ``origins`` are the real HTTP surfaces — S takes the IAM-only staging
    origin (``origin_headers`` carry the identity-token header), P every
    public origin. ``tree_origin`` serves the built ``work_dir`` through
    the §4.2 mapping — a fixture posture the result rows record as
    ``origin_kind: "tree"``; the registry's latest conf generation
    supplies the promoted map, the ``/releases/`` index set, the
    withdrawal deny map + tombstone root (V10's 410 barrier), the served
    ``X-SIG-Conf-Gen`` header, and the declared-410 routes wherever they
    are readable. ``api_origin`` is V7's served-parity surface — S names
    sig-api-staging, P the live API; ``covers``/``quality_report`` are
    V9's boundary oracle and V15's ``sig.quality-report/1``."""
    from . import release_verify as rv

    shared = dict(
        store=store,
        declared_410=_declared_410s(store),
        release_class=release_class,
        waivers=tuple(waivers),
        repo_root=repo_root,
        pushed=pushed,
        tree_clean=tree_clean,
        axe_runner=axe_runner,
        now=now,
        covers=covers,
        quality_report=quality_report,
        cadence_path=cadence_path,
        **site_kwargs,
    )
    # V7's served-parity seam — one fetcher per ctx (S: sig-api-staging,
    # P: the live API). ``api_fetcher`` injects the fixture answer (the
    # composed/test seam); ``api_origin`` builds the real HTTP fetcher.
    # Neither → the V7 served legs record a skip, which blocks (the
    # honest absence, never an assumed pass).
    if api_fetcher is None and api_origin:
        api_headers_map = {}
        for h in api_headers:
            k, _, v = h.partition(":")
            api_headers_map[k.strip()] = v.strip()
        api_fetcher = rv.HttpFetcher(api_origin, headers=api_headers_map)
    shared["api_fetcher"] = api_fetcher
    # V14's baseline — the registry's current latest ≠ the candidate (S
    # mode); its staged tree is the local store's staged root when it is
    # one (a GCS store leaves the baseline to an explicit --baseline-dir
    # through site_kwargs, or records the skip).
    prev_body = store.read("registry/latest.json")
    if prev_body is not None:
        try:
            prev_pub = str(json.loads(prev_body).get("publication_id") or "")
        except ValueError:
            prev_pub = ""
        if prev_pub and prev_pub != pub:
            shared.setdefault("previous_pub", prev_pub)
            store_root = getattr(store, "root", None)
            if (
                store_root is not None
                and (Path(store_root) / "staged" / "releases" / prev_pub).is_dir()
            ):
                shared.setdefault("previous_dir", Path(store_root) / "staged")
    headers = {}
    for h in origin_headers:
        k, _, v = h.partition(":")
        headers[k.strip()] = v.strip()
    contexts: list[Any] = []
    for url in origins:
        contexts.append(
            rv.VerifyContext(
                mode=mode,
                work_dir=work_dir,
                pub=pub,
                fetcher=rv.HttpFetcher(url, headers=headers),
                origin=url,
                origin_kind="http",
                axe_url=url,
                **shared,
            )
        )
    if tree_origin:
        promoted: frozenset[str] | None = None
        staging = mode == "S"
        latest_pub = pub
        latest_label: str | None = None
        conf_overrides: dict[str, bytes] = {}
        withdrawn_body: bytes | None = None
        tombstones: dict[str, bytes] = {}
        tombstone_root: Path | None = None
        from . import release_conf as _rc

        gen = _rc.current_generation(store)
        if gen >= 1:
            map_body = store.read(_rc._conf_name(gen, "promoted.map"))
            if mode == "P":
                promoted = (
                    frozenset(_rc.parse_promoted_map(map_body.decode("utf-8", "replace")))
                    if map_body
                    else frozenset()
                )
            latest_body = store.read(_rc._conf_name(gen, "latest.json"))
            if latest_body is not None:
                latest = json.loads(latest_body)
                if mode == "P":
                    latest_pub = str(latest.get("publication_id") or pub)
                latest_label = str(latest.get("label") or "") or None
            for rel, route in (
                ("releases/index.html", "/releases/"),
                ("releases/catalog.json", "/releases/catalog.json"),
                ("latest.json", "/releases/latest.json"),
            ):
                body = store.read(_rc._conf_name(gen, rel))
                if body is not None:
                    conf_overrides[route] = body
                    if rel == "releases/index.html":
                        conf_overrides["/releases/index.html"] = body
            # V10's deny barrier — the served generation's withdrawn.conf
            # evaluates before try_files, exactly like nginx (P34.41). The
            # tombstone bodies resolve under the store's staged root for a
            # local store; a remote store supplies them as prefetched bytes.
            withdrawn_body = store.read(_rc._conf_name(gen, "withdrawn.conf"))
            store_root = getattr(store, "root", None)
            if store_root is not None:
                tombstone_root = Path(store_root) / "staged"
            elif withdrawn_body:
                for tomb_rel in rv._parse_deny_map(withdrawn_body).values():
                    body = store.read(f"staged/{tomb_rel.lstrip('/')}")
                    if body is not None:
                        tombstones[tomb_rel.lstrip("/")] = body
            # the DCAT series catalog lives at the staged root's
            # releases/ dir (nginx's `location /releases/` prefix maps it to
            # staged/releases/catalog.jsonld — activation-overlay, not a
            # <pub>/ namespace). The public deny gate still applies to that
            # prefix: a non-pub /releases/ path is promoted=0 → 404 in P mode,
            # served only under staging (SIG_STAGING=1 never gates, GT-9) —
            # the tree mirror injects the override on S legs only, matching
            # the real edge byte-for-byte (D-P35.56-1 records the public gap).
            if mode == "S":
                for name, route in (
                    ("staged/releases/catalog.jsonld", "/releases/catalog.jsonld"),
                ):
                    body = store.read(name)
                    if body is not None:
                        conf_overrides.setdefault(route, body)
        site = rv._site_release(work_dir, pub) or {}
        label = latest_label or str(site.get("label") or "")
        latest_header = f"{label} {latest_pub}" if label else None
        # the candidate's own stamp pair rides S-mode staging (the staging
        # revision serves latest=<candidate>); P-mode serves latest.json's
        contexts.append(
            rv.VerifyContext(
                mode=mode,
                work_dir=work_dir,
                pub=pub,
                fetcher=rv.TreeFetcher(
                    work_dir,
                    latest_pub,
                    promoted=promoted,
                    staging=staging,
                    release_header=(
                        latest_header
                        if mode == "P"
                        else (f"{site.get('label')} {pub}" if site.get("label") else None)
                    ),
                    conf_gen_header=str(gen) if gen >= 1 else None,
                    overrides=conf_overrides,
                    deny_conf=withdrawn_body,
                    tombstone_root=tombstone_root,
                    tombstones=tombstones or None,
                ),
                origin=f"tree:{work_dir}",
                origin_kind="tree",
                **shared,
            )
        )
    return contexts


def verb_verify(
    store: Store,
    *,
    apply_: bool,
    work_dir: str | Path,
    publication_id: str | None = None,
    mode: str | None = None,
    origins: tuple[str, ...] = (),
    origin_headers: tuple[str, ...] = (),
    tree_origin: bool = False,
    results_dir: str | Path | None = None,
    release_class: str | None = None,
    waivers: tuple[str, ...] = (),
    repo_root: str | Path | None = None,
    pushed: bool | None = None,
    tree_clean: bool | None = None,
    axe_runner: Any = ...,
    site_kwargs: dict[str, Any] | None = None,
    api_origin: str | None = None,
    api_headers: tuple[str, ...] = (),
    api_fetcher: Any = None,
    covers: Any = None,
    quality_report: Any = None,
    cadence_path: str | Path | None = None,
    break_lock: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """``verify`` — the bounded staged==built + integrity leg plus, when a
    ``mode`` is given, the G3 §5.5 verification suite (P35.56 suite A +
    P35.58 suite B): V1–V15 over the staging origin (``S``); the §5.5
    P-subset plus P1 over every public origin (``P``). Every check writes
    a JSON result row; any failure or skip blocks promotion — a
    ``--apply`` journals ``verified`` only when the bounded leg and every
    suite verdict pass (a Class-S readout may waive named non-V12 checks;
    the waiver lands in the event detail).

    ``api_origin`` names V7's served-parity surface (sig-api-staging for
    S, the live API for P); ``api_fetcher`` injects the fetcher directly
    (the fixture/composed seam — wins over ``api_origin``); ``covers`` is
    V9's boundary oracle ``(claim_key, lat, lon) -> bool``;
    ``quality_report`` is V15's ``sig.quality-report/1`` (dict or path).
    Unsupplied inputs land their legs as recorded skips — which block
    (SIG-ENG-042).

    ``mode=None`` keeps the pre-P35.56 bounded scope exactly — the scope
    string in the result/event says so."""
    from exports.release import validate_release

    from . import release_verify as rv

    work_dir = Path(work_dir)
    pub = publication_id or _publication_id_of(work_dir)
    report = validate_release(work_dir)
    integrity = next(work_dir.glob("releases/*/integrity_manifest.json"), None)
    artifacts = json.loads(integrity.read_bytes()).get("artifacts") or [] if integrity else []
    missing: list[str] = []
    mismatched: list[str] = []
    checked = 0
    for art in artifacts:
        name = f"staged/{art['path']}"
        meta = store.stat(name)
        if meta is None:
            missing.append(name)
            continue
        body = (work_dir / str(art["path"])).read_bytes()
        if meta.get("md5Hash") != _md5_b64(body):
            mismatched.append(name)
            continue
        checked += 1
    bounded_ok = report.state == "complete" and not missing and not mismatched
    result: dict[str, Any] = {
        "verb": "verify",
        "publication_id": pub,
        "validation_state": report.state,
        "artifacts_checked": checked,
        "missing": missing[:10],
        "mismatched": mismatched[:10],
        "applied": False,
    }

    suites: list[dict[str, Any]] = []
    if mode in ("S", "P"):
        contexts = _verify_suite_contexts(
            store,
            work_dir,
            pub,
            mode=mode,
            origins=origins,
            origin_headers=origin_headers,
            tree_origin=tree_origin,
            release_class=release_class,
            waivers=waivers,
            repo_root=Path(repo_root) if repo_root else None,
            pushed=pushed,
            tree_clean=tree_clean,
            axe_runner=axe_runner,
            site_kwargs=site_kwargs or {},
            now=now,
            api_origin=api_origin,
            api_headers=api_headers,
            api_fetcher=api_fetcher,
            covers=covers,
            quality_report=quality_report,
            cadence_path=Path(cadence_path) if cadence_path else None,
        )
        for ctx in contexts:
            suites.append(rv.run_suite(ctx))
        if not contexts:
            # fail-closed: no origin to verify over — every suite check is
            # an honest skip, and a skip blocks (SIG-ENG-042).
            suites.append(
                {
                    "schema": rv.RESULT_SCHEMA,
                    "mode": mode,
                    "publication_id": pub,
                    "origin": None,
                    "origin_kind": "none",
                    "checks": list(rv.CHECKS_S if mode == "S" else rv.CHECKS_P),
                    "results": [
                        rv._row(
                            cid,
                            mode,
                            "skip",
                            "no origin supplied — the check's HTTP surface legs "
                            "are unevaluable (pass --origin/--tree)",
                        )
                        for cid in (rv.CHECKS_S if mode == "S" else rv.CHECKS_P)
                    ],
                    "counts": {
                        "pass": 0,
                        "fail": 0,
                        "skip": len(rv.CHECKS_S if mode == "S" else rv.CHECKS_P),
                    },
                    "verdict": "blocked",
                    "promotion_blocked": True,
                    "waivers": [],
                    "waivers_ignored": [],
                    "uncovered": list(rv.CHECKS_S if mode == "S" else rv.CHECKS_P),
                }
            )
        out_dir = (
            Path(results_dir)
            if results_dir
            else work_dir.parent / f"{work_dir.name}.verify-results"
        )
        written: list[str] = []
        for suite in suites:
            written.extend(str(p) for p in rv.write_results(suite, out_dir))
        result["results_dir"] = str(out_dir)
        result["results_written"] = len(written)
        result["suites"] = suites
        result["verdict"] = (
            "verified"
            if bounded_ok and all(s["verdict"] in ("pass", "waived") for s in suites)
            else "failed"
        )
        result["scope"] = (
            f"staged==built + V1–V5/V11–V13 suite mode={mode} over {[s['origin'] for s in suites]}"
        )
    else:
        result["scope"] = (
            "staged-bytes==built-bytes + integrity re-validation "
            "(no --mode → the pre-P35.56 bounded scope; the V1–V14 suite "
            "needs --mode S|P)"
        )
        result["verdict"] = "verified" if bounded_ok else "failed"

    ok = result["verdict"] == "verified"
    if not apply_:
        result["dry_run"] = True
        return result
    now = now or _now()
    with acquire_lock(store, "verify", break_lock=break_lock, now=now):
        event_detail: dict[str, Any] = {
            "outcome": "recorded",
            "validation_state": report.state,
            "artifacts_checked": checked,
            "missing": missing,
            "mismatched": mismatched,
            "suite_scope": result["scope"],
        }
        if suites:
            event_detail["suite"] = [
                {
                    "mode": s["mode"],
                    "origin": s["origin"],
                    "origin_kind": s["origin_kind"],
                    "verdict": s["verdict"],
                    "counts": s["counts"],
                    "waivers": s["waivers"],
                    "uncovered": s["uncovered"],
                }
                for s in suites
            ]
        # A P-mode green is NOT the S-mode `verified` lifecycle event —
        # re-journalling `verified` after `promoted` would fold the §3.4
        # state machine backwards, so the post-promote green records
        # `verified-p` (a non-lifecycle kind the fold keeps as history).
        if not ok:
            kind = "failed"
        elif mode == "P":
            kind = "verified-p"
        else:
            kind = "verified"
        name = emit_event(store, kind, pub, event_detail, now=now)
        result.update(applied=True, event=name)
    if not ok:
        raise PipelineError(
            "verify-failed",
            f"{pub} fails verify — bounded ok={bounded_ok}, "
            f"suite verdicts={[(s['origin'], s['verdict']) for s in suites] or 'bounded'}",
            result,
        )
    return result


def verb_classify(
    store: Store,
    *,
    apply_: bool,
    publication_id: str,
    results: str | Path | None = None,
    go: str | None = None,
    notice_hook: Any = None,
    alert_ledger: Any = None,
    notifiers: Any = None,
    break_lock: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """``classify`` — P35.60's §7.3 classifier (SIG-REL-012): consume the
    emitted V14/V15 result docs (``--results`` — a verify-results directory
    or one suite file) plus the staged release's declared metadata and the
    journal; return ``class_r`` only when every R-column condition is
    proven, ``class_s`` on any named trigger or any check it cannot
    evaluate (RM-6 / SIG-ENG-042 — fail closed).

    ``--apply`` writes three append-only records under the lock: the
    ``sig.release-classification/1`` object under
    ``registry/classifications/``, the classified journal event (which
    ``release promote``'s ``journal_class`` reads), and — for Class S — the
    agent-drafted ``sig.release-readout/1`` pair under
    ``registry/readouts/`` plus the pending-readout notice on the landed
    alert/mail channel. ``--go <name>`` evaluates the standing-go record
    as evidence and, on a voiding trigger (ratchet regression · Part VIII
    screen change · new source — B-9), appends its ``.voided`` marker.
    ``notice_hook``/``alert_ledger``/``notifiers`` are test seams; the
    operator's destination lives in the channel's env configuration, never
    in a file."""
    from . import release_classify as rcls

    now = now or _now()
    suites: list[dict[str, Any]] = []
    bad: list[str] = []
    if results is None:
        bad.append(
            "--results not supplied — the P35.58 verify results are the "
            "classifier's only input; absent → every delta check unevaluable"
        )
    else:
        suites, bad = rcls.load_suite_documents(results)
    record = rcls.classify(
        store,
        publication_id,
        suites=suites,
        unreadable_inputs=bad,
        go=go,
        now=now,
    )
    result: dict[str, Any] = {
        "verb": "classify",
        "publication_id": publication_id,
        "class": record["class"],
        "failclosed": record["failclosed"],
        "triggers": record["triggers"],
        "unevaluable": record["unevaluable"],
        "applied": False,
    }
    if go:
        result["standing_go"] = record.get("standing_go")
    if not apply_:
        result["dry_run"] = True
        result["classification"] = record
        return result
    with acquire_lock(store, "classify", break_lock=break_lock, now=now):
        # the immutable classification record — create-if-absent
        cname = (
            f"{rcls.CLASSIFICATIONS_PREFIX}{publication_id}-{now.strftime('%Y%m%dT%H%M%S')}.json"
        )
        store.insert(cname, _canonical(record), content_type="application/json")
        result["classification_object"] = cname
        readout_names: dict[str, str] = {}
        if record["class"] == "class_s":
            readout_names = rcls.write_readout(store, record, now=now)
            result["readout"] = readout_names
        voided = (
            rcls.record_go_void(store, go, publication_id, record["triggers"], now=now)
            if go
            else None
        )
        if voided:
            result["go_voided"] = voided
        alert = rcls.notify_classification(
            record,
            readout_names or None,
            ledger=alert_ledger,
            notifiers=notifiers,
            notice_hook=notice_hook,
        )
        result["notice"] = {"kind": alert.kind, "recorded_at": alert.ts}
        name = emit_event(
            store,
            "classified",
            publication_id,
            {
                "outcome": "recorded",
                "class": record["class"],
                "failclosed": record["failclosed"],
                "triggers": record["triggers"],
                "unevaluable": record["unevaluable"],
                "classification_object": cname,
                "readout": readout_names or None,
                "go": go,
                "go_voided": voided,
                "notice": result["notice"],
            },
            now=now,
        )
        result.update(applied=True, event=name)
    return result


def verb_skeleton(
    verb: str,
    store: Store,
    *,
    apply_: bool,
    publication_id: str | None = None,
    break_lock: str | None = None,
    now: datetime | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """``rollback``/``clear-latest``/``withdraw`` — declared under the
    contract (lock, dry-run, apply, journal), refused naming the owner
    row. A refusal still journals — the attempt is audit-visible.
    ``promote`` landed at P35.54 (release_conf.verb_promote)."""
    owner = VERB_OWNERS[verb]
    result: dict[str, Any] = {
        "verb": verb,
        "publication_id": publication_id,
        "owner": owner,
        "refused": True,
        "applied": False,
    }
    if not apply_:
        result["dry_run"] = True
        result["plan"] = [f"{verb} <pub> — body lands at {owner}"]
        return result
    now = now or _now()
    with acquire_lock(store, verb, break_lock=break_lock, now=now):
        emit_event(
            store,
            verb,
            publication_id,
            {"outcome": "refused", "reason": f"behaviour lands at {owner}", **(extra or {})},
            now=now,
        )
    raise VerbDeferred(verb, owner)


def verb_status(
    store: Store,
    *,
    apply_: bool,
    publication_id: str | None = None,
    break_lock: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """``status`` — read the journal + catalog, print the candidate's §3.4
    state machine. Under ``--apply`` the observation itself is journaled
    (§5.1: each verb writes an event)."""
    events = list_events(store, publication_id)
    folded = fold_state(events, publication_id)
    catalog: dict[str, Any] = {}
    body = store.read("registry/catalog.json")
    if body is not None:
        try:
            catalog = json.loads(body)
        except ValueError:
            catalog = {"_unreadable": True}
    latest_body = store.read("registry/latest.json")
    latest = json.loads(latest_body) if latest_body else None
    lock_body = store.read(LOCK_OBJECT)
    result: dict[str, Any] = {
        "verb": "status",
        "publication_id": publication_id,
        "state": folded["state"],
        "history": folded["history"],
        "latest": latest,
        "catalog_publications": len(catalog.get("publications") or []),
        "events": len(events),
        "lock_held": lock_body is not None,
        "applied": False,
    }
    if not apply_:
        result["dry_run"] = True
        return result
    now = now or _now()
    with acquire_lock(store, "status", break_lock=break_lock, now=now):
        name = emit_event(
            store,
            "status",
            publication_id,
            {"outcome": "observed", "state": folded["state"]},
            now=now,
        )
        result.update(applied=True, event=name)
    return result


def _media_type(name: str) -> str:
    if name.endswith(".json"):
        return "application/json"
    if name.endswith(".html"):
        return "text/html"
    if name.endswith(".jsonl"):
        return "application/x-ndjson"
    if name.endswith(".ttl"):
        return "text/turtle"
    if name.endswith(".csv"):
        return "text/csv"
    return "application/octet-stream"


# --------------------------------------------------------------------------- #
# The dispatch table — cli.py calls run_verb                                   #
# --------------------------------------------------------------------------- #


def run_verb(args: Any) -> dict[str, Any]:
    """Dispatch one parsed ``sig-ops release <verb>`` namespace. Returns the
    verb's report dict; refusals raise :class:`PipelineError`."""
    registry = getattr(args, "registry", None) or os.environ.get("SIG_RELEASE_REGISTRY", "")
    store = open_store(registry)
    apply_ = bool(getattr(args, "apply", False))
    verb = args.release_command
    break_lock = getattr(args, "break_lock", None)
    if verb == "cut":
        return verb_cut(
            store,
            apply_=apply_,
            as_of=getattr(args, "as_of", None),
            replay=getattr(args, "replay", None),
            emergency=getattr(args, "emergency", None),
            skip_host_clock=bool(getattr(args, "skip_host_clock_check", False)),
            break_lock=break_lock,
        )
    if verb == "build":
        return verb_build(
            store,
            apply_=apply_,
            export_dir=args.export_dir,
            work_dir=args.work_dir,
            environment=getattr(args, "environment", None),
            label=getattr(args, "label", None),
            boundaries_root=getattr(args, "boundaries_root", None),
            descriptor_version=int(getattr(args, "schema_version", 2) or 2),
            renderer_revision=getattr(args, "renderer_revision", None),
            break_lock=break_lock,
        )
    if verb == "stage":
        return verb_stage(
            store,
            apply_=apply_,
            work_dir=args.work_dir,
            publication_id=getattr(args, "publication", None),
            break_lock=break_lock,
        )
    if verb == "verify":
        repo_facts: dict[str, Any] = {}
        raw_facts = getattr(args, "repo_facts", None)
        if raw_facts:
            try:
                repo_facts = json.loads(raw_facts)
            except ValueError as exc:
                raise PipelineError("bad-input", f"--repo-facts is not JSON: {exc}") from exc
        repo_root_arg: str | None = getattr(args, "repo_root", None)
        if getattr(args, "no_repo_probe", False):
            repo_root_arg = None
        elif repo_root_arg is None and not getattr(args, "tree", False):
            probe = _git_root(Path.cwd())
            repo_root_arg = str(probe) if probe is not None else None
        return verb_verify(
            store,
            apply_=apply_,
            work_dir=args.work_dir,
            publication_id=getattr(args, "publication", None),
            mode=getattr(args, "mode", None),
            origins=tuple(getattr(args, "origin", ()) or ()),
            origin_headers=tuple(getattr(args, "origin_header", ()) or ()),
            tree_origin=bool(getattr(args, "tree", False)),
            results_dir=getattr(args, "results_dir", None),
            release_class=getattr(args, "release_class", None),
            waivers=tuple(getattr(args, "waiver", ()) or ()),
            repo_root=repo_root_arg,
            pushed=repo_facts.get("pushed"),
            tree_clean=repo_facts.get("clean"),
            api_origin=getattr(args, "api_origin", None),
            api_headers=tuple(getattr(args, "api_header", ()) or ()),
            quality_report=getattr(args, "quality_report", None),
            cadence_path=getattr(args, "cadence", None),
            break_lock=break_lock,
        )
    if verb == "classify":
        return verb_classify(
            store,
            apply_=apply_,
            publication_id=args.publication,
            results=getattr(args, "results", None),
            go=getattr(args, "go", None),
            break_lock=break_lock,
        )
    if verb == "promote":
        # Lazy imports: release_conf/release_reversal import this module's
        # machinery.
        from . import release_conf, release_reversal

        gcloud = None
        if getattr(args, "execute_rolls", False):
            from . import job_roll

            gcloud = job_roll.gcloud_cli
        return release_conf.verb_promote(
            store,
            apply_=apply_,
            publication_id=args.publication,
            approval=getattr(args, "approval", None),
            label=getattr(args, "label", None),
            release_class=getattr(args, "release_class", None),
            api_image=getattr(args, "api_image", None),
            web_image=getattr(args, "web_image", None),
            min_instances=int(getattr(args, "min_instances", 1) or 1),
            project=getattr(args, "project", None),
            region=getattr(args, "region", None),
            execute_rolls=bool(getattr(args, "execute_rolls", False)),
            gcloud=gcloud,
            # D-P35.54-1 — the promote-time barrier re-derivation hook.
            derive_barrier=release_reversal.derive_withdrawal_barrier,
            break_lock=break_lock,
        )
    if verb in ("rollback", "clear-latest", "withdraw", "import-floor"):
        # Lazy import: release_reversal imports this module's machinery.
        from . import release_reversal

        rcloud = None
        if getattr(args, "execute_rolls", False):
            from . import job_roll

            rcloud = job_roll.gcloud_cli
        if verb == "rollback":
            return release_reversal.verb_rollback(
                store,
                apply_=apply_,
                to=args.to,
                reason=getattr(args, "reason", None),
                go=getattr(args, "go", None),
                api_image=getattr(args, "api_image", None),
                web_image=getattr(args, "web_image", None),
                min_instances=int(getattr(args, "min_instances", 1) or 1),
                project=getattr(args, "project", None),
                region=getattr(args, "region", None),
                execute_rolls=bool(getattr(args, "execute_rolls", False)),
                gcloud=rcloud,
                break_lock=break_lock,
            )
        if verb == "clear-latest":
            return release_reversal.verb_clear_latest(
                store,
                apply_=apply_,
                reason=getattr(args, "reason", None),
                go=getattr(args, "go", None),
                api_image=getattr(args, "api_image", None),
                web_image=getattr(args, "web_image", None),
                min_instances=int(getattr(args, "min_instances", 1) or 1),
                project=getattr(args, "project", None),
                region=getattr(args, "region", None),
                execute_rolls=bool(getattr(args, "execute_rolls", False)),
                gcloud=rcloud,
                break_lock=break_lock,
            )
        if verb == "withdraw":
            return release_reversal.verb_withdraw(
                store,
                apply_=apply_,
                disposition=getattr(args, "disposition", None),
                authority=getattr(args, "authority", None),
                purge_versions=bool(getattr(args, "purge_versions", False)),
                api_image=getattr(args, "api_image", None),
                web_image=getattr(args, "web_image", None),
                min_instances=int(getattr(args, "min_instances", 1) or 1),
                project=getattr(args, "project", None),
                region=getattr(args, "region", None),
                execute_rolls=bool(getattr(args, "execute_rolls", False)),
                gcloud=rcloud,
                break_lock=break_lock,
            )
        return release_reversal.verb_import_floor(
            store,
            apply_=apply_,
            source_dir=args.from_dir,
            label=getattr(args, "label", None),
            go=getattr(args, "go", None),
            break_lock=break_lock,
        )
    if verb == "cutover":
        from . import release_reversal

        return release_reversal.verb_cutover(
            store,
            apply_=apply_,
            label=args.label,
            web_image=getattr(args, "web_image", None),
            min_instances=int(getattr(args, "min_instances", 1) or 1),
            go=getattr(args, "go", None),
            withdrawals=getattr(args, "withdrawals", None),
            service=getattr(args, "service", "sig-web"),
            release_bucket=getattr(args, "release_bucket", None),
            mount_path=getattr(args, "mount_path", "/mnt/rel"),
            project=getattr(args, "project", None),
            region=getattr(args, "region", None),
            break_lock=break_lock,
        )
    if verb in VERB_OWNERS:
        return verb_skeleton(
            verb,
            store,
            apply_=apply_,
            publication_id=getattr(args, "publication", None),
            break_lock=break_lock,
        )
    if verb == "status":
        return verb_status(
            store,
            apply_=apply_,
            publication_id=getattr(args, "publication", None),
            break_lock=break_lock,
        )
    raise PipelineError("no-verb", f"unknown release verb {verb!r}")


__all__ = [
    "EVENT_SCHEMA",
    "EVENTS_PREFIX",
    "GcsStore",
    "LIFECYCLE_KINDS",
    "LocalDirStore",
    "Lock",
    "LockHeld",
    "NameCollision",
    "NAMESPACE_LAYOUT",
    "PipelineError",
    "REGISTRY_STATE_FILES",
    "STAGED_NAMESPACES",
    "StaleGeneration",
    "Store",
    "VERB_OWNERS",
    "VerbDeferred",
    "acquire_lock",
    "emit_event",
    "fold_state",
    "list_events",
    "open_store",
    "registry_state_digest",
    "run_verb",
    "verb_build",
    "verb_classify",
    "verb_cut",
    "verb_stage",
    "verb_status",
    "verb_verify",
]
