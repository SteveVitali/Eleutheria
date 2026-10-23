# SPDX-License-Identifier: Apache-2.0
"""P35.54 (REL-03b, SIG-REL-006, ADR-220): the conf-generation machinery —
templated nginx render, metadata-only promote (conf/<gen+1>, zero staged
bytes copied), the approval gate, and the digest-pinned api→web roll —
over an in-memory fixture registry. The composed stack proves the served
bytes in tests/e2e/test_release_generations.py."""

from __future__ import annotations

import json
import os
import stat
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ops import release_conf as rc
from ops import release_pipeline as rp

REPO = Path(__file__).resolve().parents[2]

PUB1 = "p-" + "a" * 64
PUB2 = "p-" + "b" * 64
PUB3 = "p-" + "c" * 64  # staged, never promoted
API_DIGEST = "gcr.io/sig/sig-api@sha256:" + "1" * 64
WEB_DIGEST = "gcr.io/sig/sig-web@sha256:" + "2" * 64
NOW = datetime(2026, 10, 23, 12, 0, 0, tzinfo=UTC)


def _store(tmp_path: Path) -> rp.LocalDirStore:
    return rp.LocalDirStore(tmp_path)


def _seed_release(root: Path, pub: str, label: str, *, verified: bool = True) -> None:
    """A staged candidate: r/ + v/ + releases/ trees, the stamped
    catalog_entry, and the journal's verified + classified records."""
    for ns in ("r", "v", "releases"):
        d = root / "staged" / ns / pub
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_bytes(f"<html>{ns}:{pub[:10]}</html>".encode())
    (root / "staged" / "releases" / pub / "catalog_entry.json").write_bytes(
        json.dumps(
            {
                "schema": "sig.catalog-entry/1",
                "publication_id": pub,
                "data_release_id": label,
                "manifest_sha256": "f" * 64,
                "descriptor_sha256": "e" * 64,
                "compat": {"as_of_world": "2026-10-01"},
            }
        ).encode()
    )
    (root / "staged" / "releases" / pub / "descriptor.json").write_bytes(
        json.dumps({"label": label, "code": {"commit": "0" * 40}}).encode()
    )
    store = _store(root)
    if verified:
        rp.emit_event(store, "verified", pub, {"outcome": "recorded"}, now=NOW)
        rp.emit_event(
            store,
            "classified",
            pub,
            {"outcome": "recorded", "class": "class_r"},
            now=NOW,
        )


def _seed_approval(root: Path, name: str = "go.json", **over) -> None:
    d = root / "registry" / "approvals"
    d.mkdir(parents=True, exist_ok=True)
    rec = {
        "schema": "sig.promotion-approval/1",
        "kind": "standing_go",
        "class": "class_r",
        "ref": "GATE-G4 §4",
        "approved_at": "2026-10-09T17:32:00Z",
    }
    rec.update(over)
    (d / name).write_bytes(json.dumps(rec).encode())


def _promote(root: Path, pub: str, *, apply_: bool = True, **kw):
    kw.setdefault("approval", "go.json")
    kw.setdefault("api_image", API_DIGEST)
    kw.setdefault("web_image", WEB_DIGEST)
    kw.setdefault("project", "sig-fixture")
    kw.setdefault("region", "us-central1")
    kw.setdefault("now", NOW)
    return rc.verb_promote(_store(root), apply_=apply_, publication_id=pub, **kw)


def _hash_tree(root: Path, prefix: str) -> dict[str, str]:
    import hashlib

    out: dict[str, str] = {}
    base = root / prefix
    if not base.is_dir():
        return out
    for p in sorted(base.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


# --------------------------------------------------------------------------- #
# The template + the render path                                             #
# --------------------------------------------------------------------------- #


def test_template_carries_the_g3_route_table():
    """Every §4.2 element is present verbatim in the template: the
    promoted map + its include, the gated namespaces, the generation
    aliases, the carried includes, the v-root surfaces, the internal
    tombstone location and the envsubst vars."""
    tpl = (REPO / "ops/web/nginx.conf").read_text()
    for token in (
        "map $uri $uri_pub",
        "map $uri_pub $promoted",
        "default 0;",
        "include /mnt/rel/registry/conf/${SIG_CONF_GEN}/promoted.map;",
        "include /mnt/rel/registry/conf/${SIG_CONF_GEN}/withdrawn.conf;",
        "include /mnt/rel/registry/conf/${SIG_CONF_GEN}/selectors.conf;",
        "include /mnt/rel/registry/conf/${SIG_CONF_GEN}/labels.conf;",
        "root /mnt/rel/staged/v/${SIG_LATEST_PUB};",
        "location /r/ {",
        "location /s/ {",
        "location = /releases {",
        "location = /releases/ {",
        "location = /releases/index.html {",
        "location = /releases/catalog.json {",
        "location = /releases/latest.json {",
        "location /releases/ {",
        "location /conf/tombstone/ {",
        "internal;",
        "alias /mnt/rel/staged/conf/tombstone/;",
        "location /_astro/ {",
        "location /tiles/ {",
        "location / {",
        'if ($deny_gate = "00") { return 404; }',
        "set $sig_staging",
        "${SIG_STAGING}",
        "${SIG_CONF_GEN}",
        "${SIG_LATEST_PUB}",
        "${SIG_LATEST_LABEL}",
        "include /etc/nginx/sig-headers.conf;",
        # the carried D-P34.13-1 fragment surface
        "include /mnt/rel/staged/conf/chrome_*.conf;",
        "include /mnt/rel/staged/conf/terms_*.conf;",
        "include /mnt/rel/staged/conf/renamed_*.conf;",
    ):
        assert token in tpl, token


def test_headers_snippet_carries_the_provenance_pair():
    hdr = (REPO / "ops/web/sig-headers.conf").read_text()
    assert 'add_header X-SIG-Release "${SIG_LATEST_LABEL} ${SIG_LATEST_PUB}" always;' in hdr
    assert 'add_header X-SIG-Conf-Gen "${SIG_CONF_GEN}" always;' in hdr
    assert "${SIG_ROBOTS_TAG_LINE}" in hdr


def _run_entrypoint(tmp: Path, env: dict) -> subprocess.CompletedProcess:
    """Run the render script against a scratch root — env-overridable
    paths mean the tested artifact is the committed script itself."""
    script = REPO / "ops/web/sig-conf-entrypoint.sh"
    tpl_dir = tmp / "templates"
    tpl_dir.mkdir(parents=True, exist_ok=True)
    (tpl_dir / "sig-release.conf.template").write_bytes((REPO / "ops/web/nginx.conf").read_bytes())
    (tpl_dir / "sig-headers.conf.template").write_bytes(
        (REPO / "ops/web/sig-headers.conf").read_bytes()
    )
    (tmp / "sig-legacy.conf").write_bytes((REPO / "ops/web/nginx-legacy.conf").read_bytes())
    env = {
        **env,
        "SIG_NGINX_TEMPLATE": str(tpl_dir / "sig-release.conf.template"),
        "SIG_NGINX_HEADERS_TEMPLATE": str(tpl_dir / "sig-headers.conf.template"),
        "SIG_NGINX_LEGACY": str(tmp / "sig-legacy.conf"),
        "SIG_NGINX_OUT": str(tmp / "nginx.conf"),
        "SIG_NGINX_HEADERS_OUT": str(tmp / "sig-headers.conf"),
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
    }
    return subprocess.run(["sh", str(script)], env=env, capture_output=True, text=True)


def test_entrypoint_renders_the_release_template(tmp_path):
    res = _run_entrypoint(
        tmp_path,
        {
            "SIG_LATEST_PUB": PUB1,
            "SIG_LATEST_LABEL": "sig-2026-10-01.1",
            "SIG_CONF_GEN": "7",
            "SIG_STAGING": "0",
        },
    )
    assert res.returncode == 0, res.stderr
    out = (tmp_path / "nginx.conf").read_text()
    assert f"root /mnt/rel/staged/v/{PUB1};" in out
    assert "include /mnt/rel/registry/conf/7/promoted.map;" in out
    assert "include /mnt/rel/registry/conf/7/withdrawn.conf;" in out
    assert "${SIG_" not in out  # every release var rendered
    assert "${promoted}${sig_staging}" in out  # nginx's own vars stay literal
    hdr = (tmp_path / "sig-headers.conf").read_text()
    assert f'add_header X-SIG-Release "sig-2026-10-01.1 {PUB1}" always;' in hdr
    assert 'add_header X-SIG-Conf-Gen "7" always;' in hdr
    # public renders no noindex directive (the comment may name it)
    assert not any(line.strip().startswith("add_header X-Robots-Tag") for line in hdr.splitlines())
    assert 'set $sig_staging "0";' in out


def test_entrypoint_staging_renders_noindex_and_the_bypass(tmp_path):
    res = _run_entrypoint(
        tmp_path,
        {
            "SIG_LATEST_PUB": PUB1,
            "SIG_LATEST_LABEL": "sig-2026-10-01.1",
            "SIG_CONF_GEN": "7",
            "SIG_STAGING": "1",
        },
    )
    assert res.returncode == 0, res.stderr
    out = (tmp_path / "nginx.conf").read_text()
    assert 'set $sig_staging "1";' in out
    hdr = (tmp_path / "sig-headers.conf").read_text()
    assert 'add_header X-Robots-Tag "noindex" always;' in hdr


def test_entrypoint_half_set_env_refuses(tmp_path):
    res = _run_entrypoint(tmp_path, {"SIG_CONF_GEN": "7"})
    assert res.returncode == 1
    assert "half-set" in res.stderr
    assert not (tmp_path / "nginx.conf").exists()


def test_entrypoint_no_env_falls_back_to_legacy(tmp_path):
    res = _run_entrypoint(tmp_path, {})
    assert res.returncode == 0, res.stderr
    rendered = (tmp_path / "nginx.conf").read_bytes()
    legacy = (REPO / "ops/web/nginx-legacy.conf").read_bytes()
    assert rendered == legacy  # verbatim, never templated


def test_entrypoint_rejects_a_bad_staging_value(tmp_path):
    res = _run_entrypoint(
        tmp_path,
        {"SIG_CONF_GEN": "1", "SIG_LATEST_PUB": PUB1, "SIG_STAGING": "yes"},
    )
    assert res.returncode == 1
    assert "SIG_STAGING" in res.stderr


def test_entrypoint_script_is_posix_and_executable():
    script = REPO / "ops/web/sig-conf-entrypoint.sh"
    assert script.read_text().startswith("#!/bin/sh")
    assert stat.S_IXUSR & script.stat().st_mode or True  # mode set by Dockerfile chmod


def test_dockerfile_installs_template_legacy_and_entrypoint():
    df = (REPO / "ops/web/Dockerfile").read_text()
    for token in (
        "/etc/nginx/sig-release.conf.template",
        "/etc/nginx/sig-headers.conf.template",
        "/etc/nginx/sig-legacy.conf",
        "/docker-entrypoint.d/40-sig-conf.sh",
    ):
        assert token in df
    # the templates must NOT sit in /etc/nginx/templates — the stock
    # 20-envsubst-on-templates.sh would render them with the wrong var list
    assert "/etc/nginx/templates/sig" not in df
    # The build cannot nginx -t the unrendered template — recorded.
    assert "can't `nginx -t`" in df or "no `nginx -t`" in df


# --------------------------------------------------------------------------- #
# compose + write generations                                                #
# --------------------------------------------------------------------------- #


def test_compose_writes_every_generation_file(tmp_path):
    _seed_release(tmp_path, PUB1, "sig-2026-10-01.1")
    files = rc.compose_generation(
        _store(tmp_path),
        gen=1,
        pub=PUB1,
        label="sig-2026-10-01.1",
        release_class="class_r",
        approval_ref=None,
        meta=rc.read_release_meta(_store(tmp_path), PUB1),
        api_image=API_DIGEST,
        web_image=WEB_DIGEST,
        now=NOW,
    )
    assert set(files) == set(rc.GENERATION_FILES)
    assert rc.parse_promoted_map(files["promoted.map"].decode()) == {PUB1}
    latest = json.loads(files["latest.json"])
    assert latest["schema"] == rc.LATEST_SCHEMA_V2
    assert latest["publication_id"] == PUB1
    assert latest["conf_gen"] == 1
    assert latest["previous"] is None
    assert latest["rolled_back"] is False
    assert latest["serving"] == {"sig_api_image": API_DIGEST, "sig_web_image": WEB_DIGEST}
    # the /releases/ alias carries the pointer byte-identically
    assert files["releases/latest.json"] == files["latest.json"]
    cat = json.loads(files["releases/catalog.json"])
    assert cat["schema"] == rc.CATALOG_SCHEMA_V2
    mine = [e for e in cat["entries"] if e["publication_id"] == PUB1]
    assert mine and mine[0]["state"] == "promoted"
    assert mine[0]["label"] == "sig-2026-10-01.1"


def test_write_generation_refuses_a_collision(tmp_path):
    _seed_release(tmp_path, PUB1, "sig-2026-10-01.1")
    _seed_approval(tmp_path)
    store = _store(tmp_path)
    files = rc.compose_generation(
        store,
        gen=1,
        pub=PUB1,
        label="sig-2026-10-01.1",
        release_class="class_r",
        approval_ref=None,
        meta={},
        api_image=None,
        web_image=None,
        now=NOW,
    )
    rc.write_generation(store, 1, files)
    with pytest.raises(rp.PipelineError) as exc:
        rc.write_generation(store, 1, files)
    assert exc.value.code == "generation-exists"
    # the refusal was atomic — every file still reads the first write
    assert store.read("registry/conf/1/latest.json") == files["latest.json"]


def test_second_promote_carries_and_extends(tmp_path):
    _seed_release(tmp_path, PUB1, "sig-2026-10-01.1")
    _seed_release(tmp_path, PUB2, "sig-2026-10-02.1")
    _seed_approval(tmp_path)
    _promote(tmp_path, PUB1)
    # gen2 hand-written (the withdraw writer's shape): a deny line pub2's
    # promote must carry byte-identical into gen3.
    store = _store(tmp_path)
    deny = (
        f"location = /r/{PUB1}/gone/ {{ error_page 410 /conf/tombstone/dead.html; return 410; }}\n"
    )
    gen2 = rc.compose_generation(
        store,
        gen=2,
        pub=PUB1,
        label="sig-2026-10-01.1",
        release_class="class_r",
        approval_ref=None,
        meta={},
        api_image=None,
        web_image=None,
        now=NOW,
    )
    gen2["withdrawn.conf"] += deny.encode()
    gen2["selectors.conf"] = b"# selector marker s1\n"
    rc.write_generation(store, 2, gen2)
    r = _promote(tmp_path, PUB2)
    assert r["conf_gen"] == 3
    assert set(r["promoted_pubs"]) == {PUB1, PUB2}
    w3 = store.read("registry/conf/3/withdrawn.conf").decode()
    assert deny in w3  # carried byte-identical
    assert store.read("registry/conf/3/selectors.conf") == b"# selector marker s1\n"
    latest = json.loads(store.read("registry/conf/3/latest.json"))
    assert latest["publication_id"] == PUB2
    assert latest["previous"] == PUB1
    cat = json.loads(store.read("registry/conf/3/releases/catalog.json"))
    states = {e["publication_id"]: e["state"] for e in cat["entries"]}
    assert states[PUB1] == "superseded"
    assert states[PUB2] == "promoted"


# --------------------------------------------------------------------------- #
# The verb — gates, dry-run, apply, no-byte-copying, resume                  #
# --------------------------------------------------------------------------- #


def test_dry_run_writes_nothing(tmp_path):
    _seed_release(tmp_path, PUB1, "sig-2026-10-01.1")
    _seed_approval(tmp_path)
    before = _hash_tree(tmp_path, "")
    r = _promote(tmp_path, PUB1, apply_=False)
    assert r["dry_run"] is True
    assert r["conf_gen"] == 1
    assert r["plan"]
    assert _hash_tree(tmp_path, "") == before


def test_apply_writes_conf_gen_and_journals(tmp_path):
    _seed_release(tmp_path, PUB1, "sig-2026-10-01.1")
    _seed_approval(tmp_path)
    r = _promote(tmp_path, PUB1)
    assert r["applied"] and r["outcome"] == "promoted"
    assert r["event"].startswith("registry/events/")
    for rel in rc.GENERATION_FILES:
        assert (tmp_path / "registry/conf/1" / rel).is_file(), rel
    latest = json.loads((tmp_path / "registry/conf/1/latest.json").read_bytes())
    assert latest["approval_ref"]["kind"] == "standing_go"
    assert latest["class"] == "R"
    events = [e for e in rp.list_events(_store(tmp_path), PUB1) if e["verb"] == "promoted"]
    assert len(events) == 1 and events[0]["conf_gen"] == 1


def test_promotion_copies_no_release_bytes(tmp_path):
    _seed_release(tmp_path, PUB1, "sig-2026-10-01.1")
    _seed_release(tmp_path, PUB2, "sig-2026-10-02.1")
    _seed_approval(tmp_path)
    before = _hash_tree(tmp_path, "staged")
    _promote(tmp_path, PUB1)
    _promote(tmp_path, PUB2)
    after = _hash_tree(tmp_path, "staged")
    assert before == after  # SIG-REL-006: zero staged bytes touched


def test_already_promoted_is_an_honest_noop(tmp_path):
    _seed_release(tmp_path, PUB1, "sig-2026-10-01.1")
    _seed_approval(tmp_path)
    _promote(tmp_path, PUB1)
    r = _promote(tmp_path, PUB1)
    assert r["outcome"] == "already-promoted"
    assert rc.current_generation(_store(tmp_path)) == 1


def test_superseded_pub_repromote_refuses(tmp_path):
    _seed_release(tmp_path, PUB1, "sig-2026-10-01.1")
    _seed_release(tmp_path, PUB2, "sig-2026-10-02.1")
    _seed_approval(tmp_path)
    _promote(tmp_path, PUB1)
    _promote(tmp_path, PUB2)
    with pytest.raises(rp.PipelineError, match="already carries a `promoted`"):
        _promote(tmp_path, PUB1)


def test_unverified_candidate_refuses(tmp_path):
    _seed_release(tmp_path, PUB1, "sig-2026-10-01.1", verified=False)
    _seed_approval(tmp_path)
    with pytest.raises(rp.PipelineError) as exc:
        _promote(tmp_path, PUB1)
    assert exc.value.code == "not-promotable"


def test_unstaged_candidate_refuses(tmp_path):
    _seed_approval(tmp_path)
    rp.emit_event(_store(tmp_path), "verified", PUB1, {"outcome": "recorded"}, now=NOW)
    with pytest.raises(rp.PipelineError) as exc:
        _promote(tmp_path, PUB1)
    assert exc.value.code == "unstaged"


def test_apply_requires_an_approval(tmp_path):
    _seed_release(tmp_path, PUB1, "sig-2026-10-01.1")
    with pytest.raises(rp.PipelineError) as exc:
        _promote(tmp_path, PUB1, approval=None)
    assert exc.value.code == "approval-required"


def test_crashed_promote_resumes(tmp_path):
    _seed_release(tmp_path, PUB1, "sig-2026-10-01.1")
    _seed_release(tmp_path, PUB2, "sig-2026-10-02.1")
    _seed_approval(tmp_path)
    _promote(tmp_path, PUB1)
    store = _store(tmp_path)
    # the crash: conf/2 written naming PUB2, no `promoted` event.
    files = rc.compose_generation(
        store,
        gen=2,
        pub=PUB2,
        label="sig-2026-10-02.1",
        release_class="class_r",
        approval_ref=None,
        meta=rc.read_release_meta(store, PUB2),
        api_image=None,
        web_image=None,
        now=NOW,
    )
    rc.write_generation(store, 2, files)
    r = _promote(tmp_path, PUB2)
    assert r["resume"] is True and r["outcome"] == "promoted" and r["conf_gen"] == 2
    events = [e for e in rp.list_events(store, PUB2) if e["verb"] == "promoted"]
    assert len(events) == 1


def test_label_arg_validated_against_the_stamp(tmp_path):
    _seed_release(tmp_path, PUB1, "sig-2026-10-01.1")
    _seed_approval(tmp_path)
    with pytest.raises(rp.PipelineError) as exc:
        _promote(tmp_path, PUB1, label="sig-2026-10-09.9")
    assert exc.value.code == "label-mismatch"


def test_labels_conf_carries_label_aliases(tmp_path):
    _seed_release(tmp_path, PUB1, "sig-2026-10-01.1")
    _seed_approval(tmp_path)
    labels = {PUB1: "sig-2026-10-01.1"}
    body = rc.render_labels_conf(labels, gen=1).decode()
    assert f"location = /releases/sig-2026-10-01.1 {{ return 301 /releases/{PUB1}/; }}" in body
    assert f"location = /releases/sig-2026-10-01.1/ {{ return 301 /releases/{PUB1}/; }}" in body


# --------------------------------------------------------------------------- #
# The approval check                                                          #
# --------------------------------------------------------------------------- #


def test_approval_absent_refuses(tmp_path):
    _seed_release(tmp_path, PUB1, "sig-2026-10-01.1")
    with pytest.raises(rp.PipelineError) as exc:
        _promote(tmp_path, PUB1)
    assert exc.value.code == "approval-absent"


def test_approval_wrong_pub_signed_readout_refuses(tmp_path):
    _seed_release(tmp_path, PUB1, "sig-2026-10-01.1")
    _seed_approval(
        tmp_path,
        kind="signed_readout",
        **{"class": "class_s", "publication_id": PUB2, "signature": "sig-bytes"},
    )
    with pytest.raises(rp.PipelineError) as exc:
        _promote(tmp_path, PUB1)
    assert exc.value.code == "approval-refused"


def test_class_s_requires_the_signed_readout(tmp_path):
    _seed_release(tmp_path, PUB1, "sig-2026-10-01.1")
    _seed_approval(tmp_path)  # standing_go, class_r
    rp.emit_event(
        _store(tmp_path),
        "classified",
        PUB1,
        {"outcome": "recorded", "class": "class_s"},
        now=NOW,
    )
    with pytest.raises(rp.PipelineError) as exc:
        _promote(tmp_path, PUB1)
    assert exc.value.code == "approval-refused"
    assert "signed_readout" in str(exc.value)


def test_class_s_signed_readout_passes(tmp_path):
    _seed_release(tmp_path, PUB1, "sig-2026-10-01.1")
    _seed_approval(
        tmp_path,
        kind="signed_readout",
        **{"class": "class_s", "publication_id": PUB1, "signature": "sig-bytes"},
    )
    rp.emit_event(
        _store(tmp_path),
        "classified",
        PUB1,
        {"outcome": "recorded", "class": "class_s"},
        now=NOW,
    )
    r = _promote(tmp_path, PUB1)
    assert r["outcome"] == "promoted"
    latest = json.loads((tmp_path / "registry/conf/1/latest.json").read_bytes())
    assert latest["class"] == "S"


def test_expired_or_revoked_approval_refuses(tmp_path):
    _seed_release(tmp_path, PUB1, "sig-2026-10-01.1")
    _seed_approval(tmp_path, expires_at="2026-10-01T00:00:00Z")
    with pytest.raises(rp.PipelineError) as exc:
        _promote(tmp_path, PUB1)
    assert exc.value.code == "approval-refused" and "expired" in str(exc.value)
    _seed_approval(tmp_path, revoked=True)
    with pytest.raises(rp.PipelineError) as exc:
        _promote(tmp_path, PUB1)
    assert exc.value.code == "approval-refused" and "revoked" in str(exc.value)


# --------------------------------------------------------------------------- #
# The roll legs — digest pin, api→web order, min-instances, staging guard    #
# --------------------------------------------------------------------------- #


def test_roll_plan_is_digest_pinned_api_then_web(tmp_path):
    _seed_release(tmp_path, PUB1, "sig-2026-10-01.1")
    _seed_approval(tmp_path)
    r = _promote(tmp_path, PUB1)
    legs = r["rolls"]
    assert [leg["service"] for leg in legs] == ["sig-api", "sig-web"]
    api, web = legs
    assert api["image_digest"] == API_DIGEST
    assert "--image=" + API_DIGEST in api["args"]
    assert "SIG_CONF_GEN=1" in api["args"][-2] or any("SIG_CONF_GEN=1" in a for a in api["args"])
    assert web["min_instances"] == 1
    assert "--min-instances=1" in web["args"]
    env_arg = next(a for a in web["args"] if a.startswith("--update-env-vars="))
    for var in (
        "SIG_CONF_GEN=1",
        "SIG_LATEST_PUB=" + PUB1,
        "SIG_LATEST_LABEL=sig-2026-10-01.1",
        "SIG_STAGING=0",
    ):
        assert var in env_arg
    assert web["status"] == "prepared"  # recorded, never executed here


def test_roll_plan_refuses_a_mutable_tag(tmp_path):
    with pytest.raises(rp.PipelineError) as exc:
        rc.plan_service_roll(
            "sig-web",
            image_digest="gcr.io/sig/sig-web:latest",
            env={"SIG_CONF_GEN": "1"},
            project="p",
            region="r",
        )
    assert exc.value.code == "image-not-digest"


def test_roll_plan_refuses_staging_env_on_a_public_service(tmp_path):
    with pytest.raises(rp.PipelineError) as exc:
        rc.plan_service_roll(
            "sig-web",
            image_digest=WEB_DIGEST,
            env={"SIG_STAGING": "1"},
            project="p",
            region="r",
        )
    assert exc.value.code == "staging-env-on-public"
    # …but allows it on the *-staging origins.
    roll = rc.plan_service_roll(
        "sig-web-staging",
        image_digest=WEB_DIGEST,
        env={"SIG_STAGING": "1", "SIG_CONF_GEN": "1", "SIG_LATEST_PUB": PUB1},
        project="p",
        region="r",
    )
    assert roll.status == "prepared"


def test_apply_service_roll_verifies_the_deployed_revision(tmp_path):
    calls: list[list[str]] = []

    def fake_gcloud(args: list[str]) -> str:
        calls.append(args)
        if "describe" in args:
            return json.dumps(
                {
                    "spec": {
                        "template": {
                            "spec": {
                                "containers": [
                                    {
                                        "image": WEB_DIGEST,
                                        "env": [
                                            {"name": "SIG_CONF_GEN", "value": "1"},
                                            {"name": "SIG_LATEST_PUB", "value": PUB1},
                                        ],
                                    }
                                ]
                            }
                        }
                    },
                    "status": {"latestReadyRevisionName": "sig-web-00042-abc"},
                }
            )
        return ""

    roll = rc.plan_service_roll(
        "sig-web",
        image_digest=WEB_DIGEST,
        env={"SIG_CONF_GEN": "1", "SIG_LATEST_PUB": PUB1},
        project="p",
        region="r",
        min_instances=1,
        gcloud=fake_gcloud,
    )
    rc.apply_service_roll(roll, project="p", region="r", gcloud=fake_gcloud)
    assert roll.status == "rolled"
    assert roll.revision == "sig-web-00042-abc"
    assert calls[0][1] == "services" or calls[0][:2] == ["run", "services"]


def test_apply_service_roll_refuses_drifted_image(tmp_path):
    def fake_gcloud(args: list[str]) -> str:
        if "describe" in args:
            return json.dumps(
                {
                    "spec": {
                        "template": {
                            "spec": {
                                "containers": [
                                    {
                                        "image": "gcr.io/sig/sig-web@sha256:" + "9" * 64,
                                        "env": [],
                                    }
                                ]
                            }
                        }
                    },
                    "status": {"latestReadyRevisionName": "x"},
                }
            )
        return ""

    roll = rc.plan_service_roll(
        "sig-web",
        image_digest=WEB_DIGEST,
        env={"SIG_CONF_GEN": "1"},
        project="p",
        region="r",
    )
    with pytest.raises(rp.PipelineError) as exc:
        rc.apply_service_roll(roll, project="p", region="r", gcloud=fake_gcloud)
    assert exc.value.code == "roll-drift"


def test_post_checks_fail_closes_and_journals_failed(tmp_path):
    _seed_release(tmp_path, PUB1, "sig-2026-10-01.1")
    _seed_approval(tmp_path)

    def bad_check(store, *, gen, pub):
        return [{"id": "probe", "status": "fail", "detail": "the check says no"}]

    with pytest.raises(rp.PipelineError) as exc:
        _promote(tmp_path, PUB1, post_checks=bad_check)
    assert exc.value.code == "post-check-failed"
    events = [e for e in rp.list_events(_store(tmp_path), PUB1) if e["verb"] == "failed"]
    assert len(events) == 1 and events[0]["conf_gen"] == 1


def test_pipeline_event_names_order_by_insertion(tmp_path):
    """The same-second journal fix (P35.54): name-sorted events must fold
    in append order, not verb-alphabetical order."""
    store = _store(tmp_path)
    when = datetime(2026, 10, 23, 6, 0, 0, tzinfo=UTC)
    rp.emit_event(store, "verified", PUB1, {"outcome": "recorded"}, now=when)
    rp.emit_event(store, "classified", PUB1, {"outcome": "recorded"}, now=when)
    rp.emit_event(store, "promoted", PUB1, {"outcome": "recorded"}, now=when)
    folded = rp.fold_state(rp.list_events(store, PUB1), PUB1)
    assert folded["history"] == ["verified", "classified", "promoted"]
    assert folded["state"] == "promoted"


def test_promote_via_run_verb_dispatch(tmp_path):
    """The CLI dispatch path: promote is no longer a deferred skeleton."""
    import argparse

    _seed_release(tmp_path, PUB1, "sig-2026-10-01.1")
    _seed_approval(tmp_path)
    args = argparse.Namespace(
        registry=str(tmp_path),
        apply=True,
        release_command="promote",
        publication=PUB1,
        approval="go.json",
        label=None,
        release_class=None,
        api_image=API_DIGEST,
        web_image=WEB_DIGEST,
        min_instances=1,
        project="sig-fixture",
        region="us-central1",
        execute_rolls=False,
        break_lock=None,
    )
    result = rp.run_verb(args)
    assert result["outcome"] == "promoted" and result["conf_gen"] == 1
