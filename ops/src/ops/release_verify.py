# SPDX-License-Identifier: Apache-2.0
"""P35.56 (REL-04a, SIG-REL-007 ``Also:``) — verification suite A.

``sig-ops release verify`` runs V1–V5 and V11–V13 of the G3 §5.5 table
against a staged candidate, in the two modes the table fixes verbatim:

* **S** — the staging origin before promote (``sig-web-staging``;
  IAM-only upstream, an identity-token header here);
* **P** — every public origin after promote (the canonical LB host, the
  run.app URL, the bucket URL while it exists).

This module lands both modes' *code*; the invocations inside a promotion
are the release rows' legs — this ticket performs no hosted or public
leg. Locally the suite can be pointed at a built tree (``--tree-origin``)
so the same checks run over fixture bytes — the result rows record
``origin_kind: tree`` and never claim a staging or public run.

Every check writes a JSON result row — ``{check, mode, status, detail,
evidence, duration}`` with ``status ∈ {pass, fail, skip}``. **Any failure
or skip blocks promotion** (SIG-ENG-042 made mechanical): a check whose
pass criterion cannot be evaluated — a missing origin, an absent runner —
is ``skip``, never a silent pass. A waiver exists only under Class S and
is recorded in the readout (deliverable 10); V12's scrub is never
waivable (Part VIII: one secret hit aborts — no override flag).

The checks reuse the landed machinery rather than re-implementing it:
``exports.release.validate_release`` (V1's half), ``exports.release_identity``
(descriptor + §3.3 clock + promotion refusals — V2),
``ops.publish`` (the committed allow-list + content assertions — V3),
``policy.transparency.find_secrets`` (the J3 TX-01/P35.31 detector — V12),
and the ``sig.site-release/1`` stamp contract (V4/V13). V7's API parity is
``release_publish_verify.api_parity_check`` — owned by P35.57, never
duplicated here.
"""

from __future__ import annotations

import hashlib
import html as _html
import http.server
import json
import math
import re
import shutil
import socket
import subprocess
import threading
import time
import tomllib
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import unquote, urljoin

from exports import release_identity as RI

from . import publish as _publish

#: The suite's JSON result schema.
RESULT_SCHEMA = "sig.release-verify/1"

#: The G3 §5.5 mode→check map, verbatim. "S" runs the full suite A on the
#: staging origin before promote; "P" runs the marked subset on every
#: public origin after promote (V1 as a bounded sample, V5 as a sample).
CHECKS_S: tuple[str, ...] = ("V1", "V2", "V3", "V4", "V5", "V11", "V12", "V13")
CHECKS_P: tuple[str, ...] = ("V1", "V3", "V4", "V5", "V13")

#: V1's threshold: every integrity-manifest artifact under this size is
#: fetched and hashed; larger files (and record files, whatever their
#: size) enter the stratified sample.
SMALL_ARTIFACT_BYTES = 1 << 20  # 1 MiB — §5.5 V1 "under 1 MB"

#: The stratified 2 % sample rate over larger/record files (§5.5 V1) —
#: the monthly full-tree audit is a named later row (recorded in the run
#: ledger; the sample is this check's, never the audit's).
SAMPLE_RATE = 0.02

#: P-mode caps: V1 fetches a 200-artifact sample; V5 crawls a 200-route
#: sample (§5.5's "sample" column entries).
P_SAMPLE = 200

#: V11's axe WCAG tags — the same rule set the web e2e gate runs
#: (web/tests/e2e/a11y.spec.ts; SIG-UI-037).
AXE_WCAG_TAGS = ("wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa")
AXE_SERIOUS = ("serious", "critical")

#: The stamp's latest-view basis sentence, verbatim from
#: ``exports.release_pages`` — V13's "API is live" line (G3 §6.1).
LIVE_API_LINE = 'The public API also serves newer, unreleased records, labelled "live".'

#: Evaluation-status phrases that must never appear on a surface whose
#: descriptor declares less than ``certified`` (V13 — the same
#: forbidden-assertion classes ``release_publish_verify``'s disclosure
#: posture scans for).
CERTIFIED_CLAIMS = (
    '"pilot_complete": true',
    "final evaluation decision",
    "certified resolved",
    '"evaluation_status": "certified"',
)


#: §5.3 containment — a ``/s/<pub>/`` page's same-origin links may leave
#: the snapshot prefix only toward these roots (plus the declared
#: ``rel="latest-version"`` target).
def _containment_roots(pub: str) -> tuple[str, ...]:
    return (f"/s/{pub}/", f"/r/{pub}/", "/releases/")


class VerifyError(RuntimeError):
    """A fail-closed refusal inside the verify suite — never a pass."""


# --------------------------------------------------------------------------- #
# Result rows — deliverable 9's contract: {check, mode, pass|fail|skip,        #
# evidence, duration}                                                          #
# --------------------------------------------------------------------------- #


def _row(
    check: str,
    mode: str,
    status: str,
    detail: str,
    *,
    evidence: Any = None,
    duration: float = 0.0,
) -> dict[str, Any]:
    """One result row. ``status`` is ``pass``, ``fail`` or ``skip`` — a
    skip is a block, never a pass (SIG-ENG-042)."""
    if status not in ("pass", "fail", "skip"):
        raise VerifyError(f"result row for {check} carries status {status!r}")
    out: dict[str, Any] = {
        "check": check,
        "mode": mode,
        "status": status,
        "detail": detail,
        "duration": round(duration, 3),
    }
    if evidence is not None:
        out["evidence"] = evidence
    return out


def _aggregate(status_legs: list[str]) -> str:
    """Leg statuses → the check's status: any fail → fail; else any skip
    → skip; else pass."""
    if "fail" in status_legs:
        return "fail"
    if "skip" in status_legs:
        return "skip"
    return "pass"


# --------------------------------------------------------------------------- #
# Fetchers — the transport seam the checks read origins through                #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class FetchResult:
    """One GET's outcome: status, headers, body — the same triple an
    anonymous reader's HTTP layer would report."""

    status: int
    headers: dict[str, str]
    body: bytes


class Fetcher(Protocol):
    """One GET against the origin under verification."""

    def get(self, path: str) -> FetchResult: ...


class HttpFetcher:
    """Real HTTP GETs — the S-mode staging origin (identity token via
    ``headers``) or a P-mode public origin. Loopback is expected for the
    composed fixture origins; hosted origins are the promotion legs'."""

    def __init__(
        self, base_url: str, *, headers: dict[str, str] | None = None, timeout: float = 20.0
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.headers = dict(headers or {})
        self.timeout = timeout

    def get(self, path: str) -> FetchResult:
        url = f"{self.base_url}/{path.lstrip('/')}"
        req = urllib.request.Request(url, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
                return FetchResult(resp.status, dict(resp.headers), resp.read())
        except urllib.error.HTTPError as exc:
            return FetchResult(exc.code, dict(exc.headers), exc.read())


def _index_bytes(path: Path) -> bytes | None:
    """The served bytes a §4.2 ``try_files $uri $uri/ =404`` resolves:
    the literal file, else ``<route>/index.html``, else None."""
    if path.is_file():
        return path.read_bytes()
    if path.is_dir():
        idx = path / "index.html"
        if idx.is_file():
            return idx.read_bytes()
    return None


class TreeFetcher:
    """The fixture seam — answers GETs over a staged release *tree* with
    the §4.2 mapping the real nginx template renders:

    * ``/`` and every route outside the release namespaces resolve inside
      ``v/<latest-pub>/`` (the latest view is a root);
    * ``/r/<x>/``, ``/s/<x>/``, ``/releases/<x>/…`` resolve under the
      staged namespaces, gated by ``promoted`` exactly like the map
      (``default 0``) — ``staging=True`` never gates (GT-9);
    * ``/releases/``'s generated index set (``index.html``,
      ``catalog.json``, ``latest.json``) is served from the conf
      generation — the caller supplies those bytes through ``overrides``
      (absent → the routes fall through to the latest view, where the
      release-pipeline-owned paths are absent → 404);
    * ``X-SIG-Release``/``X-SIG-Conf-Gen`` ride every response — the env
      pair the §4.2 revision renders — supplied, never invented: a caller
      must pass them; the honest absence is an empty header, which the
      V4 check reads as the failure it is.

    Every row produced through this fetcher records
    ``origin_kind: "tree"`` — a fixture answer, never a hosted one.
    """

    def __init__(
        self,
        root: Path | str,
        latest_pub: str,
        *,
        promoted: frozenset[str] | None = None,
        staging: bool = False,
        release_header: str | None = None,
        conf_gen_header: str | None = None,
        overrides: dict[str, bytes] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.root = Path(root)
        self.latest_pub = latest_pub
        self.promoted = promoted
        self.staging = staging
        self.release_header = release_header
        self.conf_gen_header = conf_gen_header
        self.overrides = dict(overrides or {})
        self.extra_headers = dict(extra_headers or {})

    # -- the §4.2 route → file map -------------------------------------- #

    def _resolve(self, path: str) -> Path | None:
        path = "/" + path.lstrip("/")
        m = re.match(r"^/(r|s|releases)/(p-[0-9a-f]+)(/.*)?$", path)
        if m:
            ns, pub, rest = m.group(1), m.group(2), m.group(3) or "/"
            if not self.staging and self.promoted is not None and pub not in self.promoted:
                return None  # the promoted map's `default 0` — 404 by construction
            return self.root / ns / pub / rest.lstrip("/")
        # the latest view — the site root is v/<latest-pub>/
        return self.root / "v" / self.latest_pub / path.lstrip("/")

    def get(self, path: str) -> FetchResult:
        path = "/" + path.lstrip("/")
        norm = path.split("#", 1)[0].split("?", 1)[0]
        headers: dict[str, str] = dict(self.extra_headers)
        if self.release_header is not None:
            headers["X-SIG-Release"] = self.release_header
        if self.conf_gen_header is not None:
            headers["X-SIG-Conf-Gen"] = self.conf_gen_header
        if self.staging:
            headers["X-Robots-Tag"] = "noindex"
        body = self.overrides.get(norm)
        if body is None:
            target = self._resolve(norm)
            body = _index_bytes(target) if target is not None else None
        if body is None:
            return FetchResult(404, headers, b"")
        return FetchResult(200, headers, body)


class LocalOriginServer:
    """Serve a :class:`TreeFetcher` on a loopback port — the axe leg needs
    a real URL; this is the same bytes over real HTTP, never a stand-in
    byte set. ``X-SIG-Release`` is the fetcher's recorded fixture header."""

    def __init__(self, fetcher: Fetcher) -> None:
        self.fetcher = fetcher
        self._server: http.server.ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self.url = ""

    def __enter__(self) -> LocalOriginServer:
        fetcher = self.fetcher

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 - stdlib name
                res = fetcher.get(self.path)
                self.send_response(res.status)
                for k, v in res.headers.items():
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(res.body)))
                self.end_headers()
                self.wfile.write(res.body)

            def log_message(self, *_args: Any) -> None:
                return

        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = int(s.getsockname()[1])
        self._server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        self.url = f"http://127.0.0.1:{port}"
        return self

    def __exit__(self, *_exc: Any) -> None:
        if self._server is not None:
            self._server.shutdown()
        if self._thread is not None:
            self._thread.join(timeout=10)
        if self._server is not None:
            self._server.server_close()


# --------------------------------------------------------------------------- #
# The suite context — every input a check reads                                #
# --------------------------------------------------------------------------- #

#: ``Callable[[origin_url, paths], {path: [violation…]}] | None`` — the
#: axe runner seam. The default is the real playwright+axe subprocess
#: (:func:`playwright_axe`); ``None`` declares the runner unavailable,
#: which lands the axe leg as an honest ``skip`` (which blocks).
AxeRunner = Any  # Callable[[str, list[str]], dict[str, list[dict[str, Any]]] | None]


@dataclass
class VerifyContext:
    """Everything suite A reads. ``origin`` is the evidence label carried
    into every row (the URL or ``tree:<dir>``); ``origin_kind`` is
    ``http`` or ``tree`` — a tree run is a fixture answer, never a
    staging/public one."""

    mode: str  # "S" | "P"
    work_dir: Path
    pub: str
    fetcher: Fetcher
    origin: str
    origin_kind: str  # "http" | "tree"
    store: Any = None  # release_pipeline Store — V2 reads registry state
    declared_410: frozenset[str] = frozenset()  # withdrawn.conf route paths
    allowlist_path: Path | None = None
    disclosures_path: Path | None = None
    budgets_path: Path | None = None
    lhci_url_path: Path | None = None
    page_types: dict[str, str] | None = None  # injected route→type map (tests)
    axe_runner: AxeRunner = ...  # default playwright; None → skip leg
    axe_url: str | None = None  # served base URL the runner navigates
    repo_root: Path | None = None  # V2's git probes
    pushed: bool | None = None  # injected repo facts (fixtures)
    tree_clean: bool | None = None
    release_class: str | None = None  # "class_r" | "class_s"
    waivers: tuple[str, ...] = ()  # "V<n>=<readout-ref>" — Class S only
    now: datetime | None = None
    v1_sample: int | None = None  # P-mode artifact cap (default 200)
    v5_sample: int | None = None  # P-mode route cap (default 200)


# --------------------------------------------------------------------------- #
# Shared page/scan helpers                                                     #
# --------------------------------------------------------------------------- #

_HTML_SUFFIXES = (".html",)


def _html_files(*roots: Path) -> list[Path]:
    """Every emitted HTML page under the release namespaces — the crawl
    set V4/V5/V11/V13 share."""
    out: list[Path] = []
    for root in roots:
        if root.is_dir():
            out.extend(p for p in sorted(root.rglob("*")) if p.suffix in _HTML_SUFFIXES)
    return out


def _namespace_dirs(work_dir: Path, pub: str) -> dict[str, Path]:
    return {ns: work_dir / ns / pub for ns in ("r", "v", "s", "releases")}


class _TagCollector(HTMLParser):
    """Collect ``(tag, attrs)`` for every element that can carry a
    same-origin link or a resource reference — V5's crawl and V13's
    text-index share it."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict[str, str]]] = []
        self.data: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, {k: v or "" for k, v in attrs}))

    def handle_data(self, data: str) -> None:
        self.data.append(data)


_LINK_ATTRS = ("href", "src", "action", "formaction", "poster")


def _page_links(text: str) -> list[tuple[str, str, dict[str, str]]]:
    """``(tag, attr, attrs)`` per link-carrying attribute — the tag keeps
    its attr map so ``rel="latest-version"`` is visible (V5's declared
    latest-version exception needs the element, not just the href)."""
    parser = _TagCollector()
    try:
        parser.feed(text)
    except Exception:  # noqa: BLE001 - malformed markup is a V5 finding
        return []
    out: list[tuple[str, str, dict[str, str]]] = []
    for tag, attrs in parser.tags:
        for attr in _LINK_ATTRS:
            if attrs.get(attr):
                out.append((tag, attr, attrs))
    return out


def _served_route(file_path: Path, work_dir: Path, pub: str) -> str:
    """The site-root route a staged file answers at — the §4.2 layout:
    ``v/<pub>/x`` → ``/x``; ``r/``, ``s/``, ``releases/`` keep their
    prefixes."""
    rel = file_path.relative_to(work_dir).as_posix()
    parts = rel.split("/")
    if parts[0] == "v" and parts[1] == pub:
        route = "/" + "/".join(parts[2:])
    elif parts[0] in ("r", "s", "releases") and parts[1] == pub:
        route = "/" + rel
    else:
        route = "/" + rel
    if route.endswith("/index.html"):
        route = route[: -len("index.html")]
    return route


def _resolve_href(page_route: str, href: str) -> str | None:
    """Normalise one href to the absolute site route it resolves to, or
    ``None`` for non-same-origin targets (schemes, protocol-relative,
    fragments, queries)."""
    href = href.strip()
    if not href or href.startswith("#"):
        return None
    path = href.split("#", 1)[0].split("?", 1)[0]
    if not path:
        return None
    if path.startswith("//"):
        return None
    first = path.split("/", 1)[0]
    if ":" in first:
        return None
    resolved = urljoin(page_route, path) if not path.startswith("/") else path
    resolved = unquote(resolved)
    if not resolved.startswith("/"):
        resolved = "/" + resolved
    # collapse . and .. deterministically
    parts: list[str] = []
    for seg in resolved.split("/"):
        if seg == "..":
            if parts:
                parts.pop()
        elif seg and seg != ".":
            parts.append(seg)
    return "/" + "/".join(parts) + ("/" if resolved.endswith("/") else "")


def _text_of(page_html: str) -> str:
    """De-tagged, entity-decoded, whitespace-collapsed text — the
    disclosure rendering check compares *text*, not markup."""
    parser = _TagCollector()
    try:
        parser.feed(page_html)
    except Exception:  # noqa: BLE001
        pass
    return " ".join(_html.unescape(" ".join(parser.data)).split())


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _descriptor(work_dir: Path, pub: str) -> dict[str, Any]:
    path = work_dir / "releases" / pub / "descriptor.json"
    if not path.is_file():
        raise VerifyError(f"{path} absent — the staged tree carries no descriptor")
    return _load_json(path)


def _integrity_artifacts(work_dir: Path) -> list[dict[str, Any]]:
    manifests = list(work_dir.glob("releases/*/integrity_manifest.json"))
    if len(manifests) != 1:
        raise VerifyError(
            f"expected exactly one integrity manifest under {work_dir}/releases/, "
            f"found {len(manifests)}"
        )
    return list((_load_json(manifests[0]).get("artifacts")) or [])


def _site_release(work_dir: Path, pub: str) -> dict[str, Any] | None:
    path = work_dir / "releases" / pub / "release.json"
    if path.is_file():
        return _load_json(path)
    root = work_dir / "release.json"
    return _load_json(root) if root.is_file() else None


def _stratified_sample(paths: list[str], rate: float) -> list[str]:
    """Deterministic stratified pick — strata are the two leading path
    segments (``r/<pub>/<comp>/`` etc.); each stratum contributes
    ``ceil(rate × n)`` entries chosen by sha256 order, so re-runs select
    identically."""
    strata: dict[str, list[str]] = {}
    for p in paths:
        strata.setdefault("/".join(p.split("/")[:3]), []).append(p)
    out: list[str] = []
    for _stratum, members in sorted(strata.items()):
        members = sorted(members, key=lambda p: _sha256(p.encode()))
        out.extend(members[: max(1, math.ceil(len(members) * rate))])
    return sorted(out)


# --------------------------------------------------------------------------- #
# The checks                                                                   #
# --------------------------------------------------------------------------- #


def check_v1(ctx: VerifyContext) -> dict[str, Any]:
    """Integrity — ``validate_release`` complete; the descriptor
    recomputes to the pub id; manifest artifacts fetched over the origin
    and sha256-matched (all under 1 MiB + the stratified 2 % sample of
    larger/record files; P mode: a 200-artifact sample)."""
    from exports.release import descriptor_sha256, validate_release

    t0 = time.monotonic()
    failures: list[str] = []
    evidence: dict[str, Any] = {}

    report = validate_release(ctx.work_dir)
    evidence["validation_state"] = report.state
    evidence["validation_failures"] = report.failures[:20]
    evidence["artifacts_checked_local"] = report.artifacts_checked
    if report.state != "complete":
        failures.append(f"validate_release: {report.state} — {report.failures[:5]}")

    descriptor = _descriptor(ctx.work_dir, ctx.pub)
    recomputed = descriptor_sha256(descriptor)
    evidence["descriptor_recompute"] = recomputed
    if recomputed != ctx.pub.removeprefix("p-"):
        failures.append(f"descriptor recomputes to p-{recomputed[:12]}… not {ctx.pub[:16]}…")

    artifacts = _integrity_artifacts(ctx.work_dir)
    if ctx.mode == "P":
        cap = ctx.v1_sample or P_SAMPLE
        selected = sorted(artifacts, key=lambda a: _sha256(str(a.get("path")).encode()))[:cap]
        evidence["sample_rule"] = f"P-mode: first {cap} artifacts by sha256(path)"
    else:
        small = [a for a in artifacts if int(a.get("byte_size") or 0) < SMALL_ARTIFACT_BYTES]
        rest = [
            a
            for a in artifacts
            if int(a.get("byte_size") or 0) >= SMALL_ARTIFACT_BYTES
            or str(a.get("path", "")).startswith(f"r/{ctx.pub}/")
        ]
        sampled_paths = set(_stratified_sample([str(a["path"]) for a in rest], SAMPLE_RATE))
        selected = small + [a for a in rest if str(a["path"]) in sampled_paths]
        evidence["sample_rule"] = (
            f"S-mode: every artifact < {SMALL_ARTIFACT_BYTES} B + a stratified "
            f"{SAMPLE_RATE:.0%} sample of larger/record files"
        )
    evidence["artifacts_total"] = len(artifacts)
    evidence["artifacts_fetched"] = len(selected)

    mismatches: list[str] = []
    unfetchable: list[str] = []
    for art in selected:
        path = str(art["path"])
        res = ctx.fetcher.get(f"/{path}")
        if res.status != 200:
            unfetchable.append(f"{path}: HTTP {res.status}")
            continue
        if _sha256(res.body) != str(art.get("sha256")):
            mismatches.append(path)
    evidence["mismatched"] = mismatches[:20]
    evidence["unfetchable"] = unfetchable[:20]
    failures.extend(f"served bytes sha256 != manifest: {p}" for p in mismatches[:10])
    failures.extend(f"manifest artifact not served: {u}" for u in unfetchable[:10])

    return _row(
        "V1",
        ctx.mode,
        "fail" if failures else "pass",
        (
            f"validate_release={report.state}; {len(selected)}/{len(artifacts)} "
            f"artifacts fetched+hashed over {ctx.origin}"
        ),
        evidence=evidence,
        duration=time.monotonic() - t0,
    )


def check_v2(ctx: VerifyContext) -> dict[str, Any]:
    """Identity and clock — the v2 descriptor schema; environment
    ``production``; the 40-hex pushed clean commit; no ``0.0.0`` version;
    the §3.3 clock rules; a unique label; ``as_of_world`` strictly newer
    than the current latest's."""
    t0 = time.monotonic()
    descriptor = _descriptor(ctx.work_dir, ctx.pub)
    failures: list[str] = []
    skip_reasons: list[str] = []
    evidence: dict[str, Any] = {}

    failures.extend(RI.validate_descriptor(descriptor, now=ctx.now))
    env = descriptor.get("environment")
    if env != "production":
        failures.append(f"environment {env!r} != 'production'")

    # -- the live repo facts: pushed + clean are injected or probed — a
    #    fact that cannot be established is a skip leg, never assumed ---- #
    commit = str((descriptor.get("code") or {}).get("commit") or "")
    pushed = ctx.pushed
    tree_clean = ctx.tree_clean
    if ctx.repo_root is not None:
        if pushed is None:
            pushed = RI.commit_is_pushed(ctx.repo_root, commit)
        if tree_clean is None:
            tree_clean = RI.probe_repo_state(ctx.repo_root).clean
        evidence["repo_facts_source"] = f"git probe {ctx.repo_root}"
    elif pushed is not None or tree_clean is not None:
        evidence["repo_facts_source"] = "injected (fixture — recorded, not probed)"
    else:
        evidence["repo_facts_source"] = "unavailable"
    if pushed is None:
        skip_reasons.append("commit-pushed fact unverifiable (no repo root / git cannot answer)")
    if tree_clean is None and (descriptor.get("code") or {}).get("tree") in (None, "unknown"):
        skip_reasons.append(
            "tree-clean fact unverifiable (no repo root, no injected fact, descriptor records none)"
        )

    # -- registry state: label uniqueness + the monotonic rule ---------- #
    latest_as_of: str | None = None
    label_failures: list[str] = []
    if ctx.store is None:
        skip_reasons.append("no registry store — label uniqueness + monotonicity unevaluable")
    else:
        labels_body = ctx.store.read("registry/labels.json")
        if labels_body is None:
            skip_reasons.append("registry/labels.json absent — label uniqueness unevaluable")
        else:
            labels_doc = json.loads(labels_body)
            bound = {
                str(e.get("publication_id"))
                for e in labels_doc.get("labels") or []
                if e.get("label") == descriptor.get("label")
            }
            evidence["label_bound_to"] = sorted(bound)
            if bound and bound != {ctx.pub}:
                label_failures.append(
                    f"label {descriptor.get('label')!r} is bound to "
                    f"{sorted(bound)} — not unique to {ctx.pub}"
                )
        latest_body = ctx.store.read("registry/latest.json")
        catalog_body = ctx.store.read("registry/catalog.json")
        if latest_body is not None:
            latest = json.loads(latest_body)
            latest_pub = str(latest.get("publication_id") or "")
            catalog = json.loads(catalog_body) if catalog_body else {}
            for e in catalog.get("entries") or catalog.get("publications") or []:
                if e.get("publication_id") == latest_pub:
                    latest_as_of = e.get("as_of_world") or (
                        (e.get("compat") or {}).get("as_of_world")
                    )
            if latest_as_of is None:
                desc_body = ctx.store.read(f"staged/releases/{latest_pub}/descriptor.json")
                if desc_body:
                    latest_as_of = (
                        str((json.loads(desc_body).get("snapshot") or {}).get("as_of_world") or "")
                        or None
                    )
            if latest_as_of is None:
                skip_reasons.append(
                    f"latest.json names {latest_pub[:16]}… but its as_of_world is unresolvable"
                )
            evidence["latest_publication_id"] = latest_pub
            evidence["latest_as_of_world"] = latest_as_of
        else:
            evidence["latest_publication_id"] = None  # first release — vacuous

    # promotion_refusals() is the SIG-REL-002 gate — schema/commit/tree/
    # pushed/label/versions/monotonic refusals. repo_root stays None here:
    # this check probes the facts itself (above) so the fact source lands
    # in the evidence, and an unanswerable fact is a recorded skip — never
    # an assumed pass.
    refusals = RI.promotion_refusals(
        descriptor,
        tree_clean=tree_clean,
        pushed=pushed,
        previous_as_of_world=latest_as_of,
    )
    if latest_as_of is not None:
        # strict monotonicity for a fresh promotion — promotion_refusals
        # only refuses a strictly earlier world (a same-instant re-cut is
        # the rollback path's); a same-instant *new* release is not
        # promotable through this verb.
        world = (descriptor.get("snapshot") or {}).get("as_of_world")
        w, p = RI.parse_instant(world), RI.parse_instant(latest_as_of)
        if w is not None and p is not None and w <= p:
            failures.append(
                f"as_of_world {world!r} is not strictly later than the current "
                f"latest's {latest_as_of!r}"
            )
    failures.extend(refusals)
    failures.extend(label_failures)

    # -- §3.3 rule 4: no emitted date later than built_at over the stamp
    #    surfaces (descriptor, manifests, landings, every rendered page)
    built_dt = RI.parse_instant((descriptor.get("build") or {}).get("built_at"))
    if built_dt is not None:
        scan: list[Path] = []
        for rel in (
            f"releases/{ctx.pub}/descriptor.json",
            f"releases/{ctx.pub}/catalog_entry.json",
            f"releases/{ctx.pub}/release.json",
            "release.json",
            "release/build_report.json",
        ):
            f_path = ctx.work_dir / rel
            if f_path.is_file():
                scan.append(f_path)
        for ns, root in _namespace_dirs(ctx.work_dir, ctx.pub).items():
            # record payload JSON under r/ is data, not a stamp surface;
            # everything rendered (html) and all v//s//releases metadata is.
            for f_path in sorted(root.rglob("*")) if root.is_dir() else []:
                if f_path.suffix == ".html" or (f_path.suffix == ".json" and ns != "r"):
                    scan.append(f_path)
        failures.extend(RI.emitted_file_date_failures(scan, built_dt))
        evidence["emitted_date_files_scanned"] = len(scan)

    legs = ["fail" if failures else "pass"] + ["skip" for _ in skip_reasons]
    status = _aggregate(legs)
    detail = f"descriptor {env or '?'} · {len(failures)} refusal(s)" + (
        f" · {len(skip_reasons)} unevaluable leg(s)" if skip_reasons else ""
    )
    evidence["failures"] = failures[:30]
    evidence["skipped_legs"] = skip_reasons
    return _row("V2", ctx.mode, status, detail, evidence=evidence, duration=time.monotonic() - t0)


def check_v3(ctx: VerifyContext) -> dict[str, Any]:
    """Allow-list and absence — the ``v/<pub>/`` + ``s/<pub>/`` route sets
    equal ``ops/public_routes.toml`` (§5.4: ``release.json`` joins the
    allowed top level inside the namespaces); the content assertions run
    over both trees; the denied routes answer 404 on the origin."""
    t0 = time.monotonic()
    failures: list[str] = []
    skips: list[str] = []
    evidence: dict[str, Any] = {}

    allowlist = _publish.load_allowlist(ctx.allowlist_path)
    evidence["allowlist"] = str(ctx.allowlist_path or _publish.DEFAULT_ALLOWLIST_PATH)
    # §5.4's effective top-level sets: the committed list plus the
    # additions the release model names — ``release.json`` rides inside
    # both namespaces; the latest view additionally carries the activation
    # overlay objects (the ``/entity/<t>/<id>/`` per-release stubs and the
    # ``compat_index.json`` copy — nginx.conf:229 "the /entity/ stubs live
    # in this tree"; the snapshot tree is the frozen rendering — a mutable
    # overlay alias under s/<pub>/ is exactly what V3 exists to flag).
    allowed_v = _publish.PublicAllowlist(
        top_level=allowlist.top_level | {"release.json", "entity", "compat_index.json"},
        denied_routes=allowlist.denied_routes,
        required=allowlist.required,
    )
    allowed_s = _publish.PublicAllowlist(
        top_level=allowlist.top_level | {"release.json"},
        denied_routes=allowlist.denied_routes,
        required=allowlist.required,
    )
    ns_dirs = _namespace_dirs(ctx.work_dir, ctx.pub)
    for ns, allowed in (("v", allowed_v), ("s", allowed_s)):
        root = ns_dirs[ns]
        if not root.is_dir():
            failures.append(
                f"{ns}/{ctx.pub}/ absent — the route set cannot equal the "
                "allow-list (G3 §5.2: the build emits both site trees)"
            )
            continue
        try:
            _publish.assert_allowlisted_tree(root, allowed)
        except _publish.PublishError as exc:
            failures.append(f"{ns}/{ctx.pub}: {exc}")
        try:
            _publish.assert_public_tree_content(root)
        except _publish.PublishError as exc:
            failures.append(f"{ns}/{ctx.pub}: {exc}")

    # presentation/ is the fixture-export harness's demo data — banned
    # anywhere in the publish set, by name.
    for p in sorted(ctx.work_dir.rglob("*")):
        if p.is_file() and "presentation" in p.relative_to(ctx.work_dir).parts:
            failures.append(f"{p.relative_to(ctx.work_dir)}: presentation/ segment")

    # denied routes — the toml's [[denied]] set minus /releases/ (the
    # release pipeline owns that prefix per G3 §5.4 — it is a live route
    # on this surface, recorded, not probed) plus an unpromoted pub's.
    denied = [d for d in allowlist.denied_routes if d != "/releases/"]
    other_pub = "p-" + ("f" * 64 if ctx.pub != "p-" + "f" * 64 else "e" * 64)
    denied.append(f"/r/{other_pub}/")
    probed: list[dict[str, Any]] = []
    for route in denied:
        res = ctx.fetcher.get(route)
        probed.append({"route": route, "status": res.status})
        if res.status != 404:
            failures.append(f"denied route {route} answered {res.status}, expected 404")
    evidence["denied_probes"] = probed
    evidence["denied_excluded"] = ["/releases/ — the release pipeline owns it (G3 §5.4)"]

    status = _aggregate(["fail" if failures else "pass"] + ["skip" for _ in skips])
    evidence["failures"] = failures[:30]
    return _row(
        "V3",
        ctx.mode,
        status,
        f"allow-list + {len(probed)} denied probes on {ctx.origin}"
        + (f" — {len(failures)} violation(s)" if failures else ""),
        evidence=evidence,
        duration=time.monotonic() - t0,
    )


_STAMP_META_RE = re.compile(r'<meta\s+name="sig-release"\s+content="([^"]*)"')
_DESCRIBEDBY_RE = re.compile(r'<link\s+rel="describedby"[^>]*href="([^"]*)"')
_STAMP_BLOCK_RE = re.compile(r'<p class="stamp">')


def check_v4(ctx: VerifyContext) -> dict[str, Any]:
    """Stamp and manifest — crawl every HTML page: exactly one
    ``sig-release`` meta + one ``describedby`` link whose values equal
    ``release.json``'s; the visible stamp names the same label/pub/
    commit/as-of; ``X-SIG-Release`` rides every response (P mode: equals
    ``latest.json``'s ``<label> <pub>``)."""
    t0 = time.monotonic()
    site = _site_release(ctx.work_dir, ctx.pub)
    if site is None:
        return _row(
            "V4",
            ctx.mode,
            "skip",
            "no release.json in the tree — the stamp's machine twin is absent",
            evidence={"release_json": None},
            duration=time.monotonic() - t0,
        )
    label = str(site.get("label") or "")
    commit = str((site.get("code") or {}).get("commit") or "")
    expected_header = f"{label} {ctx.pub}"
    latest_header: str | None = None
    if ctx.mode == "P":
        res = ctx.fetcher.get("/releases/latest.json")
        if res.status != 200:
            return _row(
                "V4",
                ctx.mode,
                "skip",
                f"/releases/latest.json unanswered ({res.status}) on {ctx.origin} — "
                "the P-mode header contract is unevaluable",
                evidence={"latest_probe": res.status},
                duration=time.monotonic() - t0,
            )
        latest = json.loads(res.body)
        latest_header = f"{latest.get('label')} {latest.get('publication_id')}"
        if latest.get("publication_id") != ctx.pub:
            return _row(
                "V4",
                ctx.mode,
                "fail",
                f"latest.json names {latest.get('publication_id')} — not the candidate {ctx.pub}",
                evidence={"latest": latest},
                duration=time.monotonic() - t0,
            )
    want_header = latest_header or expected_header

    failures: list[str] = []
    pages = _html_files(*_namespace_dirs(ctx.work_dir, ctx.pub).values())
    fetched = 0
    for page in pages:
        route = _served_route(page, ctx.work_dir, ctx.pub)
        res = ctx.fetcher.get(route)
        if res.status != 200:
            failures.append(f"{route}: served {res.status} — a staged page must answer")
            continue
        fetched += 1
        body = res.body.decode("utf-8", errors="replace")
        metas = _STAMP_META_RE.findall(body)
        if len(metas) != 1:
            failures.append(f"{route}: {len(metas)} sig-release meta stamps (need exactly 1)")
        elif metas[0] != expected_header:
            failures.append(f"{route}: stamp names {metas[0]!r}, expected {expected_header!r}")
        links = _DESCRIBEDBY_RE.findall(body)
        if len(links) != 1:
            failures.append(f"{route}: {len(links)} describedby links (need exactly 1)")
        else:
            href = links[0]
            if not href.endswith("release.json"):
                failures.append(f"{route}: describedby href {href!r} is not release.json")
            else:
                rj = ctx.fetcher.get(_resolve_href(route, href) or href)
                if rj.status != 200:
                    failures.append(f"{route}: describedby {href} answers {rj.status}")
                else:
                    doc = json.loads(rj.body)
                    for fld in ("label", "publication_id", "as_of_world"):
                        if str(doc.get(fld)) != str(site.get(fld)):
                            failures.append(
                                f"{route}: release.json {fld} {doc.get(fld)!r} != {site.get(fld)!r}"
                            )
                    if (doc.get("code") or {}).get("commit") != commit:
                        failures.append(f"{route}: release.json commit mismatch")
        blocks = len(_STAMP_BLOCK_RE.findall(body))
        if blocks != 1:
            failures.append(f"{route}: {blocks} visible stamp blocks (need exactly 1)")
        for needle, what in (
            (label, "label"),
            (ctx.pub[:10], "publication id short form"),
            (commit[:8], "commit8"),
        ):
            if needle and needle not in body:
                failures.append(f"{route}: stamp omits the {what} ({needle!r})")
        hdr = res.headers.get("X-SIG-Release") or res.headers.get("x-sig-release")
        if hdr is None:
            failures.append(f"{route}: no X-SIG-Release header")
        elif ctx.mode == "P" and hdr != want_header:
            failures.append(f"{route}: X-SIG-Release {hdr!r} != latest.json's {want_header!r}")
        elif ctx.mode == "S" and hdr != expected_header:
            failures.append(f"{route}: X-SIG-Release {hdr!r} != {expected_header!r}")

    evidence = {
        "pages_crawled": len(pages),
        "pages_fetched": fetched,
        "expected_header": expected_header,
        "failures": failures[:30],
    }
    return _row(
        "V4",
        ctx.mode,
        "fail" if failures else "pass",
        f"{fetched}/{len(pages)} pages crawled on {ctx.origin} — "
        f"{len(failures)} stamp/header violation(s)",
        evidence=evidence,
        duration=time.monotonic() - t0,
    )


def check_v5(ctx: VerifyContext) -> dict[str, Any]:
    """Link crawl and containment — every same-origin href answers 200 or
    a declared 410; no ``s/<pub>/`` link escapes its prefix except to
    ``/r/<pub>/``, ``/releases/`` and declared latest-version targets."""
    t0 = time.monotonic()
    failures: list[str] = []
    evidence: dict[str, Any] = {}
    ns = _namespace_dirs(ctx.work_dir, ctx.pub)
    pages = _html_files(*ns.values())

    links: dict[str, set[str]] = {}  # route -> {page routes linking it}
    containment_targets: dict[str, set[str]] = {}
    for page in pages:
        page_route = _served_route(page, ctx.work_dir, ctx.pub)
        try:
            text = page.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            failures.append(f"{page_route}: unreadable html")
            continue
        for _tag, _attr, attrs in _page_links(text):
            href = next(attrs[a] for a in _LINK_ATTRS if attrs.get(a))
            route = _resolve_href(page_route, href)
            if route is None:
                continue
            links.setdefault(route, set()).add(page_route)
            if page_route.startswith(f"/s/{ctx.pub}/"):
                containment_targets.setdefault(route, set()).add(page_route)

    # -- containment (§5.3): a /s/<pub>/ page's links stay inside the
    #    snapshot prefix except /r/<pub>/, /releases/ and the declared
    #    latest-version targets ----------------------------------------- #
    latest_version_targets: set[str] = set()
    for page in pages:
        if not _served_route(page, ctx.work_dir, ctx.pub).startswith(f"/s/{ctx.pub}/"):
            continue
        text = page.read_text(encoding="utf-8", errors="replace")
        for _tag, _attr, attrs in _page_links(text):
            if "latest-version" in (attrs.get("rel") or ""):
                for a in _LINK_ATTRS:
                    if attrs.get(a):
                        rt = _resolve_href(_served_route(page, ctx.work_dir, ctx.pub), attrs[a])
                        if rt:
                            latest_version_targets.add(rt)
    escapes: list[str] = []
    allowed_roots = _containment_roots(ctx.pub)
    for route, from_pages in sorted(containment_targets.items()):
        if route in latest_version_targets:
            continue
        if any(route.startswith(r) or route == r.rstrip("/") for r in allowed_roots):
            continue
        escapes.append(f"{sorted(from_pages)[0]} → {route}")
    failures.extend(f"containment escape: {e}" for e in escapes[:20])
    evidence["containment_escapes"] = escapes[:20]
    evidence["latest_version_targets"] = sorted(latest_version_targets)

    # -- every same-origin href → 200 or a declared 410 ------------------ #
    routes = sorted(links)
    if ctx.mode == "P" and len(routes) > (ctx.v5_sample or P_SAMPLE):
        cap = ctx.v5_sample or P_SAMPLE
        routes = sorted(routes, key=lambda r: _sha256(r.encode()))[:cap]
        evidence["sample_rule"] = f"P-mode: {cap} routes by sha256 order"
    bad: list[str] = []
    dead_map: dict[int, list[str]] = {}
    for route in routes:
        res = ctx.fetcher.get(route)
        if res.status == 200:
            continue
        if res.status == 410 and route in ctx.declared_410:
            continue
        bad.append(f"{route} → {res.status} (linked from {sorted(links[route])[:2]})")
        dead_map.setdefault(res.status, []).append(route)
    failures.extend(bad[:20])
    evidence["links_total"] = len(links)
    evidence["links_fetched"] = len(routes)
    evidence["dead_or_undeclared"] = dead_map
    evidence["declared_410"] = sorted(ctx.declared_410)

    return _row(
        "V5",
        ctx.mode,
        "fail" if failures else "pass",
        f"{len(routes)}/{len(links)} same-origin routes fetched on {ctx.origin}; "
        f"{len(escapes)} containment escape(s); {len(bad)} dead link(s)",
        evidence=evidence,
        duration=time.monotonic() - t0,
    )


def _page_types_map(ctx: VerifyContext, ns: str) -> dict[str, str] | None:
    """``route → page type`` from the namespace's emitted
    ``page-types.json`` (sig.page-types-manifest/1). Injected maps (tests)
    take precedence; an absent manifest returns ``None`` and V11 treats
    every page as a content page — the fail-closed classification."""
    if ctx.page_types is not None:
        return ctx.page_types
    manifest = ctx.work_dir / ns / ctx.pub / "page-types.json"
    if not manifest.is_file():
        return None
    doc = _load_json(manifest)
    out: dict[str, str] = {}
    for r in doc.get("routes") or []:
        out[str(r.get("path"))] = str(r.get("type"))
    return out


def _page_budgets(ctx: VerifyContext) -> dict[str, Any] | None:
    path = ctx.budgets_path or (
        Path(__file__).resolve().parents[3] / "web/tests/e2e/page-budgets.json"
    )
    return _load_json(path) if path.is_file() else None


def _lhci_urls(ctx: VerifyContext) -> list[str]:
    path = ctx.lhci_url_path or (Path(__file__).resolve().parents[3] / "web/lighthouserc.json")
    if not path.is_file():
        return []
    try:
        doc = _load_json(path)
    except ValueError:
        return []
    return [str(u) for u in ((doc.get("ci") or {}).get("collect") or {}).get("url") or []]


def playwright_axe(
    origin_url: str, paths: list[str], *, timeout: float = 120.0
) -> dict[str, list[dict[str, Any]]] | None:
    """Run axe-core over ``paths`` on ``origin_url`` through the committed
    playwright+axe deps (``web/node_modules``) — a real browser scan,
    never a stub. ``None`` when node, the deps or a browser is absent:
    that absence is an honest skip upstream, never an invented pass."""
    node = shutil.which("node")
    web_dir = Path(__file__).resolve().parents[3] / "web"
    script = web_dir / "scripts" / "axe_scan.mjs"
    if node is None or not script.is_file() or not (web_dir / "node_modules").is_dir():
        return None
    try:
        out = subprocess.run(
            [node, str(script), origin_url, *paths],
            cwd=str(web_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    try:
        doc = json.loads(out.stdout)
    except ValueError:
        return None
    return doc.get("results")


def check_v11(ctx: VerifyContext) -> dict[str, Any]:
    """Zero-JS, budgets, accessibility — 0 ``<script>`` on content pages;
    the ``sig.page-budgets/1`` document + island ceilings; axe 0
    serious/critical on the Lighthouse URL set + landing + one snapshot
    page. A leg that cannot run (no budgets file, no axe runner/origin)
    records ``skip`` — and a skip blocks."""
    t0 = time.monotonic()
    legs: dict[str, str] = {}
    failures: list[str] = []
    skip_reasons: list[str] = []
    evidence: dict[str, Any] = {}

    ns = _namespace_dirs(ctx.work_dir, ctx.pub)
    types_v = _page_types_map(ctx, "v")
    types_s = _page_types_map(ctx, "s")
    budgets = _page_budgets(ctx)

    def _type_of(ns_name: str, route: str) -> str:
        """The page's ADR-155 type. r/+releases/ pages are archive pages —
        always content. An unclassified site page is treated as content
        (the ban is the safe default)."""
        if ns_name in ("r", "releases"):
            return "T0"
        m = types_v if ns_name == "v" else types_s
        if m is None:
            return "unclassified"
        # manifest paths are site-root-relative; an s/ page's route is
        # /s/<pub>/x but its manifest keys are /x
        key = route if ns_name == "v" else route.removeprefix(f"/s/{ctx.pub}")
        if not key.startswith("/"):
            key = "/" + key
        return m.get(key) or m.get(key.rstrip("/") + "/") or "unclassified"

    zero_js_violations: list[str] = []
    budget_violations: list[str] = []
    pages_scanned = 0
    for ns_name, root in ns.items():
        for page in _html_files(root):
            route = _served_route(page, ctx.work_dir, ctx.pub)
            ptype = _type_of(ns_name, route)
            try:
                text = page.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                failures.append(f"{route}: unreadable html")
                continue
            pages_scanned += 1
            scripts = len(re.findall(r"<\s*script\b", text, flags=re.IGNORECASE))
            if ptype in ("T0", "T1", "unclassified") and scripts:
                zero_js_violations.append(f"{route}: {scripts} <script> tag(s) on a {ptype} page")
            # document budget — T0/T1 (and unclassified) 150 KiB; T2 per-surface
            size = page.stat().st_size
            doc_max: int | None = None
            js_max: int | None = None
            if budgets is not None:
                if ptype in ("T0", "T1", "unclassified"):
                    doc_max = int(
                        ((budgets.get("types") or {}).get("T1") or {}).get(
                            "documentMaxBytes", 153600
                        )
                    )
                elif ptype == "T2":
                    surface = _t2_surface(route, ns_name, ctx.pub)
                    row = ((budgets.get("t2Surfaces") or {}).get(surface or "")) or {}
                    doc_max = row.get("documentMaxBytes")
                    js_max = row.get("jsInitialBytes")
            else:
                doc_max = 153600  # the criterion's verbatim ceiling
            if doc_max is not None and size > doc_max:
                budget_violations.append(
                    f"{route}: {size} B document > {doc_max} B ({ptype} ceiling)"
                )
            if ptype == "T2" and js_max is not None:
                js_bytes = _script_bytes(text, root)
                if js_bytes is not None and js_bytes > js_max:
                    budget_violations.append(
                        f"{route}: {js_bytes} B initial script > {js_max} B island ceiling"
                    )
    legs["zero_js"] = "fail" if zero_js_violations else "pass"
    legs["budgets"] = "fail" if budget_violations else ("pass" if budgets is not None else "skip")
    if budgets is None:
        skip_reasons.append("web/tests/e2e/page-budgets.json absent — island ceilings unevaluable")
    failures.extend(zero_js_violations)
    failures.extend(budget_violations)

    # -- axe: landing + the Lighthouse URL set + one snapshot page ------- #
    axe_urls = ["/"]
    lhci = _lhci_urls(ctx)
    for u in lhci:
        if u not in axe_urls:
            axe_urls.append(u)
    snap = next(
        (p for p in _html_files(ns["s"]) if p.name == "index.html"),
        None,
    )
    snap_route = _served_route(snap, ctx.work_dir, ctx.pub) if snap else f"/s/{ctx.pub}/"
    axe_urls.append(snap_route)
    # axe scans what the origin actually serves — the Lighthouse set is
    # the web surface's; a route absent from this release's v/ tree is
    # recorded absent, not scanned-as-passed.
    served_urls: list[str] = []
    absent_urls: list[str] = []
    for u in axe_urls:
        res = ctx.fetcher.get(u)
        (served_urls if res.status == 200 else absent_urls).append(u)
    evidence["axe_urls_scanned"] = served_urls
    evidence["axe_urls_absent"] = absent_urls

    runner = ctx.axe_runner if ctx.axe_runner is not ... else playwright_axe
    if ctx.axe_runner is None:
        runner = None
    axe_serious: list[str] = []
    if runner is None:
        legs["axe"] = "skip"
        skip_reasons.append("no axe runner available (node + web/node_modules + a browser)")
    elif ctx.axe_url is None and ctx.origin_kind == "tree":
        # tree mode still gets a real axe run when a browser exists —
        # the loopback server serves the same bytes.
        with LocalOriginServer(ctx.fetcher) as srv:
            legs["axe"], skip, axe_serious = _run_axe(runner, srv.url, served_urls)
            if skip:
                skip_reasons.append(skip)
    else:
        base = ctx.axe_url or ctx.origin
        legs["axe"], skip, axe_serious = _run_axe(runner, base, served_urls)
        if skip:
            skip_reasons.append(skip)
    failures.extend(axe_serious[:10])

    evidence["legs"] = legs
    evidence["pages_scanned"] = pages_scanned
    evidence["zero_js_violations"] = zero_js_violations[:20]
    evidence["budget_violations"] = budget_violations[:20]
    evidence["axe_serious"] = axe_serious[:20]
    evidence["skipped_legs"] = skip_reasons
    status = _aggregate(list(legs.values()))
    return _row(
        "V11",
        ctx.mode,
        status,
        "zero-JS/budgets/a11y — "
        + ", ".join(f"{k}={v}" for k, v in legs.items())
        + (f" · {len(failures)} violation(s)" if failures else ""),
        evidence=evidence,
        duration=time.monotonic() - t0,
    )


def _t2_surface(route: str, ns: str, pub: str) -> str | None:
    """``/map/`` → ``map`` — the t2Surfaces row a T2 page's budget reads."""
    if ns == "s":
        route = route.removeprefix(f"/s/{pub}")
    seg = route.strip("/").split("/", 1)[0]
    return seg or None


def _script_bytes(text: str, root: Path) -> int | None:
    """Sum the bytes of every ``<script src>``/modulepreload the page
    references — resolvable inside the same namespace root. ``None`` when
    a reference resolves nowhere (the page's budget is then
    unevaluable — the missing asset is itself a V5 finding)."""
    total = 0
    for _tag, attr, attrs in _page_links(text):
        if attr not in ("src", "href"):
            continue
        is_script = _tag == "script" or (attrs.get("rel") or "") == "modulepreload"
        if not is_script:
            continue
        target = root / attrs[attr].lstrip("/").split("?", 1)[0]
        # _astro paths are site-root-absolute in the served tree
        if not target.is_file():
            name = attrs[attr].split("/")[-1]
            cand = next(root.rglob(name), None)
            if cand is None:
                return None
            target = cand
        total += target.stat().st_size
    return total


def _run_axe(
    runner: AxeRunner, base_url: str, urls: list[str]
) -> tuple[str, str | None, list[str]]:
    """One axe leg — ``(status, skip_reason, serious_violations)``."""
    try:
        results = runner(base_url, urls)
    except Exception:  # noqa: BLE001 - a runner crash is an honest skip
        return "skip", f"axe runner raised on {base_url}", []
    if results is None:
        return "skip", "axe runner unavailable (node/web deps/browser absent)", []
    serious: list[str] = []
    for url, violations in (results or {}).items():
        for v in violations or []:
            if v.get("impact") in AXE_SERIOUS:
                serious.append(f"{url}: {v.get('id')} ({v.get('impact')})")
    return ("fail" if serious else "pass"), None, serious


def check_v12(ctx: VerifyContext) -> dict[str, Any]:
    """Scrub and secrets — the J3 TX-01/P35.31 scan over every file in the
    publish set; one secret-shaped hit aborts. The evidence names the
    file, line and pattern CLASS — never the matched value."""
    from policy.transparency import find_secrets

    t0 = time.monotonic()
    hits: list[str] = []
    scanned = 0
    roots = [p for p in _namespace_dirs(ctx.work_dir, ctx.pub).values() if p.is_dir()]
    extra = [ctx.work_dir / "release.json", ctx.work_dir / "release" / "build_report.json"]
    files: list[Path] = [f for r in roots for f in sorted(r.rglob("*")) if f.is_file()]
    files.extend(p for p in extra if p.is_file())
    for path in files:
        scanned += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(ctx.work_dir).as_posix()
        hits.extend(f"{rel}:{f.line}: {f.pattern_class}" for f in find_secrets(text))
    return _row(
        "V12",
        ctx.mode,
        "fail" if hits else "pass",
        f"{scanned} publish-set files scanned — {len(hits)} secret-shaped hit(s)",
        evidence={"files_scanned": scanned, "hits": hits[:50]},
        duration=time.monotonic() - t0,
    )


def _load_disclosure_texts(path: Path | None) -> dict[str, dict[str, Any]]:
    """``id → {text, targets}`` from the committed disclosures inventory
    (``ops/disclosures.toml`` — the same file the builder digests)."""
    if path is None:
        path = Path(__file__).resolve().parents[3] / "ops" / "disclosures.toml"
    if not path.is_file():
        return {}
    doc = tomllib.loads(path.read_text(encoding="utf-8"))
    out: dict[str, dict[str, Any]] = {}
    for entry in doc.get("disclosures") or []:
        if entry.get("id"):
            out[str(entry["id"])] = dict(entry)
    return out


def check_v13(ctx: VerifyContext) -> dict[str, Any]:
    """Disclosures — every descriptor ``{id, text_sha256}`` resolves
    against the committed inventory (digest re-checked), and its text
    renders on its target pages; the "API is live" line is on every
    stamped page; the surface's evaluation-status wording never claims
    more than ``evaluation.status`` declares."""
    t0 = time.monotonic()
    descriptor = _descriptor(ctx.work_dir, ctx.pub)
    site = _site_release(ctx.work_dir, ctx.pub) or {}
    failures: list[str] = []
    skips: list[str] = []
    evidence: dict[str, Any] = {}

    pages = _html_files(*_namespace_dirs(ctx.work_dir, ctx.pub).values())
    texts = _load_disclosure_texts(ctx.disclosures_path)

    # -- per-disclosure render check ------------------------------------ #
    disclosures = descriptor.get("disclosures") or []
    checked_disclosures: list[str] = []
    for d in disclosures:
        did = str(d.get("id") or "")
        want_sha = str(d.get("text_sha256") or "")
        entry = texts.get(did)
        if entry is None:
            failures.append(
                f"disclosure {did!r}: the descriptor declares it but "
                "ops/disclosures.toml carries no such id — the text is "
                "unverifiable"
            )
            continue
        text = str(entry.get("text") or "")
        got_sha = _sha256(text.encode())
        if got_sha != want_sha:
            failures.append(
                f"disclosure {did!r}: text sha256 {got_sha[:12]}… != the "
                f"descriptor's confirmed digest {want_sha[:12]}…"
            )
            continue
        targets = entry.get("targets") or [f"/releases/{ctx.pub}/index.html"]
        rendered = False
        missing: list[str] = []
        for target in targets:
            target = str(target)
            # site routes resolve inside both site trees; the release
            # landing resolves under releases/<pub>/
            cands: list[Path] = []
            if target.startswith(f"/releases/{ctx.pub}/"):
                cands = [ctx.work_dir / target.lstrip("/")]
            elif target.startswith("/"):
                cands = [
                    ctx.work_dir / "v" / ctx.pub / target.lstrip("/"),
                    ctx.work_dir / "s" / ctx.pub / target.lstrip("/"),
                ]
            else:
                cands = [ctx.work_dir / target]
            found_any = False
            for cand in cands:
                body = _index_bytes(cand)
                if body is None:
                    continue
                norm_page = _text_of(body.decode("utf-8", errors="replace"))
                norm_text = " ".join(_html.unescape(text).split())
                if norm_text in norm_page:
                    found_any = True
                    rendered = True
                else:
                    missing.append(str(cand.relative_to(ctx.work_dir)))
            if not found_any:
                missing.append(target)
        if not rendered:
            failures.append(
                f"disclosure {did!r}: confirmed text renders on no target page "
                f"({sorted(set(missing))[:4]})"
            )
        checked_disclosures.append(did)
    evidence["disclosures_checked"] = checked_disclosures

    # -- the "API is live" line on every stamped page ------------------- #
    live_missing: list[str] = []
    stamped = 0
    norm_live = " ".join(_html.unescape(LIVE_API_LINE).split())
    for page in pages:
        text = page.read_text(encoding="utf-8", errors="replace")
        if 'name="sig-release"' not in text:
            continue
        stamped += 1
        if norm_live not in _text_of(text):
            live_missing.append(page.relative_to(ctx.work_dir).as_posix())
    failures.extend(f"{p}: the stamp's 'API is live' line is absent" for p in live_missing[:10])
    evidence["stamped_pages"] = stamped
    evidence["live_line_missing"] = live_missing[:10]

    # -- eval-status wording never outruns evaluation.status ------------ #
    status = str((descriptor.get("evaluation") or {}).get("status") or "")
    site_status = str((site.get("evaluation") or {}).get("status") or "")
    if site and site_status != status:
        failures.append(
            f"release.json evaluation.status {site_status!r} != descriptor's {status!r}"
        )
    overclaims: list[str] = []
    if status != "certified":
        for path in files_under(ctx.work_dir, ctx.pub):
            if path.suffix not in (".html", ".json", ".jsonl"):
                continue
            body_text = path.read_text(encoding="utf-8", errors="replace").lower()
            for phrase in CERTIFIED_CLAIMS:
                if phrase.lower() in body_text:
                    overclaims.append(f"{path.relative_to(ctx.work_dir)}: {phrase!r}")
    failures.extend(
        f"claims a certified/final evaluation under status={status}: {o}" for o in overclaims[:10]
    )
    evidence["eval_status"] = status
    evidence["eval_overclaims"] = overclaims[:10]

    legs = ["fail" if failures else "pass"] + ["skip" for _ in skips]
    return _row(
        "V13",
        ctx.mode,
        _aggregate(legs),
        f"{len(checked_disclosures)} disclosure(s) · {stamped} stamped pages · "
        f"eval={status}" + (f" — {len(failures)} violation(s)" if failures else ""),
        evidence={**evidence, "failures": failures[:30]},
        duration=time.monotonic() - t0,
    )


def files_under(work_dir: Path, pub: str) -> list[Path]:
    out: list[Path] = []
    for root in _namespace_dirs(work_dir, pub).values():
        if root.is_dir():
            out.extend(p for p in sorted(root.rglob("*")) if p.is_file())
    for extra in (work_dir / "release.json",):
        if extra.is_file():
            out.append(extra)
    return out


_CHECK_FNS = {
    "V1": check_v1,
    "V2": check_v2,
    "V3": check_v3,
    "V4": check_v4,
    "V5": check_v5,
    "V11": check_v11,
    "V12": check_v12,
    "V13": check_v13,
}


# --------------------------------------------------------------------------- #
# The suite                                                                    #
# --------------------------------------------------------------------------- #

#: The only release class under which a waiver may cover a failed/skipped
#: check — and even then V12 is never waivable (Part VIII's scrub gate
#: has no override).
WAIVABLE_CLASS = "class_s"
NEVER_WAIVABLE = frozenset({"V12"})


def apply_waivers(
    rows: list[dict[str, Any]],
    *,
    release_class: str | None,
    waivers: tuple[str, ...],
) -> dict[str, Any]:
    """The block/waiver contract (deliverable 10): any failure or skip
    blocks promotion; a waiver exists only under Class S and is recorded
    in the readout — ``V12`` is never waivable.

    Returns ``{verdict, promotion_blocked, waivers, uncovered}`` where
    ``verdict`` ∈ ``pass | waived | blocked``.
    """
    verdict = "pass"
    applied: list[dict[str, Any]] = []
    ignored: list[dict[str, Any]] = []
    uncovered: list[str] = [r["check"] for r in rows if r["status"] != "pass"]
    waiver_map: dict[str, str] = {}
    for w in waivers:
        check, _, ref = w.partition("=")
        waiver_map[check.strip()] = ref.strip()
    for check_id in list(uncovered):
        if check_id in NEVER_WAIVABLE:
            ignored.append({"check": check_id, "reason": "never waivable (Part VIII)"})
            continue
        wref: str | None = waiver_map.get(check_id)
        if wref is None:
            continue
        if release_class != WAIVABLE_CLASS:
            ignored.append(
                {
                    "check": check_id,
                    "ref": wref,
                    "reason": f"class is {release_class!r}, waivers need class_s",
                }
            )
            continue
        applied.append({"check": check_id, "ref": wref, "class": "class_s"})
        uncovered.remove(check_id)
    if uncovered:
        verdict = "blocked"
    elif applied:
        verdict = "waived"
    return {
        "verdict": verdict,
        "promotion_blocked": verdict == "blocked",
        "waivers": applied,
        "waivers_ignored": ignored,
        "uncovered": uncovered,
    }


def run_suite(ctx: VerifyContext) -> dict[str, Any]:
    """Run suite A's mode-applicable checks (the §5.5 table verbatim —
    V2/V11/V12 are S-only; P runs V1-sample, V3, V4, V5-sample, V13) and
    return the ``sig.release-verify/1`` result document. Every check row
    is appended to ``results`` — the rows are append-only evidence of
    what ran and what it saw."""
    checks = CHECKS_S if ctx.mode == "S" else CHECKS_P
    rows: list[dict[str, Any]] = []
    for cid in checks:
        try:
            row = _CHECK_FNS[cid](ctx)
        except VerifyError as exc:
            row = _row(cid, ctx.mode, "fail", f"check could not complete: {exc}")
        except Exception as exc:  # noqa: BLE001 - a crashed check is a fail, never silent
            row = _row(cid, ctx.mode, "fail", f"check raised {type(exc).__name__}: {exc}")
        row["origin"] = ctx.origin
        row["origin_kind"] = ctx.origin_kind
        rows.append(row)
    gate = apply_waivers(rows, release_class=ctx.release_class, waivers=ctx.waivers)
    counts = {"pass": 0, "fail": 0, "skip": 0}
    for r in rows:
        counts[r["status"]] += 1
    return {
        "schema": RESULT_SCHEMA,
        "mode": ctx.mode,
        "publication_id": ctx.pub,
        "origin": ctx.origin,
        "origin_kind": ctx.origin_kind,
        "release_class": ctx.release_class,
        "checks": list(checks),
        "results": rows,
        "counts": counts,
        **gate,
    }


def write_results(suite: dict[str, Any], out_dir: Path | str) -> list[Path]:
    """Persist every check's JSON row + the suite document — the durable
    per-run evidence the readout names."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", suite.get("origin") or "origin")[:60]
    for row in suite["results"]:
        path = out / f"{suite['mode']}-{row['check']}-{slug}.json"
        path.write_text(json.dumps(row, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written.append(path)
    doc = out / f"suite-{suite['mode']}-{slug}.json"
    doc.write_text(json.dumps(suite, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    written.append(doc)
    return written


__all__ = [
    "AXE_SERIOUS",
    "AXE_WCAG_TAGS",
    "CHECKS_P",
    "CHECKS_S",
    "CERTIFIED_CLAIMS",
    "FetchResult",
    "Fetcher",
    "HttpFetcher",
    "LIVE_API_LINE",
    "LocalOriginServer",
    "NEVER_WAIVABLE",
    "P_SAMPLE",
    "RESULT_SCHEMA",
    "SAMPLE_RATE",
    "SMALL_ARTIFACT_BYTES",
    "TreeFetcher",
    "VerifyContext",
    "VerifyError",
    "apply_waivers",
    "check_v1",
    "check_v11",
    "check_v12",
    "check_v13",
    "check_v2",
    "check_v3",
    "check_v4",
    "check_v5",
    "playwright_axe",
    "run_suite",
    "write_results",
]
