#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""P36.2 terms-capture runner — bounded read-only GETs of terms pages.

Reads ``terms-manifest.toml`` (same directory) and, for each leg, fetches the
recorded terms URLs under the project descriptive UA (SIG-INGEST-036),
honoring the recorded crawl delay, and writes the response **verbatim** —
bytes, never paraphrased — under ``captures/<leg-id>/`` beside a sidecar JSON
carrying ``sha256`` + ``generated_at`` (the SIG-TRANSP-004 terms-capture
field family).

GUARD (fail-closed): the project UA cites the owned explanation page
``https://surveillancegraph.org/data-collection/`` (``connectors.net``
DEFAULT_CONTACT_URL). While that page is not live, a descriptive UA may not
be sent — every leg stays ``prepared_not_executed`` and the runner exits 42
(the same re-queue convention the OM-19 leg-runner uses).

Usage::

    python3 capture_terms.py            # run the queue (fetch only when legal)
    python3 capture_terms.py --check    # offline: print the plan, exit 0

This is a *terms-page* capture utility, not a source-content connector: it
never fetches source data and never touches ``ingestion_permitted`` (HG-03 /
OP-26 — flips are the operator's).
"""

from __future__ import annotations

import hashlib
import json
import sys
import tomllib
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "terms-manifest.toml"
CAPTURES = HERE / "captures"

CONTACT_URL = "https://surveillancegraph.org/data-collection/"
UA = (
    "SIG-rights-review/1.0 (terms evidence archival; descriptive agent; "
    f"contact/policy: {CONTACT_URL})"
)

EXIT_QUEUED = 42  # precondition unmet — re-queue, nothing fetched


def log(msg: str) -> None:
    print(msg, flush=True)


def check_precondition() -> bool:
    """True iff the owned UA-explanation page is live (`live:P35.38a`)."""
    try:
        req = urllib.request.Request("https://surveillancegraph.org/", method="HEAD")
        urllib.request.urlopen(req, timeout=15).close()
        req = urllib.request.Request(CONTACT_URL, method="GET")
        status = urllib.request.urlopen(req, timeout=15).status
    except Exception as exc:  # noqa: BLE001 — any failure = not live
        log(f"precondition probe failed: {exc}")
        return False
    return status == 200


def fetch(url: str) -> tuple[int, bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    resp = urllib.request.urlopen(req, timeout=30)
    body = resp.read()
    return resp.status, body, resp.headers.get("Content-Type", "")


def run(manifest: dict) -> int:
    now = datetime.now(timezone.utc)
    legs = manifest.get("leg", [])
    log(f"{len(legs)} legs in manifest")

    if not check_precondition():
        log(
            f"QUEUED: {CONTACT_URL} is not live (live:P35.38a fails) — no "
            "descriptive-UA fetch may run; every leg stays prepared_not_executed."
        )
        log(f"re-run: {manifest['meta']['rerun']}")
        return EXIT_QUEUED

    results = []
    for leg in legs:
        leg_dir = CAPTURES / leg["id"]
        leg_dir.mkdir(parents=True, exist_ok=True)
        delay = leg.get("crawl_delay", 5)
        for i, url in enumerate(leg.get("urls", [])):
            if i:
                import time

                time.sleep(delay)  # honor the recorded crawl delay
            try:
                status, body, ctype = fetch(url)
            except Exception as exc:  # noqa: BLE001 — record, don't fabricate
                log(f"{leg['id']}: {url} -> ERROR {exc}")
                results.append({"leg": leg["id"], "url": url, "error": str(exc)})
                continue
            suffix = ".html" if "html" in ctype else ".txt"
            name = f"capture-{i}{suffix}"
            (leg_dir / name).write_bytes(body)
            sidecar = {
                "schema": "sig.terms-capture/1",
                "leg": leg["id"],
                "subject": leg["subject"],
                "url": url,
                "http_status": status,
                "content_type": ctype,
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "generated_at": now.isoformat(),
                "verbatim": True,
            }
            (leg_dir / f"capture-{i}.json").write_text(
                json.dumps(sidecar, indent=2) + "\n"
            )
            log(f"{leg['id']}: {url} -> {status} {len(body)}B sha256={sidecar['sha256'][:12]}…")
            results.append(sidecar)
    (CAPTURES / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    return 0


def main() -> int:
    manifest = tomllib.loads(MANIFEST.read_text())
    if "--check" in sys.argv:
        for leg in manifest.get("leg", []):
            log(f"[{leg['status']}] {leg['id']}: {leg['subject']}")
        return 0
    return run(manifest)


if __name__ == "__main__":
    raise SystemExit(main())
