# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The zero-egress mirror leg of the publish path (P35.5, SIG-TRANSP-019).

The public release is served from a zero-egress object-store mirror (Cloudflare
R2, D-J3-4/A-3) so download egress cost cannot scale with traffic. The mirror
is a *public copy*, never the origin of record — GCS keeps that role.

This module is the leg's machinery:

* :func:`load_mirror_registry` / :func:`mirror_entry` read ``ops/mirrors.toml``
  (the committed mirror registry — an object-store row carries the provider,
  bucket, and public base URL).
* :class:`MirrorPushLeg` is the attachable publish step the ``publish-web``
  path takes via ``mirror`` — its :meth:`preflight` refuses **before any
  write** when the mirror row is disabled, the provider is metered-egress
  (``exports.distribution.assert_low_egress``, the SIG-EXPORT-008 check the
  ticket requires in the live publish path), the run would breach the push
  caps, or the joined egress accounting is already in alarm; :meth:`push`
  runs the non-listable-origin probe and then the content-hash-key upload.

The leg refuses rather than degrades: a mirror the registry did not enable, a
provider outside the $0/low-egress class, or an origin that would enumerate its
objects all stop the publish — never publish "half a mirror".
"""

from __future__ import annotations

import json
import tomllib
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .publish import PublishError

if TYPE_CHECKING:
    from exports.distribution import ObjectStore
    from exports.push import PushLimits, S3Client

    from .egress import EgressConfig, EgressReport

DEFAULT_MIRRORS_PATH = Path("ops") / "mirrors.toml"


class MirrorRefusal(PublishError):
    """The mirror leg refuses — the publish stops (fail-closed, SIG-TRANSP-019)."""


@dataclass(frozen=True)
class MirrorEntry:
    """One ``[[mirror]]`` row of ``ops/mirrors.toml`` (object-store shape)."""

    name: str
    kind: str
    enabled: bool
    provider: str
    bucket: str
    url: str
    role: str = ""
    status: str = ""


def load_mirror_registry(path: str | Path) -> tuple[MirrorEntry, ...]:
    """Parse the committed mirror registry into :class:`MirrorEntry` rows.

    A row without ``enabled`` defaults to ``false`` — a mirror is opt-in, never
    on by omission (fail-closed). A malformed file fails loud.
    """
    p = Path(path)
    if not p.is_file():
        raise MirrorRefusal(f"mirror registry absent: {p}")
    with p.open("rb") as fh:
        doc = tomllib.load(fh)
    rows: list[MirrorEntry] = []
    for raw in doc.get("mirror", []):
        rows.append(
            MirrorEntry(
                name=str(raw.get("name", "")),
                kind=str(raw.get("kind", "")),
                enabled=bool(raw.get("enabled", False)),
                provider=str(raw.get("provider", "")),
                bucket=str(raw.get("bucket", "")),
                url=str(raw.get("url", "")),
                role=str(raw.get("role", "")),
                status=str(raw.get("status", "")),
            )
        )
    return tuple(rows)


def mirror_entry(path: str | Path, name: str) -> MirrorEntry:
    """Resolve one named mirror row — an unknown name refuses."""
    rows = load_mirror_registry(path)
    for row in rows:
        if row.name == name:
            return row
    raise MirrorRefusal(
        f"mirror {name!r} is not in {path} (have: "
        + ", ".join(r.name for r in rows)
        + ") — refusing to push to an unregistered target"
    )


def http_get(url: str, timeout_s: float = 10.0) -> tuple[int, str]:
    """The live anonymous GET the non-listable probe wires (no credentials)."""
    req = urllib.request.Request(url, headers={"User-Agent": "sig-ops-mirror-probe/1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310
            return resp.status, resp.read(65_536).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read(65_536).decode("utf-8", "replace")
    except urllib.error.URLError as e:
        return 0, str(e)


@dataclass(frozen=True)
class MirrorPushOutcome:
    """The recorded result of a mirror leg (applied) — evidence, not prose."""

    mirror: str
    provider: str
    bucket: str
    base_url: str
    objects: int
    uploaded: int
    skipped: int
    bytes_uploaded: int
    non_listable: bool | None  # None when the probe was not run (no fetch wired)
    egress_level: str

    def as_json(self) -> dict[str, Any]:
        return {
            "mirror": self.mirror,
            "provider": self.provider,
            "bucket": self.bucket,
            "base_url": self.base_url,
            "objects": self.objects,
            "uploaded": self.uploaded,
            "skipped": self.skipped,
            "bytes_uploaded": self.bytes_uploaded,
            "non_listable": self.non_listable,
            "egress_level": self.egress_level,
        }

    def as_lines(self) -> list[str]:
        listing = (
            "non-listable origin CONFIRMED"
            if self.non_listable
            else "listing probe not run"
            if self.non_listable is None
            else "LISTING REFUSED"
        )
        return [
            f"mirror-push APPLIED: {self.mirror} ({self.provider}:{self.bucket})",
            f"  base url: {self.base_url}",
            f"  objects: {self.objects} ({self.uploaded} uploaded, "
            f"{self.skipped} already present — append-only no-op)",
            f"  bytes uploaded: {self.bytes_uploaded}",
            f"  origin: {listing}",
            f"  egress join: {self.egress_level}",
        ]


class MirrorPushLeg:
    """The attachable mirror step: ``preflight`` (refuses before any write) then
    ``push`` (probe the origin non-listable, then the content-hash-key upload).

    Injection points (all fakeable — the live leg wires the real ones):
    ``client`` the S3 client, ``fetch`` the anonymous-GET probe, ``now``/``sleep``
    the rate-guard clock, ``limits`` the push caps, ``egress_config`` +
    ``usage_gb``/``usage_usd`` the P34.5/§38.5 accounting join.
    """

    def __init__(
        self,
        *,
        mirrors_path: str | Path,
        name: str,
        export_dir: str | Path,
        client: S3Client | None = None,
        fetch: Callable[[str], tuple[int, str]] | None = None,
        limits: PushLimits | None = None,
        sleep: Callable[[float], None] | None = None,
        clock: Callable[[], float] | None = None,
        egress_config: EgressConfig | None = None,
        usage_gb: float | None = None,
        usage_usd: float | None = None,
    ) -> None:
        self.mirrors_path = Path(mirrors_path)
        self.name = name
        self.export_dir = Path(export_dir)
        self.client = client
        self.fetch = fetch
        self.limits = limits
        self.sleep = sleep
        self.clock = clock
        self.egress_config = egress_config
        self.usage_gb = usage_gb
        self.usage_usd = usage_usd
        self._entry: MirrorEntry | None = None
        self._egress_report: EgressReport | None = None

    def _resolve(self) -> MirrorEntry:
        """The mirror row, refusing disabled/unregistered/non-object-store rows."""
        if self._entry is not None:
            return self._entry
        entry = mirror_entry(self.mirrors_path, self.name)
        if entry.kind != "object-store":
            raise MirrorRefusal(
                f"mirror {entry.name!r} is kind {entry.kind!r} — the push leg only "
                "serves object-store rows"
            )
        if not entry.enabled:
            raise MirrorRefusal(
                f"mirror {entry.name!r} is enabled=false in {self.mirrors_path} — "
                "the row stays committed-disabled until the P35.5 live leg enables "
                "it after OP-09 (SIG-TRANSP-019); refusing to push to a disabled mirror"
            )
        if not entry.provider or not entry.bucket:
            raise MirrorRefusal(
                f"mirror {entry.name!r} lacks provider/bucket in {self.mirrors_path}"
            )
        self._entry = entry
        return entry

    def _egress_join(self) -> None:
        """The §38.5 accounting join: an egress report already in alarm refuses."""
        if self.egress_config is None:
            self._egress_report = None
            return
        from .egress import build_report

        report = build_report(self.egress_config, self.usage_gb, self.usage_usd)
        self._egress_report = report
        if report.level == "alarm":
            raise MirrorRefusal(
                f"egress accounting is in ALARM ({report.as_json()}) — the mirror "
                "leg refuses; the kill switch and budget review come first "
                "(SIG-TRANSP-019 / $50 ceiling)"
            )

    def _store(self) -> ObjectStore:
        from exports.distribution import ObjectStore, assert_low_egress

        entry = self._resolve()
        store = ObjectStore(provider=entry.provider, bucket=entry.bucket)
        try:
            assert_low_egress(store)
        except Exception as exc:  # exports.EgressError — one refusal type in ops
            raise MirrorRefusal(str(exc)) from exc
        return store

    def preflight(self) -> list[str]:
        """Everything the leg proves before any write: plan lines or a refusal."""
        from exports.push import PushLimits, check_push_limits

        store = self._store()
        manifest_path = self.export_dir / "manifest.json"
        if not manifest_path.is_file():
            raise MirrorRefusal(
                f"{manifest_path} is absent — the mirror leg pushes a built export "
                "dir (release tree with a manifest.json); refusing"
            )
        with manifest_path.open(encoding="utf-8") as fh:
            manifest = json.load(fh)
        limits = self.limits or PushLimits()
        check_push_limits(self.export_dir, manifest, limits)
        self._egress_join()
        artifacts = manifest.get("artifacts", [])
        return [
            f"mirror {self.name}: preflight OK — provider {store.provider} "
            f"(egress class {store.egress_class}), bucket {store.bucket}",
            f"  {len(artifacts)} artifact(s) under content-hash keys, caps within "
            f"limits (per-file ≤ {limits.max_file_bytes} B, run ≤ "
            f"{limits.max_run_objects} objects / {limits.max_run_bytes} B, "
            f"≤ {limits.max_requests_per_minute} req/min)",
        ]

    def push(self) -> MirrorPushOutcome:
        """Run the leg: non-listable probe first, then the content-hash upload."""
        from exports.push import (
            PushLimits,
            PushRefusal,
            assert_non_listable_origin,
            build_s3_client,
            push_export_dir,
        )

        self.preflight()
        entry = self._resolve()
        store = self._store()
        non_listable: bool | None = None
        try:
            if self.fetch is not None:
                assert_non_listable_origin(self.fetch, entry.url)
                non_listable = True
            client = self.client or build_s3_client(store)
            results = push_export_dir(
                str(self.export_dir),
                store,
                client,
                limits=self.limits or PushLimits(),
                sleep=self.sleep,
                clock=self.clock,
            )
        except PushRefusal as exc:
            # one refusal type in the ops layer — the CLI's refusal path
            raise MirrorRefusal(str(exc)) from exc
        report = self._egress_report
        return MirrorPushOutcome(
            mirror=entry.name,
            provider=store.provider,
            bucket=store.bucket,
            base_url=entry.url,
            objects=len(results),
            uploaded=sum(1 for r in results if not r.skipped),
            skipped=sum(1 for r in results if r.skipped),
            bytes_uploaded=sum(r.byte_size for r in results if not r.skipped),
            non_listable=non_listable,
            egress_level=report.level if report is not None else "unmeasured",
        )


__all__ = [
    "DEFAULT_MIRRORS_PATH",
    "MirrorEntry",
    "MirrorPushLeg",
    "MirrorPushOutcome",
    "MirrorRefusal",
    "http_get",
    "load_mirror_registry",
    "mirror_entry",
]
