# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.23: the corpus harness legs — M-4 perturbation, M-5 hard-negative and
the GQ-26/M-6 metamorphic invariants, run over the committed corpus records
through the real ``resolution.camera_sites`` engine.

The harness projects corpus slice bytes to ``CameraRecord``s through the
slice's declared field map (a corpus projection, not the connector's typed
extraction — the connector's own output is what the pipeline leg checks).
Every template is mechanical and declared: perturbation classes carry a
known-answer expectation derived from the declared ruleset contract (a
republished copy within ``copy_tolerance_m`` still collapses; beyond it —
or transposed, sign-flipped, co-located-distinct — it must not).

The report it returns carries the SIG-CONF-012 estimand header from the
corpus doc verbatim. The numbers are mechanical censuses over declared
classes — they are never presented as real-world precision or recall.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

from .rdc import (
    Slice,
    build_report,
    member_bytes,
)

# ---------------------------------------------------------------------------
# Record projection — slice bytes -> CameraRecord-shaped records
# ---------------------------------------------------------------------------


def _arcgis_records(s: Slice) -> list[dict[str, Any]]:
    """Project an ``arcgis_pages`` slice to camera records via its declared
    field map (``records = {projection="arcgis_camera", object_id_field=…,
    name_fields=[…], technology=…, jurisdiction=…}``). The projection reads
    the raw attributes — the connector's own extraction is what the pipeline
    leg checks, never this projection's."""
    spec = s.records
    oid_field = str(spec.get("object_id_field", "OBJECTID"))
    name_fields = tuple(spec.get("name_fields", ("NAME", "Location")))
    tech = spec.get("technology")
    jur = spec.get("jurisdiction")
    records: list[dict[str, Any]] = []
    members = member_bytes(s)
    for m in s.members:
        if m.path not in members:
            continue
        doc = json.loads(members[m.path].decode("utf-8"))
        for feat in doc.get("features", []):
            attrs = feat.get("attributes") or {}
            geom = feat.get("geometry") or {}
            oid = attrs.get(oid_field)
            x, y = geom.get("x"), geom.get("y")
            name = next(
                (str(attrs[f]) for f in name_fields if attrs.get(f) not in (None, "")),
                None,
            )
            records.append(
                {
                    "subject_id": f"rdc:{s.slice_id}:{oid}",
                    "source_id": f"rdc_{s.slice_id}",
                    "latitude": y,
                    "longitude": x,
                    "external_ref": None if oid is None else str(oid),
                    "id_namespace": f"arcgis.{s.source_id}.{oid_field.lower()}",
                    "name": name,
                    "jurisdiction": jur,
                    "technology": tech,
                    "claim_ids": (f"rdc:{s.slice_id}:{m.path}:{oid}",),
                    "target_id": s.slice_id,
                    "capture_digests": (m.sha256,),
                    "coordinate_capture_id": m.sha256[:16],
                }
            )
    return records


PROJECTIONS = {"arcgis_camera": _arcgis_records}


def project_records(s: Slice) -> list[dict[str, Any]]:
    proj = s.records.get("projection")
    if proj not in PROJECTIONS:
        raise ValueError(f"{s.slice_id}: records projection {proj!r} unregistered")
    return PROJECTIONS[proj](s)


# ---------------------------------------------------------------------------
# ER plumbing
# ---------------------------------------------------------------------------


def _to_camera_record(d: dict[str, Any]) -> Any:
    from resolution.camera_sites import CameraRecord

    return CameraRecord(
        subject_id=str(d["subject_id"]),
        source_id=str(d["source_id"]),
        latitude=d.get("latitude"),
        longitude=d.get("longitude"),
        external_ref=d.get("external_ref"),
        id_namespace=d.get("id_namespace"),
        name=d.get("name"),
        roadway=d.get("roadway"),
        direction=d.get("direction"),
        operator=d.get("operator"),
        jurisdiction=d.get("jurisdiction"),
        camera_type=d.get("camera_type"),
        technology=d.get("technology"),
        claim_ids=tuple(d.get("claim_ids", ())),
        target_id=d.get("target_id"),
        capture_digests=tuple(d.get("capture_digests", ())),
        coordinate_capture_id=d.get("coordinate_capture_id"),
        geometry_defects=tuple(d.get("geometry_defects", ())),
    )


def _resolve(
    records: list[Any],
    *,
    declared: dict[str, str] | None = None,
    details: dict[str, Any] | None = None,
    geo_rule: Any = None,
) -> Any:
    from resolution.camera_sites import CameraSiteRules, resolve_camera_sites

    return resolve_camera_sites(
        records,
        gold=None,
        threshold=0.95,
        rules=CameraSiteRules.from_data(),
        declared_lineages=declared,
        declared_details=details,
        geo_rule=geo_rule,
    )


def _mirror_decls(sources: Iterable[str]) -> tuple[dict[str, str], dict[str, Any]]:
    """Declared copy lineage for the M-4/M-6 twin templates: one primary +
    mirror members in one independence class (kind=mirror carries the
    documentary evidence C1/C2 gate on)."""
    from resolution.camera_sites import LineageDeclaration

    srcs = list(sources)
    declared = {s: "rdc-copy" for s in srcs}
    details = {
        srcs[0]: LineageDeclaration("rdc-copy", "primary", "the upstream publisher"),
    }
    for s in srcs[1:]:
        details[s] = LineageDeclaration(
            "rdc-copy", "mirror", f"{s} republishes {srcs[0]} verbatim (declared corpus lineage)"
        )
    return declared, details


def _cluster_of(result: Any, subject: str) -> str:
    return str(result.clusters.get(subject, subject))


# ---------------------------------------------------------------------------
# M-4 — perturbation known-answer tests
# ---------------------------------------------------------------------------

#: Perturbation classes and their declared expectations. ``join`` means the
#: perturbed copy still collapses onto its origin under the declared ruleset
#: contract (a republished copy inside the copy tolerance, or a non-key field
#: changed); ``separate`` means it must not collapse (beyond the declared
#: tolerance, geometrically corrupted, or a distinct device).
M4_CLASSES: dict[str, str] = {
    "id_reformat": "join",  # "51" republished as "51.0" normalises equal
    "name_variant": "join",  # name is never a collapse condition
    "dropped_fields": "join",  # absent descriptive fields change nothing
    "jitter_within_tolerance": "join",  # <= copy_tolerance_m
    "jitter_beyond_tolerance": "separate",  # > copy_tolerance_m: not a byte-copy
    "jitter_far": "separate",
    "precision_5dp": "join",  # sub-metre truncation
    "precision_2dp": "separate",  # ~600 m shift: outside every candidate band
    "axis_swap": "separate",  # transposed point can never prove a copy
    "sign_flip": "separate",  # hemisphere mirror can never prove a copy
    "co_located_distinct_device": "separate",  # same point, distinct ref: multi-view, not a copy
}


def _perturb(
    twin: dict[str, Any], cls: str, *, jitter_lat_m: float = 0.0, jitter_lon_m: float = 0.0
) -> dict[str, Any]:
    t = dict(twin)
    lat, lon = t.get("latitude"), t.get("longitude")
    if cls == "id_reformat":
        ref = str(t.get("external_ref") or "")
        t["external_ref"] = f"{ref}.0" if ref.lstrip("-").isdigit() else f"{ref} "
    elif cls == "name_variant":
        name = t.get("name") or ""
        t["name"] = (
            name.replace("Police Department", "PD")
            .replace("Street", "St")
            .replace("street", "st")
            .upper()
            or "UNNAMED"
        )
    elif cls == "dropped_fields":
        for k in ("name", "roadway", "direction", "operator", "camera_type", "jurisdiction"):
            t[k] = None
    elif cls == "jitter_within_tolerance":
        t["latitude"] = lat + jitter_lat_m / 111_320.0 if lat is not None else None
    elif cls == "jitter_beyond_tolerance":
        t["latitude"] = lat + 5.0 / 111_320.0 if lat is not None else None
    elif cls == "jitter_far":
        t["latitude"] = lat + 50.0 / 111_320.0 if lat is not None else None
    elif cls == "precision_5dp":
        t["latitude"] = round(lat, 5) if lat is not None else None
        t["longitude"] = round(lon, 5) if lon is not None else None
    elif cls == "precision_2dp":
        t["latitude"] = round(lat, 2) if lat is not None else None
        t["longitude"] = round(lon, 2) if lon is not None else None
    elif cls == "axis_swap":
        t["latitude"], t["longitude"] = t["longitude"], t["latitude"]
    elif cls == "sign_flip":
        t["longitude"] = -lon if lon is not None else None
    elif cls == "co_located_distinct_device":
        ref = str(t.get("external_ref") or "")
        t["external_ref"] = f"{ref}-DEV2"
    return t


def run_m4(
    corpus_records: list[dict[str, Any]], *, seed: int = 7, sample: int = 25
) -> dict[str, Any]:
    """M-4: for each sampled corpus record, mint a declared-mirror twin, apply
    each perturbation class, and compare the outcome against the declared
    known answer."""
    import random

    usable = [
        r
        for r in corpus_records
        if r.get("latitude") is not None
        and r.get("longitude") is not None
        and r.get("external_ref") not in (None, "")
    ]
    rng = random.Random(seed)
    base = rng.sample(usable, min(sample, len(usable)))
    declared, details = _mirror_decls(["rdc_m4_origin", "rdc_m4_mirror"])

    per_class: dict[str, dict[str, Any]] = {}
    for cls, expected in M4_CLASSES.items():
        tested = joined = mismatches = 0
        examples: list[dict[str, Any]] = []
        for i, rec in enumerate(base):
            origin = dict(rec)
            origin["subject_id"] = f"m4:{cls}:{i}:origin"
            origin["source_id"] = "rdc_m4_origin"
            twin = dict(rec)
            twin["subject_id"] = f"m4:{cls}:{i}:twin"
            twin["source_id"] = "rdc_m4_mirror"
            twin = _perturb(twin, cls)
            a = _to_camera_record(origin)
            b = _to_camera_record(twin)
            result = _resolve([a, b], declared=declared, details=details)
            did_join = _cluster_of(result, a.subject_id) == _cluster_of(result, b.subject_id)
            tested += 1
            joined += int(did_join)
            want_join = expected == "join"
            if did_join != want_join:
                mismatches += 1
                if len(examples) < 3:
                    examples.append(
                        {
                            "origin_ref": rec.get("external_ref"),
                            "expected": expected,
                            "observed": "join" if did_join else "separate",
                        }
                    )
        per_class[cls] = {
            "expected": expected,
            "tested": tested,
            "joined": joined,
            "join_rate": round(joined / tested, 4) if tested else None,
            "mismatches": mismatches,
            "examples": examples,
            "outcome": "pass" if mismatches == 0 else "fail",
        }
    violations = sum(c["mismatches"] for c in per_class.values())
    return {
        "sample_size": len(base),
        "seed": seed,
        "classes": per_class,
        "violations": violations,
        "outcome": "pass" if violations == 0 else "fail",
    }


# ---------------------------------------------------------------------------
# M-5 — mechanical hard negatives
# ---------------------------------------------------------------------------


def run_m5(corpus_records: list[dict[str, Any]], *, seed: int = 11) -> dict[str, Any]:
    """M-5: mechanically-declared known-distinct pairs that must never merge.

    Classes: unique distinct ids in one origin namespace (including real
    co-located records), incompatible technology classes, and records >10 km
    apart sharing a normalised reference.
    """
    import random

    usable = [
        r
        for r in corpus_records
        if r.get("latitude") is not None and r.get("external_ref") not in (None, "")
    ]
    rng = random.Random(seed)

    # Real co-located distinct-ref pairs from the corpus itself.
    by_point: dict[str, list[dict[str, Any]]] = {}
    for r in usable:
        pt = f"{round(float(r['latitude']), 6)},{round(float(r['longitude']), 6)}"
        by_point.setdefault(pt, []).append(r)
    real_colocated: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for group in by_point.values():
        refs = {r["external_ref"] for r in group}
        if len(group) >= 2 and len(refs) >= 2:
            real_colocated.append((group[0], group[1]))

    base = rng.sample(usable, min(20, len(usable)))
    from resolution.camera_sites import LineageDeclaration

    declared, details = _mirror_decls(["rdc_m5_a", "rdc_m5_b"])
    independent = {"rdc_m5_a": "ind-a", "rdc_m5_b": "ind-b"}
    ind_details = {
        "rdc_m5_a": LineageDeclaration("ind-a", "primary", "independent origin"),
        "rdc_m5_b": LineageDeclaration("ind-b", "primary", "independent origin"),
    }

    def pair_outcome(
        ra: dict[str, Any], rb: dict[str, Any], decl: dict[str, str], det: dict[str, Any]
    ) -> tuple[bool, int]:
        a = _to_camera_record(ra)
        b = _to_camera_record(rb)
        result = _resolve([a, b], declared=decl, details=det)
        merged = _cluster_of(result, a.subject_id) == _cluster_of(result, b.subject_id)
        assessed = len(result.decisions)
        return merged, assessed

    classes: dict[str, dict[str, Any]] = {}

    def tally(name: str, pairs: list[tuple[dict, dict, dict, dict]]) -> None:
        tested = merged_n = assessed_n = 0
        examples: list[dict[str, Any]] = []
        for ra, rb, decl, det in pairs:
            merged, assessed = pair_outcome(ra, rb, decl, det)
            tested += 1
            merged_n += int(merged)
            assessed_n += int(assessed > 0)
            if merged and len(examples) < 3:
                examples.append(
                    {"left_ref": ra.get("external_ref"), "right_ref": rb.get("external_ref")}
                )
        classes[name] = {
            "tested": tested,
            "merged": merged_n,
            "assessed": assessed_n,
            "merge_rate": round(merged_n / tested, 4) if tested else None,
            "examples": examples,
            "outcome": "pass" if merged_n == 0 else "fail",
        }

    # (i) unique distinct ids in one origin namespace — distinct refs at the
    # same point, independent origins, never merge. Includes every real
    # co-located corpus pair plus synthetic distinct-device templates.
    pairs: list[tuple[dict, dict, dict, dict]] = []
    for i, (ra, rb) in enumerate(real_colocated[:10]):
        a = {**ra, "subject_id": f"m5:co:{i}:a", "source_id": "rdc_m5_a"}
        b = {**rb, "subject_id": f"m5:co:{i}:b", "source_id": "rdc_m5_b"}
        pairs.append((a, b, independent, ind_details))
    for i, rec in enumerate(base):
        a = {**rec, "subject_id": f"m5:co:t{i}:a", "source_id": "rdc_m5_a"}
        b = {
            **rec,
            "subject_id": f"m5:co:t{i}:b",
            "source_id": "rdc_m5_b",
            "external_ref": f"{rec['external_ref']}-DISTINCT",
        }
        pairs.append((a, b, independent, ind_details))
    tally("unique_distinct_ids_one_namespace", pairs)

    # (ii) incompatible technology classes — same point, distinct refs,
    # alpr vs cctv are declared incompatible: never even a candidate.
    pairs = []
    for i, rec in enumerate(base):
        a = {
            **rec,
            "subject_id": f"m5:tech:{i}:a",
            "source_id": "rdc_m5_a",
            "technology": "alpr-fixed",
        }
        b = {
            **rec,
            "subject_id": f"m5:tech:{i}:b",
            "source_id": "rdc_m5_b",
            "external_ref": f"{rec['external_ref']}-ALPR",
            "technology": "fixed-camera-cctv",
        }
        pairs.append((a, b, independent, ind_details))
    tally("incompatible_technology", pairs)

    # (iii) >10 km apart sharing a normalised reference — the copy join's
    # distance guard holds even inside a declared namespace + copy lineage.
    pairs = []
    for i, rec in enumerate(base):
        lat = rec["latitude"]
        a = {**rec, "subject_id": f"m5:far:{i}:a", "source_id": "rdc_m5_a"}
        b = {
            **rec,
            "subject_id": f"m5:far:{i}:b",
            "source_id": "rdc_m5_b",
            "latitude": float(lat) + 12_000.0 / 111_320.0,  # ~12 km north
        }
        pairs.append((a, b, declared, details))
    tally("far_shared_reference", pairs)

    violations = sum(c["merged"] for c in classes.values())
    return {
        "sample_size": len(base),
        "seed": seed,
        "real_co_located_pairs": len(real_colocated),
        "classes": classes,
        "violations": violations,
        "outcome": "pass" if violations == 0 else "fail",
    }


# ---------------------------------------------------------------------------
# M-6 / GQ-26 — metamorphic invariants
# ---------------------------------------------------------------------------


def _alt_geo_rule() -> Any:
    """A different blocking page size (4x cells) — the metamorphic 'changed
    page-size' input; still sized to cover the candidate radius."""
    from resolution.blocking import GeoGridRule

    return GeoGridRule(
        rule_id="rdc_alt_page",
        cell_lat_deg=0.004,
        cell_lon_deg=0.008,
        max_abs_latitude=73.0,
        covers_radius_m=50.0,
        description="M-6 metamorphic page-size variant (P35.23)",
    )


def run_m6(corpus_records: list[dict[str, Any]], *, seed: int = 13) -> dict[str, Any]:
    """GQ-26's invariants over the corpus record set + a declared-mirror twin
    population:

    * input-order permutation ⇒ identical cluster sets;
    * a changed blocking page size ⇒ identical cluster sets;
    * removing a declared mirror ⇒ unchanged distinct-record (site) count;
    * adding an origin whose mirror already exists ⇒ unchanged count;
    * re-run ⇒ +0 changes.
    """
    import random

    rng = random.Random(seed)
    usable = [
        r
        for r in corpus_records
        if r.get("latitude") is not None and r.get("external_ref") not in (None, "")
    ]
    base = rng.sample(usable, min(15, len(usable)))

    # The twin population: each base record mirrored into a declared copy
    # lineage — real collapses the invariants must hold over.
    declared, details = _mirror_decls(["rdc_m6_origin", "rdc_m6_mirror"])
    origins: list[Any] = []
    mirrors: list[Any] = []
    for i, rec in enumerate(base):
        origins.append(
            _to_camera_record({**rec, "subject_id": f"m6:o:{i}", "source_id": "rdc_m6_origin"})
        )
        mirrors.append(
            _to_camera_record({**rec, "subject_id": f"m6:m:{i}", "source_id": "rdc_m6_mirror"})
        )
    full = origins + mirrors

    checks: dict[str, dict[str, Any]] = {}

    def cluster_sets(result: Any) -> set[frozenset]:
        groups: dict[str, set] = {}
        for sub, rep in result.clusters.items():
            groups.setdefault(str(rep), set()).add(sub)
        return {frozenset(g) for g in groups.values()}

    r1 = _resolve(full, declared=declared, details=details)
    checks["baseline_sites"] = {
        "records": len(full),
        "distinct_sites": len(cluster_sets(r1)),
        "decisions": len(r1.decisions),
    }

    # order permutation
    shuffled = list(full)
    rng.shuffle(shuffled)
    r_perm = _resolve(shuffled, declared=declared, details=details)
    same = cluster_sets(r_perm) == cluster_sets(r1)
    checks["input_order_permutation"] = {
        "invariant": "identical cluster sets under input-order permutation",
        "same": same,
        "outcome": "pass" if same else "fail",
    }

    # page-size change
    r_page = _resolve(full, declared=declared, details=details, geo_rule=_alt_geo_rule())
    same = cluster_sets(r_page) == cluster_sets(r1)
    checks["page_size_change"] = {
        "invariant": "identical cluster sets under a changed blocking page size",
        "same": same,
        "outcome": "pass" if same else "fail",
    }

    # remove a declared mirror — the distinct-site count must not move
    r_removed = _resolve(origins, declared=declared, details=details)
    same = len(cluster_sets(r_removed)) == len(cluster_sets(r1))
    checks["remove_declared_mirror"] = {
        "invariant": "removing a declared mirror leaves the distinct-record count unchanged",
        "baseline": len(cluster_sets(r1)),
        "after": len(cluster_sets(r_removed)),
        "same": same,
        "outcome": "pass" if same else "fail",
    }

    # add an origin whose mirror exists — unchanged distinct count
    extra = [
        _to_camera_record(
            {
                **base[i],
                "subject_id": f"m6:x:{i}",
                "source_id": "rdc_m6_origin2",
            }
        )
        for i in range(min(3, len(base)))
    ]
    declared3 = {**declared, "rdc_m6_origin2": "rdc-copy"}
    from resolution.camera_sites import LineageDeclaration

    details3 = {
        **details,
        "rdc_m6_origin2": LineageDeclaration(
            "rdc-copy", "primary", "the same upstream publisher (second origin row)"
        ),
    }
    # the added origin's records coincide with the mirrors of the same rows
    r_added = _resolve(full + extra, declared=declared3, details=details3)
    same = len(cluster_sets(r_added)) == len(cluster_sets(r1))
    checks["add_origin_with_existing_mirror"] = {
        "invariant": "adding an origin whose mirror exists leaves the "
        "distinct-record count unchanged",
        "baseline": len(cluster_sets(r1)),
        "after": len(cluster_sets(r_added)),
        "same": same,
        "outcome": "pass" if same else "fail",
    }

    # idempotent re-run
    r2 = _resolve(full, declared=declared, details=details)
    same = cluster_sets(r2) == cluster_sets(r1) and [
        (d.disposition, d.assessment.tier, d.assessment.left, d.assessment.right)
        for d in r1.decisions
    ] == [
        (d.disposition, d.assessment.tier, d.assessment.left, d.assessment.right)
        for d in r2.decisions
    ]
    checks["rerun_plus_zero"] = {
        "invariant": "a re-run yields +0 changes",
        "same": same,
        "outcome": "pass" if same else "fail",
    }

    violations = sum(1 for c in checks.values() if c.get("outcome") == "fail")
    return {
        "checks": checks,
        "violations": violations,
        "outcome": "pass" if violations == 0 else "fail",
    }


# ---------------------------------------------------------------------------
# The harness entry point
# ---------------------------------------------------------------------------


def run_harness(
    corpus: Any, *, with_pipeline: bool = True, generated_at: str | None = None
) -> dict[str, Any]:
    """Run every leg over every materialized slice and build the report."""
    from datetime import UTC, datetime

    from .rdc import run_oracle, run_pipeline_leg

    gen = generated_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    evaluated = 0
    deferred: list[str] = []
    sections: dict[str, Any] = {"slices": {}, "m4": None, "m5": None, "m6": None}
    all_records: list[dict[str, Any]] = []
    failures: list[str] = []

    for s in corpus.slices:
        from .rdc import materialized as _mat

        if s.lane == "restricted" and not _mat(s):
            deferred.append(s.slice_id)
            continue
        evaluated += 1
        sec: dict[str, Any] = {"lane": s.lane, "archetype": s.archetype, "legs": list(s.legs)}
        if "oracle" in s.legs:
            sec["oracle"] = run_oracle(s)
        if with_pipeline and "pipeline" in s.legs and s.pipeline:
            sec["pipeline"] = run_pipeline_leg(s)
            # declared expectations on the pipeline outcome
            expect = s.pipeline.get("expect", {})
            checks = []
            for key, want in expect.items():
                got = sec["pipeline"].get(key)
                checks.append({"fact": key, "expected": want, "actual": got, "ok": got == want})
            sec["pipeline_expectations"] = checks
            failures.extend(
                f"{s.slice_id}: pipeline.{c['fact']} expected {c['expected']!r} got {c['actual']!r}"
                for c in checks
                if not c["ok"]
            )
        if any(leg in s.legs for leg in ("records", "m4", "m5", "m6")) and s.records:
            recs = project_records(s)
            all_records.extend(recs)
            sec["records"] = len(recs)
        sections["slices"][s.slice_id] = sec

    if evaluated == 0:
        failures.append("zero slices evaluated — vacuous run refused (SIG-ENG-042)")

    m_records = all_records
    sections["m4"] = run_m4(m_records) if m_records else {"outcome": "fail", "error": "no records"}
    sections["m5"] = run_m5(m_records) if m_records else {"outcome": "fail", "error": "no records"}
    sections["m6"] = run_m6(m_records) if m_records else {"outcome": "fail", "error": "no records"}
    for leg in ("m4", "m5", "m6"):
        if sections[leg].get("outcome") != "pass":
            failures.append(f"{leg.upper()}: {sections[leg].get('violations', '?')} violations")

    verdict = "pass" if not failures else "fail"
    report = build_report(
        corpus,
        sections=sections,
        generated_at=gen,
        verdict=verdict,
        slices_evaluated=evaluated,
        slices_deferred=deferred,
    )
    report["failures"] = failures
    return report
