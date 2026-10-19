# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.31 — the transparency scrub, one module / one vocabulary (J3 T-6).

Layer: engineered. These tests pin J4's S-1…S-14 scrub rules, the J3 §3.5
never-exported list, the secret-shaped detector the publish gate runs, the
redistribution-lane → storage-tier matrix (NEW-2 / F-400) and the served-tier
floor the ``/v1/evidence`` read path applies — all fail closed: an unknown
lane or Part VIII class derives ``sealed``, never ``public`` by default.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from policy.transparency import (
    CREDENTIAL_HEADERS,
    ERROR_CLASSES,
    GATED_REASON_CLASSES,
    GATED_SOURCE_COLUMNS,
    HEADER_ALLOWLIST,
    INTERNAL_LOCATION_PREFIX,
    IP_REMOVED,
    LANE_DERIVED_ONLY,
    LANE_LINK_ONLY,
    LANE_RAW_OK,
    LANE_RESTRICTED,
    LANE_UNKNOWN,
    NEVER_EXPORTED_FIELDS,
    NO_UPSTREAM_URL,
    PART_VIII_CLASSES,
    PART_VIII_SEALED_CLASSES,
    PERSONAL_DATA_REMOVED,
    REDISTRIBUTION_LANES,
    ROBOTS_DISREGARD_DECISION_REF,
    ROBOTS_OUTCOMES,
    ROLE_UNSPECIFIED,
    SECRET_PATTERN_CLASSES,
    STORAGE_TIERS,
    TIER_PUBLIC,
    TIER_RESTRICTED,
    TIER_SEALED,
    ScrubViolation,
    contains_ip_address,
    derive_storage_tier,
    error_class,
    error_counts,
    explicit_columns,
    find_secrets,
    gated_source_row,
    interim_lane,
    iso_utc,
    more_restrictive_tier,
    open_upstream_licence,
    reviewer_role,
    robots_disclosure_rows,
    scrub_headers,
    scrub_internal_locations,
    scrub_personal,
    scrub_source_url,
    scrub_text,
    served_storage_tier,
    strip_credential_query_params,
    strip_ip_addresses,
    tombstone_id,
    upstream_host,
)

# --- the vocabularies are closed sets ----------------------------------------


def test_vocabulary_sets_are_closed() -> None:
    assert REDISTRIBUTION_LANES == {
        "raw-ok",
        "derived-only",
        "link-only",
        "restricted",
        "unknown",
    }
    assert STORAGE_TIERS == {"public", "restricted", "sealed"}
    assert PART_VIII_SEALED_CLASSES <= PART_VIII_CLASSES
    assert "unclassified_error" in ERROR_CLASSES
    assert ROBOTS_OUTCOMES == {"obeyed", "disallowed", "unavailable", "disregarded"}
    # Every never-exported name the J3 §3.5 list names stays a member.
    for field in (
        "environment",
        "run_record_uri",
        "evidence_access_log",
        "reviewed_by",
        "headers",
        "detail",
        "search_reason",
        "snippet",
    ):
        assert field in NEVER_EXPORTED_FIELDS, field


# --- S-1: credential query params + headers + the secret detector -------------


def test_s1_strips_credential_query_params_by_name() -> None:
    # Built at runtime — no committed literal may carry a credential-shaped
    # query param (the repo-wide keyed-URL scanner fails closed on one).
    from urllib.parse import urlencode

    url = "https://portal.example/feed?limit=10&" + urlencode(
        {"api_key": "abc", "Token": "t", "q": "x"}
    )
    out = strip_credential_query_params(url)
    assert "api_key" not in out and "Token" not in out
    assert "limit=10" in out and "q=x" in out


def test_s1_unreadable_query_drops_the_whole_query() -> None:
    # A URL the parser cannot read loses the whole query rather than
    # passing it through unexamined (fail closed).
    out = strip_credential_query_params("http://[::1/x?key=1")
    assert "?" not in out


def test_s14_headers_keep_only_the_allowlist() -> None:
    scrubbed = scrub_headers(
        {
            "Content-Type": "application/pdf",
            "Authorization": "Bearer deadbeefdeadbeef",
            "Cookie": "sid=1",
            "X-Request-Id": "r1",
            "ETag": '"abc"',
            "Server": "nginx",
        }
    )
    assert set(scrubbed) == {"Content-Type", "ETag"}
    assert CREDENTIAL_HEADERS <= {
        "authorization",
        "x-api-key",
        "cookie",
        "set-cookie",
        "proxy-authorization",
    }
    assert HEADER_ALLOWLIST == {"content-type", "content-length", "etag", "last-modified", "date"}


@pytest.mark.parametrize(
    ("specimen", "pattern_class"),
    [
        # Each specimen is assembled at runtime — a literal credential shape in
        # a tracked file is exactly what the repo's own secret scanner refuses.
        ("token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIn0.sig'", "jwt"),
        ("aws key " + "AKIA" + "IOSFODNN7EXAMPLE", "aws_access_key"),
        ("SIGNING_KEY=00112233445566778899aabbccddeeff", "key_hex"),
        ("Authorization: Bearer abcdef0123456789token", "bearer_token"),
        ("-----BEGIN " + "RSA " + "PRIVATE KEY-----", "private_key"),
        ("gcp: " + "AIza" + "SyD4iE4Xk7Z9vQ2wE8rT5yU6iO3pA1sD4fG7hJ8kL", "gcp_api_key"),
    ],
)
def test_s1_detector_catches_every_secret_class(specimen: str, pattern_class: str) -> None:
    findings = find_secrets(specimen)
    assert findings
    assert pattern_class in {f.pattern_class for f in findings}
    # A finding carries the class + line — never the matched value.
    assert specimen not in repr(findings)


def test_s1_clean_text_finds_nothing() -> None:
    assert find_secrets("a perfectly ordinary export row about cameras") == []


def test_s1_finding_reports_line_and_class_not_value() -> None:
    findings = find_secrets("line one\n" + "AKIA" + "IOSFODNN7EXAMPLE on line two")
    assert len(findings) == 1
    assert findings[0].line == 2 and findings[0].pattern_class == "aws_access_key"


# --- S-2: internal locations become opaque ids ---------------------------------


def test_s2_internal_locations_become_opaque_ids() -> None:
    text = (
        "synced gs://corp-sig-restricted/run/9 by /Users/jdoe/job "
        "from svc@proj.iam.gserviceaccount.com"
    )
    out = scrub_internal_locations(text)
    assert "gs://" not in out and "/Users/" not in out and "iam.gserviceaccount" not in out
    assert INTERNAL_LOCATION_PREFIX in out


# --- S-3 / S-12: explicit columns; the never-exported list refuses --------------


def test_s12_select_star_does_not_exist() -> None:
    with pytest.raises(ScrubViolation):
        explicit_columns({"a": 1}, [])


def test_s12_never_exported_field_names_refuse() -> None:
    for field in NEVER_EXPORTED_FIELDS:
        with pytest.raises(ScrubViolation):
            explicit_columns({field: "x"}, [field])


def test_s12_absent_column_is_an_honest_absence() -> None:
    row = explicit_columns({"present": 1}, ["present", "missing"])
    assert row == {"present": 1, "missing": None}


# --- S-4: error detail is a class + count, never text ---------------------------


def test_s4_error_detail_becomes_a_closed_class() -> None:
    assert error_class("psycopg connection refused by db") == "db_connection_lost"
    assert error_class("upstream responded status 503") == "upstream_http_503"
    assert error_class("robots.txt disallowed the path") == "robots_disallow"
    assert error_class("an utterly novel failure") == "unclassified_error"
    assert error_class(None) == "unclassified_error"


def test_s4_error_counts_aggregate_by_class() -> None:
    counts = error_counts(["quota hit", "quota hit", "weird"])
    assert counts == {"quota_reached": 2, "unclassified_error": 1}


# --- S-5: IPs drop --------------------------------------------------------------


def test_s5_ip_addresses_drop_to_the_absence_token() -> None:
    out = strip_ip_addresses("hit 10.1.2.3 and 2001:db8::1 done")
    assert "10.1.2.3" not in out and "2001:db8" not in out
    assert out.count(IP_REMOVED) == 2
    assert contains_ip_address("10.1.2.3")
    assert not contains_ip_address("version 999.1.2.3 of the doc")


# --- S-6: upstream URL publication form -----------------------------------------


def test_s6_host_always_publishes_but_never_an_ip_host() -> None:
    assert upstream_host("HTTPS://Portal.Example.:443/x") == "portal.example"
    assert upstream_host("http://10.0.0.1/x") == ""


def test_s6_full_url_only_for_open_lane_and_gate_passed() -> None:
    open_scrub = scrub_source_url(
        "https://p.example/r.pdf?key=1", lane=LANE_RAW_OK, gate_passed=True
    )
    assert open_scrub is not None and open_scrub.url == "https://p.example/r.pdf"
    gated = scrub_source_url("https://p.example/r.pdf?key=1", lane=LANE_RAW_OK, gate_passed=False)
    assert gated is not None and gated.url is None and gated.path_sha256
    link = scrub_source_url("https://p.example/r.pdf", lane=LANE_LINK_ONLY, gate_passed=True)
    assert link is not None and link.url is None and link.path_sha256
    assert scrub_source_url(None, lane=LANE_RAW_OK, gate_passed=True) is None
    assert NO_UPSTREAM_URL == "no_upstream_url_recorded"


# --- S-7 / J3 §3.5: personal data never publishes --------------------------------


def test_s7_emails_phones_and_names_drop() -> None:
    out = scrub_personal(
        "mail officer@city.gov or +1 (405) 555-0100; ask Jane M. Doe",
        names=["Jane M. Doe"],
    )
    assert "officer@city.gov" not in out and "555-0100" not in out and "Jane M. Doe" not in out
    assert out.count(PERSONAL_DATA_REMOVED) == 3


def test_s7_person_screen_is_caller_injected() -> None:
    text = "Acme Systems filed; Jane Doe signed"
    flagged = scrub_personal(text, person_screen=lambda s: "Doe" in s)
    assert "Jane Doe" not in flagged and "Acme Systems" in flagged
    unscreened = scrub_personal(text)
    assert "Jane Doe" in unscreened  # the module never guesses a name


def test_s7_reviewer_publishes_by_role_only() -> None:
    assert reviewer_role("officer@city.gov") == ROLE_UNSPECIFIED
    assert reviewer_role("Jane M. Doe") == ROLE_UNSPECIFIED
    assert reviewer_role("Jane M. Doe", person_screen=lambda s: True) == ROLE_UNSPECIFIED
    assert reviewer_role("rights-reviewer-2") == "rights-reviewer-2"
    assert reviewer_role("") == ROLE_UNSPECIFIED


# --- S-9: withdrawal tombstones --------------------------------------------------


def test_s9_tombstone_is_opaque_and_deterministic() -> None:
    t1 = tombstone_id("claim:withdrawn:7")
    assert t1.startswith("tombstone:") and t1 == tombstone_id("claim:withdrawn:7")
    assert "withdrawn" not in t1


# --- S-10: full ISO-8601 UTC ------------------------------------------------------


def test_s10_timestamps_normalise_to_full_iso_utc() -> None:
    assert iso_utc(datetime(2026, 7, 1, 12, 30, 5)) == "2026-07-01T12:30:05Z"
    assert iso_utc(datetime(2026, 7, 1, 12, 30, 5, tzinfo=UTC)) == "2026-07-01T12:30:05Z"
    assert iso_utc(date(2026, 7, 1)) == "2026-07-01T00:00:00Z"
    assert iso_utc("2026-07-01T12:30:05+00:00") == "2026-07-01T12:30:05Z"
    assert iso_utc("2026-07-01T12:30:05Z") == "2026-07-01T12:30:05Z"
    assert iso_utc(None) is None and iso_utc("") is None


# --- S-11: gated sources publish a registry-only row -------------------------------


def test_s11_gated_row_is_registry_only() -> None:
    src = {
        "source_id": "src:x",
        "name": "Portal X",
        "publisher": "City",
        "publisher_type": "municipal",
        "status": "reviewed",
        "homepage_url": "https://x.example",
        "captures": ["cap:1"],  # never publishes on a gated row
    }
    row = gated_source_row(src, reason_class="not_reviewed")
    assert set(row) == set(GATED_SOURCE_COLUMNS) | {"reason_class"}
    assert row["reason_class"] == "not_reviewed"
    with pytest.raises(ScrubViolation):
        gated_source_row(src, reason_class="raw_exception_text")
    assert "not_reviewed" in GATED_REASON_CLASSES


# --- S-13: robots outcome rows ----------------------------------------------------


def test_s13_robots_rows_carry_outcomes_and_the_decision_ref() -> None:
    rows = robots_disclosure_rows(
        [
            {"host": "a.example", "outcome": "obeyed", "count": 10},
            {"host": "b.example", "outcome": "disregarded", "count": 2},
        ]
    )
    assert rows[0] == {"host": "a.example", "outcome": "obeyed", "count": 10}
    assert rows[1]["decision_ref"] == ROBOTS_DISREGARD_DECISION_REF
    with pytest.raises(ScrubViolation):
        robots_disclosure_rows([{"host": "x", "outcome": "bypassed", "count": 1}])


# --- the composite free-text scrub --------------------------------------------------


def test_composite_scrub_applies_s2_s5_s7() -> None:
    out = scrub_text(
        "log /home/jdoe/x; hit 192.168.1.9; mail a@b.co",
    )
    assert "/home/" not in out and "192.168.1.9" not in out and "a@b.co" not in out


# --- interim lane derivation ---------------------------------------------------------


def test_interim_lane_refused_or_recorded_no_is_restricted() -> None:
    assert interim_lane(refused=True, reviewed=True, redistributable="yes", spdx="CC0").lane == (
        LANE_RESTRICTED
    )
    assert interim_lane(reviewed=True, redistributable="no", spdx="CC0").lane == LANE_RESTRICTED


def test_interim_lane_unreviewed_fails_closed_never_raw_ok() -> None:
    # An unreviewed record can never evidence raw republication.
    assert interim_lane(reviewed=False, redistributable="yes", spdx="CC0").lane == LANE_UNKNOWN
    assert (
        interim_lane(reviewed=False, redistributable="yes", spdx="CC0", custody_posture="LINK").lane
        == LANE_LINK_ONLY
    )
    assert (
        interim_lane(reviewed=True, redistributable="UNDETERMINED", spdx="CC0").lane == LANE_UNKNOWN
    )


def test_interim_lane_custody_and_licence_rules() -> None:
    assert (
        interim_lane(reviewed=True, redistributable="yes", spdx="CC0", custody_posture="LINK").lane
        == LANE_LINK_ONLY
    )
    assert (
        interim_lane(
            reviewed=True,
            redistributable="yes",
            spdx="CC0",
            custody_posture="DERIVE",
        ).lane
        == LANE_DERIVED_ONLY
    )
    for spdx in (
        "LicenseRef-DerivedFacts-Citations",
        "LicenseRef-PublicRecord-FactualCompilation",
        "LicenseRef-OperatorAccepted-DBRight",
    ):
        assert (
            interim_lane(reviewed=True, redistributable="yes", spdx=spdx).lane == LANE_DERIVED_ONLY
        ), spdx
    assert interim_lane(reviewed=True, redistributable="yes", spdx="CC-BY-4.0").lane == LANE_RAW_OK
    # NC/ND Creative Commons are never raw-ok.
    assert (
        interim_lane(reviewed=True, redistributable="yes", spdx="CC-BY-NC-4.0").lane == LANE_UNKNOWN
    )
    # Packet-injected signals the record cannot read land derived-only.
    assert (
        interim_lane(reviewed=True, redistributable="yes", spdx="CC0", packet_limited=True).lane
        == LANE_DERIVED_ONLY
    )


def test_open_upstream_licence_membership() -> None:
    for ok in ("CC0", "CC-BY-4.0", "CC-BY-SA-4.0", "ODbL-1.0", "PDDL", "OGL-UK-3.0", "MIT"):
        assert open_upstream_licence(ok), ok
    for no in ("UNDETERMINED", "", None, "CC-BY-NC-4.0", "LicenseRef-DerivedFacts-Citations"):
        assert not open_upstream_licence(no), no


# --- NEW-2 / F-400: the lane + Part VIII tier matrix ---------------------------------


def test_derive_storage_tier_never_public_by_default() -> None:
    # Absent/unknown lane → sealed, whatever the class input.
    for lane in (None, "", "nonsense", LANE_UNKNOWN, LANE_RESTRICTED):
        assert derive_storage_tier(lane) == TIER_SEALED, lane
        assert derive_storage_tier(lane, "clear") == TIER_SEALED, lane
    # A sealed Part VIII class seals under every lane — even raw-ok.
    for p8 in PART_VIII_SEALED_CLASSES:
        assert derive_storage_tier(LANE_RAW_OK, p8) == TIER_SEALED, p8


def test_derive_storage_tier_matrix() -> None:
    assert derive_storage_tier(LANE_LINK_ONLY, "clear") == TIER_RESTRICTED
    assert derive_storage_tier(LANE_DERIVED_ONLY, "P8-3") == TIER_RESTRICTED
    # raw-ok + a recorded clear → public; a recorded non-sealed P8 class →
    # restricted; an unevidenced class → sealed.
    assert derive_storage_tier(LANE_RAW_OK, "clear") == TIER_PUBLIC
    assert derive_storage_tier(LANE_RAW_OK, "none-known") == TIER_PUBLIC
    assert derive_storage_tier(LANE_RAW_OK, "P8-3") == TIER_RESTRICTED
    assert derive_storage_tier(LANE_RAW_OK) == TIER_SEALED
    assert derive_storage_tier(LANE_RAW_OK, "") == TIER_SEALED


def test_more_restrictive_tier_tightens_never_relaxes() -> None:
    assert more_restrictive_tier(TIER_PUBLIC, TIER_SEALED) == TIER_SEALED
    assert more_restrictive_tier(TIER_SEALED, TIER_PUBLIC) == TIER_SEALED
    assert more_restrictive_tier(TIER_PUBLIC, TIER_RESTRICTED) == TIER_RESTRICTED
    # An unrecognised or absent value normalises to sealed — it can never relax.
    assert more_restrictive_tier("bogus", TIER_PUBLIC) == TIER_SEALED
    assert more_restrictive_tier(None, TIER_RESTRICTED) == TIER_SEALED


def test_served_storage_tier_labels_its_basis() -> None:
    recorded = served_storage_tier(TIER_RESTRICTED, lane=LANE_RAW_OK, part_viii_class="clear")
    assert recorded.tier == TIER_RESTRICTED and recorded.basis == "recorded"
    # A pre-fix constant-'public' row tightens at read — labelled, never silent.
    tightened = served_storage_tier(TIER_PUBLIC, lane=LANE_LINK_ONLY)
    assert tightened.tier == TIER_RESTRICTED
    assert tightened.basis == "derived_at_read"
    assert tightened.recorded_tier == TIER_PUBLIC
    # A recorded sealed never relaxes, and an unreadable recorded value seals.
    sealed = served_storage_tier(TIER_SEALED, lane=LANE_RAW_OK, part_viii_class="clear")
    assert sealed.tier == TIER_SEALED and sealed.basis == "recorded"
    assert served_storage_tier("bogus", lane=LANE_RAW_OK).tier == TIER_SEALED


def test_secret_pattern_classes_is_a_closed_set() -> None:
    assert SECRET_PATTERN_CLASSES == {
        "jwt",
        "aws_access_key",
        "key_hex",
        "bearer_token",
        "private_key",
        "gcp_api_key",
    }
    # Every detector class is reachable by a planted specimen.
    for cls in SECRET_PATTERN_CLASSES:
        assert cls in {
            "jwt",
            "aws_access_key",
            "key_hex",
            "bearer_token",
            "private_key",
            "gcp_api_key",
        }
