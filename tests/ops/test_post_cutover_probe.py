# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.67 — the post-DNS-cutover probe (``sig-ops post-cutover-probe``).

Fixture-verified, never live-pinned: the parsers + check verdicts are proven
against committed dig/curl/openssl/gcloud/whois captures — the ``good/`` tree
(the post-switch state the runbook's checklist expects) and ``precutover/``
(the real 2026-10-10 capture of the still-Squarespace zone, OP-09 not yet
landed). Failure-mode variants override single capture values in a stub
runner. The live leg is queued in RETURN PASS behind the operator's OP-09 —
these tests assert the probe's *semantics*, never the current DNS state
(BM-TEST-01: the zone is a living record).
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from ops import post_cutover_probe as pcp

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "post_cutover"
GOOD = FIXTURES / "good"
PRECUTOVER = FIXTURES / "precutover"
CHECKLIST = REPO_ROOT / "docs" / "build" / "reports" / "POST_CUTOVER_PROBE_CHECKLIST.md"


class StubRunner:
    """A ProbeRunner over an in-memory capture dict (key → stdout text)."""

    def __init__(self, outputs: dict[str, str | None], rc: int = 0):
        self.outputs = outputs
        self.rc = rc
        self.seen: list[tuple[str, tuple[str, ...]]] = []

    def run(self, key: str, argv: tuple[str, ...]) -> pcp.CmdResult | None:
        self.seen.append((key, argv))
        assert pcp.argv_is_readonly(argv), f"non-readonly argv reached the runner: {argv}"
        out = self.outputs.get(key)
        if out is None:
            return None
        return pcp.CmdResult(argv, self.rc, out, "")


def _capture_dict(root: Path) -> dict[str, str]:
    """Load a capture directory into the StubRunner's key→stdout map."""
    outputs: dict[str, str] = {}
    for key, fname in pcp.CAPTURE_FILES.items():
        path = root / fname
        if path.is_file():
            outputs[key] = path.read_text(encoding="utf-8")
    index = root / pcp.ROUTE_INDEX_FILE
    if index.is_file():
        for line in index.read_text(encoding="utf-8").splitlines():
            k, fname = line.split("\t")
            route_file = root / fname
            if route_file.is_file():
                outputs[k] = route_file.read_text(encoding="utf-8")
    return outputs


def _run(root: Path, leg: str = "l1", **overrides) -> dict:
    outputs = _capture_dict(root)
    outputs.update(overrides)
    return pcp.run_probe(
        leg=leg,
        project="sig-test-project",
        runner=StubRunner(outputs),
        repo_root=REPO_ROOT,
        now="2026-10-10T05:00:00Z",
    )


# --- the read-only command contract -------------------------------------------


def test_every_command_builder_stays_readonly() -> None:
    """The probe can only build read-only argv (OM-14: no mutation reachable)."""
    builders = [
        pcp._dig_argv("surveillancegraph.org", "NS"),
        pcp._dig_argv("surveillancegraph.org", "A", dnssec=True),
        pcp._curl_head_argv("https://surveillancegraph.org/"),
        pcp._curl_get_argv("https://surveillancegraph.org/sitemap.xml"),
        pcp._openssl_s_client_argv("surveillancegraph.org"),
        pcp._openssl_x509_argv(),
        pcp._gcloud_cert_argv("sig-web-cert", "proj"),
        pcp._whois_argv("surveillancegraph.org"),
    ]
    for argv in builders:
        assert pcp.argv_is_readonly(argv), f"builder produced non-readonly argv: {argv}"


@pytest.mark.parametrize(
    "argv",
    [
        ("gcloud", "compute", "ssl-certificates", "delete", "sig-web-cert"),
        ("gcloud", "compute", "ssl-certificates", "describe", "c", "--global", "update"),
        ("gcloud", "compute", "ssl-certificates", "describe", "c", "patch"),
        ("gcloud", "compute", "addresses", "create", "x"),
        ("curl", "-sSI", "-X", "DELETE", "https://x/"),
        ("curl", "-sS", "--data", "x=1", "https://x/"),
        ("dig", "+nsupdate", "x", "A"),
        ("openssl", "req", "-new"),
        ("openssl", "x509", "-signkey", "k.pem"),
        ("rm", "-rf", "/"),
        ("whois", "-h", "evil.example", "x"),
    ],
)
def test_mutating_argv_is_refused(argv: tuple[str, ...]) -> None:
    assert not pcp.argv_is_readonly(argv)


def test_live_runner_refuses_a_mutating_argv() -> None:
    with pytest.raises(ValueError, match="non-readonly"):
        pcp.LiveRunner().run("ns", ("gcloud", "compute", "addresses", "create", "x"))


# --- the parsers ---------------------------------------------------------------


def test_parse_dig_records_and_status() -> None:
    text = (PRECUTOVER / "dig_ns.txt").read_text()
    records = pcp.parse_dig_records(text, "NS")
    assert {r["data"].rstrip(".") for r in records} == {
        "nsc1.squarespacedns.com",
        "nsc2.squarespacedns.com",
        "nsc3.squarespacedns.com",
        "nsc4.squarespacedns.com",
    }
    assert pcp.parse_dig_status(text) == "NOERROR"


def test_parse_dig_flags() -> None:
    text = (PRECUTOVER / "dig_dnssec_apex_a.txt").read_text()
    assert "ad" in pcp.parse_dig_flags(text)
    assert pcp.parse_dig_records(text, "RRSIG"), "fixture should carry an RRSIG"


def test_parse_head_and_redirect_normalisation() -> None:
    head = pcp.parse_head((PRECUTOVER / "curl_https_www.txt").read_text())
    assert head["status"] == 301
    assert head["headers"]["location"] == "https://surveillancegraph.org:443/"
    assert (
        pcp.normalize_redirect_target("https://surveillancegraph.org:443/")
        == "https://surveillancegraph.org"
    )
    assert (
        pcp.normalize_redirect_target("http://surveillancegraph.org:80/")
        == "http://surveillancegraph.org"
    )


def test_parse_x509() -> None:
    cert = pcp.parse_x509((PRECUTOVER / "openssl_apex.txt").read_text())
    assert cert["sans"] == ["surveillancegraph.org", "www.surveillancegraph.org"]
    assert cert["notAfter"] == "Dec 22 18:47:21 2026 GMT"


def test_parse_whois_statuses_normalised() -> None:
    statuses = pcp.parse_whois_statuses((PRECUTOVER / "whois.txt").read_text())
    assert "clienttransferprohibited" in statuses
    assert "clientdeleteprohibited" in statuses
    assert not set(statuses) & pcp.BAD_WHOIS_STATUSES


def test_parse_sitemap_locs() -> None:
    xml = (
        "<urlset><url><loc>https://surveillancegraph.org/</loc></url>"
        "<url><loc> https://surveillancegraph.org/dossier/ </loc></url></urlset>"
    )
    assert pcp.parse_sitemap_locs(xml) == [
        "https://surveillancegraph.org/",
        "https://surveillancegraph.org/dossier/",
    ]


def test_is_cloudflare_anycast() -> None:
    assert pcp.is_cloudflare_anycast("104.16.1.1")
    assert pcp.is_cloudflare_anycast("172.64.0.1")
    assert pcp.is_cloudflare_anycast("188.114.96.1")
    assert not pcp.is_cloudflare_anycast("136.81.80.102")


# --- leg L1: the post-switch good state ----------------------------------------


def test_leg_l1_good_state_all_green() -> None:
    record = _run(GOOD)
    assert record["version"] == "sig.probe-run/1"
    assert record["leg"] == "L1"
    assert record["overall"] == "pass", json.dumps(record["checks"], indent=1)[:2000]
    assert record["cutover_detected"] == "detected"
    for name in pcp.L1_CHECKS:
        assert name in record["checks"], name
    assert record["checks"]["ns_pair"]["all_cloudflare"] is True
    assert record["checks"]["dnssec"]["ds_keytags"] == ["2371"]
    assert record["checks"]["cert_status"]["managed_status"] == "ACTIVE"
    assert record["checks"]["mail"]["posture"] == "no_mail (pre-OP-10 design)"


def test_leg_l1_pre_cutover_reports_not_landed() -> None:
    """The real 2026-10-10 capture — OP-09 has not run; the probe says so."""
    record = _run(PRECUTOVER)
    assert record["overall"] == "fail"
    assert record["cutover_detected"] == "not_detected"
    ns = record["checks"]["ns_pair"]
    assert ns["verdict"] == "fail"
    assert ns["state"] == "pre_cutover"
    assert any("squarespacedns" in h for h in ns["nameservers"])
    assert record["checks"]["dnssec"]["verdict"] == "fail"
    # …while everything OP-09-independent still measures green.
    for name in ("apex_a", "www_a", "apex_https", "apex_https_tls", "mail", "registrar_lock"):
        assert record["checks"][name]["verdict"] == "pass", name
    assert record["checks"]["routes"]["route_source"] == "ops/public_routes.toml"


# --- failure modes (each pins one check) ----------------------------------------


def test_missing_ad_flag_fails_dnssec() -> None:
    bad = (GOOD / "dig_dnssec_apex_a.txt").read_text().replace("qr rd ra ad", "qr rd ra")
    record = _run(GOOD, dnssec_a=bad)
    dnssec = record["checks"]["dnssec"]
    assert dnssec["verdict"] == "fail"
    assert dnssec["ad_flag"] is False


def test_legacy_ds_only_fails_dnssec() -> None:
    record = _run(GOOD, ds=(PRECUTOVER / "dig_ds.txt").read_text())
    assert record["checks"]["dnssec"]["verdict"] == "fail"


def test_double_ds_rollover_is_a_pass_with_a_note() -> None:
    both = (GOOD / "dig_ds.txt").read_text() + (
        "surveillancegraph.org.\t3600\tIN\tDS\t17039 8 2 3F5E85B0\n"
    )
    record = _run(GOOD, ds=both)
    dnssec = record["checks"]["dnssec"]
    assert dnssec["verdict"] == "pass"
    assert dnssec["rollover_in_progress"] is True


def test_missing_cert_fails_apex_tls() -> None:
    record = _run(GOOD, openssl_apex="")
    assert record["checks"]["apex_https_tls"]["verdict"] == "fail"


def test_missing_san_fails_apex_tls() -> None:
    bad = (GOOD / "openssl_apex.txt").read_text().replace(", DNS:www.surveillancegraph.org", "")
    record = _run(GOOD, openssl_apex=bad)
    assert record["checks"]["apex_https_tls"]["verdict"] == "fail"


def test_cert_provisioning_fails_cert_status() -> None:
    doc = json.loads((GOOD / "gcloud_cert.txt").read_text())
    doc["managed"]["status"] = "PROVISIONING"
    record = _run(GOOD, gcloud_cert=json.dumps(doc))
    assert record["checks"]["cert_status"]["verdict"] == "fail"


def test_no_project_skips_cert_status() -> None:
    record = pcp.run_probe(
        leg="l1",
        project=None,
        runner=StubRunner(_capture_dict(GOOD)),
        repo_root=REPO_ROOT,
    )
    assert record["checks"]["cert_status"]["verdict"] == "skipped"
    assert record["overall"] != "pass"  # skipped never reads as a pass


def test_cloudflare_anycast_answer_fails_grey_cloud() -> None:
    proxied = "surveillancegraph.org.\t300\tIN\tA\t104.16.1.10\n"
    record = _run(GOOD, apex_a=proxied)
    check = record["checks"]["apex_a"]
    assert check["verdict"] == "fail"
    assert "grey-cloud" in check["reason"]


def test_wrong_apex_ip_fails() -> None:
    record = _run(GOOD, apex_a="surveillancegraph.org.\t300\tIN\tA\t203.0.113.9\n")
    assert record["checks"]["apex_a"]["verdict"] == "fail"


def test_www_not_redirecting_fails() -> None:
    ok_head = (GOOD / "curl_https_apex.txt").read_text()
    record = _run(GOOD, https_www=ok_head)  # www answers 200 instead of 301→apex
    assert record["checks"]["www_redirect"]["verdict"] == "fail"


def test_mail_mx_present_is_op10_posture() -> None:
    mx = "surveillancegraph.org.\t300\tIN\tMX\t10 mx.example-mail.net.\n"
    txt = 'surveillancegraph.org.\t300\tIN\tTXT\t"v=spf1 include:example-mail.net -all"\n'
    record = _run(GOOD, mx=mx, txt=txt)
    mail = record["checks"]["mail"]
    assert mail["verdict"] == "pass"
    assert mail["posture"].startswith("op10_configured")


def test_mail_drift_fails() -> None:
    record = _run(GOOD, txt='surveillancegraph.org.\t300\tIN\tTXT\t"some other txt"\n')
    assert record["checks"]["mail"]["verdict"] == "fail"


def test_mx_present_without_spf_fails() -> None:
    mx = "surveillancegraph.org.\t300\tIN\tMX\t10 mx.example-mail.net.\n"
    txt = 'surveillancegraph.org.\t300\tIN\tTXT\t"nothing relevant"\n'
    record = _run(GOOD, mx=mx, txt=txt)
    assert record["checks"]["mail"]["verdict"] == "fail"


def test_pending_transfer_fails_registrar_lock() -> None:
    whois = (GOOD / "whois.txt").read_text() + (
        "\nDomain Status: pendingTransfer https://icann.org/epp#pendingTransfer\n"
    )
    record = _run(GOOD, whois=whois)
    reg = record["checks"]["registrar_lock"]
    assert reg["verdict"] == "fail"
    assert "pendingtransfer" in reg["drift"]


def test_absent_tool_skips_never_fakes() -> None:
    record = _run(GOOD, ns=None, whois=None)
    assert record["checks"]["ns_pair"]["verdict"] == "skipped"
    assert record["checks"]["registrar_lock"]["verdict"] == "skipped"


# --- leg L2: the cert-renewal read ----------------------------------------------


def test_leg_l2_good_state() -> None:
    record = _run(GOOD, leg="l2")
    assert record["leg"] == "L2"
    assert record["overall"] == "pass"
    assert set(record["checks"]) == {"ns_pair", "apex_https_tls", "cert_status", "renewal_read"}
    assert record["checks"]["renewal_read"]["expected_expiry"] == pcp.CERT_EXPIRY_ISO


def test_leg_l2_cert_not_active_fails() -> None:
    doc = json.loads((GOOD / "gcloud_cert.txt").read_text())
    doc["managed"]["status"] = "FAILED_NOT_VISIBLE"
    record = _run(GOOD, leg="l2", gcloud_cert=json.dumps(doc))
    assert record["checks"]["renewal_read"]["verdict"] == "fail"


# --- capture round-trip + the CLI -----------------------------------------------


def test_capture_runner_replays_a_directory() -> None:
    live = pcp.run_probe(
        leg="l1",
        project="sig-test-project",
        runner=pcp.CaptureRunner(GOOD),
        repo_root=REPO_ROOT,
        now="2026-10-10T05:00:00Z",
    )
    stub = _run(GOOD)
    assert live["overall"] == stub["overall"] == "pass"
    for name, check in live["checks"].items():
        assert check["verdict"] == stub["checks"][name]["verdict"], name


def test_capture_runner_reports_missing_files_as_skipped(tmp_path: Path) -> None:
    record = pcp.run_probe(
        leg="l2",
        project="x",
        runner=pcp.CaptureRunner(tmp_path),
        repo_root=REPO_ROOT,
    )
    assert record["checks"]["ns_pair"]["verdict"] == "skipped"


def test_cli_from_capture_replays(tmp_path: Path) -> None:
    out = tmp_path / "record.json"
    env = {**os.environ, "SIG_GCP_PROJECT": "sig-test-project"}
    proc = subprocess.run(
        [
            "uv",
            "run",
            "sig-ops",
            "post-cutover-probe",
            "--leg",
            "l1",
            "--from-capture",
            str(GOOD),
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    record = json.loads(out.read_text())
    assert record["overall"] == "pass"


def test_cli_from_capture_precutover_exits_1(tmp_path: Path) -> None:
    out = tmp_path / "record.json"
    proc = subprocess.run(
        [
            "uv",
            "run",
            "sig-ops",
            "post-cutover-probe",
            "--leg",
            "l1",
            "--from-capture",
            str(PRECUTOVER),
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 1
    record = json.loads(out.read_text())
    assert record["cutover_detected"] == "not_detected"


# --- the committed checklist ----------------------------------------------------


def test_probe_checklist_exists_and_covers_every_check() -> None:
    assert CHECKLIST.is_file()
    text = CHECKLIST.read_text(encoding="utf-8")
    for name in pcp.L1_CHECKS + ("www_redirect", "apex_https", "renewal_read"):
        assert name in text, f"checklist never names check {name}"
    for needle in ("L1", "L2", "OP-09", "post-cutover-probe", "DNS_CUTOVER_RUNBOOK"):
        assert needle in text, f"checklist lost {needle}"
    assert "2026-11-22" in text  # future-ok: scheduled: the ticket's L2 window
