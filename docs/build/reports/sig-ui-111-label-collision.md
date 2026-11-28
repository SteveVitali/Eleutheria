# SIG-UI-111 label-collision — diagnosis + fix (OPS-EXPORT-GCE-2 Blocker 6)

- **Date:** 2026-11-24 · **Harness:** devin-desktop/swe-2-high/subagent
- **Branch:** `r11/ops-label-collision-fix` (worktree `/tmp/sig-label-fix`),
  base `r11/P38.3c-round11-integration-plan-2`
- **Upstream:** `docs/build/runs/OPS-EXPORT-GCE-2.md` "Blocker 6" —
  `python -m exports build --from-spine` refused at
  `check_unique_labels` (`policy/slug_history.py:219`, call site
  `exports/spine_export.py:5928`) after 81.1 min:
  `duplicate display label 'surveillance camera in iso3166-2:US-WA #tyvj'
  within kind 'site' (entities 01a0b0d1-…b6161 and 01a0b0e6-…8324)`.

## Diagnosis — sub-issue 1: `#{hash4}` collides at real scale

`resolve_disambiguators` (K2 §3.2 disambiguation cascade `· {place}` →
`· {source}` → `#{hash4}`) ended every group with a 4-char Crockford-base32
suffix — a **20-bit space**. Its docstring claimed `#{hash4}` "always can"
separate a group. At ~260k entities the birthday bound guarantees colliding
hash4s inside large collision groups (~√(2·2²⁰) ≈ 1024 members per expected
collision, and the `site`-kind groups are far larger — see sub-issue 2).

The two named cameras:

| entity | `entity_hash` | hash4 |
|---|---|---|
| `01a0b0d1-462b-70bf-b40e-880db02b6161` | `tyvjdr9` | `tyvj` |
| `01a0b0e6-03bb-7486-a807-47e73838e324` | `tyvjwn5` | `tyvj` |

Both members of the same `(site, "surveillance camera in iso3166-2:US-WA")`
group → identical emitted labels → `check_unique_labels` correctly failed
closed. The assumption "hash4 always separates" does not hold at scale.

## Diagnosis — sub-issue 2: the `camera_name` loss is a CODE BUG, verified

The OPS-EXPORT-GCE-2 probe (`11-dup-label-probe.txt`) showed tier-0
`camera_name` claims on both entities but could not say which pipeline stage
dropped them. This leg ran the **exact** `EXPORT_QUERIES["label_facts"]` SQL
(real `latest_decision` + `claim_source` CTEs, real `claim_eligible_sql`
gate) against `sig-pg` via `cloud-sql-proxy` + `sig-pg-password`, scoped to
the two subject ids, `default_transaction_read_only=on` (no spine writes):

```
('…b6161', 'camera_name', 'SR 167 at MP 21.3: 84th Ave S')     | src: dot_511_wa spdx: CC0-1.0
('…b6161', 'camera_operator', 'Washington State Department of Transportation') | CC0-1.0
('…b6161', 'external_id', '1180')                              | CC0-1.0
('…8324', 'camera_name', 'SR 16 at MP 7.5: TNB EB East Anchorage') | CC0-1.0
('…8324', 'camera_operator', 'Washington State Department of Transportation') | CC0-1.0
('…8324', 'external_id', '9957')                               | CC0-1.0
```

Gate bisect on the six `camera_name` claims: `tier0=6, current
(upper_inf sys_period)=6, gated (claim_eligible_sql)=6, has value=6`; no
`publication_disposition` rows touch either entity. **The claims pass every
`label_facts` filter and populate `LabelFacts.fields["camera_name"]`.** The
loss is downstream, in the injected Part VIII screen:

```python
>>> natural_person_signal("SR 167 at MP 21.3: 84th Ave S")
"person_shaped"          # ← before the fix
```

`person_tokens` (rules `data/partner_identity.toml`) carries `"sr"` as the
generational suffix ("John Smith Sr"). `normalize_org_name` folds
`"SR 167 …"` → tokens `[sr, 167, …]`, and the check was a position-blind set
intersection — a **leading** "SR" (State Route — the WSDOT `SR <route> at
MP <mile>: <place>` convention, and every other DOT that names cameras the
same way) read as a person-name suffix. `derive_label` then skipped the
`camera_name` candidate under L-6 (`part8: fallback`) and the **derived**
candidate `{tech_words} camera in {place}` won — collapsing every screened
`site` in a jurisdiction onto one label and manufacturing the giant
collision groups that made sub-issue 1 fire.

So: **code path bug**, not a data posture. No spine change is needed or was
made.

## Fix (machinery only — no spine writes, no label-policy re-decisions)

### `policy/src/policy/labels.py` — `resolve_disambiguators` step 3

The `#{hash4}` step now applies the **same extension rule the slug registry
already uses for its 7-char URL hash** (K2 §3.3,
`slug_history.freeze_hashes`): members in sorted `entity_id` order take the
shortest `entity_hash` prefix not already taken within the group —
first-come keeps `#{hash4}`, a colliding member grows one base32 character
at a time until unique. Deterministic; emitted shape stays
`{name} in {place} #{disambiguator}`; only the colliding set changes.

On the incident pair this now emits
`surveillance camera in iso3166-2:US-WA #tyvj` (first, unchanged) and
`… #tyvjw` (second, extended to 5 chars).

Two robustness companions, each strictly limited to inputs that previously
**crashed** the export (emitted behaviour is byte-identical whenever the old
code produced unique labels):

- Steps 1/2 now verify their suffixed labels actually separate the group
  (on `casefold`, the same comparison `check_unique_labels` makes); a step
  that fails to separate — e.g. a `LABEL_MAX` truncation erasing the very
  `· {place}`/`· {source}` suffix — falls through to the next step instead
  of emitting duplicates.
- Step 3 reserves the disambiguator's width
  (`_with_disambig(..., reserve_suffix=True)`): the base label truncates
  *before* the ` #{hash}` suffix, never through it — the emitted label can
  never lose the characters that distinguish it.

`check_unique_labels` is unchanged — still fail-closed.

### `resolution/src/resolution/partner_identity.py` — `natural_person_signal`

The post-nominal subset of `person_tokens` — `jr, sr, ii, iii, iv, esq` —
now evidences a person **only in terminal token position**
(`"Kowalski Sr"`, `"Beaumont Esq"` still screen; honorifics/given/role
tokens unchanged in any position). The TOML remains the token authority;
`_POST_NOMINAL_TOKENS` only supplies the position the suffix class is
meaningful in. Verified: `"SR 167 at MP 21.3: 84th Ave S"` → `None`, and
`derive_label` now emits it with `label_basis: source_name, part8: pass`.

**Deliberately unchanged:** `partner_identity` (the entity-minting path)
keeps the flat `person_tokens` check — its `"SR"`-leading false positive is
a *conservative refusal* (the partner stays a text claim), and relaxing it
would change entity minting on re-ingest — a data-shape change outside this
ticket's scope. Recorded as a follow-up candidate for the identity layer.

## Tests

`tests/unit/test_policy_labels.py` (+44 tests, all green):

- `test_sr_route_camera_name_labels` — the two real camera names pass the
  screen and label `source_name`/`pass`.
- `test_post_nominal_suffix_still_screens` — terminal `Sr/Jr/Esq/III` still
  screens (names chosen without given-name tokens so the suffix itself is
  what fires).
- `test_disambiguation_extends_hash_on_hash4_collision` — the real incident
  ids; ` #tyvj` kept, ` #tyvjw` extended, `check_unique_labels` accepts.

Suite results: `tests/unit` + `tests/resolution` 3650 passed / 9 skipped;
`tests/exports` 1479 passed; the `natural_person_signal` consumers'
connector suites (dot_511 ×4, osm-adjacent, partner_refs, org_crosswalk,
aggregate/federal/document_list lanes, acq11, p37_69a) 301 passed. The 3
`tests/resolution/test_pg_backend.py` errors are environmental —
`postgis/postgis:18-3.6` has no linux/arm64 manifest on this host
(image pull fails before any test runs); unrelated to the change.
`ruff check`, `ruff format --check`, `mypy` (policy+resolution) all clean.

## Notes for the export re-run

- Zero spine writes this leg; the probe session was `read_only=on`.
- Re-run path: `run-export-on-vm.sh` + `probe-rights.sh` from
  `docs/build/logs/ops-export-gce-2/`; the SIG-UI-111 gate should now clear
  — the two cameras will emit their real `camera_name` labels and the
  remaining hash4-collision groups extend deterministically.
- `D-P37.65a-1` remains OPEN until an export actually lands.
