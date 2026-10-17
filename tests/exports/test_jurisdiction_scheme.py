# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.18 (JUR-02a / K4 §3.2, SIG-JUR-D02): the declared jurisdiction scheme.

The contract under test:

* a claim's persisted ``value_json`` ``{scheme, value}`` pair keys its
  jurisdiction bucket under the canonical key — never the bare code;
* a legacy claim (no pair) derives its scheme from the source's declared
  config, labelled ``declared_scheme_from_config@<sha256>``;
* two same-valued claims under different schemes land in different buckets;
* ``sig.unresolved`` stays in the honest ``unresolved`` bucket — no key minted;
* a bucket never mixes a scheme-keyed claim with an undeclared bare value;
* no ``_slugify(<bare value>)`` remains on the jurisdiction path.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path

import pytest
from exports.jurisdictions import (
    DECLARED_SCHEME_FROM_CLAIM,
    DECLARED_SCHEME_FROM_CONFIG,
    jurisdiction_key,
    jurisdiction_slug,
    load_jurisdiction_scheme_config,
)
from exports.shaping import (
    UNRESOLVED_JURISDICTION,
    ShapingClaim,
    build_shaped_dataset,
    jurisdiction_scheme_mix_violations,
    shape_sites,
)

_REPO = Path(__file__).resolve().parents[2]
_DATA = _REPO / "connectors" / "src" / "connectors" / "data"


def _claim(
    claim_id: str,
    subject_id: str,
    predicate_id: str,
    *,
    value_text: str | None = None,
    raw_value: str | None = None,
    value_json: str | None = None,
    source_id: str | None = "src_x",
    sensitivity_tier: int = 0,
) -> ShapingClaim:
    raw = raw_value if raw_value is not None else (value_text or "")
    return ShapingClaim(
        claim_id=claim_id,
        subject_id=subject_id,
        predicate_id=predicate_id,
        value_kind="value",
        value_text=value_text,
        value_num=None,
        raw_value=raw,
        observed_at=date(2026, 5, 1),
        sensitivity_tier=sensitivity_tier,
        source_id=source_id,
        connector_name="camreg",
        effective_rights_id="rights-1",
        effective_spdx="CC0-1.0",
        effective_redistributable="yes",
        effective_derivative_permitted="yes",
        effective_attribution="",
        effective_terms_url="",
        value_json=value_json,
    )


def _site_claims(subject: str, juris_value: str, **kw) -> list[ShapingClaim]:
    return [
        _claim(f"{subject}-lat", subject, "camera_latitude", value_text="35.46"),
        _claim(f"{subject}-lon", subject, "camera_longitude", value_text="-97.52"),
        _claim(
            f"{subject}-jur",
            subject,
            "camera_jurisdiction",
            value_text=juris_value,
            **kw,
        ),
    ]


def _raw(claims: list[ShapingClaim]) -> dict:
    def _row(c: ShapingClaim) -> tuple:
        return (
            c.claim_id,
            c.subject_id,
            c.predicate_id,
            c.value_kind,
            c.value_text,
            c.value_num,
            c.raw_value,
            c.observed_at,
            c.sensitivity_tier,
            c.source_id,
            c.connector_name,
            c.occurrence_capture_id,
            c.occurrence_retrieved_at,
            c.occurrence_bound_at,
            c.effective_rights_id,
            c.effective_spdx,
            c.effective_redistributable,
            c.effective_derivative_permitted,
            c.effective_attribution,
            c.effective_terms_url,
            c.publication_permitted,
            c.effective_decision_decided_at,
            c.effective_decision_basis,
            c.value_json,
        )

    return {
        "shaping_claims": [_row(c) for c in claims],
        "subject_entities": [(s, "deployment") for s in sorted({c.subject_id for c in claims})],
        "source_stats": [],
        "source_runs": [],
        "sharing_edges": [],
        "spine_watermark": "claims=1 closed=0",
    }


def _pair(scheme: str, value: str) -> str:
    return json.dumps({"scheme": scheme, "value": value})


# --- the persisted {scheme, value} pair keys the bucket ---------------------- #


def test_a_persisted_pair_keys_the_bucket_by_scheme() -> None:
    """A claim whose ``value_json`` carries ``{scheme: us.state_abbr, value:
    OK}`` buckets under ``iso3166-2:US-OK`` — the declared key, never bare OK."""
    claims = _site_claims("s1", "OK", value_json=_pair("us.state_abbr", "OK"))
    (site,) = shape_sites(claims, entity_types={"s1": "deployment"})
    assert site.jurisdiction == "iso3166-2:US-OK"
    obs = site.jurisdiction_envelope.observations[0]
    assert obs.scheme == "us.state_abbr"
    assert obs.scheme_basis == DECLARED_SCHEME_FROM_CLAIM
    assert obs.display_value == "iso3166-2:US-OK"
    assert obs.raw_value == "OK"  # the asserted value is preserved verbatim


def test_same_scheme_same_value_groups_deterministically() -> None:
    claims = _site_claims("s1", "OK", value_json=_pair("us.state_abbr", "OK")) + _site_claims(
        "s2", "OK", value_json=_pair("us.state_abbr", "OK")
    )
    ds = build_shaped_dataset(
        _raw(claims),
        as_of="2026-10-17",
        generated_at="2026-10-17T00:00:00Z",
        spine_label="unit",
    )
    buckets = {j.jurisdiction: j.subjects for j in ds.jurisdictions}
    assert buckets == {"iso3166-2:US-OK": 2}


def test_two_same_valued_claims_different_schemes_never_share_a_bucket() -> None:
    """THE JUR-02a regression: ``us.state_abbr:OK`` and a foreign-scheme ``OK``
    must not land together — the bare value would have mixed them."""
    claims = _site_claims("s1", "OK", value_json=_pair("us.state_abbr", "OK")) + _site_claims(
        "s2", "OK", value_json=_pair("fr.insee", "OK")
    )
    ds = build_shaped_dataset(
        _raw(claims),
        as_of="2026-10-17",
        generated_at="2026-10-17T00:00:00Z",
        spine_label="unit",
    )
    buckets = {j.jurisdiction: j.subjects for j in ds.jurisdictions}
    assert buckets == {"iso3166-2:US-OK": 1, "fr.insee:OK": 1}
    sites = {s.entity_id: s.jurisdiction for s in ds.sites}
    assert sites == {"s1": "iso3166-2:US-OK", "s2": "fr.insee:OK"}


def test_sig_unresolved_never_mints_a_key() -> None:
    """``sig.unresolved`` maps to no key — the honest ``unresolved`` bucket."""
    claims = _site_claims("s1", "x", value_json=_pair("sig.unresolved", "x"))
    (site,) = shape_sites(claims, entity_types={"s1": "deployment"})
    assert site.jurisdiction == UNRESOLVED_JURISDICTION
    obs = site.jurisdiction_envelope.observations[0]
    assert obs.scheme == "sig.unresolved"


# --- the legacy path: declared_scheme_from_config@<sha256> ------------------- #


def test_a_legacy_claim_gets_the_config_declared_scheme() -> None:
    """A pre-P35.18 claim (no value_json) from a source whose config declares
    the scheme keys under it — basis labelled ``declared_scheme_from_config``
    with the sha256 of the file actually read."""
    claims = _site_claims("s1", "KY", source_id="dot_511_ky")
    (site,) = shape_sites(claims, entity_types={"s1": "deployment"})
    assert site.jurisdiction == "iso3166-2:US-KY"
    obs = site.jurisdiction_envelope.observations[0]
    assert obs.scheme == "us.state_abbr"
    expected_sha = hashlib.sha256((_DATA / "dot_511_targets.toml").read_bytes()).hexdigest()
    assert obs.scheme_basis == f"{DECLARED_SCHEME_FROM_CONFIG}@{expected_sha}"


def test_a_multi_scheme_source_resolves_per_value() -> None:
    """A source whose targets span two schemes resolves each claim under the
    scheme its value was emitted with (the (source, value) basis) — never a
    guessed single scheme."""
    claims = _site_claims("s1", "US-IL", source_id="camreg_chicago_il") + _site_claims(
        "s2", "IL", source_id="camreg_chicago_il"
    )
    ds = build_shaped_dataset(
        _raw(claims),
        as_of="2026-10-17",
        generated_at="2026-10-17T00:00:00Z",
        spine_label="unit",
    )
    sites = {s.entity_id: s.jurisdiction for s in ds.sites}
    assert sites == {"s1": "iso3166-2:US-IL", "s2": "iso3166-2:US-IL"}
    # Both landed under the same key via different declared schemes — the
    # canonical merge the K4 §3.2 map intends, recorded per-claim.
    for s in ds.sites:
        assert s.jurisdiction_envelope.observations[0].scheme_basis.startswith(
            DECLARED_SCHEME_FROM_CONFIG + "@"
        )


def test_an_undeclared_source_keeps_the_bare_value() -> None:
    """Back-compat: a claim whose source declares nothing keeps its bare
    value — undeclared, honest, never guessed."""
    claims = _site_claims("s1", "OK", source_id="atlas")
    (site,) = shape_sites(claims, entity_types={"s1": "deployment"})
    assert site.jurisdiction == "OK"
    obs = site.jurisdiction_envelope.observations[0]
    assert obs.scheme is None and obs.scheme_basis is None


def test_a_declared_pair_beats_the_config() -> None:
    """A new claim's own pair wins over any config derivation — the claim
    itself is the authoritative declaration."""
    claims = _site_claims(
        "s1", "KY", source_id="dot_511_ky", value_json=_pair("iso.3166_2", "US-KY")
    )
    (site,) = shape_sites(claims, entity_types={"s1": "deployment"})
    assert site.jurisdiction == "iso3166-2:US-KY"
    obs = site.jurisdiction_envelope.observations[0]
    assert obs.scheme == "iso.3166_2"
    assert obs.scheme_basis == DECLARED_SCHEME_FROM_CLAIM


# --- the no-mix guard --------------------------------------------------------- #


def test_no_mix_when_a_bare_value_collides_with_a_key() -> None:
    """A bare claim asserting text identical to a derived key would land in
    the keyed bucket — the guard names that mix."""
    claims = _site_claims("s1", "OK", value_json=_pair("us.state_abbr", "OK")) + _site_claims(
        "s2", "iso3166-2:US-OK", source_id="atlas"
    )
    violations = jurisdiction_scheme_mix_violations(
        [c for c in claims if c.predicate_id == "camera_jurisdiction"]
    )
    assert len(violations) == 1
    assert "iso3166-2:US-OK" in violations[0]


def test_the_build_fails_closed_on_a_mixed_bucket() -> None:
    claims = _site_claims("s1", "OK", value_json=_pair("us.state_abbr", "OK")) + _site_claims(
        "s2", "iso3166-2:US-OK", source_id="atlas"
    )
    with pytest.raises(ValueError, match="mix"):
        build_shaped_dataset(
            _raw(claims),
            as_of="2026-10-17",
            generated_at="2026-10-17T00:00:00Z",
            spine_label="unit",
        )


def test_clean_schemes_report_no_violations() -> None:
    claims = _site_claims("s1", "OK", value_json=_pair("us.state_abbr", "OK")) + _site_claims(
        "s2", "TX", source_id="dot_511_tx"
    )
    assert (
        jurisdiction_scheme_mix_violations(
            [c for c in claims if c.predicate_id == "camera_jurisdiction"]
        )
        == []
    )


# --- the config loader -------------------------------------------------------- #


def test_the_committed_config_covers_every_camera_jurisdiction_source() -> None:
    """Every source that emits ``camera_jurisdiction`` claims (the ``camreg_*``
    / ``dot_511_*`` registry rows) declares a scheme somewhere in config — the
    (source, value) target basis or a single-scheme source row."""
    import tomllib

    cfg = load_jurisdiction_scheme_config()
    registry = tomllib.loads((_DATA / "sources.toml").read_text())["sources"]
    emitters = {s for s in registry if s.startswith(("camreg_", "dot_511_"))}
    assert emitters  # the fixture is non-trivial — the registry is populated
    uncovered = [
        s
        for s in sorted(emitters)
        if s not in cfg.by_source and not any(sv[0] == s for sv in cfg.by_source_value)
    ]
    assert uncovered == []


def test_jurisdiction_key_covers_the_k4_map() -> None:
    assert jurisdiction_key("us.state_abbr", "OK") == "iso3166-2:US-OK"
    assert jurisdiction_key("iso.3166_1_alpha2", "FR") == "iso3166-1:FR"
    assert jurisdiction_key("iso.3166_2", "US-DE") == "iso3166-2:US-DE"
    assert jurisdiction_key("sig.unresolved", "x") is None
    # A declared scheme outside the K4 §3.2 map keys under the national form —
    # still scheme-named, never bare.
    assert jurisdiction_key("fr.insee", "75") == "fr.insee:75"


def test_jurisdiction_slug_is_the_key_not_the_value() -> None:
    assert jurisdiction_slug("iso3166-2:US-OK") == "iso3166-2-us-ok"
    assert jurisdiction_slug("unresolved") == "unresolved"
    # distinct keys never collapse onto one slug
    assert jurisdiction_slug("iso3166-1:US") != jurisdiction_slug("iso3166-2:US-OK")


# --- the grep guard: no bare-value slug on the jurisdiction path ------------- #


def test_no_bare_value_slugify_remains_on_the_jurisdiction_path() -> None:
    """The JUR-02a grep guard: ``_slugify(<bare jurisdiction value>)`` is
    gone — the jurisdiction path slugs the declared-scheme key only."""
    src = (_REPO / "exports" / "src" / "exports" / "spine_export.py").read_text()
    assert not re.search(r"_slugify\(\s*(group\.)?jurisdiction", src)
    # ``_slugify`` itself is gone from the module — its only callers were the
    # jurisdiction sites, now routed through ``jurisdiction_slug``.
    assert "_slugify" not in src
    # The jurisdiction path goes through the key-aware slug.
    assert "jurisdiction_slug(jurisdiction)" in src
    assert "jurisdiction_slug(group.jurisdiction)" in src
    shaping_src = (_REPO / "exports" / "src" / "exports" / "shaping.py").read_text()
    assert "_slugify" not in shaping_src


def test_value_json_is_additive_on_the_claim_row() -> None:
    """Row-shape back-compat: a 23-column pre-P35.18 row set still parses —
    the trailing ``value_json`` column is optional everywhere."""
    from exports.shaping import parse_shaping_claims

    claim = _claim("c1", "s", "camera_jurisdiction", value_text="OK")
    row = (
        claim.claim_id,
        claim.subject_id,
        claim.predicate_id,
        claim.value_kind,
        claim.value_text,
        claim.value_num,
        claim.raw_value,
        claim.observed_at,
        claim.sensitivity_tier,
        claim.source_id,
        claim.connector_name,
        claim.occurrence_capture_id,
        claim.occurrence_retrieved_at,
        claim.occurrence_bound_at,
        claim.effective_rights_id,
        claim.effective_spdx,
        claim.effective_redistributable,
        claim.effective_derivative_permitted,
        claim.effective_attribution,
        claim.effective_terms_url,
        claim.publication_permitted,
        claim.effective_decision_decided_at,
        claim.effective_decision_basis,
        # no 24th column — a pre-P35.18 row
    )
    (parsed,) = parse_shaping_claims([row])
    assert parsed.value_json is None
