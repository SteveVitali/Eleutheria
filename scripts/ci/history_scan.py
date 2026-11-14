#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Public-git-history scan for secrets and restricted data (P37.55, Q-E2-23
[B-6] = a — "scan the public history for secrets and restricted data first,
then I submit it").

The Software Heritage save-now request and any Zenodo deposit of git history
make the repository's *whole history* permanently public in a third archive —
what the scan finds there cannot be recalled. ``secret_scan.py`` already gates
the tracked *tip* on every PR; this scanner walks every blob reachable from
the **public ref surface** — the refs ``git ls-remote`` advertises
(``refs/heads/*`` + ``refs/pull/*`` + ``refs/tags/*``), mirrored locally as
``refs/remotes/origin/*`` and ``refs/remotes/pull/*`` — so a secret committed
and "removed" in a later commit is still found. That is the whole point of a
history scan.

Rule classes:

* ``secret:*`` — the same high-confidence credential shapes as
  ``scripts/ci/secret_scan.py`` (imported, never duplicated): AWS/GitHub/
  Slack/OpenAI/Google key shapes, PEM private-key blocks, and the
  ``SIG_*_TOKEN|KEY|SECRET|PASSWORD = "…"`` literal shape (HG-09). Two
  *value-shape* exemptions apply on top of the source scanner's
  ``secrets = { … }`` name-binding exemption: a value matching the
  ``sig-<name>`` Secret Manager *name* shape (a name is never a credential)
  and a ``$(…)``/``${…}`` command-substitution value (a command, not a
  literal) are not findings — in prose these shapes are quoted constantly.
* ``path:*`` — credential-shaped *paths* ever tracked: ``.env*``,
  ``*.pem``/``*.key``/``*.p12``/``*.pfx``/``*.keystore``/``*.jks``,
  ``id_rsa*``, ``*credentials.json``, ``service-account*.json`` carrying a
  ``private_key`` field (a ``service-accounts.json`` *listing* is not a key),
  and the gitignored build-log subtree ``docs/build/logs/**`` (except the
  mechanism file ``.gitignore`` itself — the restricted handle list lives
  under that subtree in a build checkout and must never have been committed).
* ``restricted:email-shape`` — e-mail-shaped literals, *distinct-token*
  accounting: every token is classified (``EMAIL_CLASSES`` — deterministic
  benign shapes) or lands in ``unclassified`` and blocks unless covered by a
  committed disposition.
* ``restricted:handle-token`` — every literal on the gitignored personal-handle
  list (``docs/build/logs/next-phase/C3/personal_like_ids.txt``), when the list
  is present. These are the *disclosed* class: the operator accepted retained
  history and disclosed it in P34.18's correction note (A-0.4 = a, OD-20), so
  handle findings are **recorded, not blocking**. Absent the list the class is
  recorded ``skipped`` — never silently empty.

Non-echo rule (same as ``secret_scan.py``): findings name the rule id, paths,
and a **sha256 of the matched literal** — never the matched bytes.
``--tokens-out`` writes the distinct e-mail-shaped tokens to a caller-chosen
path for the human reviewer (point it at a gitignored location; it is never
committed).

**Dispositions.** A committed ``sig.history-scan-dispositions/1`` TOML file
(``--dispositions``) maps finding keys to ``exempt`` (a reviewed false
positive — e.g. the documented AWS example key seeded in tests) or
``disclosed`` (accepted-and-disclosed — the A-0.4 pattern: retained,
recorded, operator-visible). Matchers: ``literal_sha256`` (the matched
literal's digest), ``path_glob``, ``token_sha256`` (an e-mail token's digest),
``domain`` / ``domain_suffix`` (e-mail domain buckets). An entry that matches
**no** finding is *stale* and fails the report — the file can never silently
drift out of sync with history.

``disposition``: ``clean`` when no undisposed finding remains, no e-mail token
is unclassified-and-undispositioned, and no disposition entry is stale;
``findings`` otherwise — a red report blocks the archival submission until
remediated or disclosed (the ``sig-ops swh-save --now`` gate reads it).

Usage::

    uv run python scripts/ci/history_scan.py --json <report.json> \
        --dispositions docs/build/reports/p37.55-archival-deposits/history_scan_dispositions.toml
    uv run python scripts/ci/history_scan.py --tokens-out docs/build/logs/history-scan-emails.txt

Exit codes: 0 clean · 1 findings · 2 usage/environment error.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import tomllib
from collections.abc import Iterator
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import secret_scan  # noqa: E402 — same-directory CI scanner, rules reused verbatim

REPORT_SCHEMA = "sig.history-scan/1"
DISPOSITIONS_SCHEMA = "sig.history-scan-dispositions/1"

#: The ref namespaces the public remote advertises, as mirrored locally.
#: ``refs/remotes/origin`` mirrors ``refs/heads/*`` (+ HEAD); ``refs/remotes/pull``
#: mirrors the advertised ``refs/pull/*`` (fetched on demand); ``refs/tags``
#: mirrors ``refs/tags/*``. A namespace absent locally is recorded, not a
#: failure — an unfetched mirror means that namespace contributed no objects.
DEFAULT_REF_NAMESPACES = ("refs/remotes/origin", "refs/remotes/pull", "refs/tags")

#: The gitignored restricted handle list (P34.18): present in a build
#: checkout, never committed, never quoted into a committed file.
HANDLE_LIST_REL = "docs/build/logs/next-phase/C3/personal_like_ids.txt"

#: Path shapes that were ever tracked and name a credential or the restricted
#: log subtree. ``predicate`` (optional) is a content check the blob must also
#: pass — a ``service-accounts.json`` *listing* of account names is not a key.
PATH_RULES: list[dict] = [
    {"id": "path:env-file", "pattern": re.compile(r"(^|/)\.env(\..+)?$", re.IGNORECASE)},
    {
        "id": "path:pem-file",
        "pattern": re.compile(r"\.(pem|key|p12|pfx|keystore|jks)$", re.IGNORECASE),
    },
    {
        "id": "path:ssh-private-key",
        "pattern": re.compile(r"(^|/)id_(rsa|dsa|ecdsa|ed25519)(\.|$)", re.IGNORECASE),
    },
    {
        "id": "path:credentials-json",
        "pattern": re.compile(r"credentials[^/]*\.json$", re.IGNORECASE),
    },
    {
        "id": "path:service-account-key",
        "pattern": re.compile(r"service.account[^/]*\.json$", re.IGNORECASE),
        # a service-account *key file* carries a private_key field; a listing
        # (`gcloud iam service-accounts list`) does not.
        "predicate": lambda blob: b"private_key" in blob or b"PRIVATE KEY" in blob,
    },
    {
        "id": "path:gitignored-build-log",
        "pattern": re.compile(r"^docs/build/logs/"),
        # the mechanism file that keeps the gitignored directory tracked-empty
        "path_exempt": {"docs/build/logs/.gitignore"},
    },
]

#: Generic e-mail-shaped literal. The count is over *distinct* tokens; each is
#: classified below or lands in ``unclassified`` and blocks unless covered by a
#: committed disposition.
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")

#: Deterministic benign e-mail classes (reviewed this run, P37.55): robot
#: noreply aliases, RFC-2606 reserved and example/test domains, fixture-shaped
#: literals, file-suffix false positives (``x@file.sql``, DSN ``user@host``
#: forms), GCP service-account *identifiers* (a name is public; the private key
#: is the credential), and the project's own public aliases + synthetic
#: contact-id forms. A token matching none of these is ``unclassified``.
EMAIL_CLASSES: list[tuple[str, re.Pattern[str]]] = [
    (
        "github-noreply",
        re.compile(
            r"^[A-Za-z0-9._%+\-]+@(users\.)?noreply\.github\.com$|^noreply@github\.com$",
            re.IGNORECASE,
        ),
    ),
    ("vendor-noreply", re.compile(r"^noreply@anthropic\.com$", re.IGNORECASE)),
    (
        "example-domain",
        re.compile(
            r"@(.*\.)?example\.(com|org|net|test|invalid|localhost)$|@(.*\.)?example$",
            re.IGNORECASE,
        ),
    ),
    # A domain that IS `example.<tld>` is a doc placeholder regardless of the
    # TLD (example.fr, example.gov.uk, example.iam, …).
    ("example-literal", re.compile(r"@example\.[a-z0-9.]+$", re.IGNORECASE)),
    (
        "example-prefix",
        re.compile(r"@example-[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$", re.IGNORECASE),
    ),
    (
        "file-suffix",
        re.compile(
            r"@([A-Za-z0-9.\-]+\.(sql|py|json|toml|md|txt|csv|tsv|ndjson|jsonl|yml|yaml|sh|tf|log|txt|cff|xml|html?)|host\.docker\.internal|.*\.internal)$",
            re.IGNORECASE,
        ),
    ),
    (
        "gserviceaccount",
        re.compile(r"@([A-Za-z0-9.\-]+\.)?gserviceaccount\.com$", re.IGNORECASE),
    ),
    (
        "project-domain",
        re.compile(r"@(sig-project\.org|surveillancegraph\.org|sig\.org)$", re.IGNORECASE),
    ),
]

#: A ``SIG_*_TOKEN|KEY|… = "…"`` match whose *value* is a Secret Manager name
#: (``sig-<lowercase-hyphenated>``) or a command substitution is never a
#: credential literal — these shapes are quoted constantly in docs.
# The rule's match ends before the closing quote, so the extractor treats the
# opening quote-to-end-of-match span as the value.
_SIG_CRED_VALUE_RE = re.compile(r"[:=]\s*[\"']([^\"']+)")
_SECRET_NAME_VALUE = re.compile(r"^sig-[a-z0-9-]+$")

MAX_BLOB_BYTES = 4 << 20  # 4 MiB — larger blobs are counted and skipped.
MAX_EXAMPLES_PER_RULE = 5  # examples name rule + path + literal sha256, never content.


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _git(
    root: Path, *args: str, input_bytes: bytes | None = None
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        input=input_bytes,
        capture_output=True,
        check=True,
    )


def _refs(root: Path, namespaces: tuple[str, ...]) -> tuple[list[str], list[str]]:
    """(refs, missing-namespaces): every local ref under each namespace."""
    refs: list[str] = []
    missing: list[str] = []
    for ns in namespaces:
        proc = _git(root, "for-each-ref", "--format=%(refname)", ns)
        found = [r for r in proc.stdout.decode().split("\n") if r]
        if found:
            refs.extend(found)
        else:
            missing.append(ns)
    return refs, missing


def _rev_list_objects(root: Path, refs: list[str]) -> tuple[int, dict[str, str]]:
    """`git rev-list --objects <refs>` → (commit count, {object sha: first path}).

    Commit count comes from a separate ``rev-list --count`` — the ``--objects``
    listing also emits root *trees* with an empty path, which an empty-path
    heuristic would miscount as commits.
    """
    count_proc = _git(root, "rev-list", "--count", *refs)
    n_commits = int(count_proc.stdout.decode().strip())
    proc = _git(root, "rev-list", "--objects", *refs)
    objects: dict[str, str] = {}
    for line in proc.stdout.decode("utf-8", errors="replace").split("\n"):
        if not line:
            continue
        sha, _, path = line.partition(" ")
        if path:
            objects.setdefault(sha, path)
    return n_commits, objects


def _blob_types(root: Path, shas: list[str]) -> dict[str, str]:
    """`git cat-file --batch-check` → {sha: type} for the reachable objects."""
    out: dict[str, str] = {}
    data = "".join(f"{s}\n" for s in shas).encode()
    proc = _git(root, "cat-file", "--batch-check", input_bytes=data)
    for line in proc.stdout.decode().split("\n"):
        if not line:
            continue
        sha, _, rest = line.partition(" ")
        out[sha] = rest.split(" ", 1)[0]
    return out


def _iter_blobs(root: Path, shas: list[str]) -> Iterator[tuple[str, bytes]]:
    """Stream ``git cat-file --batch`` for ``shas``; yields (sha, bytes).

    The sha list is fed from a temp file, not a pipe: writing ~50k shas into a
    pipe would fill the buffer while ``cat-file``'s own output goes unread —
    a deadlock.
    """
    with tempfile.TemporaryFile(mode="w+b") as feed:
        feed.write("".join(f"{s}\n" for s in shas).encode())
        feed.seek(0)
        proc = subprocess.Popen(
            ["git", "-C", str(root), "cat-file", "--batch"],
            stdin=feed,
            stdout=subprocess.PIPE,
        )
        assert proc.stdout is not None
        out = proc.stdout
        header = out.readline()
        while header:
            parts = header.decode().split()
            if len(parts) >= 3 and parts[1] == "blob":
                sha, size = parts[0], int(parts[2])
                blob = out.read(size)
                out.read(1)  # trailing LF
                yield sha, blob
            header = out.readline()
    proc.wait()


def _load_handle_list(root: Path) -> tuple[frozenset[str], str]:
    path = root / HANDLE_LIST_REL
    if not path.is_file():
        return frozenset(), f"absent ({HANDLE_LIST_REL} is gitignored; skipped, recorded)"
    tokens = frozenset(t for t in path.read_text(encoding="utf-8", errors="replace").split() if t)
    return tokens, f"loaded {len(tokens)} tokens (gitignored; never committed or printed)"


def _classify_email(token: str, handles: frozenset[str]) -> str:
    if token in handles:
        return "handle-list"
    for name, pattern in EMAIL_CLASSES:
        if pattern.search(token):
            return name
    return "unclassified"


def _is_credential_value(matched_text: str) -> bool:
    """Whether a ``SIG_*_… = "…"`` match's quoted value is a real literal —
    a Secret Manager name (``sig-*``) or a shell template/command is not."""
    m = _SIG_CRED_VALUE_RE.search(matched_text)
    if not m:
        return True  # can't tell — treat as a finding, never waive
    value = m.group(1)
    if _SECRET_NAME_VALUE.fullmatch(value):
        return False
    # A value embedding a shell substitution (``$(…)``/``${…}`` anywhere), or
    # *being* one (a leading ``$`` — ``"$VAR"`` indirection), is a *template* —
    # the credential material is interpolated at runtime, never written as the
    # literal (e.g. a DSN built from ``${SIG_PG_PASSWORD}``).
    if value.startswith("$") or "$(" in value or "${" in value:
        return False
    return True


def load_dispositions(path: Path) -> tuple[list[dict], list[str]]:
    """Parse a ``sig.history-scan-dispositions/1`` TOML file → (entries, errors)."""
    try:
        doc = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return [], [f"dispositions file unreadable: {exc}"]
    if doc.get("schema") != DISPOSITIONS_SCHEMA:
        return [], [f"dispositions schema is {doc.get('schema')!r}, not {DISPOSITIONS_SCHEMA!r}"]
    entries: list[dict] = []
    errors: list[str] = []
    for i, entry in enumerate(doc.get("disposition", [])):
        eid = entry.get("id") or f"entry-{i}"
        disp = entry.get("disposition")
        if disp not in ("exempt", "disclosed"):
            errors.append(f"{eid}: disposition must be exempt|disclosed")
            continue
        match = entry.get("match")
        if not isinstance(match, dict) or not any(
            k in match
            for k in (
                "literal_sha256",
                "path_glob",
                "token_sha256",
                "domains",
                "domain_suffixes",
            )
        ):
            errors.append(
                f"{eid}: match needs literal_sha256|path_glob|token_sha256|domains|domain_suffixes"
            )
            continue
        if not entry.get("justification"):
            errors.append(f"{eid}: justification required")
            continue
        entry = dict(entry)
        entry["id"] = eid
        entry["matched"] = 0
        entries.append(entry)
    return entries, errors


def _disposition_for(
    entries: list[dict],
    *,
    literal_sha256: str | None = None,
    path: str | None = None,
    token_sha256: str | None = None,
    domain: str | None = None,
) -> dict | None:
    """The first disposition entry matching this finding key (None → undisposed)."""
    for entry in entries:
        match = entry["match"]
        if literal_sha256 and match.get("literal_sha256") == literal_sha256:
            entry["matched"] += 1
            return entry
        if path and "path_glob" in match and fnmatch.fnmatch(path, str(match["path_glob"])):
            entry["matched"] += 1
            return entry
        if token_sha256 and match.get("token_sha256") == token_sha256:
            entry["matched"] += 1
            return entry
        if domain:
            d_lower = domain.lower()
            for d in match.get("domains", []) or []:
                d = str(d).lower()
                if d_lower == d or d_lower.endswith("." + d):
                    entry["matched"] += 1
                    return entry
            for suffix in match.get("domain_suffixes", []) or []:
                if d_lower.endswith(str(suffix).lower()):
                    entry["matched"] += 1
                    return entry
    return None


def scan_history(
    root: Path,
    *,
    namespaces: tuple[str, ...] = DEFAULT_REF_NAMESPACES,
    handle_path: Path | None = None,
    dispositions_path: Path | None = None,
    generated_at: str = "",
    token_sink: dict[str, str] | None = None,
) -> dict:
    """Scan every blob reachable from the public ref surface. Returns the
    ``sig.history-scan/1`` report document (counts, paths, literal digests —
    never matched bytes).

    ``token_sink``, when a dict is passed, is filled with each distinct
    e-mail-shaped token → its class — the reviewer-only material the report
    deliberately never carries (the sink's destination is the caller's
    responsibility: a gitignored path, never a committed file).
    """
    if handle_path is None:
        handles, handle_note = _load_handle_list(root)
    elif handle_path.is_file():
        toks = frozenset(
            t for t in handle_path.read_text(encoding="utf-8", errors="replace").split() if t
        )
        handles = toks
        handle_note = f"loaded {len(toks)} tokens (explicit path; never committed or printed)"
    else:
        handles, handle_note = frozenset(), f"absent ({handle_path}; skipped, recorded)"

    dispositions: list[dict] = []
    disposition_errors: list[str] = []
    if dispositions_path is not None:
        dispositions, disposition_errors = load_dispositions(dispositions_path)

    refs, missing = _refs(root, namespaces)
    if not refs:
        raise RuntimeError("no refs found under the scanned namespaces")
    n_commits, objects = _rev_list_objects(root, refs)
    types = _blob_types(root, list(objects))
    blob_shas = [s for s, t in types.items() if t == "blob"]
    path_by_sha = {s: objects[s] for s in blob_shas}

    # rule_id -> {count, paths:set, literals:set, dispositioned:{disp_id:count}}
    findings: dict[str, dict] = {}
    email_tokens: dict[str, dict] = {}  # token -> {count, paths:set}
    handle_hits: dict[str, int] = {}
    path_candidates: dict[str, dict[str, str]] = {}  # rule_id -> {sha: path}
    blob_count = 0
    byte_count = 0
    skipped_large = 0

    def hit(rule_id: str, path: str, literal_sha256: str | None = None) -> None:
        entry = findings.setdefault(
            rule_id, {"count": 0, "paths": set(), "literals": set(), "dispositioned": {}}
        )
        entry["count"] += 1
        entry["paths"].add(path)
        if literal_sha256:
            entry["literals"].add(literal_sha256)

    # Path candidates from the listing — content predicates resolve below.
    for sha, path in path_by_sha.items():
        for rule in PATH_RULES:
            if path in rule.get("path_exempt", set()):
                continue
            if rule["pattern"].search(path):
                if rule.get("predicate") is None:
                    hit(rule["id"], path)
                else:
                    path_candidates.setdefault(rule["id"], {})[sha] = path

    # One pre-filter regex over the union of every rule's shape — a blob that
    # cannot match anything is skipped without a per-line pass (the public
    # history is ~5 GB of text). Rules still run on survivors, unchanged.
    prefilter_src = "|".join(
        [f"(?:{p.pattern})" for _, p in secret_scan.RULES]
        + [f"(?:{EMAIL_RE.pattern})"]
        + [f"(?:{re.escape(t)})" for t in handles]
    )
    prefilter = re.compile(prefilter_src) if prefilter_src else None
    handle_re = re.compile("|".join(re.escape(t) for t in handles)) if handles else None

    for sha, blob in _iter_blobs(root, blob_shas):
        blob_count += 1
        byte_count += len(blob)
        path = path_by_sha[sha]
        for rule in PATH_RULES:
            if sha in path_candidates.get(rule["id"], {}):
                if rule["predicate"](blob):
                    hit(rule["id"], path)
        if len(blob) > MAX_BLOB_BYTES:
            skipped_large += 1
            continue
        if b"\x00" in blob[:8192]:
            continue  # binary — never a text secret line
        text = blob.decode("utf-8", errors="ignore")
        if prefilter is not None and not prefilter.search(text):
            continue  # no rule shape anywhere in the blob — the common case
        for line in text.splitlines():
            if prefilter is not None and not prefilter.search(line):
                continue
            for rule_id, pattern in secret_scan.RULES:
                for m in pattern.finditer(line):
                    if rule_id == "sig-credential-literal" and (
                        secret_scan._is_secret_name_binding(line)
                        or not _is_credential_value(m.group(0))
                    ):
                        continue  # a Secret Manager name or a command, never a value
                    hit(f"secret:{rule_id}", path, _sha256_text(m.group(0)))
            for m in EMAIL_RE.finditer(line):
                token = m.group(0)
                e = email_tokens.setdefault(token, {"count": 0, "paths": set()})
                e["count"] += 1
                if len(e["paths"]) < MAX_EXAMPLES_PER_RULE:
                    e["paths"].add(path)
            if handle_re is not None:
                for m in handle_re.finditer(line):
                    token = m.group(0)
                    handle_hits[token] = handle_hits.get(token, 0) + 1

    # ── classify e-mail tokens ───────────────────────────────────────────────
    email_classes: dict[str, int] = {}
    unclassified: dict[str, dict] = {}
    for token, data in email_tokens.items():
        klass = _classify_email(token, handles)
        email_classes[klass] = email_classes.get(klass, 0) + 1
        if klass == "unclassified":
            unclassified[token] = data
        if token_sink is not None:
            token_sink[token] = klass

    # ── apply dispositions ───────────────────────────────────────────────────
    exempted: dict[str, int] = {}
    disclosed_extra: dict[str, int] = {}
    email_dispositioned: dict[str, int] = {}
    remaining_unclassified = 0
    for rule_id, entry in list(findings.items()):
        kept_paths: set[str] = set()
        kept_literals: set[str] = set()
        kept = 0
        for path in sorted(entry["paths"]):
            disp = (
                _disposition_for(
                    dispositions,
                    path=path,
                    literal_sha256=None,
                )
                if rule_id.startswith("path:")
                else None
            )
            if disp is not None:
                bucket = exempted if disp["disposition"] == "exempt" else disclosed_extra
                bucket[disp["id"]] = bucket.get(disp["id"], 0) + 1
                continue
            kept_paths.add(path)
        if rule_id.startswith("secret:"):
            for lit in sorted(entry["literals"]):
                disp = _disposition_for(dispositions, literal_sha256=lit)
                if disp is not None:
                    bucket = exempted if disp["disposition"] == "exempt" else disclosed_extra
                    bucket[disp["id"]] = bucket.get(disp["id"], 0) + 1
                    continue
                kept_literals.add(lit)
                kept += 1
        else:
            kept += len(kept_paths)
        if kept:
            findings[rule_id]["paths"] = kept_paths
            findings[rule_id]["literals"] = kept_literals
            findings[rule_id]["count"] = kept
        else:
            del findings[rule_id]

    for token in unclassified:
        token_sha = _sha256_text(token)
        domain = token.rsplit("@", 1)[-1]
        disp = _disposition_for(dispositions, token_sha256=token_sha, domain=domain)
        if disp is not None:
            email_dispositioned[disp["id"]] = email_dispositioned.get(disp["id"], 0) + 1
        else:
            remaining_unclassified += 1
    if remaining_unclassified:
        findings["restricted:unclassified-email"] = {
            "count": remaining_unclassified,
            "paths": set(),
            "literals": set(),
            "note": ("distinct tokens; `sha256` deliberately not emitted for unclassified tokens"),
        }

    stale = [e["id"] for e in dispositions if e["matched"] == 0]
    secret_left = sum(e["count"] for k, e in findings.items() if k.startswith("secret:"))
    path_left = sum(e["count"] for k, e in findings.items() if k.startswith("path:"))
    blocking = (
        secret_left + path_left + remaining_unclassified + len(disposition_errors) + len(stale)
    )
    disposition = "clean" if blocking == 0 else "findings"

    report_findings = {
        rid: {
            "count": e["count"],
            "paths": sorted(e["paths"])[:MAX_EXAMPLES_PER_RULE],
            "paths_total": len(e["paths"]),
            "literal_sha256": sorted(e["literals"]),
        }
        for rid, e in sorted(findings.items())
    }
    return {
        "schema": REPORT_SCHEMA,
        "generated_at": generated_at,
        "repo": str(root),
        "scope": {
            "ref_namespaces": list(namespaces),
            "missing_namespaces": missing,
            "refs": len(refs),
            "commits": n_commits,
            "blobs_scanned": blob_count,
            "bytes_scanned": byte_count,
            "blobs_skipped_large": skipped_large,
            "note": (
                "Blob contents + tracked paths reachable from the public ref "
                "surface (ls-remote-advertised refs/heads/*, refs/pull/*, "
                "refs/tags/* mirrored under refs/remotes/{origin,pull} + "
                "refs/tags). Commit-author metadata is inherent git data, "
                "outside the remediation scope."
            ),
        },
        "rules": {
            "secret": [f"secret:{r}" for r, _ in secret_scan.RULES],
            "path": [r["id"] for r in PATH_RULES],
            "restricted": ["restricted:email-shape", "restricted:handle-token"],
        },
        "findings": report_findings,
        "dispositions": {
            "path": str(dispositions_path) if dispositions_path else None,
            "errors": disposition_errors,
            "exempt": dict(sorted(exempted.items())),
            "disclosed": dict(sorted({**disclosed_extra, **email_dispositioned}.items())),
            "stale": stale,
        },
        "disclosed": {
            "handle_list": handle_note,
            "handle_tokens_matched": len(handle_hits),
            "handle_token_hits": sum(handle_hits.values()),
            "disclosure": (
                "Retained-history class — disclosed by P34.18's correction "
                "note (docs/governance/identifier-rekey-note.md; OD-20 / "
                "A-0.4 = a). Recorded, never blocking."
            ),
        },
        "email_shape": {
            "distinct_tokens": len(email_tokens),
            "classes": dict(sorted(email_classes.items())),
            "unclassified_remaining": remaining_unclassified,
            "dispositioned": dict(sorted(email_dispositioned.items())),
        },
        "disposition": disposition,
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=None, help="git work-tree root (default: repo toplevel)")
    ap.add_argument(
        "--json", dest="json_path", default=None, help="write the sig.history-scan/1 report here"
    )
    ap.add_argument(
        "--tokens-out",
        default=None,
        help="write the distinct e-mail-shaped tokens here for review — point it at a "
        "gitignored path; the output is never committed",
    )
    ap.add_argument(
        "--handle-list",
        default=None,
        help="explicit handle-list path (default: the gitignored "
        f"{HANDLE_LIST_REL}; absent → the handle class is recorded skipped)",
    )
    ap.add_argument(
        "--dispositions",
        default=None,
        help="a sig.history-scan-dispositions/1 TOML file mapping finding keys to "
        "exempt|disclosed with justification (stale entries fail the report)",
    )
    ap.add_argument(
        "--generated-at",
        default=None,
        help="ISO timestamp stamped on the report (default: `date -u` now)",
    )
    ap.add_argument(
        "--namespaces",
        default=",".join(DEFAULT_REF_NAMESPACES),
        help="comma-separated ref namespaces to scan",
    )
    args = ap.parse_args(argv)

    root = Path(args.root) if args.root else None
    if root is None:
        proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
        )
        if proc.returncode != 0:
            print("history_scan: not inside a git work tree", file=sys.stderr)
            return 2
        root = Path(proc.stdout.strip())

    namespaces = tuple(n for n in args.namespaces.split(",") if n)
    generated_at = args.generated_at
    if not generated_at:
        import datetime

        generated_at = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    token_sink: dict[str, str] | None = {} if args.tokens_out else None
    try:
        report = scan_history(
            root,
            namespaces=namespaces,
            handle_path=Path(args.handle_list) if args.handle_list else None,
            dispositions_path=Path(args.dispositions) if args.dispositions else None,
            generated_at=generated_at,
            token_sink=token_sink,
        )
    except RuntimeError as exc:
        print(f"history_scan: {exc}", file=sys.stderr)
        return 2

    if args.tokens_out and token_sink is not None:
        # Reviewer-only dump — the caller points this at a gitignored path.
        out = Path(args.tokens_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as fh:
            for tok, klass in sorted(token_sink.items()):
                fh.write(f"{klass}\t{tok}\n")
        print(
            f"history_scan: {len(token_sink)} distinct e-mail tokens -> {out} "
            "(reviewer-only; never commit)",
            file=sys.stderr,
        )

    if args.json_path:
        out = Path(args.json_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")

    scope = report["scope"]
    print(
        f"history_scan: {scope['commits']} commits / {scope['blobs_scanned']} blobs "
        f"/ {scope['bytes_scanned']} bytes over {scope['refs']} refs "
        f"({', '.join(scope['ref_namespaces'])})",
        file=sys.stderr,
    )
    n_findings = sum(f["count"] for f in report["findings"].values())
    if report["disposition"] == "clean":
        print(
            f"history_scan: CLEAN — 0 undisposed findings "
            f"(disclosed: {report['disclosed']['handle_token_hits']} handle hits; "
            f"{report['email_shape']['distinct_tokens']} e-mail tokens all classified "
            "or dispositioned).",
            file=sys.stderr,
        )
        return 0
    print(
        f"history_scan: FINDINGS — {n_findings} undisposed rule hit(s); remediate or "
        "disclose before the archival submission (never echoes content).",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
