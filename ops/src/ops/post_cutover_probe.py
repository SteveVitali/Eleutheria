# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""post_cutover_probe — the P35.67 post-DNS-cutover probe (leg L1) and the
managed-cert renewal read (leg L2), emitting one ``sig.probe-run/1`` record.

The probe is the machine half of the OP-09 post-switch checklist in
``docs/build/reports/DNS_CUTOVER_RUNBOOK.md`` — it verifies that the A-3
"yes, all three" posture actually holds in production after the operator's
nameserver switch:

* the Cloudflare NS pair serves the zone (runbook step 8),
* apex + ``www`` still answer the load-balancer IP and never a Cloudflare
  anycast address (steps 9/10/14 — the grey-cloud rule that keeps the
  Google-managed certificate renewing toward its December expiry — the
  inventoried ``CERT_EXPIRY_ISO`` below),
* ``www`` 301s to the apex, the apex answers 200 on TLS with SAN
  ``{apex, www}``, and ``:80`` 301s to HTTPS (steps 11/12/15),
* DNSSEC validates — an RRSIG on the apex ``A`` answer, the ``ad`` flag, and
  the Cloudflare DS at the parent (step 13; the legacy ``17039`` DS leaving
  is the rollover's end state, its presence alongside is the in-flight
  double-DS state — both are recorded honestly),
* the managed certificate reads ``ACTIVE`` on ``gcloud … describe``
  (read-only; skipped, never fabricated, when ADC is absent),
* every public route in the sitemap answers,
* the mail posture is classified — ``no_mail`` (empty MX + ``v=spf1 -all``,
  the pre-OP-10 design) or ``op10_configured`` (MX present after the
  operator's ``contact@`` alias leg) — and anomalies fail loudly,
* the registrar WHOIS shows no transfer-state drift.

**Read-only by construction.** The probe issues only ``dig``, ``curl -sSI``
/ ``curl -sS`` (HEAD/GET), ``openssl s_client`` + ``openssl x509 -noout``,
``gcloud compute ssl-certificates describe``, and ``whois`` — the command
table :data:`READONLY_ARGV_RULES` names every allowed argv shape and a test
pins that no mutating verb is reachable. There is no ``shell=True`` anywhere:
every command is an argv list built by a named builder function.

Two runners implement the same seam: :class:`LiveRunner` shells out (and can
``--capture`` every raw output for the run-ledger evidence), and
:class:`CaptureRunner` replays a captured directory — the same file names a
``--capture`` run writes, so a committed capture is also a test fixture. A
check whose tool is absent or whose read fails reports ``skipped`` (or
``fail`` when the read proves a bad answer), never a fabricated pass.
"""

from __future__ import annotations

import ipaddress
import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

PROBE_RUN_VERSION = "sig.probe-run/1"
PROBE_NAME = "post-cutover"

# --- the runbook's expected posture (D-P34.50-1 / A-3) ------------------------
CLOUDFLARE_NS_SUFFIX = "ns.cloudflare.com"
LEGACY_DS_KEYTAG = "17039"  # the Squarespace-era DS; removed post-cutover
EXPECTED_APEX_IP = "136.81.80.102"  # the Google HTTPS LB static IP (ADR-098)
DEFAULT_DOMAIN = "surveillancegraph.org"
DEFAULT_CERT = "sig-web-cert"
# The managed cert's inventoried expiry (zone_inventory_2026-10-02; openssl
# s_client read) — the runbook's renewal deadline and the P34.4 alert anchor.
CERT_EXPIRY_ISO = "2026-12-22T18:47:21Z"  # future-ok: scheduled: inventoried cert expiry
EXPECTED_DENY_ALL_SPF = "v=spf1 -all"  # the no-mail design posture pre-OP-10

# Cloudflare's published IPv4 anycast ranges (public config, never a secret).
# An apex/www A answer inside one of these means the record is proxied — the
# grey-cloud rule is broken and the managed cert's renewal can silently fail.
CLOUDFLARE_ANYCAST_V4 = tuple(
    ipaddress.ip_network(cidr)
    for cidr in (
        "173.245.48.0/20",
        "103.21.244.0/22",
        "103.22.200.0/22",
        "103.31.4.0/22",
        "141.101.64.0/18",
        "108.162.192.0/18",
        "190.93.240.0/20",
        "188.114.96.0/20",
        "197.234.240.0/22",
        "198.41.128.0/17",
        "162.158.0.0/15",
        "104.16.0.0/13",
        "104.24.0.0/14",
        "172.64.0.0/13",
        "131.0.72.0/22",
    )
)

# WHOIS `Domain Status:` values that mean the registrar record drifted — a
# transfer or a hold is never an expected post-cutover state.
BAD_WHOIS_STATUSES = {
    "pendingtransfer",
    "serverhold",
    "clienthold",
    "redemptionperiod",
    "pendingdelete",
}

COMMAND_TIMEOUT_S = 20.0

# The read-only argv contract. Every command the probe can build matches one
# of these rules; `tests/ops/test_post_cutover_probe.py` asserts the built
# argv stay inside it and that no mutating token is ever reachable.
READONLY_ARGV_RULES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    # binary: (required leading tokens, forbidden tokens anywhere)
    "dig": (("dig",), ("+nsupdate", "-y", "nsupdate")),
    "curl": (
        ("curl",),
        ("-X", "--request", "-d", "--data", "-T", "--upload-file", "-F", "--form", "-o"),
    ),
    "openssl_s_client": (("openssl", "s_client"), ("req", "ca", "x509")),
    "openssl_x509": (("openssl", "x509", "-noout"), ("-signkey", "-req", "-CA")),
    "gcloud": (
        ("gcloud", "compute", "ssl-certificates", "describe"),
        ("create", "delete", "update", "add", "remove", "import", "patch", "set-"),
    ),
    "whois": (("whois",), ("-h", "-H")),
}

# The capture-file names LiveRunner writes and CaptureRunner reads — a
# `--capture` directory is a byte-exact replay fixture.
CAPTURE_FILES = {
    "ns": "dig_ns.txt",
    "apex_a": "dig_apex_a.txt",
    "www_a": "dig_www_a.txt",
    "ds": "dig_ds.txt",
    "dnssec_a": "dig_dnssec_apex_a.txt",
    "mx": "dig_mx.txt",
    "txt": "dig_txt.txt",
    "https_apex": "curl_https_apex.txt",
    "https_www": "curl_https_www.txt",
    "http_apex": "curl_http_apex.txt",
    "openssl_apex": "openssl_apex.txt",
    "gcloud_cert": "gcloud_cert.txt",
    "whois": "whois.txt",
}
_CAPTURE_KEY_PREFIXES = ("route:", "sitemap:")
ROUTE_INDEX_FILE = "routes.tsv"  # url \t capture-file-name
PUBLIC_ROUTES_TOML = Path(__file__).resolve().parents[3] / "ops" / "public_routes.toml"

# Route-sweep status semantics: a sitemap <loc> is a route the site itself
# advertises — it must serve (2xx/3xx). The allowlist fallback names routes
# that MAY be public: a deliberate 4xx (section not yet built, error pages)
# is recorded ``absent``, never counted a serve; 5xx/unreachable fails.
_ROUTE_SERVE = {200, 301, 302}
_ROUTE_ABSENT = {400, 401, 403, 404, 410}


def _utcnow() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class CmdResult:
    """One executed read: argv, exit code and captured output."""

    argv: tuple[str, ...]
    rc: int
    stdout: str
    stderr: str = ""


@dataclass(frozen=True)
class CheckResult:
    """One probe-run leg: a verdict plus structured, redaction-safe detail."""

    verdict: str  # "pass" | "fail" | "skipped"
    detail: dict[str, Any] = field(default_factory=dict)

    def as_json(self) -> dict[str, Any]:
        return {"verdict": self.verdict, **self.detail}


class ProbeRunner(Protocol):
    """The read seam every check goes through — live or captured."""

    def run(self, key: str, argv: tuple[str, ...]) -> CmdResult | None:
        """Execute (or replay) the read; ``None`` = the tool is absent."""
        ...


# --- command builders (argv only, never a shell) --------------------------------


def _dig_argv(name: str, rtype: str, *, dnssec: bool = False) -> tuple[str, ...]:
    argv: list[str] = ["dig"]
    if dnssec:
        argv += ["+dnssec"]
    argv += ["+noall", "+answer", "+comments", name, rtype]
    return tuple(argv)


def _curl_head_argv(url: str) -> tuple[str, ...]:
    return ("curl", "-sSI", "--max-time", "15", url)


def _curl_get_argv(url: str) -> tuple[str, ...]:
    return ("curl", "-sS", "--max-time", "20", url)


def _openssl_s_client_argv(domain: str) -> tuple[str, ...]:
    return (
        "openssl",
        "s_client",
        "-connect",
        f"{domain}:443",
        "-servername",
        domain,
        "-verify_return_error",
    )


def _openssl_x509_argv() -> tuple[str, ...]:
    return ("openssl", "x509", "-noout", "-dates", "-ext", "subjectAltName")


def _gcloud_cert_argv(cert: str, project: str) -> tuple[str, ...]:
    return (
        "gcloud",
        "compute",
        "ssl-certificates",
        "describe",
        cert,
        "--global",
        "--project",
        project,
        "--format=json",
    )


def _whois_argv(domain: str) -> tuple[str, ...]:
    return ("whois", domain)


def argv_is_readonly(argv: tuple[str, ...]) -> bool:
    """Does this argv stay inside the read-only contract?"""
    if len(argv) < 1:
        return False
    two = f"{argv[0]}_{argv[1]}" if len(argv) > 1 else ""
    key = two if two in READONLY_ARGV_RULES else argv[0]
    rules = READONLY_ARGV_RULES.get(key)
    if rules is None:
        return False
    required, forbidden = rules
    if tuple(argv[: len(required)]) != required:
        return False
    for tok in argv[len(required) :]:
        for bad in forbidden:
            if bad.startswith("--"):
                hit = tok == bad or tok.startswith(bad)
            elif bad.startswith("-"):
                hit = tok == bad  # an exact short flag, e.g. curl -X
            elif bad.endswith("-"):
                hit = tok.startswith(bad)  # a verb family, e.g. gcloud set-*
            else:
                hit = tok == bad  # a plain verb word, e.g. gcloud delete
            if hit:
                return False
    return True


class LiveRunner:
    """Executes the read commands; optionally captures every raw output."""

    def __init__(self, *, capture_dir: Path | None = None, timeout: float = COMMAND_TIMEOUT_S):
        self.capture_dir = capture_dir
        self.timeout = timeout
        if capture_dir is not None:
            capture_dir.mkdir(parents=True, exist_ok=True)

    def run(self, key: str, argv: tuple[str, ...]) -> CmdResult | None:
        if not argv_is_readonly(argv):
            raise ValueError(f"refusing non-readonly argv: {argv}")
        try:
            if argv[:2] == ("openssl", "s_client"):
                # s_client | x509 — one logical read, still argv-only.
                s_client = subprocess.run(  # noqa: S603
                    list(argv),
                    input="",
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    check=False,
                )
                x509 = subprocess.run(  # noqa: S603
                    list(_openssl_x509_argv()),
                    input=s_client.stdout,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    check=False,
                )
                result = CmdResult(argv, s_client.returncode, x509.stdout, s_client.stderr)
            else:
                proc = subprocess.run(  # noqa: S603
                    list(argv),
                    input="",
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    check=False,
                )
                result = CmdResult(argv, proc.returncode, proc.stdout, proc.stderr)
        except FileNotFoundError:
            return None
        except (subprocess.TimeoutExpired, OSError) as exc:
            result = CmdResult(argv, 124, "", f"{type(exc).__name__}: {exc}")
        if self.capture_dir is not None:
            if key in CAPTURE_FILES:
                (self.capture_dir / CAPTURE_FILES[key]).write_text(result.stdout, encoding="utf-8")
            elif key.startswith(_CAPTURE_KEY_PREFIXES):
                import hashlib

                url = key.split(":", 1)[1]
                prefix = key.split(":", 1)[0]
                fname = f"{prefix}_{hashlib.sha1(url.encode()).hexdigest()[:12]}.txt"  # noqa: S324
                (self.capture_dir / fname).write_text(result.stdout, encoding="utf-8")
                with (self.capture_dir / ROUTE_INDEX_FILE).open("a", encoding="utf-8") as fh:
                    fh.write(f"{key}\t{fname}\n")
        return result


class CaptureRunner:
    """Replays a ``--capture`` directory — offline fixture replay."""

    def __init__(self, capture_dir: Path):
        self.capture_dir = capture_dir

    def run(self, key: str, argv: tuple[str, ...]) -> CmdResult | None:
        if key in CAPTURE_FILES:
            path = self.capture_dir / CAPTURE_FILES[key]
            if not path.is_file():
                return None
            return CmdResult(argv, 0, path.read_text(encoding="utf-8"))
        if key.startswith(_CAPTURE_KEY_PREFIXES):
            index = self.capture_dir / ROUTE_INDEX_FILE
            if not index.is_file():
                return None
            for line in index.read_text(encoding="utf-8").splitlines():
                k, fname = line.split("\t")
                if k == key:
                    route_file = self.capture_dir / fname
                    if route_file.is_file():
                        return CmdResult(argv, 0, route_file.read_text(encoding="utf-8"))
            return None
        return None


# --- parsers (pure; fixture-tested) ---------------------------------------------

_DIG_RECORD = re.compile(r"^(\S+)\s+(\d+)\s+IN\s+([A-Z]+)\s+(.+)$")
_DIG_STATUS = re.compile(r"status:\s*([A-Z]+)")
_DIG_FLAGS = re.compile(r"flags:\s*([a-z ]+)")


def parse_dig_records(text: str, rtype: str) -> list[dict[str, str]]:
    """``dig +noall +answer`` answer rows for one rtype: name/ttl/data."""
    out = []
    for line in text.splitlines():
        m = _DIG_RECORD.match(line.strip())
        if m and m.group(3) == rtype:
            out.append({"name": m.group(1), "ttl": m.group(2), "data": m.group(4).strip()})
    return out


def parse_dig_status(text: str) -> str | None:
    m = _DIG_STATUS.search(text)
    return m.group(1) if m else None


def parse_dig_flags(text: str) -> set[str]:
    m = _DIG_FLAGS.search(text)
    return set(m.group(1).split()) if m else set()


def parse_head(text: str) -> dict[str, Any]:
    """The last HTTP response block of a ``curl -sSI`` capture."""
    blocks = re.split(r"\r?\n\r?\n", text.strip())
    for block in reversed([b for b in blocks if b.strip()]):
        lines = block.strip().splitlines()
        m = re.match(r"HTTP/[\d.]+\s+(\d+)", lines[0].strip())
        if m:
            headers = {}
            for ln in lines[1:]:
                if ":" in ln:
                    k, v = ln.split(":", 1)
                    headers[k.strip().lower()] = v.strip()
            return {"status": int(m.group(1)), "headers": headers}
    return {"status": None, "headers": {}}


def parse_x509(text: str) -> dict[str, Any]:
    """``openssl x509 -noout -dates -ext subjectAltName`` → dates + SANs."""
    out: dict[str, Any] = {"sans": []}
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("notBefore="):
            out["notBefore"] = line.split("=", 1)[1]
        elif line.startswith("notAfter="):
            out["notAfter"] = line.split("=", 1)[1]
        elif line.startswith("DNS:"):
            out["sans"] += [p.strip()[4:] for p in line.split(",") if p.strip().startswith("DNS:")]
    return out


def parse_whois_statuses(text: str) -> list[str]:
    """WHOIS ``Domain Status:`` codes (the status text, spaces stripped)."""
    statuses = []
    for line in text.splitlines():
        m = re.match(r"\s*Domain Status:\s*(.+?)\s*(?:https?://\S+)?\s*$", line)
        if m:
            statuses.append(re.sub(r"\s+", "", m.group(1)).lower())
    return statuses


def parse_sitemap_locs(text: str) -> list[str]:
    return [m.strip() for m in re.findall(r"<loc>\s*([^<]+?)\s*</loc>", text)]


def is_cloudflare_anycast(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in net for net in CLOUDFLARE_ANYCAST_V4)


# --- the checks -----------------------------------------------------------------


def _check_ns_pair(runner: ProbeRunner, domain: str) -> CheckResult:
    """Runbook step 8: the Cloudflare pair serves the zone."""
    res = runner.run("ns", _dig_argv(domain, "NS"))
    if res is None:
        return CheckResult("skipped", {"reason": "dig unavailable"})
    records = parse_dig_records(res.stdout, "NS")
    hosts = sorted({r["data"].rstrip(".") for r in records})
    status = parse_dig_status(res.stdout)
    if not hosts or status == "NXDOMAIN":
        return CheckResult("fail", {"reason": f"no NS answer (status {status})", "observed": hosts})
    cloudflare = [h for h in hosts if h.endswith(CLOUDFLARE_NS_SUFFIX)]
    if len(cloudflare) == len(hosts) and hosts:
        return CheckResult("pass", {"nameservers": hosts, "all_cloudflare": True})
    return CheckResult(
        "fail",
        {
            "nameservers": hosts,
            "all_cloudflare": False,
            "state": "pre_cutover" if any("squarespacedns" in h for h in hosts) else "partial",
        },
    )


def _check_a_record(runner: ProbeRunner, key: str, name: str, expected_ip: str) -> CheckResult:
    """Runbook steps 9/10: the A answer is the load-balancer IP."""
    res = runner.run(key, _dig_argv(name, "A"))
    if res is None:
        return CheckResult("skipped", {"reason": "dig unavailable"})
    records = parse_dig_records(res.stdout, "A")
    addrs = sorted({r["data"] for r in records})
    status = parse_dig_status(res.stdout)
    if status == "NXDOMAIN" or not addrs:
        return CheckResult("fail", {"reason": f"no A answer for {name} (status {status})"})
    if is_cloudflare_anycast(next(iter(addrs), "")) or any(is_cloudflare_anycast(a) for a in addrs):
        return CheckResult(
            "fail",
            {
                "addresses": addrs,
                "reason": "Cloudflare anycast address — the record is proxied "
                "(grey-cloud rule broken)",
            },
        )
    if addrs == [expected_ip]:
        return CheckResult("pass", {"addresses": addrs, "expected": expected_ip})
    return CheckResult("fail", {"addresses": addrs, "expected": expected_ip})


def normalize_redirect_target(url: str) -> str:
    """Redirect equivalence: ``https://host:443/`` == ``https://host/``."""
    url = re.sub(r"^(https://[^/:?#]+):443(?=[/?#]|$)", r"\1", url)
    url = re.sub(r"^(http://[^/:?#]+):80(?=[/?#]|$)", r"\1", url)
    return url.rstrip("/")


def _check_https(runner: ProbeRunner, key: str, url: str, *, expect: dict[str, Any]) -> CheckResult:
    """A ``curl -sSI`` read: expected status (and optional redirect target)."""
    res = runner.run(key, _curl_head_argv(url))
    if res is None:
        return CheckResult("skipped", {"reason": "curl unavailable"})
    head = parse_head(res.stdout)
    want_status = expect["status"]
    detail: dict[str, Any] = {"url": url, "status": head["status"], "expected_status": want_status}
    if head["status"] != want_status:
        return CheckResult("fail", {**detail, "headers": head["headers"]})
    want_loc = expect.get("location")
    if want_loc is not None:
        loc = head["headers"].get("location", "")
        detail["location"] = loc
        if normalize_redirect_target(loc) != normalize_redirect_target(want_loc):
            return CheckResult("fail", detail)
    return CheckResult("pass", detail)


def _check_apex_tls(runner: ProbeRunner, domain: str) -> CheckResult:
    """Runbook step 12: the apex TLS cert — SAN {apex, www}, dates recorded."""
    res = runner.run("openssl_apex", _openssl_s_client_argv(domain))
    if res is None:
        return CheckResult("skipped", {"reason": "openssl unavailable"})
    if not res.stdout.strip():
        return CheckResult(
            "fail", {"reason": "no certificate presented", "stderr_tail": res.stderr[-300:]}
        )
    cert = parse_x509(res.stdout)
    www = f"www.{domain}"
    sans = cert.get("sans", [])
    missing = [n for n in (domain, www) if n not in sans]
    detail = {"sans": sans, "notBefore": cert.get("notBefore"), "notAfter": cert.get("notAfter")}
    if missing:
        return CheckResult("fail", {**detail, "missing_san": missing})
    return CheckResult("pass", detail)


def _check_dnssec(runner: ProbeRunner, domain: str) -> CheckResult:
    """Runbook step 13: RRSIG + ad flag; the DS set at the parent."""
    res = runner.run("dnssec_a", _dig_argv(domain, "A", dnssec=True))
    ds_res = runner.run("ds", _dig_argv(domain, "DS"))
    if res is None or ds_res is None:
        return CheckResult("skipped", {"reason": "dig unavailable"})
    flags = parse_dig_flags(res.stdout)
    rrsig = parse_dig_records(res.stdout, "RRSIG")
    ds_records = parse_dig_records(ds_res.stdout, "DS")
    keytags = sorted({r["data"].split()[0] for r in ds_records})
    detail: dict[str, Any] = {
        "ad_flag": "ad" in flags,
        "rrsig_present": bool(rrsig),
        "ds_keytags": keytags,
    }
    if "ad" not in flags or not rrsig:
        detail["reason"] = "no authenticated answer (missing ad flag or RRSIG)"
        return CheckResult("fail", detail)
    if not keytags:
        detail["reason"] = "signed answer but no DS at the parent"
        return CheckResult("fail", detail)
    detail["rollover_in_progress"] = LEGACY_DS_KEYTAG in keytags and len(keytags) > 1
    if keytags == [LEGACY_DS_KEYTAG]:
        detail["reason"] = (
            "only the legacy 17039 DS remains — the Cloudflare DS was never published"
        )
        return CheckResult("fail", detail)
    return CheckResult("pass", detail)


def _check_cert(runner: ProbeRunner, cert: str, project: str | None) -> CheckResult:
    """The managed-cert state (``gcloud … describe`` — read-only, ADC-gated)."""
    if not project:
        return CheckResult("skipped", {"reason": "SIG_GCP_PROJECT unset — cert read needs ADC"})
    res = runner.run("gcloud_cert", _gcloud_cert_argv(cert, project))
    if res is None:
        return CheckResult("skipped", {"reason": "gcloud unavailable"})
    if res.rc != 0:
        return CheckResult(
            "skipped",
            {"reason": "gcloud describe failed (ADC absent?)", "stderr_tail": res.stderr[-300:]},
        )
    try:
        doc = json.loads(res.stdout)
    except json.JSONDecodeError:
        return CheckResult("fail", {"reason": "gcloud describe emitted no JSON"})
    managed = doc.get("managed") or {}
    detail = {
        "cert": cert,
        "managed_status": managed.get("status"),
        "domain_status": managed.get("domainStatus"),
        "expire_time": doc.get("expireTime"),
    }
    domains = managed.get("domainStatus") or {}
    inactive = [d for d, s in domains.items() if s != "ACTIVE"]
    if managed.get("status") == "ACTIVE" and not inactive:
        return CheckResult("pass", detail)
    return CheckResult("fail", {**detail, "inactive_domains": inactive})


def _allowlist_routes(repo_root: Path, domain: str) -> list[str] | None:
    """The committed public-route fallback (``ops/public_routes.toml``).

    Every ``[allowlist].top_level`` entry becomes a probe URL — directory
    entries as ``/<name>/``, files as ``/<name>``. The allowlist names what
    a public build MAY carry, so a deliberate 4xx is recorded ``absent``,
    not failed.
    """
    path = repo_root / "ops" / "public_routes.toml"
    if not path.is_file():
        return None
    import tomllib

    doc = tomllib.loads(path.read_text(encoding="utf-8"))
    entries = (doc.get("allowlist") or {}).get("top_level") or []
    urls = []
    for entry in entries:
        if entry.startswith("_") or entry.startswith("."):
            continue
        if "." in entry:
            urls.append(f"https://{domain}/{entry}")
        else:
            urls.append(f"https://{domain}/{entry}/")
    return urls


def _check_routes(
    runner: ProbeRunner, domain: str, *, max_routes: int, repo_root: Path | None = None
) -> CheckResult:
    """Every public route answers — sitemap sweep, allowlist fallback."""
    locs: list[str] = []
    sitemaps_seen: list[str] = []
    for name in ("sitemap.xml", "sitemap-index.xml"):
        url = f"https://{domain}/{name}"
        res = runner.run(f"sitemap:{url}", _curl_get_argv(url))
        if res is None:
            return CheckResult("skipped", {"reason": "curl unavailable"})
        found = [u for u in parse_sitemap_locs(res.stdout) if domain in u]
        if found:
            sitemaps_seen.append(url)
            locs += found
    # One level of sitemap-index nesting (sub-sitemaps are .xml locs).
    sub_sitemaps = [u for u in locs if u.endswith(".xml")][:8]
    for url in sub_sitemaps:
        res = runner.run(f"sitemap:{url}", _curl_get_argv(url))
        if res is not None:
            locs += [u for u in parse_sitemap_locs(res.stdout) if domain in u]
    page_locs = sorted({u for u in locs if not u.endswith(".xml")})
    strict = bool(page_locs)
    if not strict:
        fallback = _allowlist_routes(repo_root or Path(__file__).resolve().parents[3], domain)
        if not fallback:
            return CheckResult(
                "fail",
                {
                    "reason": "no sitemap served and no public_routes.toml fallback",
                    "sitemaps_seen": sitemaps_seen,
                },
            )
        page_locs = fallback
    capped = page_locs[: max_routes or None]
    probes = []
    failed = []
    absent = []
    for url in capped:
        head_res = runner.run(f"route:{url}", _curl_head_argv(url))
        if head_res is None:
            probes.append({"url": url, "status": None, "class": "unreachable"})
            failed.append(url)
            continue
        head = parse_head(head_res.stdout)
        status = head["status"]
        if status in _ROUTE_SERVE:
            cls = "served"
        elif status in _ROUTE_ABSENT:
            cls = "absent"
        else:
            cls = "unreachable"
        probes.append({"url": url, "status": status, "class": cls})
        if cls == "unreachable" or (strict and cls != "served"):
            failed.append(url)
        elif cls == "absent":
            absent.append(url)
    return CheckResult(
        "fail" if failed else "pass",
        {
            "route_source": "sitemap" if strict else "ops/public_routes.toml",
            "sitemaps_seen": sitemaps_seen,
            "routes_listed": len(page_locs),
            "routes_checked": len(capped),
            "served": len([p for p in probes if p["class"] == "served"]),
            "absent": absent,
            "failed": failed[:20],
            "probes": probes,
        },
    )


def _check_mail(runner: ProbeRunner, domain: str) -> CheckResult:
    """Mail posture: MX + TXT — ``no_mail`` (design) or ``op10_configured``."""
    mx_res = runner.run("mx", _dig_argv(domain, "MX"))
    txt_res = runner.run("txt", _dig_argv(domain, "TXT"))
    if mx_res is None or txt_res is None:
        return CheckResult("skipped", {"reason": "dig unavailable"})
    mx = [r["data"] for r in parse_dig_records(mx_res.stdout, "MX")]
    txt = [r["data"].strip('"') for r in parse_dig_records(txt_res.stdout, "TXT")]
    spf = [t for t in txt if t.startswith("v=spf1")]
    detail: dict[str, Any] = {"mx": mx, "spf": spf, "txt_records": txt}
    if not mx and spf == [EXPECTED_DENY_ALL_SPF]:
        return CheckResult("pass", {**detail, "posture": "no_mail (pre-OP-10 design)"})
    if mx:
        detail["posture"] = "op10_configured (contact@ alias landed)"
        if not spf:
            return CheckResult("fail", {**detail, "reason": "MX present but no SPF record — drift"})
        return CheckResult("pass", detail)
    return CheckResult(
        "fail",
        {
            **detail,
            "reason": "MX empty but the deny-all SPF is gone — neither the no-mail "
            "design nor a configured mail posture",
        },
    )


def _check_registrar(runner: ProbeRunner, domain: str) -> CheckResult:
    """WHOIS transfer/lock state — a read, never a registrar call."""
    res = runner.run("whois", _whois_argv(domain))
    if res is None:
        return CheckResult("skipped", {"reason": "whois unavailable"})
    statuses = parse_whois_statuses(res.stdout)
    bad = [s for s in statuses if s in BAD_WHOIS_STATUSES]
    detail = {"domain_statuses": statuses}
    if not statuses:
        return CheckResult("skipped", {**detail, "reason": "WHOIS carried no Domain Status lines"})
    if bad:
        return CheckResult("fail", {**detail, "drift": bad})
    return CheckResult("pass", detail)


L1_CHECKS = (
    "ns_pair",
    "apex_a",
    "www_a",
    "apex_https_tls",
    "http_redirect",
    "dnssec",
    "cert_status",
    "routes",
    "mail",
    "registrar_lock",
)
L2_CHECKS = ("ns_pair", "apex_https_tls", "cert_status")


def run_probe(
    *,
    leg: str,
    domain: str = DEFAULT_DOMAIN,
    expected_ip: str = EXPECTED_APEX_IP,
    cert: str = DEFAULT_CERT,
    project: str | None = None,
    runner: ProbeRunner,
    max_routes: int = 400,
    repo_root: Path | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    """Run one leg and build the ``sig.probe-run/1`` record."""
    www = f"www.{domain}"
    checks: dict[str, CheckResult] = {}

    if leg == "l1":
        checks["ns_pair"] = _check_ns_pair(runner, domain)
        checks["apex_a"] = _check_a_record(runner, "apex_a", domain, expected_ip)
        checks["www_a"] = _check_a_record(runner, "www_a", www, expected_ip)
        www_head = _check_https(
            runner,
            "https_www",
            f"https://{www}/",
            expect={"status": 301, "location": f"https://{domain}/"},
        )
        checks["www_redirect"] = www_head
        checks["apex_https_tls"] = _check_apex_tls(runner, domain)
        apex_head = _check_https(runner, "https_apex", f"https://{domain}/", expect={"status": 200})
        checks["apex_https"] = apex_head
        checks["http_redirect"] = _check_https(
            runner,
            "http_apex",
            f"http://{domain}/",
            expect={"status": 301, "location": f"https://{domain}/"},
        )
        checks["dnssec"] = _check_dnssec(runner, domain)
        checks["cert_status"] = _check_cert(runner, cert, project)
        checks["routes"] = _check_routes(runner, domain, max_routes=max_routes, repo_root=repo_root)
        checks["mail"] = _check_mail(runner, domain)
        checks["registrar_lock"] = _check_registrar(runner, domain)
    elif leg == "l2":
        checks["ns_pair"] = _check_ns_pair(runner, domain)
        checks["apex_https_tls"] = _check_apex_tls(runner, domain)
        checks["cert_status"] = _check_cert(runner, cert, project)
        cert_res = checks["cert_status"]
        cert_detail = cert_res.detail
        if cert_res.verdict == "skipped":
            renewal_verdict = "skipped"
        elif cert_res.verdict == "pass" and cert_detail.get("managed_status") == "ACTIVE":
            renewal_verdict = "pass"
        else:
            renewal_verdict = "fail"
        checks["renewal_read"] = CheckResult(
            renewal_verdict,
            {
                "note": "the P34.4 TLS-expiry alert (≈21 days) is the "
                "tripwire if the renewal slips toward expected_expiry",
                "managed_status": cert_detail.get("managed_status"),
                "expire_time": cert_detail.get("expire_time"),
                "expected_expiry": CERT_EXPIRY_ISO,
            },
        )
    else:
        raise ValueError(f"unknown leg {leg!r} — expected l1|l2")

    verdicts = [c.verdict for c in checks.values()]
    if "fail" in verdicts:
        overall = "fail"
    elif "skipped" in verdicts:
        overall = "partial"
    else:
        overall = "pass"
    ns = checks.get("ns_pair")
    cutover = (
        "detected"
        if ns is not None and ns.verdict == "pass"
        else "not_detected"
        if ns is not None and ns.verdict == "fail"
        else "unknown"
    )
    return {
        "version": PROBE_RUN_VERSION,
        "probe": PROBE_NAME,
        "leg": leg.upper(),
        "domain": domain,
        "expected_ip": expected_ip,
        "generated_at": now or _utcnow(),
        "cutover_detected": cutover,
        "checks": {name: c.as_json() for name, c in checks.items()},
        "overall": overall,
    }
