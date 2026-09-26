# Rights-review packet — `declarationcamera_be` (Déclaration Caméra, Belgium)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1). Reading the
> terms page is permitted research, not ingestion; no source *content* was fetched.
> Drafted 2026-09-15 in the B rights-review pass (the packet did not exist before).

- **Source id:** `declarationcamera_be`
- **Homepage:** https://declarationcamera.be/
- **Terms URL(s) fetched:** https://declarationcamera.be/ — retrieved 2026-09-15; the page
  is a JavaScript-only application shell ("platform-ui-custom doesn't work properly
  without JavaScript enabled") — **no terms/licence text was reachable**.
- **robots.txt:** honor.

## Terms (verbatim)

> UNDETERMINED — no terms page was reachable (JS-only app shell; no linked licence or
> legal notice found). Déclaration Caméra is a Belgian civic project registering
> declared surveillance cameras with police zones. The registry records no rights
> block (SIG-LIC-004; fails the export gate closed).

## SPDX candidate

`UNDETERMINED` — no licence text reachable.

## redistributable analysis

Not asserted (UNDETERMINED). The register's entries are operator-declared camera
records; republication needs a real rights review (SIG-LIC-003) and likely HG-04
outreach to the project.

## derivative_permitted analysis

Not asserted (UNDETERMINED).

## ODbL compartment implications

Not OSM-derived.

## Custody posture recommendation

**LINK** — link out, do not re-host. `ingestion_permitted = false` until terms are
reachable and reviewed; HG-04 outreach is the honest next step.

## Decision

- [x] permit ingestion — reviewer: counsel (HG-02), operator-reported counsel approval 2026-09-15
- SPDX to record: `LicenseRef-DerivedFacts-Citations`   rights_reviewed_by (role, never a name): counsel (HG-02)   rights_reviewed_on: 2026-09-15
- **Status:** FLIPPED 2026-09-15 on counsel's approval — DERIVE custody, derived-facts only (metadata/facts, never the upstream expressive content), `redistributable=false`.

## Counsel-needed flag

**YES — terms unreachable; Belgian civic-project register; HG-04 outreach owed before
any flip.**

**HG-02 resolved 2026-09-16 (counsel, operator-reported):** derived facts/citations publishable — dedicated `derived_facts` compartment (ADR-086); `redistributable` flipped to true on the registry record (it gates SIG's emitted claims; upstream bytes are still never re-hosted — architectural, not flag-borne).

## eID access-path investigation (2026-09-16)

Operator asked whether the eID wall is crossable. Finding — the wall is real **and**
structural, so the recorded `NoLiveTargets` posture is correct and likely permanent:

- `declarationcamera.be` is a **declaration filing portal**, not a published
  register. Citizens file *their own* camera declarations to police; there is no
  public queryable dataset of registered cameras behind the login — authenticated
  access reaches only the filer's own declarations, not a national browse.
- Authentication runs through Belgium's federal CSAM service (SPF BOSA): Belgian
  eID card, citizen token, or itsme mobile-app code. Non-Belgian nationals can
  request an alternative identification means from SPF BOSA directly — a manual,
  human account-registration process.
- Even with credentials, there is no bulk/public data surface to ingest; the
  register's contents are visible only to police and the DPA.

**Consequence:** `NoLiveTargets` stands as the honest terminal posture for this
source. A future Belgian data path would come from a *different* origin (e.g.
municipal camera registers published under open-data terms), not from
declarationcamera access. Sources: besafe.be declaration-system docs, ibz.be
node/1241, anpi.be declaration guidance (all public pages, fetched 2026-09-16).
