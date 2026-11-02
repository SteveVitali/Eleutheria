# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The search benchmark harness (P36.32 / K3 SRCH-02 — ``sig.search-benchmark/1``).

Runs a query set through :class:`exports.search_query_v2.SearchEngineV2`
and reports the SIG-SRCH-013 metrics: top-3 success on answerable
queries, mean reciprocal rank, the zero-result rate, and the
misleading-top-hit count on the honest set — every measured figure
reported as measured, latency percentiles included (SIG-ENG-042).

Modes:

* ``dev`` — a committed development query set
  (``sig.search-benchmark-queries/1``) over the fixture the run provides.
  Dev expectations are agent-authored and stay labelled so (K3 §9: "agent-
  written expectations, not human relevance labels").
* ``held-out`` — the P36.79 sealed set (D-K3-7 [B-28] = 'Separate agent,
  labelled'). This context reads the committed
  ``sig.held-out-relevance-descriptor/1`` — the digest — and NEVER the
  set: ``verify_held_out_blob`` answers only "do these bytes hash to the
  committed sha256"; the metric surface carries the estimand label
  ``agent-authored held-out set; not independent`` verbatim (SIG-CONF-012,
  TS-20 — always, never elided).
* ``release`` — the dev set run against a built release directory
  (``SearchEngineV2.open_release`` — SIG-SRCH-011 verification first).
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from .search_query_v2 import SearchEngineV2, SearchParamsV2

#: The report contract this harness emits.
SEARCH_BENCHMARK_SCHEMA = "sig.search-benchmark/1"
#: The query-set file contract (committed dev sets + the acceptance row's
#: converted held-out rows).
QUERY_SET_SCHEMA = "sig.search-benchmark-queries/1"
#: The committed digest the held-out mode verifies against — the ONLY
#: reference this context may read (B-28 = b; the set itself never lands).
HELD_OUT_DESCRIPTOR_RELPATH = "docs/build/reports/p36.79-held-out-relevance/descriptor.json"
HELD_OUT_DESCRIPTOR_SCHEMA = "sig.held-out-relevance-descriptor/1"
#: The estimand label carried on every held-out metric surface, verbatim
#: (TS-20 — always; SIG-CONF-012).
HELD_OUT_METRIC_LABEL = "agent-authored held-out set; not independent"
DEV_METRIC_LABEL = "agent-authored development set; not independent"
TOP_K = 3
#: Match reasons a top-3 card may carry on an honest ("none expected")
#: query without counting as a misleading top hit — an alias card that
#: says "SIG's release names no record for this" is the honest answer.
HONEST_MATCHED_DEFAULT = ("alias", "alias target")


def engine_params(q: str, *, limit: int = 10) -> SearchParamsV2:
    """A plain text-query request (the benchmark + the simplest callers)."""
    from .search_index import normalize_query

    return SearchParamsV2(
        q_raw=q,
        q_tokens=normalize_query(q) if q and q.strip() else [],
        types=None,
        filters={},
        limit=limit,
        group=None,
        cursor=None,
    )


class SearchBenchmarkError(Exception):
    """A benchmark-harness failure — machine code + detail."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


# --------------------------------------------------------------------------- #
# Query sets + the sealed-set digest                                          #
# --------------------------------------------------------------------------- #


def load_query_set(path: Path | str) -> dict[str, Any]:
    """Load + validate a ``sig.search-benchmark-queries/1`` file —
    fail closed (SIG-ENG-042): malformed rows are an error, never skipped."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if doc.get("schema") != QUERY_SET_SCHEMA:
        raise SearchBenchmarkError("query_set", f"{path}: schema is not {QUERY_SET_SCHEMA}")
    rows = doc.get("queries")
    if not isinstance(rows, list) or not rows:
        raise SearchBenchmarkError("query_set", f"{path}: no queries rows")
    failures: list[str] = []
    seen: set[str] = set()
    for i, r in enumerate(rows):
        if not isinstance(r, dict):
            failures.append(f"queries[{i}]: not an object")
            continue
        rid = str(r.get("id") or "")
        if not rid or rid in seen:
            failures.append(f"queries[{i}]: missing/duplicate id {rid!r}")
        seen.add(rid)
        if not str(r.get("q") or "").strip():
            failures.append(f"{rid}: empty q")
        j = r.get("judgement")
        if j not in ("top3", "honest"):
            failures.append(f"{rid}: judgement must be top3|honest")
        exp = r.get("expected")
        if not isinstance(exp, dict):
            failures.append(f"{rid}: expected must be an object")
        elif j == "top3" and not (
            str(exp.get("match") or "") or str(exp.get("suggestion_of") or "")
        ):
            failures.append(f"{rid}: top3 rows need expected.match")
    if failures:
        raise SearchBenchmarkError("query_set", f"{path}: " + "; ".join(failures[:8]))
    return doc


def load_held_out_descriptor(path: Path | str | None = None) -> dict[str, Any]:
    """The committed ``sig.held-out-relevance-descriptor/1`` — the digest
    + reader rule, the ONLY held-out surface this module ever reads."""
    p = Path(path) if path is not None else Path(HELD_OUT_DESCRIPTOR_RELPATH)
    doc = json.loads(p.read_text(encoding="utf-8"))
    if doc.get("schema") != HELD_OUT_DESCRIPTOR_SCHEMA:
        raise SearchBenchmarkError(
            "held_out_descriptor", f"{p}: schema is not {HELD_OUT_DESCRIPTOR_SCHEMA}"
        )
    if doc.get("label") != HELD_OUT_METRIC_LABEL:
        raise SearchBenchmarkError(
            "held_out_descriptor",
            f"{p}: label drifted from {HELD_OUT_METRIC_LABEL!r}",
        )
    if not str(doc.get("sha256") or "") or len(str(doc["sha256"])) != 64:
        raise SearchBenchmarkError("held_out_descriptor", f"{p}: missing sha256")
    return doc


def verify_held_out_blob(blob: bytes, descriptor: Mapping[str, Any]) -> dict[str, Any]:
    """sha256-verify held-out set bytes against the committed descriptor.

    Returns the parsed set document ONLY when the digest matches — the
    digest check is the seal (a mismatched blob is refused, never read).
    """
    digest = hashlib.sha256(blob).hexdigest()
    if digest != str(descriptor["sha256"]):
        raise SearchBenchmarkError(
            "held_out_digest_mismatch",
            "the supplied bytes do not match the committed held-out "
            "descriptor sha256 — refused, never read",
        )
    try:
        doc = json.loads(blob.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SearchBenchmarkError("held_out_malformed", "the held-out object is not JSON") from exc
    if str(doc.get("set_id") or "") != str(descriptor.get("set_id") or ""):
        raise SearchBenchmarkError(
            "held_out_set_id", "set_id does not match the committed descriptor"
        )
    return doc


def adapt_held_out_queries(doc: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Map sealed-set rows onto benchmark queries — field names per the
    emitted contract (id/q/kind/judgement/expected/answerable)."""
    queries: list[dict[str, Any]] = []
    for row in doc.get("queries") or []:
        exp = row.get("expected") or {}
        q: dict[str, Any] = {
            "id": str(row.get("id") or ""),
            "kind": str(row.get("kind") or ""),
            "q": str(row.get("query") or ""),
            "judgement": str(row.get("judgement") or ""),
            "answerable": bool(row.get("answerable")),
            "expected": {
                "type": str(exp.get("type") or ""),
                "match": str(exp.get("match") or ""),
                "allow": list(exp.get("allow") or []),
            },
        }
        if exp.get("expects_suggestion"):
            q["expects_suggestion"] = True
        queries.append(q)
    return queries


# --------------------------------------------------------------------------- #
# Judging                                                                     #
# --------------------------------------------------------------------------- #


def flatten_results(resp: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The response in presentation order: top, then sections, then the
    licence groups in order (collapsed groups contribute nothing)."""
    out: list[dict[str, Any]] = list(resp.get("top") or [])
    for sec in resp.get("sections") or []:
        out.extend(sec.get("results") or [])
    for g in resp.get("record_groups") or []:
        out.extend(g.get("results") or [])
    return out


def _card_texts(card: Mapping[str, Any]) -> list[str]:
    vals = [
        card.get("doc_id"),
        card.get("record_key"),
        card.get("entity_id"),
        card.get("name"),
        card.get("href"),
        card.get("key"),
        card.get("jkey"),
        card.get("source_id"),
    ]
    target = card.get("target")
    if isinstance(target, dict):
        vals += [target.get("doc_id"), target.get("name"), target.get("href")]
    return [str(v).casefold() for v in vals if v]


def judge_query(resp: Mapping[str, Any], query: Mapping[str, Any]) -> dict[str, Any]:
    """Judge one response: rank of the expected answer, hit@k, and for an
    honest query whether a misleading top hit surfaced."""
    flat = flatten_results(resp)
    exp = query.get("expected") or {}
    want_type = str(exp.get("type") or "")
    want_match = str(exp.get("match") or "").casefold()
    rank = None
    for i, card in enumerate(flat[:TOP_K], 1):
        if want_type and want_type != "none" and str(card.get("type")) != want_type:
            continue
        if want_match and not any(want_match in t for t in _card_texts(card)):
            continue
        if want_type == "none":
            continue
        rank = i
        break
    judgement = str(query.get("judgement") or "")
    misleading = False
    if judgement == "honest" or want_type == "none":
        allow = set(exp.get("allow") or ()) | set(HONEST_MATCHED_DEFAULT)
        misleading = any(str(card.get("matched") or "") not in allow for card in flat[:TOP_K])
    return {
        "rank": rank,
        "hit_at_k": rank is not None,
        "misleading_top_hit": misleading,
        "results_returned": len(flat),
        "suggestion": (resp.get("query") or {}).get("suggestion"),
    }


# --------------------------------------------------------------------------- #
# The run                                                                     #
# --------------------------------------------------------------------------- #


def _pctl(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    xs = sorted(xs)
    k = min(len(xs) - 1, max(0, round((p / 100.0) * (len(xs) - 1))))
    return xs[int(k)]


def run_benchmark(
    search_fn: Callable[[str], Mapping[str, Any]],
    queries: Sequence[Mapping[str, Any]],
    *,
    mode: str,
    set_id: str | None = None,
    release: Mapping[str, Any] | None = None,
    held_out_descriptor: Mapping[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Run a query set through ``search_fn`` (query string → a
    ``sig.search-results/2`` response) and emit the labelled
    ``sig.search-benchmark/1`` report. Latencies are measured; the
    estimand label is always present, never elided (TS-20)."""
    if mode not in ("dev", "held-out", "release"):
        raise SearchBenchmarkError("mode", f"unknown benchmark mode {mode!r}")
    rows: list[dict[str, Any]] = []
    lat: list[float] = []
    hits = 0
    answerable = 0
    rr_sum = 0.0
    zero_results = 0
    misleading = 0
    per_kind: dict[str, dict[str, int]] = {}
    for q in queries:
        t0 = time.monotonic()
        resp = search_fn(str(q.get("q") or ""))
        ms = (time.monotonic() - t0) * 1000.0
        lat.append(ms)
        judged = judge_query(resp, q)
        is_answerable = bool(q.get("answerable", q.get("judgement") == "top3"))
        kind = str(q.get("kind") or "")
        k = per_kind.setdefault(kind, {"queries": 0, "hits": 0, "misleading": 0, "zero": 0})
        k["queries"] += 1
        if is_answerable:
            answerable += 1
            if judged["hit_at_k"]:
                hits += 1
                k["hits"] += 1
                rr_sum += 1.0 / float(judged["rank"])
            else:
                k["misleading"] += 0  # answered-later class, not misleading
        if judged["misleading_top_hit"]:
            misleading += 1
            k["misleading"] += 1
        if judged["results_returned"] == 0:
            zero_results += 1
            k["zero"] += 1
        rows.append(
            {
                "id": str(q.get("id") or ""),
                "kind": kind,
                "judgement": str(q.get("judgement") or ""),
                "answerable": is_answerable,
                "rank": judged["rank"],
                "hit_at_k": judged["hit_at_k"],
                "misleading_top_hit": judged["misleading_top_hit"],
                "results_returned": judged["results_returned"],
                "suggestion": judged["suggestion"],
                "latency_ms": round(ms, 3),
            }
        )
    label = HELD_OUT_METRIC_LABEL if mode == "held-out" else DEV_METRIC_LABEL
    report: dict[str, Any] = {
        "schema": SEARCH_BENCHMARK_SCHEMA,
        "mode": mode,
        "set_id": set_id,
        "estimand_label": label,
        "release": dict(release) if release else None,
        "generated_at": generated_at,
        "summary": {
            "queries": len(rows),
            "answerable": answerable,
            "top3_success": hits,
            "top3_success_rate": (hits / answerable) if answerable else None,
            "mrr": (rr_sum / answerable) if answerable else None,
            "zero_result_rate": (zero_results / len(rows)) if rows else None,
            "misleading_top_hits": misleading,
            "latency_ms": {
                "p50": round(_pctl(lat, 50), 3),
                "p95": round(_pctl(lat, 95), 3),
                "max": round(max(lat) if lat else 0.0, 3),
            },
            "per_kind": {k: per_kind[k] for k in sorted(per_kind)},
        },
        "queries": rows,
    }
    if mode == "held-out":
        desc = dict(held_out_descriptor or {})
        report["held_out"] = {
            "descriptor": HELD_OUT_DESCRIPTOR_RELPATH,
            "descriptor_sha256": desc.get("sha256"),
            "set_id": desc.get("set_id"),
            "reader": desc.get("reader"),
            "label": HELD_OUT_METRIC_LABEL,
        }
    return report


def run_release_benchmark(
    release_dir: Path | str,
    query_set: Mapping[str, Any],
    *,
    mode: str = "release",
    generated_at: str | None = None,
) -> dict[str, Any]:
    """The release-mode run: open the built release through the verified
    path (SIG-SRCH-011 — a drifted artifact fails before serving) and run
    the query set through ``SearchEngineV2.search``."""
    engine = SearchEngineV2.open_release(release_dir)
    try:

        def _go(q: str) -> Mapping[str, Any]:
            return engine.search(engine_params(q))

        return run_benchmark(
            _go,
            list(query_set.get("queries") or []),
            mode=mode,
            set_id=str(query_set.get("set_id") or ""),
            release={
                "publication_id": engine.publication_id,
                "label": engine.release_label,
                "as_of_world": engine.as_of_world,
            },
            generated_at=generated_at,
        )
    finally:
        engine.close()
