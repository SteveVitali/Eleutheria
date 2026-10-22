# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The agent review lane (P35.48, SIG-CONF-002; ADR-152/ADR-153; gate Q-L3-4).

A labelled, never-gating review lane: a seeded weekly stratified sample
(50 sites + 30 edges) is drawn deterministically, every item is judged by
**two blind same-family agent contexts** (L3 §4.3; gate B-31 = "no" to
frontier cross-family review), and the verdicts append as
``sig.agent-review/1`` JSONL records under
``docs/build/reports/agent-review/``.

The lane's own rules, by construction:

* **Never a human label.** Every record carries ``labeller_kind: "agent"``
  with the model id, prompt digest, context id, and seed. Records append to
  the agent-review prefix — never a ``human_eval_*`` table (ADR-128); the
  human-evaluation machinery is a separate schema with reviewer-role gates.
* **Never a gate.** Nothing in this module is read by an auto-write gate,
  eval-status promotion, or a release gate (SIG-CONF-003: B3/B4 evidence may
  never gate). Agreement is recorded as ``agent_consensus`` — *never*
  "correct". Agent–agent Cohen's κ reports "agreement between two AI runs",
  never accuracy: two runs of the same model family share blind spots, so
  agreement is correlated by construction (B-31).
* **Disagreement routes, it never decides.** Two differing verdicts on one
  item mint a ``sig.maintainer-queue-entry/1`` row for the §4.4 S4 maintainer
  queue — a queue entry, not a decision.
* **Blind by construction.** A packet item carries ``item_id``, ``kind``,
  ``stratum``, ``question``, and the item's ``evidence`` only; any evidence
  key hinting at matcher internals or earlier labels (tier, score, weight,
  cluster, label, verdict, decision, model, prompt, context, partition,
  answer, expected, truth, gold, history, …) makes :func:`build_packet`
  refuse the item. The two prompt framings are different wordings of the
  same question; neither embeds the other's verdict.
* **Partition-reserved items refuse.** An item carrying a ``partition`` in
  :data:`RESERVED_PARTITIONS` (the partitions a future independent/B5
  campaign reserves — SIG-EVAL-001) is excluded from every candidate set;
  drawing one raises, defence in depth.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

#: The committed JSONL label record family this module writes.
SCHEMA_VERSION = "sig.agent-review/1"
#: The drawn weekly packet artifact.
PACKET_SCHEMA_VERSION = "sig.agent-review-packet/1"
#: The S4 maintainer-queue entry a disagreement mints.
QUEUE_SCHEMA_VERSION = "sig.maintainer-queue-entry/1"
#: The per-week lane summary (consensus, κ, queue appends).
REPORT_SCHEMA_VERSION = "sig.agent-review-report/1"
#: The sampled corpus a packet draws over.
CORPUS_SCHEMA_VERSION = "sig.agent-review-corpus/1"

#: Where appended records live — a committed, append-only records dir, never
#: a ``human_eval_*`` table (ADR-128).
LANE_DIR = Path("docs/build/reports/agent-review")

KIND_SITE = "site"
KIND_EDGE = "edge"
KINDS = (KIND_SITE, KIND_EDGE)

#: The weekly sample design (L3 §4.3): the named strata dominate, and the
#: fixed simple-random block gives every corpus item a known nonzero draw
#: share. Quotas are declared constants — part of the lane contract.
SAMPLE_SITES = 50
SAMPLE_EDGES = 30
SIMPLE_RANDOM = "simple_random"
SITE_STRATUM_QUOTAS: dict[str, int] = {
    "new_sources": 15,
    "possible_duplicates": 15,
    "dossier_delta_sites": 10,
    SIMPLE_RANDOM: 10,
}
EDGE_STRATUM_QUOTAS: dict[str, int] = {
    "operator_edges": 10,
    "procurement_edges": 10,
    SIMPLE_RANDOM: 10,
}
STRATUM_QUOTAS: dict[str, dict[str, int]] = {
    KIND_SITE: SITE_STRATUM_QUOTAS,
    KIND_EDGE: EDGE_STRATUM_QUOTAS,
}
KIND_TARGET = {KIND_SITE: SAMPLE_SITES, KIND_EDGE: SAMPLE_EDGES}

#: The judgment questions: sites answer record fidelity (L2 C14 — fidelity,
#: type, role, and date correctness); edges answer topical relevance
#: (GQ-22's population — surveillance-infrastructure records).
QUESTION_BY_KIND = {KIND_SITE: "site_fidelity", KIND_EDGE: "edge_relevance"}
VERDICT_VOCAB: dict[str, tuple[str, ...]] = {
    "site_fidelity": ("faithful", "error", "unsure"),
    "edge_relevance": ("relevant", "off_topic", "unsure"),
}
#: Defect tags a ``site_fidelity`` error verdict may carry (L2 C14).
DEFECT_VOCAB = ("fidelity", "type", "role", "date")

#: The two blind context ids — closed; a third context is a schema violation.
CONTEXT_IDS = ("a", "b")

#: Partitions an independent (B5) human-evaluation campaign reserves
#: (SIG-EVAL-001; resolution.human_eval.PARTITIONS). An item in one is never
#: agent-labelled by this lane — permitted uses allow training/development
#: only.
RESERVED_PARTITIONS = ("calibration", "pilot", "sealed_final")

#: Evidence keys a blind packet item may never carry (any path segment of a
#: key, lower-cased). These name matcher internals, earlier labels, or the
#: other verdict — anything that would unblind a context.
FORBIDDEN_EVIDENCE_TOKENS = frozenset(
    {
        "tier",
        "score",
        "weight",
        "weights",
        "cluster",
        "label",
        "labels",
        "labelled",
        "verdict",
        "verdicts",
        "decision",
        "decisions",
        "prediction",
        "predicted",
        "confidence",
        "estimand",
        "model",
        "prompt",
        "context",
        "partition",
        "review",
        "reviewer",
        "answer",
        "expected",
        "truth",
        "gold",
        "history",
        "human",
        "kappa",
        "correct",
        "accuracy",
    }
)

#: The packet item's closed key set — the whole blind payload a context sees.
_PACKET_ITEM_KEYS = frozenset({"item_id", "kind", "stratum", "question", "evidence"})

#: The closed record key set for ``sig.agent-review/1``.
_RECORD_KEYS = frozenset(
    {
        "version",
        "record_id",
        "packet_id",
        "packet_digest",
        "week",
        "seed",
        "corpus_digest",
        "item_id",
        "item_kind",
        "stratum",
        "question",
        "labeller_kind",
        "model_id",
        "prompt_digest",
        "context_id",
        "verdict",
        "defects",
        "rationale",
        "labelled_at",
        "basis_class",
        "basis_label",
    }
)

#: The two prompt framings — different wordings of the same question, so a
#: wording artifact shows up as an honest disagreement, never as agreement
#: forced by one phrasing. The evidence block is the item's evidence only.
PROMPT_TEMPLATES: dict[str, dict[str, str]] = {
    "site_fidelity": {
        "a": (
            "You are auditing one surveillance-infrastructure site record for "
            "data quality. Below is the record's evidence only.\n\n"
            "EVIDENCE:\n{evidence}\n\n"
            "Does the parsed record faithfully reproduce the upstream source "
            "(fidelity, type, role and date correct)? Answer with exactly one "
            "verdict: faithful | error | unsure. On error, also name the "
            "defect kinds from: fidelity, type, role, date."
        ),
        "b": (
            "Independent record-QA check. The evidence for one site record "
            "follows — nothing else is given.\n\n"
            "EVIDENCE:\n{evidence}\n\n"
            "Judge whether the record's parsed fields match what the cited "
            "upstream text actually says. Verdict (pick one): faithful | "
            "error | unsure. If the answer is error, list which of these "
            "went wrong: fidelity, type, role, date."
        ),
    },
    "edge_relevance": {
        "a": (
            "You are auditing one sampled record for topical relevance to "
            "surveillance infrastructure. Below is the record's evidence "
            "only.\n\n"
            "EVIDENCE:\n{evidence}\n\n"
            "Is this record about surveillance infrastructure (cameras, "
            "monitoring systems, their operators, procurement or siting)? "
            "Answer with exactly one verdict: relevant | off_topic | unsure."
        ),
        "b": (
            "Topic check — one record. The evidence follows; nothing else "
            "is given.\n\n"
            "EVIDENCE:\n{evidence}\n\n"
            "Decide whether the record concerns surveillance infrastructure "
            "(any public-space sensing/monitoring capability or its "
            "operation/procurement). Verdict (pick one): relevant | "
            "off_topic | unsure."
        ),
    },
}

_WEEK_RE = re.compile(r"^\d{4}-W\d{2}$")
_TOKEN_SPLIT = re.compile(r"[^a-z0-9]+")


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def universe_digest(universe: Mapping[str, Any]) -> str:
    """The corpus identity a packet binds — a digest of the item list's
    canonical form (ids, kinds, strata, evidence). Same bytes in, same digest."""
    items = sorted(
        universe.get("items", ()),
        key=lambda i: str(i.get("item_id", "")),
    )
    return _sha(_canonical(items))


def reserved_item_ids(rows: Iterable[Mapping[str, Any]]) -> frozenset[str]:
    """The item ids a partition reservation covers.

    ``rows`` are partition-bearing mappings (e.g. the human_eval sample
    table's ``sample_id``/``pair_id``/``left_ref``/``right_ref`` + ``partition``
    shape, or any ``item_id`` + ``partition`` mapping). An id whose partition
    is in :data:`RESERVED_PARTITIONS` may never carry an agent label.
    """
    ids: set[str] = set()
    for row in rows:
        partition = str(row.get("partition", ""))
        if partition not in RESERVED_PARTITIONS:
            continue
        for key in ("item_id", "sample_id", "pair_id", "left_ref", "right_ref"):
            value = row.get(key)
            if value:
                ids.add(str(value))
    return frozenset(ids)


def _key_tokens(key: str) -> set[str]:
    return {t for t in _TOKEN_SPLIT.split(key.lower()) if t}


def _check_blind(value: Any, where: str) -> list[str]:
    """Forbidden-key hits under an evidence payload."""
    hits: list[str] = []
    if isinstance(value, Mapping):
        for key, sub in value.items():
            tokens = _key_tokens(str(key))
            bad = sorted(tokens & FORBIDDEN_EVIDENCE_TOKENS)
            if bad:
                hits.append(f"{where}.{key}: forbidden key tokens {bad}")
            hits.extend(_check_blind(sub, f"{where}.{key}"))
    elif isinstance(value, list):
        for i, sub in enumerate(value):
            hits.extend(_check_blind(sub, f"{where}[{i}]"))
    return hits


def assert_blind_item(item: Mapping[str, Any]) -> None:
    """Refuse a packet item that could unblind a context.

    The item must carry exactly the packet keys, and its ``evidence`` payload
    must contain no forbidden key at any depth (matcher internals, earlier
    labels, the other verdict). Raises ``ValueError`` listing every hit.
    """
    extra = set(item) - _PACKET_ITEM_KEYS
    missing = _PACKET_ITEM_KEYS - set(item)
    errors = []
    if missing:
        errors.append(f"missing packet keys {sorted(missing)}")
    if extra:
        errors.append(f"forbidden packet keys {sorted(extra)}")
    errors.extend(_check_blind(item.get("evidence", {}), "evidence"))
    if errors:
        raise ValueError(f"item {item.get('item_id', '?')!r} is not blind: " + "; ".join(errors))


def _universe_items(universe: Mapping[str, Any]) -> list[dict[str, Any]]:
    items = universe.get("items")
    if not isinstance(items, list):
        raise ValueError("universe must carry an 'items' list")
    for it in items:
        for key in ("item_id", "kind", "evidence"):
            if key not in it:
                raise ValueError(f"universe item missing {key!r}: {it!r}")
        if it["kind"] not in KINDS:
            raise ValueError(f"universe item kind must be one of {KINDS}: {it!r}")
    return items


def build_packet(
    universe: Mapping[str, Any],
    *,
    seed: str | int,
    week: str,
    reserved_ids: Iterable[str] = (),
) -> dict[str, Any]:
    """Draw the weekly stratified sample — deterministic on (seed, corpus).

    Same ``seed`` + same corpus content (``universe_digest``) → the same
    packet; either changing yields a different draw. Reserved-partition ids
    (``reserved_ids`` plus any item's own ``partition`` in
    :data:`RESERVED_PARTITIONS`) are excluded from every candidate set and a
    drawn reserved id raises — the lane never labels an item a B5 campaign
    has claimed.
    """
    if not _WEEK_RE.match(week):
        raise ValueError(f"week must be ISO 'YYYY-Www', got {week!r}")
    items = _universe_items(universe)
    corpus = universe_digest(universe)
    capture_kind = str(universe.get("capture_kind", "unspecified"))

    reserved = {str(i) for i in reserved_ids}
    for it in items:
        if str(it.get("partition", "")) in RESERVED_PARTITIONS:
            reserved.add(str(it["item_id"]))

    packet_items: list[dict[str, Any]] = []
    draws: dict[str, dict[str, list[str]]] = {}
    for kind in KINDS:
        kind_items = [
            it for it in items if it["kind"] == kind and str(it["item_id"]) not in reserved
        ]
        by_id = {str(it["item_id"]): it for it in kind_items}
        quotas = STRATUM_QUOTAS[kind]
        target = KIND_TARGET[kind]
        drawn: list[str] = []
        strata_draws: dict[str, list[str]] = {}
        rngs = {stratum: random.Random(f"{seed}:{corpus}:{kind}:{stratum}") for stratum in quotas}

        def candidates(
            stratum: str,
            _items: list[dict[str, Any]] = kind_items,
            _by_id: dict[str, dict[str, Any]] = by_id,
            _drawn: list[str] = drawn,
        ) -> list[str]:
            if stratum == SIMPLE_RANDOM:
                return sorted(i for i in _by_id if i not in _drawn)
            return sorted(
                str(it["item_id"])
                for it in _items
                if stratum in (it.get("strata") or ()) and str(it["item_id"]) not in _drawn
            )

        # First pass: fill each stratum's declared quota.
        for stratum, quota in quotas.items():
            pool = candidates(stratum)
            take = min(quota, len(pool))
            picked = rngs[stratum].sample(pool, take) if take else []
            strata_draws[stratum] = list(picked)
            drawn.extend(picked)
        # Top-up: a stratum that could not fill its quota yields headroom —
        # redistributed deterministically in spec order until the union
        # reaches the target or the corpus is exhausted. A corpus that cannot
        # reach the target records the honest drawn count (never padded).
        for stratum in quotas:
            while len(drawn) < target:
                pool = candidates(stratum)
                if not pool:
                    break
                take = min(target - len(drawn), len(pool))
                picked = rngs[stratum].sample(pool, take)
                strata_draws[stratum].extend(picked)
                drawn.extend(picked)
            if len(drawn) >= target:
                break

        first_stratum: dict[str, str] = {}
        for stratum, ids in strata_draws.items():
            for i in ids:
                first_stratum.setdefault(i, stratum)
        draws[kind] = {s: list(ids) for s, ids in strata_draws.items()}
        for item_id in drawn:
            src = by_id[item_id]
            packet_items.append(
                {
                    "item_id": item_id,
                    "kind": kind,
                    "stratum": first_stratum[item_id],
                    "question": QUESTION_BY_KIND[kind],
                    "evidence": src["evidence"],
                }
            )

    packet: dict[str, Any] = {
        "version": PACKET_SCHEMA_VERSION,
        "week": week,
        "seed": str(seed),
        "corpus_digest": corpus,
        "capture_kind": capture_kind,
        "design": {
            "sites": SAMPLE_SITES,
            "edges": SAMPLE_EDGES,
            "stratum_quotas": STRATUM_QUOTAS,
            "simple_random_block": True,
        },
        "strata_draws": draws,
        "n_sites": sum(1 for i in packet_items if i["kind"] == KIND_SITE),
        "n_edges": sum(1 for i in packet_items if i["kind"] == KIND_EDGE),
        "items": packet_items,
    }
    # Defence in depth: blindness and the reservation guard are enforced on
    # the emitted packet itself, not only on the inputs.
    for item in packet["items"]:
        assert_blind_item(item)
        if item["item_id"] in reserved:
            raise ValueError(
                f"reserved-partition item {item['item_id']!r} may never be "
                f"agent-labelled (SIG-EVAL-001)"
            )
    packet_digest = _sha(_canonical(packet))
    packet["packet_digest"] = packet_digest
    packet["packet_id"] = "arp-" + packet_digest.split(":", 1)[1][:16]
    return packet


def build_labelling_prompts(packet: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    """Per-item prompt text for the two blind contexts.

    Each item yields ``{"a": ..., "b": ...}`` — two different wordings of the
    item's question over the same evidence. A prompt names neither the other
    verdict nor any packet metadata (stratum, seed, corpus): the context sees
    the question and the evidence only.
    """
    prompts: dict[str, dict[str, str]] = {}
    for item in packet["items"]:
        assert_blind_item(item)
        templates = PROMPT_TEMPLATES[item["question"]]
        evidence = json.dumps(item["evidence"], indent=2, sort_keys=True, ensure_ascii=True)
        prompts[str(item["item_id"])] = {
            ctx: templates[ctx].format(evidence=evidence) for ctx in CONTEXT_IDS
        }
    return prompts


def prompt_digest(prompt: str) -> str:
    return _sha(prompt)


def make_record(
    packet: Mapping[str, Any],
    item: Mapping[str, Any],
    *,
    context_id: str,
    verdict: str,
    model_id: str,
    labelled_at: str,
    rationale: str = "",
    defects: Sequence[str] = (),
) -> dict[str, Any]:
    """One ``sig.agent-review/1`` verdict record.

    ``context_id`` is the blind lane ("a" or "b"); ``labelled_at`` is an
    ISO-UTC stamp the caller takes from the clock. The record carries the
    full provenance the lane contract names — model id, prompt digest,
    context id, seed, corpus digest — and never a human identity.
    """
    question = item["question"]
    record = {
        "version": SCHEMA_VERSION,
        "packet_id": packet["packet_id"],
        "packet_digest": packet["packet_digest"],
        "week": packet["week"],
        "seed": packet["seed"],
        "corpus_digest": packet["corpus_digest"],
        "item_id": item["item_id"],
        "item_kind": item["kind"],
        "stratum": item["stratum"],
        "question": question,
        "labeller_kind": "agent",
        "model_id": model_id,
        "prompt_digest": prompt_digest(
            build_labelling_prompts({"items": [item]})[item["item_id"]][context_id]
        )
        if context_id in CONTEXT_IDS
        else "",
        "context_id": context_id,
        "verdict": verdict,
        "defects": sorted(set(defects)),
        "rationale": rationale,
        "labelled_at": labelled_at,
        "basis_class": "B3",
        "basis_label": "agent review",
    }
    core = {
        k: record[k]
        for k in (
            "packet_id",
            "item_id",
            "context_id",
            "verdict",
            "model_id",
            "prompt_digest",
            "labelled_at",
        )
    }
    record["record_id"] = "ar-" + _sha(_canonical(core)).split(":", 1)[1][:16]
    errors = validate_record(record)
    if errors:
        raise ValueError(f"invalid agent-review record: {errors}")
    return record


def validate_record(record: Mapping[str, Any]) -> list[str]:
    """The ``sig.agent-review/1`` schema — a closed key set. Returns the
    violation list; empty means valid."""
    errors: list[str] = []
    if record.get("version") != SCHEMA_VERSION:
        errors.append(f"version must be {SCHEMA_VERSION!r}")
    missing = {
        "record_id",
        "packet_id",
        "packet_digest",
        "week",
        "seed",
        "corpus_digest",
        "item_id",
        "item_kind",
        "stratum",
        "question",
        "labeller_kind",
        "model_id",
        "prompt_digest",
        "context_id",
        "verdict",
        "labelled_at",
        "basis_class",
        "basis_label",
    } - set(record)
    if missing:
        errors.append(f"missing keys {sorted(missing)}")
    extra = set(record) - _RECORD_KEYS
    if extra:
        errors.append(f"unknown keys {sorted(extra)}")
    if record.get("labeller_kind") != "agent":
        errors.append("labeller_kind must be 'agent' — this lane never impersonates a human")
    if record.get("basis_class") != "B3":
        errors.append("basis_class must be 'B3' — agent review may never masquerade as B5")
    if record.get("basis_label") != "agent review":
        errors.append("basis_label must be 'agent review'")
    kind = record.get("item_kind")
    if kind not in KINDS:
        errors.append(f"item_kind must be one of {KINDS}")
    question = record.get("question")
    if kind in KINDS and question != QUESTION_BY_KIND.get(kind):
        errors.append(f"question must be {QUESTION_BY_KIND.get(kind)!r} for kind {kind!r}")
    if question in VERDICT_VOCAB and record.get("verdict") not in VERDICT_VOCAB[question]:
        errors.append(f"verdict must be one of {VERDICT_VOCAB[question]} for {question!r}")
    if record.get("context_id") not in CONTEXT_IDS:
        errors.append(f"context_id must be one of {CONTEXT_IDS}")
    if record.get("stratum") not in STRATUM_QUOTAS.get(str(kind), {}):
        errors.append(f"stratum must be a declared {kind!r} stratum")
    for key in ("model_id", "prompt_digest", "record_id", "packet_id", "corpus_digest"):
        if not str(record.get(key) or "").strip():
            errors.append(f"{key} must be a non-empty string")
    if record.get("prompt_digest") and not str(record["prompt_digest"]).startswith("sha256:"):
        errors.append("prompt_digest must be a sha256: digest")
    defects = record.get("defects", ())
    if defects and any(d not in DEFECT_VOCAB for d in defects):
        errors.append(f"defects must come from {DEFECT_VOCAB}")
    week = record.get("week")
    if week is not None and not _WEEK_RE.match(str(week)):
        errors.append("week must be ISO 'YYYY-Www'")
    return errors


def _existing_ids(path: Path, key: str) -> set[str]:
    ids: set[str] = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, Mapping) and row.get(key):
                ids.add(str(row[key]))
    return ids


def append_records(path: Path | str, records: Sequence[Mapping[str, Any]]) -> int:
    """Append validated ``sig.agent-review/1`` records to a JSONL file.

    Append-only and idempotent: every record validates first (any violation
    refuses the whole append), and a ``record_id`` already present is skipped
    rather than duplicated — a re-run of the same labelling appends nothing.
    Returns the number of lines appended.
    """
    path = Path(path)
    for record in records:
        errors = validate_record(record)
        if errors:
            raise ValueError(
                f"refusing to append invalid record {record.get('record_id')}: {errors}"
            )
    existing = _existing_ids(path, "record_id")
    path.parent.mkdir(parents=True, exist_ok=True)
    appended = 0
    with path.open("a", encoding="utf-8") as fh:
        for record in records:
            if str(record["record_id"]) in existing:
                continue
            fh.write(json.dumps(record, sort_keys=True, ensure_ascii=True) + "\n")
            existing.add(str(record["record_id"]))
            appended += 1
    return appended


def read_records(path: Path | str) -> list[dict[str, Any]]:
    """Read every ``sig.agent-review/1`` record in a JSONL file (validated)."""
    out: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if isinstance(row, Mapping) and row.get("version") == SCHEMA_VERSION:
            errors = validate_record(row)
            if errors:
                raise ValueError(f"stored record fails the schema: {errors}")
            out.append(dict(row))
    return out


def route_verdicts(
    packet: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    *,
    queued_at: str,
) -> dict[str, Any]:
    """Fold the two contexts' verdicts into consensus + S4 queue entries.

    Two equal verdicts → the item records ``agent_consensus`` (never
    "correct"). Two differing verdicts → a ``sig.maintainer-queue-entry/1``
    for the §4.4 S4 maintainer queue — a queue entry, *not* a decision; the
    maintainer decides, the lane only routes. An item with a single recorded
    verdict is honestly ``unpaired`` — neither consensus nor routed.
    """
    by_item: dict[str, list[Mapping[str, Any]]] = {}
    for record in records:
        errors = validate_record(record)
        if errors:
            raise ValueError(f"invalid record {record.get('record_id')}: {errors}")
        by_item.setdefault(str(record["item_id"]), []).append(record)

    consensus: dict[str, str] = {}
    unpaired: list[str] = []
    queue_entries: list[dict[str, Any]] = []
    for item in packet["items"]:
        item_id = str(item["item_id"])
        recs = sorted(by_item.get(item_id, ()), key=lambda r: str(r["context_id"]))
        verdicts = {str(r["verdict"]) for r in recs}
        if len(recs) < 2:
            unpaired.append(item_id)
            continue
        if len(verdicts) == 1:
            consensus[item_id] = recs[0]["verdict"]
            continue
        core = {"packet_id": packet["packet_id"], "item_id": item_id, "verdicts": sorted(verdicts)}
        entry = {
            "version": QUEUE_SCHEMA_VERSION,
            "entry_id": "mq-" + _sha(_canonical(core)).split(":", 1)[1][:16],
            "queue": "maintainer",
            "stratum": "S4",
            "reason": "agent_disagreement",
            "item_id": item_id,
            "item_kind": item["kind"],
            "question": item["question"],
            "packet_id": packet["packet_id"],
            "context_ids": [str(r["context_id"]) for r in recs],
            "verdicts": [str(r["verdict"]) for r in recs],
            "record_ids": [str(r["record_id"]) for r in recs],
            "queued_at": queued_at,
            "note": (
                "queue entry, not a decision — the §4.4 S4 maintainer queue "
                "decides; two agent contexts disagreed and the item routes "
                "for human judgment"
            ),
        }
        queue_entries.append(entry)
    return {
        "consensus": consensus,
        "unpaired": sorted(unpaired),
        "queue_entries": queue_entries,
    }


def append_queue_entries(path: Path | str, entries: Sequence[Mapping[str, Any]]) -> int:
    """Append S4 queue entries to the maintainer-queue JSONL (idempotent)."""
    path = Path(path)
    for entry in entries:
        if entry.get("version") != QUEUE_SCHEMA_VERSION:
            raise ValueError(f"queue entry must carry {QUEUE_SCHEMA_VERSION!r}")
        if entry.get("queue") != "maintainer" or entry.get("stratum") != "S4":
            raise ValueError("queue entry must target the maintainer S4 queue")
    existing = _existing_ids(path, "entry_id")
    path.parent.mkdir(parents=True, exist_ok=True)
    appended = 0
    with path.open("a", encoding="utf-8") as fh:
        for entry in entries:
            if str(entry["entry_id"]) in existing:
                continue
            fh.write(json.dumps(entry, sort_keys=True, ensure_ascii=True) + "\n")
            existing.add(str(entry["entry_id"]))
            appended += 1
    return appended


def cohens_kappa(a: Sequence[str], b: Sequence[str]) -> float | None:
    """Agent–agent Cohen's κ over two parallel verdict lists.

    This is **agreement between two AI runs — never accuracy**: same-family
    runs share blind spots, so κ overstates nothing about truth. ``None``
    when there are no paired verdicts.
    """
    if len(a) != len(b) or not a:
        return None
    categories = sorted(set(a) | set(b))
    n = len(a)
    p_o = sum(1 for x, y in zip(a, b, strict=True) if x == y) / n
    p_e = 0.0
    for cat in categories:
        pa = sum(1 for x in a if x == cat) / n
        pb = sum(1 for y in b if y == cat) / n
        p_e += pa * pb
    if p_e >= 1.0:
        return 1.0 if p_o >= 1.0 else 0.0
    return (p_o - p_e) / (1 - p_e)


def lane_report(
    packet: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    queue_entries: Sequence[Mapping[str, Any]],
    *,
    generated_at: str,
) -> dict[str, Any]:
    """The ``sig.agent-review-report/1`` weekly summary.

    Carries the lane's prescribed disclosures verbatim: agreement is
    ``agent_consensus`` (never "correct") and κ is agreement between two AI
    runs (never accuracy). B3 basis — report-only, never a gate.
    """
    routed = route_verdicts(packet, records, queued_at=generated_at)
    pairs_a: list[str] = []
    pairs_b: list[str] = []
    by_item: dict[str, dict[str, str]] = {}
    for record in records:
        by_item.setdefault(str(record["item_id"]), {})[str(record["context_id"])] = str(
            record["verdict"]
        )
    for verdicts in by_item.values():
        if "a" in verdicts and "b" in verdicts:
            pairs_a.append(verdicts["a"])
            pairs_b.append(verdicts["b"])
    kappa = cohens_kappa(pairs_a, pairs_b)

    per_question: dict[str, dict[str, int]] = {}
    for item_id, verdict in routed["consensus"].items():
        item = next(i for i in packet["items"] if str(i["item_id"]) == item_id)
        q = str(item["question"])
        bucket = per_question.setdefault(q, {})
        bucket[verdict] = bucket.get(verdict, 0) + 1

    model_ids = sorted({str(r["model_id"]) for r in records})
    families = {m.split("@", 1)[0] for m in model_ids}
    return {
        "version": REPORT_SCHEMA_VERSION,
        "generated_at": generated_at,
        "packet_id": packet["packet_id"],
        "packet_digest": packet["packet_digest"],
        "week": packet["week"],
        "seed": packet["seed"],
        "corpus_digest": packet["corpus_digest"],
        "capture_kind": packet["capture_kind"],
        "n_items": len(packet["items"]),
        "n_records": len(records),
        "paired_items": len(pairs_a),
        "agent_consensus": len(routed["consensus"]),
        "unpaired_items": len(routed["unpaired"]),
        "disagreements_routed_to_s4": len(queue_entries),
        "agent_agent_kappa": kappa,
        "model_ids": model_ids,
        "same_model_family": len(families) <= 1,
        "labeller_kind": "agent",
        "basis_class": "B3",
        "basis_label": "agent review",
        "consensus_by_question": per_question,
        "queue_appends": [str(e["entry_id"]) for e in queue_entries],
        "disclosure": (
            "agent consensus is agreement between two AI runs of the same "
            "model family — never 'correct', never accuracy; same-family "
            "agreement is correlated by construction (B-31). B3 agent-review "
            "evidence is report-only and may never gate (SIG-CONF-003)."
        ),
        "never_claims": [
            "agent consensus is not correctness",
            "agent–agent κ is not accuracy",
            "B3 evidence never gates",
            "this lane never impersonates independent human review",
        ],
    }


def lane_paths(root: Path | str, packet_id: str) -> dict[str, Path]:
    """The committed record paths for one packet under the lane dir."""
    root = Path(root)
    return {
        "packet": root / "packets" / f"packet-{packet_id}.json",
        "labels": root / "labels" / f"labels-{packet_id}.jsonl",
        "queue": root / "maintainer-queue-s4.jsonl",
        "report": root / "reports" / f"report-{packet_id}.json",
    }


def write_run(
    root: Path | str,
    packet: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    queue_entries: Sequence[Mapping[str, Any]],
    report: Mapping[str, Any],
    *,
    universe: Mapping[str, Any] | None = None,
) -> dict[str, Path]:
    """Append one weekly run's artifacts under the lane dir.

    The packet + report write as pretty JSON (idempotent — same packet id,
    same bytes); label records + queue entries append as JSONL (dedupe on
    their ids). ``universe`` writes the sampled corpus once, keyed by its
    digest.
    """
    root = Path(root)
    paths = lane_paths(root, str(packet["packet_id"]))
    paths["packet"].parent.mkdir(parents=True, exist_ok=True)
    paths["report"].parent.mkdir(parents=True, exist_ok=True)
    paths["packet"].write_text(
        json.dumps(packet, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    append_records(paths["labels"], records)
    append_queue_entries(paths["queue"], queue_entries)
    paths["report"].write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    if universe is not None:
        udir = root / "universes"
        udir.mkdir(parents=True, exist_ok=True)
        digest = universe_digest(universe).split(":", 1)[1][:12]
        paths["universe"] = udir / f"universe-{digest}.json"
        paths["universe"].write_text(
            json.dumps(universe, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
    return paths


__all__ = [
    "CONTEXT_IDS",
    "CORPUS_SCHEMA_VERSION",
    "DEFECT_VOCAB",
    "EDGE_STRATUM_QUOTAS",
    "FORBIDDEN_EVIDENCE_TOKENS",
    "KINDS",
    "KIND_EDGE",
    "KIND_SITE",
    "LANE_DIR",
    "PACKET_SCHEMA_VERSION",
    "PROMPT_TEMPLATES",
    "QUESTION_BY_KIND",
    "QUEUE_SCHEMA_VERSION",
    "REPORT_SCHEMA_VERSION",
    "RESERVED_PARTITIONS",
    "SAMPLE_EDGES",
    "SAMPLE_SITES",
    "SCHEMA_VERSION",
    "SIMPLE_RANDOM",
    "SITE_STRATUM_QUOTAS",
    "STRATUM_QUOTAS",
    "VERDICT_VOCAB",
    "append_queue_entries",
    "append_records",
    "assert_blind_item",
    "build_labelling_prompts",
    "build_packet",
    "cohens_kappa",
    "lane_paths",
    "lane_report",
    "make_record",
    "prompt_digest",
    "read_records",
    "reserved_item_ids",
    "route_verdicts",
    "universe_digest",
    "validate_record",
    "write_run",
]
