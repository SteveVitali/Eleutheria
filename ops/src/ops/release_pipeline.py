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
row, and never pretend to do work they do not. ``classify`` additionally
answers Class S — RM-6: a classifier that cannot decide says Class S.
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
VERB_OWNERS: dict[str, str] = {
    "rollback": "P35.55 (REL-08 — rollback/withdrawal bodies)",
    "clear-latest": "P35.55 (REL-08)",
    "withdraw": "P35.55 (REL-08)",
}


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


def verb_verify(
    store: Store,
    *,
    apply_: bool,
    work_dir: str | Path,
    publication_id: str | None = None,
    break_lock: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """``verify`` — this row's bounded subset: the built tree re-validates
    (``exports.release.validate_release``) AND every manifest artifact is
    staged with byte-identical md5. The V1–V14 staging-surface suite lands
    at P35.56/P35.58 — the event records that scope honestly."""
    from exports.release import validate_release

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
    ok = report.state == "complete" and not missing and not mismatched
    result: dict[str, Any] = {
        "verb": "verify",
        "publication_id": pub,
        "validation_state": report.state,
        "artifacts_checked": checked,
        "missing": missing[:10],
        "mismatched": mismatched[:10],
        "scope": "staged-bytes==built-bytes + integrity re-validation; "
        "the V1–V14 staging-surface suite is P35.56/P35.58's",
        "applied": False,
    }
    if not apply_:
        result["dry_run"] = True
        result["verdict"] = "verified" if ok else "failed"
        return result
    now = now or _now()
    with acquire_lock(store, "verify", break_lock=break_lock, now=now):
        name = emit_event(
            store,
            "verified" if ok else "failed",
            pub,
            {
                "outcome": "recorded",
                "validation_state": report.state,
                "artifacts_checked": checked,
                "missing": missing,
                "mismatched": mismatched,
                "suite_scope": result["scope"],
            },
            now=now,
        )
        result.update(applied=True, event=name, verdict="verified" if ok else "failed")
    if not ok:
        raise PipelineError(
            "verify-failed",
            f"{pub} fails the bounded verify — {len(missing)} missing, "
            f"{len(mismatched)} mismatched, validation={report.state}",
            result,
        )
    return result


def verb_classify(
    store: Store,
    *,
    apply_: bool,
    publication_id: str,
    break_lock: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """``classify`` — the P35.60 classifier is not landed; RM-6 fails closed:
    a classifier that cannot decide says Class S."""
    result: dict[str, Any] = {
        "verb": "classify",
        "publication_id": publication_id,
        "class": "class_s",
        "failclosed": True,
        "owner": "P35.60 (REL-06 — the §7.3 classifier matrix + readout)",
        "applied": False,
    }
    if not apply_:
        result["dry_run"] = True
        return result
    now = now or _now()
    with acquire_lock(store, "classify", break_lock=break_lock, now=now):
        name = emit_event(
            store,
            "classified",
            publication_id,
            {
                "outcome": "recorded",
                "class": "class_s",
                "failclosed": True,
                "reason": "the §7.3 classifier lands at P35.60 — RM-6 fail-closed default",
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
        return verb_verify(
            store,
            apply_=apply_,
            work_dir=args.work_dir,
            publication_id=getattr(args, "publication", None),
            break_lock=break_lock,
        )
    if verb == "classify":
        return verb_classify(
            store,
            apply_=apply_,
            publication_id=args.publication,
            break_lock=break_lock,
        )
    if verb == "promote":
        # Lazy import: release_conf imports this module's machinery.
        from . import release_conf

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
