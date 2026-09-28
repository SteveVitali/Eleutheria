# P32.24 — agent walkthrough log

The walkthrough half of the acceptance run: every row is one executed
walkthrough, with what was exercised, what was observed, and which suite owns
the interactive proof the agent cannot honestly claim. Evidence classes are
the portfolio's: `agent_walkthrough` (this document, executed by the agent)
vs `automated_conformance` (byte-digest checks) vs `independent_human`
(none — deferred).

Subject release: `p-81f1986aac5cb18b29f2dae0458f74d8b639f6efc1a9de35abc38167b126d2dd`
(the staged `sig.journey-corpus/1` release under `corpus_registry/`).

## W1 — no-JS record→evidence→claim→dossier path · **pass** (`agent_walkthrough` + `automated_conformance`)

- **Walked:** browse index page 1 → page 2 (tail record
  `ent-acc-dep-54`) → record page → evidence anchor page (`art-acc-1`) →
  jurisdiction page (`unreported`) → dossier page (`okc`).
- **Observed:** every page is a single self-contained HTML document — zero
  `<script>` tags across the whole staged tree (verified byte-wise, WT.no_js);
  navigation is pure `<a href>` + tables; every record page carries its
  immutable `/r/p-…/…` citation block; the tail record exists only on browse
  page ≥2.
- **Owned elsewhere:** nothing — fully discharged in this run.

## W2 — keyboard-only traversal · **verified_by_test**

- **Walked:** the emitted markup is plain links/tables in DOM order — tab
  order = document order, no focus traps, no JS handlers to lose.
- **Observed:** record, browse, evidence, dossier pages contain only
  semantic markup + embedded CSS; there is no interactive widget in the
  released archive to keyboard-test beyond link traversal.
- **Owned elsewhere:** the interactive keyboard + axe pass over the *web
  app* surface is `web/`'s e2e suite (`npm --prefix web run check` →
  `test:e2e`, WCAG 2.2 AA). This log never merges the two claims.

## W3 — print rendering · **pass** (`agent_walkthrough`)

- **Walked:** record page, browse page, dossier page opened for print
  review — each is one static HTML file with all CSS embedded and no
  external assets (fonts/images/scripts).
- **Observed:** nothing to fetch = nothing that can fail at print time; the
  printed bytes are the served bytes. Column tables print as tables; the
  citation block is on-page (a printout carries its own citable identity).
- **Owned elsewhere:** nothing — fully discharged.

## W4 — back/forward + deep-link restore · **verified_by_test**

- **Walked:** the archive is plain multipage HTML — every view is a URL;
  back/forward is browser-native navigation between static documents (no
  SPA state to corrupt, no scroll-restoration JS).
- **Observed:** no history-manipulation markup in the released bytes; the
  only history adapter in the system is the app's `sig.workspace-state/1`
  (`web/src/islands/workspace.ts`), outside this archive.
- **Owned elsewhere:** the workspace-state contract's parse/emit/restore is
  pinned by the web unit suite — flagged, not re-claimed.

## W5 — release citation round-trip · **pass** (`agent_walkthrough` + `automated_conformance`)

- **Walked:** copied the immutable record route
  `/r/p-81f1986a…/c/sig_graph/entity/deployment/ent-acc-dep-00/` from a record
  page's citation block; resolved it inside the staged release; verified the
  record JSON + HTML bytes against `integrity_manifest.json`; confirmed the
  convenience `/entity/` overlay stub labels itself *never cite* and points
  back at the immutable route.
- **Observed:** cited bytes == manifest bytes; the mutable-alias
  distinction is printed on the page itself.
- **Owned elsewhere:** nothing — fully discharged. (The same citation under
  a future correction still serves these exact bytes — C.citation_persists.)

## W6 — receipt→moderation narrative · **verified_by_test**

- **Walked:** the journey-C narrative end-to-end on the committed PG proof:
  anonymous report filed against record `ent-acc-dep-00` citing claim
  `target` → receipt `rct-…` durable before acknowledgement → fresh-
  connection receiver still resolves it → reviewer queue row → reviewer
  proposes `correct`, curator approves → bridge applies the §16.6 pair
  (close + revises, `asserted_by=cur-1`) in one txn → `applied` event →
  `mark_published` links `p-81f1986a…` + the new-claim ref → public state
  resolves.
- **Observed:** 10/10 proof steps ok (`INTAKE_JOURNEY.json`); the receiver
  role's claim/application/event writes are refused live; lifecycle states
  stayed visibly distinct at every hop.
- **Owned elsewhere:** the deterministic execution is
  `tests/db/test_journey_portfolio_pg.py` (Docker); the user-facing "can a
  stranger file a correction" question is `D-R10-USERS-1`.

## Deliberately NOT walked

- **Independent human usability session** — no volunteers were available;
  `UX.independent_sessions` is `deferred` under `D-R10-USERS-1` with
  `USABILITY_TASK_PROTOCOL.md` as the compensating control. Nothing above is
  a proxy for it.
- **Production candidate walkthrough** — the P32.23a candidate publishes
  zero records; walking it is `not_applicable`, re-run at the
  `D-R10-LIVE-1` return pass.
