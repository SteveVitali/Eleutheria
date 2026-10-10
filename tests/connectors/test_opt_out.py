# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The host-level opt-out register + reservation refusal paths (P36.1a).

Two controls land together, both fixture-exercised with no sockets:

* **§26 rule 7** — the host-level opt-out register is consulted before EVERY
  fetch (before even the robots probe); a listed host receives zero egress.
* **SIG-INGEST-046c** — an affirmative machine-readable rights reservation on a
  response (Content-Signal / TDM-Reservation / X-Robots-Tag / Article 4 meta)
  is honoured as a refusal: bytes are never captured, the refusal is recorded
  distinctly from ``UNDETERMINED``, and GL-GATE-08's ``robots_disregarded``
  behaviour is untouched.
"""

from __future__ import annotations

import dataclasses
import json
from datetime import UTC, date, datetime
from typing import Any

import pytest
from connectors.loader import IngestionNotPermitted, assert_loadable
from connectors.net import HostOptOut, ReservationRefused
from connectors.opt_out import (
    OPT_OUT_REGISTER_ENV,
    OptOutRegisterError,
    load_register,
    normalize_host,
    parse_register,
)
from connectors.pipeline import run
from connectors.registry import _reservation_from_row
from connectors.review import gate_breakdown, review_metadata_violations
from connectors.runner import live_gate_reasons
from connectors.stages import FetchResult
from policy.rights import RightsReservation

_REGISTER = """\
register_version = "sig.opt-out-register/1"

[[opt_outs]]
host = "portal.example"
recorded_on = 2026-10-01
evidence = "intake record INTAKE-TEST-1"
note = "fixture opt-out"

[[opt_outs]]
host = "www.news.example"
recorded_on = 2026-10-02
evidence = "operator instruction 2026-10-02"
"""


def _reserved_fixture(kind: str = "content_signal") -> RightsReservation:
    return RightsReservation(
        kind=kind,
        verbatim="ai-train=no",
        observed_on=date(2026, 10, 1),
        evidence="test fixture",
    )


def _response(
    url: str, *, headers: dict[str, str] | None = None, body: bytes | None = None
) -> FetchResult:
    return FetchResult(
        url=url,
        status=200,
        body=body if body is not None else json.dumps({"id": "p1", "cameras": 1}).encode(),
        media_type="application/json",
        retrieved_at=datetime(2026, 10, 1, tzinfo=UTC),
        headers=headers or {},
    )


# --- the register itself ------------------------------------------------------


def test_register_parses_and_hosts_normalize() -> None:
    register = parse_register(_REGISTER)
    assert len(register.entries) == 2
    assert normalize_host("HTTPS://Portal.Example:8443/x") == "portal.example"
    assert normalize_host("Portal.Example.") == "portal.example"
    assert register.is_listed("portal.example")
    assert not register.is_listed("other.example")


def test_a_listed_host_covers_its_subdomains() -> None:
    register = parse_register(_REGISTER)
    # Opting out of portal.example covers www.portal.example — a host-level
    # opt-out is never dodged by a hostname tweak.
    assert register.is_listed("www.portal.example")
    assert register.is_listed("a.b.portal.example")
    # The reverse never holds: www.news.example lists only itself and below.
    assert register.is_listed("www.news.example")
    assert not register.is_listed("news.example")


def test_register_reason_carries_record_date_and_evidence() -> None:
    register = parse_register(_REGISTER)
    reason = register.reason_for("portal.example")
    assert reason is not None
    assert "portal.example" in reason
    assert "2026-10-01" in reason
    assert "INTAKE-TEST-1" in reason


@pytest.mark.parametrize(
    "row",
    [
        'host = ""\nrecorded_on = 2026-10-01\nevidence = "e"',  # empty host
        'host = "h.example"\nevidence = "e"',  # missing recorded_on
        'host = "h.example"\nrecorded_on = 2026-10-01',  # missing evidence (§3.1)
        'host = "h.example"\nrecorded_on = "yesterday"\nevidence = "e"',  # bad date
    ],
)
def test_malformed_register_rows_fail_closed(row: str) -> None:
    # An opt-out register asserts only on evidence: a malformed row never
    # parses silently into "no opt-outs" (fail-closed).
    with pytest.raises(OptOutRegisterError):
        parse_register(f"[[opt_outs]]\n{row}\n")


def test_duplicate_hosts_fail_closed() -> None:
    with pytest.raises(OptOutRegisterError, match="duplicate"):
        parse_register(
            '[[opt_outs]]\nhost = "h.example"\nrecorded_on = 2026-10-01\nevidence = "a"\n'
            '[[opt_outs]]\nhost = "h.example"\nrecorded_on = 2026-10-02\nevidence = "b"\n'
        )


def test_env_override_applies_without_a_rebuild(tmp_path: Any, monkeypatch: Any) -> None:
    # §26 rule 7's "immediately": pointing $SIG_OPT_OUT_REGISTER at a file the
    # operator can swap makes an entry apply on the next consult — no code
    # change, no registry rebuild (the mechanism E2-06/NEW-3 found missing).
    override = tmp_path / "register.toml"
    override.write_text(_REGISTER, encoding="utf-8")
    monkeypatch.setenv(OPT_OUT_REGISTER_ENV, str(override))
    register = load_register()
    assert register.is_listed("portal.example")


def test_a_missing_env_override_fails_closed(tmp_path: Any, monkeypatch: Any) -> None:
    monkeypatch.setenv(OPT_OUT_REGISTER_ENV, str(tmp_path / "absent.toml"))
    with pytest.raises(OptOutRegisterError):
        load_register()


def test_packaged_register_loads_and_is_well_formed() -> None:
    # The committed artifact parses under the fail-closed rules (its contents
    # are deliberately not pinned — rows are append-only operational data).
    register = load_register()
    assert isinstance(register.entries, tuple)


# --- the fetch seam -----------------------------------------------------------


def test_opt_out_host_refuses_with_zero_egress(make_fetcher, transport_factory) -> None:  # type: ignore[no-untyped-def]
    # Before ANY fetch — before even the robots probe — a listed host refuses:
    # zero egress of any kind, the refusal recorded verbatim.
    url = "https://portal.example/api"
    transport = transport_factory({url: _response(url)})
    fetcher = make_fetcher(transport, opt_out_register=parse_register(_REGISTER))
    with pytest.raises(HostOptOut) as exc:
        fetcher.fetch(url)
    assert exc.value.host == "portal.example"
    assert transport.robots_log == []  # not even robots.txt was probed
    assert transport.request_log == []  # no request ever left
    assert fetcher.opt_out_refusals == [
        {"url": url, "host": "portal.example", "reason": exc.value.reason}
    ]


def test_opt_out_verdict_is_recorded_without_a_probe(make_fetcher, transport_factory) -> None:  # type: ignore[no-untyped-def]
    url = "https://portal.example/api"
    transport = transport_factory({url: _response(url)})
    fetcher = make_fetcher(transport, opt_out_register=parse_register(_REGISTER))
    assert not fetcher.can_fetch(url)
    assert transport.robots_log == []  # the verdict cost zero egress too


def test_content_signal_response_refuses_before_capture(make_fetcher, transport_factory) -> None:  # type: ignore[no-untyped-def]
    # SIG-INGEST-046c: ``ai-train=no`` on the response is honoured as a refusal
    # — the request happened (the signal rides the response), but the bytes are
    # never captured and the signals are kept verbatim for the rights record.
    url = "https://portal.example/api"
    transport = transport_factory(
        {url: _response(url, headers={"Content-Signal": "ai-train=no, search=yes"})}
    )
    fetcher = make_fetcher(transport)
    with pytest.raises(ReservationRefused) as exc:
        fetcher.fetch(url)
    assert exc.value.host == "portal.example"
    assert transport.request_log == [url]  # the response was observed…
    assert fetcher.reservations == [
        {
            "url": url,
            "host": "portal.example",
            "status": 200,
            "signals": [{"kind": "content_signal", "detail": "ai-train=no"}],
        }
    ]
    assert exc.value.verdict.signals[0].detail == "ai-train=no"  # verbatim


@pytest.mark.parametrize(
    "headers",
    [
        {"TDM-Reservation": "1"},  # EU DSM Article 4, header form
        {"TDM-Reservation": "true"},
        {"X-Robots-Tag": "noindex, noai"},
    ],
)
def test_tdm_and_x_robots_reservations_refuse(make_fetcher, transport_factory, headers) -> None:  # type: ignore[no-untyped-def]
    url = "https://portal.example/api"
    transport = transport_factory({url: _response(url, headers=headers)})
    fetcher = make_fetcher(transport)
    with pytest.raises(ReservationRefused):
        fetcher.fetch(url)
    assert len(fetcher.reservations) == 1


def test_meta_reservation_on_html_refuses(make_fetcher, transport_factory) -> None:  # type: ignore[no-untyped-def]
    # The page-level Article 4 form (TDMRep meta): only HTML is scanned.
    url = "https://portal.example/page"
    body = b'<html><head><meta name="tdm-reservation" content="1"></head><body/></html>'
    result = FetchResult(
        url=url,
        status=200,
        body=body,
        media_type="text/html",
        retrieved_at=datetime(2026, 10, 1, tzinfo=UTC),
    )
    transport = transport_factory({url: result})
    fetcher = make_fetcher(transport)
    with pytest.raises(ReservationRefused):
        fetcher.fetch(url)


def test_a_permissive_response_still_fetches(make_fetcher, transport_factory) -> None:  # type: ignore[no-untyped-def]
    # A response without a reservation is unchanged: absent signals are never
    # treated as refusals (nor as grants).
    url = "https://portal.example/api"
    transport = transport_factory(
        {url: _response(url, headers={"Content-Signal": "search=yes, ai-train=yes"})}
    )
    fetcher = make_fetcher(transport)
    assert fetcher.fetch(url).status == 200
    assert fetcher.reservations == []


def test_reservation_wins_over_a_challenge_status(make_fetcher, transport_factory) -> None:  # type: ignore[no-untyped-def]
    # The reservation is the stronger signal: a 403 body that also carries a
    # reservation is a refusal, not a challenge outcome.
    url = "https://portal.example/api"
    result = FetchResult(
        url=url,
        status=403,
        body=b"denied",
        media_type="text/plain",
        retrieved_at=datetime(2026, 10, 1, tzinfo=UTC),
        headers={"Content-Signal": "ai-train=no"},
    )
    transport = transport_factory({url: result})
    fetcher = make_fetcher(transport)
    with pytest.raises(ReservationRefused):
        fetcher.fetch(url)


def test_robots_disregarded_still_recorded_when_a_reservation_refuses(  # type: ignore[no-untyped-def]
    make_fetcher, transport_factory
) -> None:
    # GL-GATE-08 is untouched and the two axes stay distinct: a Disallow
    # verdict is recorded ``robots_disregarded`` as before, AND the
    # affirmative reservation — a different signal entirely — refuses.
    url = "https://portal.example/secret"
    transport = transport_factory(
        {url: _response(url, headers={"Content-Signal": "ai-train=no"})},
        robots_text="User-agent: *\nDisallow: /secret\n",
    )
    fetcher = make_fetcher(transport)
    with pytest.raises(ReservationRefused):
        fetcher.fetch(url)
    assert fetcher.robots_disregarded == [
        {"url": url, "host": "portal.example", "verdict": "disallowed"}
    ]
    assert not fetcher.can_fetch(url)


# --- the gate seams -----------------------------------------------------------


def test_reserved_source_refuses_at_the_loader_gate(permitted_source: Any) -> None:
    # A recorded reservation is honoured as a refusal on EVERY gate — the
    # loader gate included (SIG-INGEST-046c); the flag can never bypass it.
    reserved = dataclasses.replace(
        permitted_source,
        rights=dataclasses.replace(permitted_source.rights, reservation=_reserved_fixture()),
    )
    with pytest.raises(IngestionNotPermitted, match="reservation"):
        assert_loadable(reserved)


def test_live_gate_reasons_names_the_reservation(permitted_source: Any) -> None:
    reserved = dataclasses.replace(
        permitted_source,
        rights=dataclasses.replace(permitted_source.rights, reservation=_reserved_fixture()),
    )
    reasons = live_gate_reasons(reserved)
    assert any("reservation" in r and "content_signal" in r for r in reasons)


def test_live_gate_consults_the_opt_out_register(  # type: ignore[no-untyped-def]
    permitted_source, tmp_path, monkeypatch
) -> None:
    # §26 rule 7 at the gate: a newly listed host refuses the live run before
    # a socket is constructed, via the no-redeploy override seam.
    override = tmp_path / "register.toml"
    override.write_text(
        '[[opt_outs]]\nhost = "eyesonflock.com"\nrecorded_on = 2026-10-01\nevidence = "test"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv(OPT_OUT_REGISTER_ENV, str(override))
    reasons = live_gate_reasons(permitted_source)
    assert any("opt-out register" in r for r in reasons)


def test_gate_breakdown_marks_reserved_never_flip_ready(permitted_source: Any) -> None:
    # A reserved source is never flip-ready and never loadable — the refusal
    # routes to the operator, not to a flag flip (SIG-INGEST-046c).
    reserved = dataclasses.replace(
        permitted_source,
        rights=dataclasses.replace(permitted_source.rights, reservation=_reserved_fixture()),
    )
    breakdown = gate_breakdown(reserved)
    assert breakdown.rights_reserved
    assert not breakdown.flip_ready
    assert not breakdown.loadable


def test_review_metadata_flags_a_permitted_reserved_source(permitted_source: Any) -> None:
    # The flip-metadata rule: a flag on a refused record is a review-metadata
    # violation — the recorded refusal stands.
    reserved = dataclasses.replace(
        permitted_source,
        rights=dataclasses.replace(permitted_source.rights, reservation=_reserved_fixture()),
    )
    violations = review_metadata_violations([reserved])
    assert any("reservation" in v for v in violations)


def test_registry_reservation_subtable_is_fail_closed() -> None:
    # A malformed rights.reservation row raises rather than silently dropping a
    # refusal (the defining standard, §3.1).
    reservation = _reservation_from_row(
        "fixture",
        {
            "kind": "tdm_reservation",
            "verbatim": "TDM-Reservation: 1",
            "observed_on": date(2026, 10, 1),
            "evidence": "fetch record",
        },
    )
    assert reservation is not None and reservation.kind == "tdm_reservation"
    assert _reservation_from_row("fixture", None) is None
    with pytest.raises(ValueError):
        _reservation_from_row("fixture", {"kind": "tdm_reservation"})  # missing fields
    with pytest.raises(ValueError):
        _reservation_from_row("fixture", "tdm_reservation")  # not a table


# --- the run report -----------------------------------------------------------


def test_opt_out_refusal_records_on_the_run_report(  # type: ignore[no-untyped-def]
    make_fetcher, make_context, transport_factory, toy_connector
) -> None:
    # The refusal lands in the run report as a first-class disposition — never
    # a swallowed exception, never a disappearance — and no claim derives.
    url = "https://portal.example/p1"
    transport = transport_factory({url: _response(url)})
    fetcher = make_fetcher(transport, opt_out_register=parse_register(_REGISTER))
    ctx = make_context(fetcher=fetcher, parameters={"targets": [{"id": "p1", "url": url}]})
    report = run(toy_connector, ctx)
    assert [r["refusal"] for r in report.refusals] == ["HostOptOut"]
    assert report.claims == []
    assert report.captures == []
    assert report.disappearances == []  # refused, not unreachable
    assert transport.request_log == []  # zero egress


def test_reservation_refusal_records_on_the_run_report(  # type: ignore[no-untyped-def]
    make_fetcher, make_context, transport_factory, toy_connector
) -> None:
    url = "https://portal.example/p1"
    transport = transport_factory({url: _response(url, headers={"Content-Signal": "ai-train=no"})})
    ctx = make_context(
        fetcher=make_fetcher(transport), parameters={"targets": [{"id": "p1", "url": url}]}
    )
    report = run(toy_connector, ctx)
    assert [r["refusal"] for r in report.refusals] == ["ReservationRefused"]
    assert "ai-train=no" in report.refusals[0]["detail"]
    assert report.claims == []
    assert report.captures == []
