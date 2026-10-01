# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The repo-owned `sig-web` image + deploy path (P31.15 / SURFACE.2, ADR-R9-TILES).

Deterministic proxies for the compression deliverable: `ops/web/nginx.conf` carries
gzip + Brotli for the text types, the registered `application/vnd.pmtiles` media
type, byte-range serving for the per-compartment archives, and the sane cache
policy; `ops/web/Dockerfile` compiles ngx_brotli against the EXACT nginx version
from sha256-verified sources (Alpine's packaged module is ABI-incompatible);
`ops/gcp/web.sh` reproduces the hand-made service shape on the pinned-digest image.

A real `nginx -t` + byte-range serve test runs when a Docker daemon is present
(else it skips loudly like tests/db does — the structural assertions below always
run).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = REPO_ROOT / "ops" / "web"
NGINX_CONF = WEB_DIR / "nginx.conf"
DOCKERFILE = WEB_DIR / "Dockerfile"
WEB_SH = REPO_ROOT / "ops" / "gcp" / "web.sh"


def _no_adc_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k != "SIG_GCP_PROJECT"}
    env.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
    env["CLOUDSDK_CONFIG"] = "/nonexistent-sig-adc"
    return env


def _docker() -> bool:
    if shutil.which("docker") is None:
        return False
    return subprocess.run(["docker", "info"], capture_output=True, check=False).returncode == 0


requires_docker = pytest.mark.skipif(not _docker(), reason="no Docker daemon")

# --- the nginx config is linted ------------------------------------------------

_BALANCED = re.compile(r"^[^{}]*$")


def test_nginx_conf_braces_balanced_and_directives_terminated() -> None:
    text = NGINX_CONF.read_text(encoding="utf-8")
    stripped = [ln.split("#", 1)[0].strip() for ln in text.splitlines()]
    stripped = [ln for ln in stripped if ln]
    depth = 0
    pending: str | None = None  # a multi-line directive (e.g. gzip_types … ;)
    for ln in stripped:
        if pending is not None:
            pending += " " + ln
            if "{" in ln or "}" in ln:
                raise AssertionError(f"directive crosses a block boundary: {pending!r}")
            if pending.rstrip().endswith(";"):
                pending = None
            continue
        depth += ln.count("{") - ln.count("}")
        assert depth >= 0, f"brace underflow at {ln!r}"
        if "{" not in ln and "}" not in ln and not ln.endswith(";"):
            pending = ln
    assert depth == 0, "unbalanced braces in nginx.conf"
    assert pending is None, f"unterminated directive: {pending!r}"


def test_nginx_conf_compression_contract() -> None:
    text = NGINX_CONF.read_text(encoding="utf-8")
    assert "load_module /usr/lib/nginx/modules/ngx_http_brotli_filter_module.so;" in text
    assert re.search(r"^\s*gzip\s+on;", text, re.M)
    assert re.search(r"^\s*brotli\s+on;", text, re.M)
    # Both compressors cover the ticket's text types — JSON, CSS, HTML (implicit),
    # SVG (+ the island JS + geo+json).
    for mime in (
        "text/css",
        "application/json",
        "application/javascript",
        "image/svg+xml",
        "application/geo+json",
    ):
        assert mime in text, f"{mime} not in the compression type lists"
    # application/vnd.pmtiles is the REGISTERED media type and is never a
    # compression type (the archive is already gzip-compressed inside).
    assert "application/vnd.pmtiles pmtiles;" in text
    for directive in ("gzip_types", "brotli_types"):
        block = re.search(rf"{directive}\s+([^;]+);", text, re.S)
        assert block is not None
        assert "vnd.pmtiles" not in block.group(1), directive


def test_nginx_conf_serves_the_gcsfuse_root_with_ranges_and_cache_policy() -> None:
    text = NGINX_CONF.read_text(encoding="utf-8")
    assert re.search(r"^\s*root\s+/mnt/sig-web;", text, re.M)  # the bucket mount
    assert re.search(r"^\s*listen\s+8080;", text, re.M)  # Cloud Run $PORT
    assert re.search(r"location\s+/tiles/", text)  # the per-compartment archives
    assert re.search(r"location\s+/_astro/", text)
    assert "immutable" in text  # content-hashed assets only
    assert "must-revalidate" in text  # everything else revalidates on publish
    # Nothing disables ranges: no `max_ranges 0` / chunked transfer games.
    assert "max_ranges" not in text


# --- the image is a real compile, not the incompatible Alpine package ----------


def test_dockerfile_compiles_brotli_against_the_runtime_nginx() -> None:
    text = DOCKERFILE.read_text(encoding="utf-8")
    # Runtime base IS the version the modules are built against — never the
    # ABI-mismatched Alpine package.
    assert "FROM nginx:1.27.5-alpine" in text
    assert "NGINX_VERSION=1.27.5" in text
    # Never the ABI-mismatched Alpine package (a comment may name it; no apk add).
    assert not re.search(r"apk\s+add[^\n]*nginx-mod-http-brotli", text)
    assert "--with-compat --add-dynamic-module=" in text
    assert 'make -j"$(nproc)" modules' in text or "make -j$(nproc) modules" in text
    # Every downloaded source is sha256-verified before use.
    for var in ("NGINX_SHA256", "NGX_BROTLI_SHA256", "BROTLI_SHA256"):
        assert re.search(rf"{var}=[0-9a-f]{{64}}", text), var
    assert text.count("sha256sum -c") >= 3
    # The submodule tarball is laid in by hand (GitHub archives drop gitlinks).
    assert "deps/brotli" in text
    # Both modules land where nginx.conf's load_module lines point.
    assert "ngx_http_brotli_filter_module.so" in text
    assert "ngx_http_brotli_static_module.so" in text
    assert "COPY ops/web/nginx.conf /etc/nginx/nginx.conf" in text


# --- the deploy path is digest-pinned and reproduces the live shape ------------


def test_web_sh_check_plans_the_repo_owned_deploy() -> None:
    proc = subprocess.run(
        ["bash", str(WEB_SH), "--check", "service"],
        capture_output=True,
        text=True,
        check=False,
        env={**_no_adc_env(), "SIG_GCP_PROJECT": "sig-test-project"},
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    plan = proc.stdout
    # Live-read first (the ticket's contract), then the reproduced shape.
    assert "run services describe sig-web" in plan
    deploy = [ln for ln in plan.splitlines() if "run deploy sig-web" in ln]
    assert deploy, plan
    for ln in deploy:
        assert "--image" in ln and "@sha256:" in ln  # pinned digest (ADR-111)
        assert ":latest" not in ln
        assert "type=cloud-storage,bucket=sig-test-project-sig-web" in ln
        assert "mount-path=/mnt/sig-web" in ln
        assert "--allow-unauthenticated" in ln
        assert "--ingress all" in ln


def test_web_sh_never_names_latest_or_an_untagged_image() -> None:
    text = WEB_SH.read_text(encoding="utf-8")
    assert not re.search(r"--image\s+\S*:latest", text)
    assert "pin_image_digest" in text


# --- real lint + range-serve test when a Docker daemon is present ---------------


@requires_docker
def test_sig_web_image_builds_lints_and_serves_byte_ranges(tmp_path: Path) -> None:
    """docker build + `nginx -t` + a real byte-range GET against a fixture site."""
    tag = "sig-web:test-p3115"
    build = subprocess.run(
        ["docker", "build", "-f", "ops/web/Dockerfile", "-t", tag, "."],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(REPO_ROOT),
    )
    assert build.returncode == 0, build.stderr[-3000:]

    lint = subprocess.run(
        ["docker", "run", "--rm", tag, "nginx", "-t"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert lint.returncode == 0, lint.stderr
    assert "syntax is ok" in lint.stderr and "test is successful" in lint.stderr

    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("<h1>sig</h1>", encoding="utf-8")
    # > gzip_min_length/brotli_min_length so the response actually compresses.
    (site / "data.json").write_text(
        json.dumps({"sites": [{"id": i, "label": f"site-{i}"} for i in range(50)]}),
        encoding="utf-8",
    )
    payload = bytes(range(256)) * 64  # 16 KiB of addressable bytes
    tiles = site / "tiles"
    tiles.mkdir()
    (tiles / "sig_graph-sites.pmtiles").write_bytes(payload)

    name = "sig-web-test-p3115"
    subprocess.run(["docker", "rm", "-f", name], capture_output=True, check=False)
    try:
        up = subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                name,
                "-p",
                "18080:8080",
                "-v",
                f"{site}:/mnt/sig-web:ro",
                tag,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert up.returncode == 0, up.stderr
        import time

        deadline = time.time() + 15
        body = None
        while time.time() < deadline:
            r = subprocess.run(
                [
                    "curl",
                    "-fsS",
                    "-o",
                    "/dev/null",
                    "-w",
                    "%{http_code}",
                    "http://localhost:18080/",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if r.stdout == "200":
                body = "up"
                break
            time.sleep(0.4)
        assert body == "up", "nginx did not come up"

        def get(url: str, *extra: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                ["curl", "-sS", "-D", "-", "-o", "/dev/null", *extra, url],
                capture_output=True,
                text=True,
                check=False,
            )

        headers = get("http://localhost:18080/tiles/sig_graph-sites.pmtiles").stdout
        assert "application/vnd.pmtiles" in headers
        assert "accept-ranges: bytes" in headers.lower()
        ranged = get(
            "http://localhost:18080/tiles/sig_graph-sites.pmtiles",
            "-r",
            "100-199",
        )
        assert "206" in ranged.stdout.splitlines()[0]
        # No recompression of the archive.
        compressed = get(
            "http://localhost:18080/tiles/sig_graph-sites.pmtiles",
            "-H",
            "Accept-Encoding: gzip, br",
        )
        assert "content-encoding" not in compressed.stdout.lower()
        # JSON is compressed for a client that asks.
        jz = get("http://localhost:18080/data.json", "-H", "Accept-Encoding: gzip")
        assert "content-encoding: gzip" in jz.stdout.lower()
        jbr = get("http://localhost:18080/data.json", "-H", "Accept-Encoding: br")
        assert "content-encoding: br" in jbr.stdout.lower()
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, check=False)
