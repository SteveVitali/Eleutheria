# ADR-100 — Identity minimization for contribution; no homegrown accounts

- **Status:** Accepted
- **Phase / ticket:** Phase 29 / P29.1 (`docs/tickets/P29.1__contributor-identity-and-ops.md`) — Round 7 (Activation, Trust & Reach) `ACTIVATE.1`; the ticket this ADR is owned by and lands with.
- **Date:** 2026-09-23
- **Related:** **§0.7 / Part VIII** (minimal PII; the curation surface is not public), **§34 / §36** (curation, dispositions, governance), **ADR-068** (the loopback-bound `/curate` island allowance), P15.x (`/dispute` — the one-click no-account corrections flow), P16.1 (`tasks.contributor.Contributor` — pseudonymous tiered contributor), P16.2 / P21.7 (OSM contribution-back via the changeset feed → `LeverageLedger`), `api/src/api/curation.py` (bearer-token → pseudonymous tiered contributor), `tasks/poisoning.py` (anti-poisoning), the deferral **D-R7.1-AUTH** (this ADR opens), the gates **HG-08 / HG-10** (contribution-back accounts / usability), backlog home **BL-057**.

## Context

Round 7 turns on the human loop — corrections, curation, data entry, verification — under public
scrutiny. The first-principles question is whether that requires user identity / login / accounts. The
honest answer is **identity *minimization*: use the least identity each contribution type actually
requires, and never build a homegrown account/credential system.** SIG's pilot users are activists in
an adversarial domain (motivated adversaries: vendors, police, doxxers, poisoners, Sybils), so account
data on *contributors to a surveillance-watchdog* is itself sensitive, and running credentials/PII
contradicts SIG's minimal-PII posture.

Three contribution types map to three identity needs, and two of the three are **already built**:

1. **Corrections / disputes** — the public channel. Already a **one-click, no-account** flow
   (`/dispute`, P15.x). Requires **zero identity**. Lowest friction, no PII, no account liability.
2. **OSM contribution-back** — mediated through **OSM's own identity**: a contributor edits OSM and SIG
   observes via the changeset feed + hashtag → `LeverageLedger` (P16.2/P21.7). SIG stores **no** identity
   here; OSM owns it.
3. **Curation / L0 data entry / dispositions / revert** — the only path that needs SIG-side identity, and
   it **already exists**: `api/curation.py` maps a **bearer token → a pseudonymous, tiered**
   `tasks.contributor.Contributor` (401 without a token, 403 without the tier scope); every write is
   append-only carrying the pseudonymous handle as the human actor id; anti-poisoning applies
   (`tasks/poisoning.py`); the surface is **not public** (Part VIII §0.7; loopback-bound;
   `SIG_CURATION_ENABLED`). The only gap is the demo tier-token store (`CURATION_KEYS`).

## Decision

1. **Three tiers of identity, no accounts SIG owns.**
   - **Anonymous (no account):** corrections/disputes — the public channel. *(built; kept as-is)*
   - **Federated / mediated:** OSM contribution-back — identity owned by OSM. *(built; kept)*
   - **Tiered, invite/issue-based curators:** the P16.1 pseudonymous contributor + bearer-token curation
     surface, for a **small vetted set** (the operator + trusted collaborators), promoted through tiers,
     with anti-poisoning + append-only attribution intact.

2. **Productionize the tier-token curator store minimally** (P29.1): replace the demo `CURATION_KEYS`
   registry with a real store, kept **issue/invite-based, pseudonymous, NOT open signup**, everything
   else (401/403 tiering, append-only actor id, anti-poisoning, loopback binding) unchanged.

3. **Never build a public username/password account system.** For this project it is the wrong trade on
   ethos (minimal PII), attack surface/safety (open signup invites Sybil/poisoning at scale; contributor
   account data is itself sensitive), and liability (auth/session/reset/moderation obligations
   disproportionate to the pilot).

4. **Defer public authenticated contribution — open `D-R7.1-AUTH`.** If/when contribution must scale
   beyond a vetted curator set, do it via **OAuth against an external IdP (OSM and/or GitHub)** — store
   only a **pseudonymous external subject id + tier**, **never** passwords or PII — behind anti-poisoning
   + a written moderation/safety plan + a threat model for contributor exposure. This is "identity
   without an account system." It is a **deliberate later decision** (its own ADR + ticket), **gated on
   demonstrated demand**, and is **not built speculatively**; recorded as `D-R7.1-AUTH` (OPEN, homed to
   BL-057).

## Consequences

- The human loop turns on with the least identity each channel needs and no new PII surface: anonymous
  corrections stay the default public channel; OSM owns the federated identity; a small vetted curator
  set uses the existing pseudonymous bearer-token surface with a real (invite-based) token store.
- SIG never becomes an account platform; there are no credentials to breach and no contributor-PII
  honeypot on a surveillance-watchdog.
- Scaling public authenticated contribution is possible later without re-architecting — it is an
  external-IdP OAuth addition (`D-R7.1-AUTH`), gated on demand + a safety plan, not a homegrown build.
- The productionized curator store is deliberately small (issue/invite-based); onboarding more than a
  vetted set requires re-opening the deferred decision, not quietly opening signup.

## Alternatives considered

- **A public username/password account system.** Rejected on ethos, attack surface/safety, and
  liability (above) — the wrong trade for an adversarial-domain pilot.
- **OAuth-external-IdP public auth now.** Rejected as premature: no demonstrated demand, and turning it
  on responsibly needs a moderation/abuse/safety plan + a contributor-exposure threat model that do not
  exist yet — hence the deferral, not the build.
- **No SIG-side identity at all (anonymous everything).** Rejected: curation/dispositions/revert need a
  tiered, attributable, anti-poisoning-guarded actor — the existing pseudonymous bearer-token surface is
  exactly the minimal identity that path requires.
- **Keep the demo `CURATION_KEYS` store.** Rejected: a hard-coded demo registry is not a real
  invite/issue-based store; productionizing it minimally is the small, in-scope step.

## Revisit trigger

- **Demonstrated demand for public authenticated contribution** beyond the vetted curator set, **plus a
  ratified moderation/abuse/safety plan and a contributor-exposure threat model** — then design external-
  IdP OAuth (pseudonymous subject id + tier only) in a **new ADR** + ticket, closing `D-R7.1-AUTH`; never
  a homegrown account system, and never a silent flip to open signup.
- **Curator scale or abuse** outgrows the invite/issue-based tier-token store (Sybil/poisoning pressure
  the anti-poisoning layer cannot absorb, or the vetted set stops scaling) — reconsider the store and the
  deferred OAuth path.
- **A named-IdP requirement is forced on SIG** (a partner or governance requirement to attribute
  contributions to a specific external identity) — reconsider the federated-identity choice in a new ADR.
