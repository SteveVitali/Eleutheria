# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The eight-stage connector interface (§21.1, SIG-INGEST-001/002/003).

Every source adapter implements the same eight stages:

``discover → fetch → capture → parse → extract → normalize → link → load``

The stages are **separately addressable** and **separately retryable**, and each
persists a **content-addressed** artifact, so any downstream stage can be re-run
without re-contacting the source (SIG-INGEST-001). ``fetch()`` is the **only**
stage permitted network egress (SIG-INGEST-002); every stage from ``capture()``
onward is a pure function of stored artifacts, which is what makes the
network-isolated replay of :mod:`connectors.replay` possible. Stages are
idempotent: re-running a stage over identical inputs yields an identical artifact
digest modulo generated ids and timestamps (SIG-INGEST-003).

This module owns the stage contract itself: the :class:`Stage` vocabulary and its
egress rules, the content-addressed :class:`StageArtifact` and the stores that
hold artifacts/captures/claims, the :class:`RunContext` threaded through a run,
and the :class:`Connector` base class every adapter subclasses. It writes **no
source-specific connector** — OSM and Atlas are P04.2/P04.3.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from evidence.digest import multihash
from evidence.ingest_run import IngestRun

from .registry import SourceRecord


class Stage(StrEnum):
    """The eight pipeline stages, in canonical order (§21.1, SIG-INGEST-001)."""

    DISCOVER = "discover"
    FETCH = "fetch"
    CAPTURE = "capture"
    PARSE = "parse"
    EXTRACT = "extract"
    NORMALIZE = "normalize"
    LINK = "link"
    LOAD = "load"


#: The stages in execution order.
STAGE_ORDER: tuple[Stage, ...] = (
    Stage.DISCOVER,
    Stage.FETCH,
    Stage.CAPTURE,
    Stage.PARSE,
    Stage.EXTRACT,
    Stage.NORMALIZE,
    Stage.LINK,
    Stage.LOAD,
)

#: ``fetch()`` is the only stage that obtains content bytes over the network
#: (SIG-INGEST-002). All egress flows through the shared politeness layer
#: (:mod:`connectors.net`), which is handed only to this stage.
EGRESS_STAGE: Stage = Stage.FETCH

#: Every stage from ``capture()`` onward is a pure function of stored artifacts
#: (SIG-INGEST-002); the pipeline runs these under network isolation so an
#: accidental egress fails the run rather than silently succeeding.
POST_CAPTURE_STAGES: tuple[Stage, ...] = (
    Stage.PARSE,
    Stage.EXTRACT,
    Stage.NORMALIZE,
    Stage.LINK,
    Stage.LOAD,
)


def is_post_capture(stage: Stage) -> bool:
    """Whether ``stage`` runs after ``capture()`` and must be a pure function."""
    return STAGE_ORDER.index(stage) > STAGE_ORDER.index(Stage.CAPTURE)


def may_egress(stage: Stage) -> bool:
    """Whether ``stage`` is permitted network egress (only ``fetch()``)."""
    return stage is EGRESS_STAGE


# --- content addressing -------------------------------------------------------


def _jsonable(obj: Any) -> Any:
    """Render ``obj`` as a JSON-canonicalisable structure for content addressing."""
    if hasattr(obj, "canonical"):
        return obj.canonical()
    if isinstance(obj, Mapping):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(x) for x in obj]
    return obj


def content_digest(payload: Any) -> str:
    """Content-address a stage payload as a base32 multihash (SIG-INGEST-001).

    The payload is rendered to canonical JSON (sorted keys) and hashed with the
    evidence store's interop digest, so re-running a stage over identical inputs
    produces an identical digest (SIG-INGEST-003).
    """
    data = json.dumps(_jsonable(payload), sort_keys=True, ensure_ascii=False, default=str)
    return multihash(data.encode("utf-8"))


@dataclass(frozen=True)
class StageArtifact:
    """A content-addressed artifact persisted by one stage (SIG-INGEST-001)."""

    stage: Stage
    digest: str
    payload: Any

    @classmethod
    def of(cls, stage: Stage, payload: Any) -> StageArtifact:
        return cls(stage=stage, digest=content_digest(payload), payload=payload)


# --- stage payloads (the two the framework itself needs to be concrete) -------


@dataclass(frozen=True)
class FetchResult:
    """The output of ``fetch()`` — the raw bytes obtained over the network."""

    url: str
    status: int
    body: bytes
    media_type: str = "application/octet-stream"
    retrieved_at: datetime | None = None
    headers: Mapping[str, str] = field(default_factory=dict)

    def canonical(self) -> dict[str, Any]:
        # Address the fetch by a hash of its body plus the request envelope, so two
        # fetches of identical bytes address identically (SIG-INGEST-003). Response
        # headers are deliberately excluded: values like Date / Server vary between
        # otherwise-identical fetches and would break idempotency. Headers remain on
        # the object for connectors that need them (e.g. challenge detection).
        return {
            "url": self.url,
            "status": self.status,
            "media_type": self.media_type,
            "body_digest": multihash(self.body),
        }


@dataclass(frozen=True)
class CaptureRef:
    """A reference to an archived, content-addressed capture (§17, SIG-INGEST-001).

    The post-capture stages are pure functions of this reference: they read the
    bytes back from the capture store by ``digest`` and never touch the network.
    """

    digest: str
    media_type: str
    source_uri: str
    byte_size: int
    retrieved_at: datetime | None = None

    def canonical(self) -> dict[str, Any]:
        # ``retrieved_at`` is retrieval metadata, deliberately excluded from the
        # content address: a capture is addressed by its bytes, so re-capturing
        # identical content at a later time addresses identically (SIG-INGEST-003).
        return {
            "digest": self.digest,
            "media_type": self.media_type,
            "source_uri": self.source_uri,
            "byte_size": self.byte_size,
        }


# --- stores (artifacts, captures, claims) -------------------------------------


@runtime_checkable
class CaptureStore(Protocol):
    """A content-addressed archive of capture bytes (§17).

    The framework depends only on this narrow contract; :class:`InMemoryCaptureStore`
    backs the tests and replay harness, and a later ticket adapts the real OCFL
    :class:`evidence.store.EvidenceStore` to it. ``put`` returns a
    :class:`CaptureRef` whose digest is stable for identical bytes.
    """

    def put(
        self,
        data: bytes,
        *,
        media_type: str,
        source_uri: str,
        retrieved_at: datetime | None = ...,
    ) -> CaptureRef: ...

    def get(self, digest: str) -> bytes: ...

    def has(self, digest: str) -> bool: ...


class InMemoryCaptureStore:
    """A content-addressed capture store held in memory (tests + replay)."""

    def __init__(self) -> None:
        self._blobs: dict[str, bytes] = {}

    def put(
        self,
        data: bytes,
        *,
        media_type: str,
        source_uri: str,
        retrieved_at: datetime | None = None,
    ) -> CaptureRef:
        digest = multihash(data)
        self._blobs[digest] = data
        return CaptureRef(
            digest=digest,
            media_type=media_type,
            source_uri=source_uri,
            byte_size=len(data),
            retrieved_at=retrieved_at,
        )

    def get(self, digest: str) -> bytes:
        return self._blobs[digest]

    def has(self, digest: str) -> bool:
        return digest in self._blobs


class ArtifactStore:
    """Holds every stage's content-addressed artifact (SIG-INGEST-001).

    Keying artifacts by ``(stage, digest)`` is what makes stages separately
    addressable and retryable: a downstream stage re-runs from the stored
    upstream artifact without re-contacting the source.
    """

    def __init__(self) -> None:
        self._by_key: dict[tuple[Stage, str], StageArtifact] = {}
        self._latest: dict[Stage, StageArtifact] = {}

    def put(self, artifact: StageArtifact) -> StageArtifact:
        self._by_key[(artifact.stage, artifact.digest)] = artifact
        self._latest[artifact.stage] = artifact
        return artifact

    def get(self, stage: Stage, digest: str) -> StageArtifact:
        return self._by_key[(stage, digest)]

    def latest(self, stage: Stage) -> StageArtifact | None:
        return self._latest.get(stage)


@runtime_checkable
class ClaimSink(Protocol):
    """Where ``load()`` asserts claims into L1 (§16).

    The pipeline calls this **only** on a live run — never during replay or in
    shadow mode (SIG-INGEST-019), where claims are produced and diffed but not
    asserted.
    """

    def assert_claims(self, claims: Sequence[Mapping[str, Any]]) -> None: ...


class InMemoryClaimSink:
    """A claim sink that records asserted claims in memory (tests)."""

    def __init__(self) -> None:
        self.claims: list[Mapping[str, Any]] = []

    def assert_claims(self, claims: Sequence[Mapping[str, Any]]) -> None:
        self.claims.extend(claims)


@runtime_checkable
class Fetcher(Protocol):
    """The shared politeness layer a connector fetches through (SIG-INGEST-011).

    Connectors hold no HTTP client of their own; they are handed a fetcher on the
    :class:`RunContext` and it is the single seam through which any egress passes.
    :class:`connectors.net.PoliteFetcher` is the implementation. Optional
    ``headers`` carry a per-request credential (e.g. a Bearer JWT) through the
    shared seam for an authenticated source (§23.5); most connectors omit them.
    """

    def fetch(self, url: str, *, headers: Mapping[str, str] | None = None) -> FetchResult: ...


# --- run context --------------------------------------------------------------


@dataclass
class RunContext:
    """Everything one connector run threads through its stages.

    ``fetcher`` is present only for the egress stage; the post-capture stages
    receive ``captures`` (to read archived bytes) but never the fetcher.
    ``replay`` / ``shadow`` suppress claim assertion (SIG-INGEST-018/019).
    """

    source: SourceRecord
    run: IngestRun
    fetcher: Fetcher | None = None
    captures: CaptureStore = field(default_factory=InMemoryCaptureStore)
    artifacts: ArtifactStore = field(default_factory=ArtifactStore)
    claim_sink: ClaimSink | None = None
    resolver: Any = None
    parameters: Mapping[str, Any] = field(default_factory=dict)
    replay: bool = False
    shadow: bool = False

    @property
    def asserts_claims(self) -> bool:
        """Live runs assert; replay and shadow runs never do (SIG-INGEST-018/019)."""
        return not (self.replay or self.shadow)


# --- the connector contract ---------------------------------------------------


class Connector(ABC):
    """The eight-stage interface every source adapter implements (SIG-INGEST-001).

    Subclasses set :attr:`name` / :attr:`version` and implement the acquisition and
    interpretation stages. The three stages with a stable framework meaning —
    :meth:`capture`, :meth:`link`, :meth:`load` — carry defaults here; the rest are
    source-specific and abstract. Every stage takes the previous stage's payload
    and returns the next, and the driver (:mod:`connectors.pipeline`) content-
    addresses and persists each output.
    """

    #: Connector identity; stamped into lineage and the UA (SIG-INGEST-011/015).
    name: str = "connector"
    version: str = "0"

    # -- acquisition (source-specific) --
    @abstractmethod
    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        """Enumerate what exists at the source now — identifiers, not content."""

    @abstractmethod
    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        """Obtain bytes for one target. The ONLY stage permitted egress."""

    # -- capture (stable framework meaning) --
    def capture(self, ctx: RunContext, fetched: FetchResult) -> CaptureRef:
        """Store the fetched bytes immutably and content-addressed (§17)."""
        return ctx.captures.put(
            fetched.body,
            media_type=fetched.media_type,
            source_uri=fetched.url,
            retrieved_at=fetched.retrieved_at,
        )

    # -- interpretation (source-specific, pure functions of the capture) --
    @abstractmethod
    def parse(self, ctx: RunContext, capture: CaptureRef) -> Any:
        """Structure from the captured bytes. Pure: reads the store, not the net."""

    @abstractmethod
    def extract(self, ctx: RunContext, parsed: Any) -> list[Mapping[str, Any]]:
        """Raw claims with locators, preserving raw values (P2)."""

    @abstractmethod
    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        """Typed values beside the preserved raw values (P2)."""

    # -- link + load (stable framework meaning; link() calls P03.2) --
    def link(self, ctx: RunContext, normalized: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Resolve entities against the identity layer (P03.2).

        The default is identity — a connector overrides this to call
        :func:`resolution.cascade.resolve` against ``ctx.resolver``. This ticket
        does **not** implement entity resolution (that is P03.2/P05.1); it only
        owns the seam where ``link()`` calls it.
        """
        return normalized

    def load(self, ctx: RunContext, linked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Produce the claim rows for L1. The driver asserts them (live only)."""
        return list(linked)


# --- connector registry (so every stage is runnable as a plain CLI) ----------

_REGISTRY: dict[str, type[Connector]] = {}


def register(connector_cls: type[Connector]) -> type[Connector]:
    """Register a connector class under its :attr:`name` (SIG-INGEST-021)."""
    name = connector_cls.name
    if name in _REGISTRY and _REGISTRY[name] is not connector_cls:
        raise ValueError(f"connector name already registered: {name!r}")
    _REGISTRY[name] = connector_cls
    return connector_cls


def registered_connectors() -> dict[str, type[Connector]]:
    """Every registered connector, keyed by name (empty until P04.2)."""
    return dict(_REGISTRY)


def get_connector(name: str) -> type[Connector]:
    """Return a registered connector class by name, or raise :class:`KeyError`."""
    return _REGISTRY[name]


def stage_names() -> list[str]:
    """The eight stage names in order (for the CLI listing)."""
    return [s.value for s in STAGE_ORDER]


__all__ = [
    "ArtifactStore",
    "CaptureRef",
    "CaptureStore",
    "ClaimSink",
    "Connector",
    "EGRESS_STAGE",
    "FetchResult",
    "Fetcher",
    "InMemoryCaptureStore",
    "InMemoryClaimSink",
    "POST_CAPTURE_STAGES",
    "RunContext",
    "STAGE_ORDER",
    "Stage",
    "StageArtifact",
    "content_digest",
    "get_connector",
    "is_post_capture",
    "may_egress",
    "register",
    "registered_connectors",
    "stage_names",
]
