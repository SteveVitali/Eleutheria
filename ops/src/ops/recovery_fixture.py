# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Seed a REAL claim spine from the P32.6 audit fixture (P32.22, SIG-TRUST-008).

``fixture_spine.json`` is the audit loader's *row* shape — synthetic string ids,
not DB rows. This module maps it onto an actual deployed spine so the bounded
apply, the +0 rerun, the receipt/restart semantics, and the frozen snapshot run
against real PostgreSQL mechanics (triggers, PKs, RLS, FK checks) rather than a
dump:

* every synthetic id is mapped to a deterministic ``uuid5`` so a re-seed is
  idempotent (``ON CONFLICT DO NOTHING`` everywhere) and the seeded population
  is reproducible;
* the fixture classes are preserved faithfully — actual captures with recorded
  digests + agreeing run marks (recoverable), recorded digests whose OCFL
  bytes differ (digest-mismatch), recorded objects absent from the root
  (missing), restricted/sealed tiers, and synthetic zero-byte placeholders
  (no byte expectation, no fabricated occurrence);
* no person/plate data — the fixture's entities are a deployment subject, two
  organisation objects, and one asserted-by person entity, exactly as the
  fixture rows name them;
* the id map (fixture id → real uuid) is returned and written so the audit's
  targeted set, the adjudications file, and repair instructions can be
  re-expressed over the real spine.

The seeder writes only rows the fixture rows name — it never fabricates an
occurrence, a mark, or an eligibility verdict.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

__all__ = ["FIXTURE_NAMESPACE", "fixture_uuid", "seed_fixture_spine", "load_fixture_dir"]

FIXTURE_NAMESPACE = uuid.NAMESPACE_URL
ZERO_DIGEST = "0" * 64


def fixture_uuid(kind: str, fixture_id: str) -> str:
    """Deterministic id mapping — re-seeding converges to the same uuids."""
    return str(uuid.uuid5(FIXTURE_NAMESPACE, f"sig-p32.22-fixture:{kind}:{fixture_id}"))


def load_fixture_dir(fixture_dir: str | Path) -> dict[str, Any]:
    """Read the committed fixture packet."""
    root = Path(fixture_dir)
    spine = json.loads((root / "fixture_spine.json").read_text(encoding="utf-8"))
    out: dict[str, Any] = {"spine": spine, "root": root}
    if (root / "targeted_ids.txt").exists():
        out["targeted_ids"] = [
            line.strip()
            for line in (root / "targeted_ids.txt").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]
    if (root / "adjudications.json").exists():
        out["adjudications"] = json.loads((root / "adjudications.json").read_text(encoding="utf-8"))
    return out


_PREDICATE_DEFS: dict[str, dict[str, str]] = {
    "camera_location": {
        "value_datatype": "string",
        "object_type": "literal",
        "volatility_class": "SLOW",
        "half_life_days": "1825",
        "definition": "fixture predicate — the camera's recorded location (P32.6 fixture)",
    },
    "camera_operator": {
        "value_datatype": "entity",
        "object_type": "entity_ref",
        "volatility_class": "SLOW",
        "half_life_days": "1825",
        "definition": "fixture predicate — the operating organisation (P32.6 fixture)",
    },
}

_ENTITY_TYPES: dict[str, str] = {
    "ent-subj": "deployment",
    "ent-org": "organization",
    "ent-flock": "organization",
}


def seed_fixture_spine(conn: Any, fixture_dir: str | Path) -> dict[str, Any]:
    """Insert the fixture's population into a deployed spine; return the id map.

    Idempotent: every insert is ``ON CONFLICT DO NOTHING`` or keyed by the
    deterministic mapped uuid, so a second call converges to the same spine.
    """
    loaded = load_fixture_dir(fixture_dir)
    spine = loaded["spine"]
    rows = [dict(r) for r in spine["rows"]]
    cur = conn.cursor()

    # --- vocabulary + prerequisites ---------------------------------------
    cur.execute(
        "INSERT INTO vocab_resolution_strategy(strategy_id,definition) "
        "VALUES('authoritative_source_wins','fixture') ON CONFLICT DO NOTHING"
    )
    for predicate_id, spec in _PREDICATE_DEFS.items():
        cur.execute(
            "INSERT INTO vocab_predicate(predicate_id,vocab_version,value_datatype,"
            "object_type,definition,volatility_class,half_life_days,"
            "resolution_strategy) VALUES(%s,'fixture-1.0',%s,%s,%s,%s,%s,"
            "'authoritative_source_wins') ON CONFLICT (predicate_id) DO NOTHING",
            (
                predicate_id,
                spec["value_datatype"],
                spec["object_type"],
                spec["definition"],
                spec["volatility_class"],
                int(spec["half_life_days"]),
            ),
        )

    # --- entities ----------------------------------------------------------
    entity_ids = {name: fixture_uuid("entity", name) for name in _ENTITY_TYPES}
    entity_ids["ent-asserted"] = fixture_uuid("entity", "ent-asserted")
    for name, etype in _ENTITY_TYPES.items():
        cur.execute(
            "INSERT INTO entity(entity_id, entity_type) VALUES(%s::uuid, %s)"
            " ON CONFLICT (entity_id) DO NOTHING",
            (entity_ids[name], etype),
        )
    cur.execute(
        "INSERT INTO entity(entity_id, entity_type) VALUES(%s::uuid, 'person')"
        " ON CONFLICT (entity_id) DO NOTHING",
        (entity_ids["ent-asserted"],),
    )

    # --- rights + sources + runs -------------------------------------------
    rights_ids: dict[str, str] = {}
    for spdx in sorted({str(r["spdx_expression"]) for r in rows}):
        rid = fixture_uuid("rights", spdx)
        cur.execute(
            "INSERT INTO rights_record(rights_id,spdx_expression,redistributable,"
            "derivative_permitted,retrieval_date) VALUES(%s::uuid,%s,'yes','yes',"
            "'2026-01-01') ON CONFLICT (rights_id) DO NOTHING",
            (rid, spdx),
        )
        rights_ids[spdx] = rid

    source_ids = sorted({str(r["source_id"]) for r in rows})
    for sid in source_ids:
        spdx = next(str(r["spdx_expression"]) for r in rows if r["source_id"] == sid)
        cur.execute(
            "INSERT INTO source_registry(source_id,name,source_kind,"
            "default_reliability,reliability_justification,rights_id,"
            "custody_posture,compact_status,robots_policy) VALUES(%s,%s,"
            "'registry','R1','fixture source',%s::uuid,'MIRROR','active','allow')"
            " ON CONFLICT (source_id) DO NOTHING",
            (sid, f"Fixture {sid}", rights_ids[spdx]),
        )

    run_ids: dict[str, str] = {}
    for run_name in sorted({str(r["ingest_run_id"]) for r in rows}):
        rid = fixture_uuid("run", run_name)
        conn_rows = [r for r in rows if r["ingest_run_id"] == run_name]
        r0 = conn_rows[0]
        cur.execute(
            "INSERT INTO ingest_run(run_id,connector_name,connector_version,"
            "code_commit,ruleset_version,vocab_version,parameters,environment,"
            "input_digests,started_at,finished_at,status) VALUES(%s::uuid,%s,%s,"
            "%s,'ruleset-fixture-1','vocab-fixture-1','{}'::jsonb,"
            '\'{"TZ":"UTC","LC_ALL":"C"}\'::jsonb,\'{}\'::text[],%s,%s,'
            "'succeeded') ON CONFLICT (run_id) DO NOTHING",
            (
                rid,
                r0["connector_name"],
                r0["connector_version"],
                r0["code_commit"],
                r0["run_started_at"],
                r0["run_started_at"],
            ),
        )
        run_ids[run_name] = rid

    # --- artifacts + blobs + captures --------------------------------------
    artifact_ids: dict[str, str] = {}
    capture_ids: dict[str, str] = {}
    claim_ids: dict[str, str] = {}
    for r in rows:
        art = fixture_uuid("artifact", str(r["artifact_id"]))
        artifact_ids[str(r["artifact_id"])] = art
        # (source_id, stable_locator) is UNIQUE — the fixture reuses one locator
        # across artifacts, so the seeded locator is suffixed deterministically.
        stable_locator = f"{r['stable_locator']}#{r['artifact_id']}"
        cur.execute(
            "INSERT INTO evidence_artifact(artifact_id,source_id,url,"
            "stable_locator,artifact_type,acquisition_method,"
            "primary_or_secondary,rights_id,capture_status) VALUES(%s::uuid,%s,"
            "%s,%s,%s,%s,'primary',%s::uuid,%s) ON CONFLICT DO NOTHING",
            (
                art,
                r["source_id"],
                r.get("artifact_url"),
                stable_locator,
                r["artifact_type"],
                r["acquisition_method"],
                rights_ids[str(r["spdx_expression"])],
                r["capture_status"],
            ),
        )
        digest = str(r["capture_digest"])
        # Synthetic/zero-byte placeholders record NO byte-bearing occurrence —
        # empty strings satisfy NOT NULL while keeping ``expects_bytes`` false
        # (a fabricated object id would mislabel them unrecoverable).
        ocfl_obj = r.get("ocfl_object_id") or ""
        ocfl_ver = r.get("ocfl_version") or ""
        if digest != ZERO_DIGEST:
            cur.execute(
                "INSERT INTO evidence_blob(blob_digest,source_uri,byte_size,"
                "ocfl_object_id,ocfl_version,first_seen_at) VALUES(%s,%s,%s,%s,"
                "%s,%s) ON CONFLICT (blob_digest,source_uri) DO NOTHING",
                (
                    digest,
                    r["capture_source_uri"],
                    r["byte_size"],
                    ocfl_obj,
                    ocfl_ver,
                    r["retrieved_at"],
                ),
            )
        cap = fixture_uuid("capture", str(r["capture_id"]))
        capture_ids[str(r["capture_id"])] = cap
        cur.execute(
            "INSERT INTO evidence_capture(capture_id,artifact_id,content_digest,"
            "byte_size,media_type,retrieved_at,retrieved_by_run_id,"
            "ocfl_object_id,ocfl_version,storage_tier,capture_method,"
            "capture_tool_version,source_uri,blob_digest,capture_classification)"
            " VALUES(%s::uuid,%s::uuid,%s,%s,%s,%s,%s::uuid,%s,%s,%s,%s,'fixture',"
            "%s,%s,%s) ON CONFLICT (capture_id) DO NOTHING",
            (
                cap,
                art,
                digest,
                r["byte_size"],
                r["media_type"],
                r["retrieved_at"],
                run_ids[str(r["retrieved_by_run_id"])],
                ocfl_obj,
                ocfl_ver,
                r["storage_tier"],
                r["acquisition_method"],
                r["capture_source_uri"],
                None if digest == ZERO_DIGEST else digest,
                r["capture_classification"],
            ),
        )

    # --- claims ------------------------------------------------------------
    for r in rows:
        cid = fixture_uuid("claim", str(r["claim_id"]))
        claim_ids[str(r["claim_id"])] = cid
        object_entity = entity_ids.get(str(r["object_entity"])) if r.get("object_entity") else None
        cur.execute(
            "INSERT INTO claim(claim_id,subject_id,predicate_id,object_entity,"
            "object_type,value_kind,value_text,raw_value,observed_at,"
            "source_reliability,claim_directness,artifact_integrity,"
            "asserted_by,assertion_rationale,ingest_run_id,rights_id,"
            "sensitivity_tier,review_status,content_digest) VALUES(%s::uuid,"
            "%s::uuid,%s,%s,%s,%s,%s,%s,LEAST(%s::timestamptz,"
            "clock_timestamp()),'R1','D1','I1',%s::uuid,"
            "'fixture assertion',%s::uuid,%s::uuid,%s,%s,%s)"
            " ON CONFLICT (claim_id) DO NOTHING",
            (
                cid,
                entity_ids[str(r["subject_id"])],
                r["predicate_id"],
                object_entity,
                r["object_type"],
                r["value_kind"],
                r.get("value_text"),
                r["raw_value"],
                r["observed_at"],
                entity_ids["ent-asserted"],
                run_ids[str(r["ingest_run_id"])],
                rights_ids[str(r["spdx_expression"])],
                r["sensitivity_tier"],
                r["review_status"],
                r["claim_digest"],
            ),
        )

    # --- bindings ----------------------------------------------------------
    for r in rows:
        cur.execute(
            "INSERT INTO claim_evidence(claim_id,capture_id,role,locator,"
            "extraction_config_digest,extractor_version,binding_status,bound_at)"
            " VALUES(%s::uuid,%s::uuid,%s,%s::jsonb,%s,%s,%s,%s)"
            " ON CONFLICT (claim_id,capture_id,role) DO NOTHING",
            (
                claim_ids[str(r["claim_id"])],
                capture_ids[str(r["capture_id"])],
                r["role"],
                json.dumps(r["locator"]) if r.get("locator") is not None else None,
                r.get("extraction_config_digest"),
                r.get("extractor_version"),
                r["binding_status"],
                r["bound_at"],
            ),
        )

    # --- run marks ----------------------------------------------------------
    marks = spine.get("marks") or {}
    inserted_marks = 0
    for digest, mark_list in marks.items():
        for m in mark_list:
            # (run_id, target_key, state) is the PK — the fixture reuses one
            # target key per run, so the seeded key carries the digest prefix.
            target_key = f"{m['target_key']}#{digest[:8]}"
            cur.execute(
                "INSERT INTO ingest_run_capture(run_id,target_key,state,"
                "capture_digest,source_uri,media_type,byte_size,retrieved_at,"
                "records,ocfl_object_id,ocfl_version,recorded_at) VALUES"
                "(%s::uuid,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                " ON CONFLICT (run_id,target_key,state) DO NOTHING",
                (
                    run_ids.get(str(m["run_id"]), fixture_uuid("run", str(m["run_id"]))),
                    target_key,
                    m["state"],
                    digest,
                    m["source_uri"],
                    m["media_type"],
                    m["byte_size"],
                    m.get("retrieved_at"),
                    m.get("records"),
                    m.get("ocfl_object_id"),
                    m.get("ocfl_version"),
                    m.get("recorded_at") or m.get("retrieved_at"),
                ),
            )
            inserted_marks += cur.rowcount

    id_map = {
        "claims": claim_ids,
        "captures": capture_ids,
        "artifacts": artifact_ids,
        "entities": entity_ids,
        "runs": run_ids,
        "rights": rights_ids,
        "capture_root": str(loaded["root"] / "capture_root"),
        "targeted_ids": {fid: claim_ids.get(fid, fid) for fid in loaded.get("targeted_ids", [])},
        "adjudications": {
            claim_ids.get(k, k): v for k, v in (loaded.get("adjudications") or {}).items()
        },
    }
    return id_map


def write_remapped_fixtures(id_map: Mapping[str, Any], out_dir: str | Path) -> dict[str, Path]:
    """Write the claim-id-remapped companion files the audit consumes:
    ``targeted_ids.txt`` + ``adjudications.json`` over the REAL claim uuids."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    targeted = out / "targeted_ids.txt"
    targeted.write_text(
        "\n".join(str(v) for v in (id_map.get("targeted_ids") or {}).values()) + "\n",
        encoding="utf-8",
    )
    adjud = out / "adjudications.json"
    adjud.write_text(
        json.dumps(id_map.get("adjudications") or {}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {"targeted": targeted, "adjudications": adjud}
