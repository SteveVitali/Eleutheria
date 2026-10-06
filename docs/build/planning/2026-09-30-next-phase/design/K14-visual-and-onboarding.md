# K14 — Visual design, clarity and onboarding narrative

- **Row:** K14 (Stream K, P/D) · **Written:** 2026-09-30, work window 22:09:29Z–22:40Z (`date -u`) · **Worktree HEAD:**
  `b6b3d970` (branch `claude/next-phase-planning`). `web/`, `AGENTS.md` and the generated spec are byte-identical to chain
  tip `b051732c` (`git diff --stat b051732c HEAD -- web AGENTS.md docs/2_canonical_design_spec.md` is empty, 22:22:29Z), so
  every `code` citation below is also a chain-tip citation.
- **Operator input answered (verbatim in `feedback/OPERATOR_FEEDBACK.md`):** U-004 (*"I like how technically precise the
  language is and how clear the definitions, editorial standards, methodology, etc. are articulated, so that the project can
  pass open source scrutiny muster"*), U-005 (*"confusing and verbose"*), U-007 (*"a beautiful experience … very clear what
  the project is and why it exists and what its capabilities are"*), U-009 (*"we will announce surveillancegraph.org publicly
  without holding back when the time is right"*), with U-001 (what SIG is, confirmed) and U-002 (advocate design centre;
  journalists and organizers co-primary).
- **Inputs read:** META_PLAN §3 and the K14 row; U-001…U-015; **K0** (binding: page types T0–T3, budgets, least-power
  ladder, CSP, I-1…I-10); K12a (§0, §5–§7); K12b (§1, `data/k12b_ideas.csv`); C2 `JOURNEYS.md` (§2, §5–§10); C6
  `REVIEW_SYNTHESIS.md` (§0, TH-05, TH-09, TH-12, §6, §8); C5 (§0, §5–§7); D3 (all); J3 (§0, §5); the web design system
  (`web/src/styles/epistemic.css`, `web/src/layouts/BaseLayout.astro`, `web/src/components/*`, `web/src/lib/epistemic.ts`,
  `web/src/pages/{index,visual-language,style-guide,methodology}.astro`, `web/src/islands/MapIsland.tsx`, `web/dist`); spec
  §1.1–1.4, §39.0–39.9, §40, §41, Appendix E (glossary).
- **Evidence classes (P1):** `code` (file:line at `b6b3d970`); `live-read` (17 headless-Chrome page loads, 22:12:57Z–
  22:14:02Z, plus two drift-guard HEADs); `recorded-execution` (offline analysis of C2's hashed text captures; contrast and
  palette validation; font-size measurement — commands in §13). Every design choice, estimate and copy draft is
  **`inference`** or **agent-drafted** and labelled.
- **Status vocabulary (P5):** nothing here is engineered or verified. It is a design and a set of draft requirements. The
  statements in §2 are **agent-drafted** and stay provisional until the operator confirms them verbatim (D-K14-1).
- **P3/P14/P16:** production was only read (GETs of public pages; no form, POST or login). The browser user agent carried
  `SIG-planning-K14-review/1 (read-only)` and no personal identifier. Font packages were installed only into the session
  scratchpad (`npm install --userconfig=/dev/null --ignore-scripts`). No secrets appear here.
- **Writes:** this file and `findings/incoming/K14.csv` only. Screenshots and measurement JSON are in
  `docs/build/logs/next-phase/K14/` (gitignored; 26 files hashed in `SHA256SUMS`, sha256 `e2261b86d988…`).
- **Drift guard:** `HEAD /` at 22:12:30Z and 22:22:21Z both returned `Last-Modified: Sun, 27 Sep 2026 01:33:43 GMT`, ETag
  `"6ab87277-14f54"`. This is the same release C2 and K12b reviewed (`sig-2026-09-27-ce480ab1`), so there was no drift.

---

## 0. On one page

**Positioning (agent-drafted, §2.1).**
- **Tagline (the home H1):** *The evidence behind public surveillance, place by place.*
- **One sentence:** *SIG joins public records about government surveillance so anyone can see, for a place, what is
  deployed, who runs it, who can access its data and when it is next decided — with every fact linked to its source,
  every disagreement shown and every gap labelled.*
- **Niche (from C5 §7):** peers each answer one question. SIG shows whether they agree, which document says what, what is
  still unknown and when the next decision is, on one page you can cite and print.

**Diagnosis.** The operator's praise (U-004) and complaint (U-005) are about the same text, in two different places:
- **The precision is real.** It lives in the reference pages: methodology, editorial standards, the visual language.
- **The verbosity comes from repetition and from internal vocabulary leaking into the chrome.** Four measurements show it:
  - The same ~90–110-word provenance, dispute and citation block ends every page. With the 15-link header, shared chrome is
    a median **138 words per page**. That is **36 % of the words on the median page**, and **≥ 50 % on 11 of 41 pages**.
  - The home page repeats one caveat **126 times**.
  - Each dossier says "absence … is not evidence of absence" **3 times**.
  - Every page carries about **13 undefined technical tokens** (belief, ruleset, untiered, W1, W3, tier).

  (§1; NEW-1.)
- **There is no visual system to make the site "beautiful".** Today it has:
  - **17** font-size literals;
  - prose lines of about 120–140 characters;
  - **no** dark mode;
  - **no** logo, favicon or imagery;
  - a colour ramp that fails its own ordinal job;
  - a "contested" colour reused for four other meanings.

  (§1; NEW-2…NEW-5.)

**The design in five moves.**
1. **Say what SIG is before anything else.** The home page leads with the tagline, one sentence and a place search. Then
   come three persona "start here" paths, at most six traceable figures and a short "what makes SIG different". The
   126 tiles move off the home page (§2.3).
2. **Two layers of language.** Every page is plain first, and the precise definition is always one click away:
   - a **glossary** built from spec Appendix E;
   - native HTML `popover` definitions, which need no JavaScript;
   - an "In brief" box on top of each precise reference page, which keeps its text **unchanged** (U-004);
   - requirement ids kept in "Spec references" disclosures, never in prose.

   (§2.5, §3.)
3. **One caveat, where the number is.** Caveats become short linked labels attached to figures ("not a census",
   "Provisional"). The page-footer block becomes a one-line strip that expands on demand (§3.2, §3.7). This proposes a
   SIG-UI-044 amendment (D-K14-6).
4. **A calm, record-like visual system in which colour means "look here".**
   - Type does the hierarchy, using one self-hosted OFL face (Public Sans Variable, 26.2 KiB, D-K14-3) on a 1.25 scale
     with 8 steps.
   - Neutrals do the structure.
   - Colour is reserved: **raspberry** means sources disagree, **amber** means provisional, **blue** means links and data.
   - Support is a monotone slate ramp plus the ⊕ glyph.
   - Dark mode follows the OS setting with no JavaScript.
   - Every colour was contrast-checked and CVD-checked with a validator (§4.3).
5. **Onboarding that cannot lie.**
   - Example questions are generated from the release and tested, and they render only when they resolve to sourced data.
   - Capability claims are bound to release metrics.
   - Every empty state names its kind, its reason, what is nearby, what to do next and when it may change (§6).

**Sized for K0.** All K14 pages are **T1**: zero JavaScript unless an element from the kit earns its place. The design
system CSS should stay ≤ 12 KiB gzip; today it is 4.1 KiB. The font should stay ≤ 30 KiB. All definitions, menus and
"cite" disclosures are HTML (`<details>`, `popover`). Nothing here needs a new runtime dependency (§4.13).

**Output for S2/T3:**
- **22 draft requirements** (DR-K14-01…22, §8);
- **12 tickets** (UXK14-1…12, §9: 1 L, 6 M, 5 S);
- **9 operator decisions** (§10);
- **11 new findings** (§12; 4 S2, 7 S3).

---

## 1. What the live site says today (measured)

### 1.1 Copy load (C2's 50 desktop text captures, re-analysed offline; `tools/copy_audit.py`)

| measure | value | evidence |
|---|---|---|
| Shared chrome per page (the 15-link header, then "How we know this", the dispute line and "Cite this page") | median **138 words**; the footer block alone is 89 words on `/watch/` | `copy_audit.json` sha256 `87eb1ca5db15…` |
| Share of a page's words that are shared chrome | median **36 %** over 41 non-print pages; **≥ 50 % on 11** (all 9 task pages, `/evidence/` 60 %, `/corrections/` 52 %); dossiers 31–39 % | same |
| One caveat repeated | "…an inventory, not a census or an estimate (SIG-METRIC-008)" appears **126×** on `/` and 126× on `/coverage-metrics/` | same; F-09, F-108 |
| The absence sentence on dossiers | "absence … is not evidence of absence" appears **3×** on each of 9 dossiers (banner, summary, full list) | same |
| Undefined technical tokens | ~**13 per page** (belief, ruleset, untiered, W1/W3, tier, as of world…), almost all from the chrome: the footer uses "ruleset" 4× and "belief" 2× | same |
| Requirement ids in prose | 126 on `/`, 127 on `/coverage-metrics/`, 7–9 on `/visual-language/`, `/map/` and `/network/`; 1 on every dossier (`SIG-RECON-058`) | same; RI-50 / DR-C6-28 |
| Readability (Flesch–Kincaid grade, heuristic syllable count) | median about 9; `/methodology/` 12.3, `/editorial-standards/` 12.1, `/network/` 15.8, `unresolved` dossier 16.7 | same (the estimate is rough, **inference**) |
| Missing spaces at inline-element boundaries | "concern?Dispute" on **41 of 50** pages; also "SIGreports", "toresearch", "withnamed", "devicesacross", "(SIG-UI-022).Every" | NEW-7 |
| Digit grouping | **56** numbers of 5 or more digits with no separators on home, dossiers and methodology ("2423200 of 2423200"), and **0** grouped | NEW-8 |

### 1.2 Visual system (17 live loads, `json/k14_metrics.json` sha256 `21f346dcf650…`; `code`)

| measure | value |
|---|---|
| Font family | the system stack (`web/src/styles/epistemic.css:68`), so it renders as SF, Segoe or Roboto depending on the OS |
| Font sizes | **17** distinct `font-size` literals in source (0.62–1.9 rem). **10–15** distinct rendered sizes per page. 9.92 px nav-group labels on every page; 9 px text on `/map/` and `/network/` |
| Measure (line length) | `main` max-width 62 rem (`epistemic.css:75`) gives prose lines of about 120–140 characters at 1440 px (estimate at 0.5 em per character, **inference**). The readable band is 45–75 |
| Dark mode | none: 0 `prefers-color-scheme` rules and no `color-scheme` meta. Under `colorScheme: "dark"` the body stays `rgb(255,255,255)` (`home_dark.png` `9aa5b5f90d69…`) |
| Colour ramp (support) | four hues over 156°; lightness out of order (L 0.67 / 0.72 / 0.57 / 0.47 from weak to confirmed); `probable` 2.50:1 and `withdrawn` 2.85:1 against white (NEW-3) |
| Colour meaning | the `contested` token also colours the incompleteness banner (`epistemic.css:271-273`), bound map-layer controls (`:410-411`) and speculative access paths (`:478-487`) (NEW-2) |
| Header | 15 links in 3 groups and no current-page marker (0 `aria-current` in the header on 16 pages). The H1 starts **230 px** down at 1440×900 and **344 px (41 %)** down the 844-px mobile screen. The header's left edge (168 px) does not line up with `main` (244 px) (NEW-9) |
| Brand and imagery | a text-only "SIG" wordmark; 0 images or SVG on content pages; no favicon; 0 Open Graph tags (C2 NEW-27) |
| Home length | 14,432 px at 1440 and 36,036 px at 390. "Where to start" comes after all 126 tiles and the 55-item jurisdiction list (`web/src/pages/index.astro:67-150`) |
| Motion | map cluster click uses animated `easeTo` (`MapIsland.tsx:383`), although the file's header says "no auto-pan animation; reduced-motion safe" (`:33`) (NEW-10) |
| CSS weight | `epistemic.css` is 19,046 B raw, **4,149 B gzip** (`web/dist/_astro`) |

### 1.3 What to keep (U-004; C2 §9; C6 §8)

- **The epistemic vocabulary:**
  - four independent fields;
  - the four-step ⊕ glyph with its reason;
  - the ≠ contested marker;
  - one absence texture with four typed kinds;
  - the contradiction range.

  No peer does this (C5 §0).
- **The register rules** (SIG-UI-043) and the three conformant hard cases (SIG-UI-045).
- **The methodology's precision**: named denominators, "what SIG does not do", and PROVISIONAL disclosures.
- **Honest empty states**: the decision-date framing on `/watch/`; "not evidence of absence".
- **Static pages at Lighthouse 1.0**, with the skip link, the 3-px focus ring and no keyboard traps.
- **The access-edge legend** ("Never implies: That anyone used it").

---

## 2. Positioning and narrative

### 2.1 Statements (agent-drafted; the operator confirms at D-K14-1, together with D3 Q5)

**Tagline (home H1, 8 words):**
> The evidence behind public surveillance, place by place.

*Alternates:*
- "Public surveillance, traced to the documents."
- "Who watches, who shares, who decides — sourced."

**One sentence (45 words; the home sub-head — the meta description uses its first clause, ≤ 160 characters):**
> SIG joins public records about government surveillance so anyone can see, for a place, what is deployed, who runs it,
> who can access its data and when it is next decided — with every fact linked to its source, every disagreement shown and
> every gap labelled.

**One paragraph (the About page opening and the press-kit boilerplate):**
> The Surveillance Infrastructure Graph (SIG) is an open record of the surveillance technology public agencies use —
> licence-plate readers, camera networks, real-time crime centres, face recognition and more — and of the contracts,
> policies and data-sharing arrangements behind it. It joins many independent public sources: agency and vendor
> disclosures, contracts, council records, grants, crowdsourced maps and records releases. Every fact stays linked to the
> document it came from. Where sources disagree, SIG shows both sides. Where SIG does not know, it says what kind of unknown
> it is and what would settle it. SIG is not another camera map and not a census: it reconciles what others publish, links
> back to them, and turns the result into place pages you can explore, cite and print — for an advocate preparing for a
> council vote, a journalist checking a claim, and an organizer working out who decides what.

**Why it exists (one line, About):**
> Facts about public surveillance are scattered across thousands of agency portals, contracts and meeting records, and
> each existing project answers one piece. SIG joins the pieces so anyone can see the whole picture for a place — and check
> every part of it.

**What SIG is not (four short lines, About and footer):**
- **Not a census.** Counts are what named sources record, never a total.
- **Not another camera map.** It links to the projects that map cameras.
- **Not advocacy.** It reports; it does not characterize or endorse.
- **Not live.** It publishes dated, citable releases.

**Grounding.**
- U-001 (confirmed): joined evidence, a printable sourced dossier, and linking rather than rebuilding.
- The C5 niche (A3 cost and decision date, A8 do sources disagree, A11 a cited brief).
- SIG-CHART-001/002 and SIG-UI-027b neutrality.

**Honesty rule.** The statements describe the *target*. Each capability clause renders on the live site only when the
release demonstrates it (DR-K14-05). Today, for example, "when it is next decided" would render as "decision dates: being
built — none tracked yet", because the watch is empty (K7) and every dossier's decision date is unknown (C2 P1-T2).

### 2.2 Capabilities, in five verbs (the home "What you can do" row and the About page)

| verb | plain promise | surface | shown only when (capability binding, DR-K14-05) |
|---|---|---|---|
| **Find** | "Look up a state, county or city and see what the record holds." | place search → dossier (K3/K4) | ≥ 1 dossier; the search resolves the 55 jurisdiction names (D3 §3a) |
| **Trace** | "Follow any figure to the sources and rows behind it." | figure → "explain this number" → record → evidence (J3 §5.4) | the pointer contract holds for every home figure |
| **Compare** | "See where sources agree, disagree, or say nothing." | contested markers, contradiction ranges, gap views (K12b I-11/I-12) | ≥ 1 published contradiction record is reachable from a page |
| **Follow** | "Know what is up for a decision, and subscribe." | watch + iCal/RSS (K7) | ≥ 1 tracked decision; otherwise the card reads "Decision tracking — being built" |
| **Take** | "Cite a pinned page, print a council brief, download the data." | cite, print (TH-10), `/data/` (J3) | pinned citations live (G3); downloads behind the egress guard (J3 C3) |

### 2.3 Landing page (T1, zero JavaScript; ≤ 5 screens at 390 px, D3 §3c)

| # | section | content | rules |
|---|---|---|---|
| 0 | Header | wordmark (logo + name); ≤ 6 section links; a search field (GET `/search/`) | ≤ 64 px tall on desktop; on mobile, "Menu" is a `<details>` (§5.3) |
| 1 | **Hero** | tagline (H1); the one-sentence sub-head; a **place search** ("State, county, city, agency or vendor", GET form, placeholder only, never pre-filled); 3 example chips generated from the release (§6.2); the release stamp "Data as of 27 Sep 2026 · release ce480ab1 · N days old" | above the fold at 390×844 and 1440×900; H1 top ≤ 120 px on mobile and ≤ 160 px on desktop |
| 2 | **Start here** | three persona cards (advocate, journalist, organizer), each a 3–4-step path, plus a small "I want the data" link (§6.1) | every step link resolves to real data in a golden place (C5 §7, D3 §4) |
| 3 | **The record today** | **≤ 6 headline figures**, each a J3 `<Figure>` with value (digit-grouped), unit, denominator, "not a census" label where applicable, as-of, a **Provisional** chip where the method is unevaluated (L3), a contested marker where contested, and a "Sources ›" link | one label per quantity site-wide (C2 NEW-18); the 126 tiles move to `/coverage-metrics/` (QW-9) |
| 4 | **What makes SIG different** | four items, each with a tiny static-SVG illustration drawn in the epistemic language: *Joined, not copied* · *Disagreements stay visible* · *Gaps are labelled* · *Cite it, print it* | each links to a live example in the golden dossier |
| 5 | **See an example** | one golden-place card: name, 3 joined facts from ≥ 3 sources, 1 real disagreement, the decision date (or its typed absence), and "Open dossier ›" | only once a joined city-level dossier exists (C5 §6 "seek a listing only after…"); until then this section is omitted, not faked |
| 6 | **How to read SIG** | a 4-item key: ⊕ support, ≠ contested, the hatch with its four kinds, Provisional; one line each; "Full visual guide ›" | built from the lexicon (§3.4) |
| 7 | **Trust and method** | links: How SIG works · Methodology · Editorial standards · Corrections (with count) · Known issues · Data & licences; one plain disclosure line: "SIG is maintained by a single independent maintainer with AI agents; its data has not yet been independently reviewed." (wording at D-K14-7) | this is the **only** place the review-status disclosure appears in full; elsewhere it is a chip or the footer strip |
| 8 | Footer | licence line; "Dispute or correct" (SIG-UI-033); About · Contact · Releases · Status · Other public resources (D3 Q4); "not a census / not advocacy" line | the same on every page (§4.6) |

**Removed from home:**
- the 126 predicate tiles (moved to `/coverage-metrics/` as a sortable table);
- the 55-item jurisdiction list (replaced by the search, and by K4's country index one click away);
- the long "How to read this record" paragraph (replaced by the 4-item key).

**Budget:**
- T1 (K0 §4.3): document ≤ 150 KiB, total ≤ 170 KiB, 0 KiB JavaScript. A ≤ 20 KiB `<sig-typeahead>` on the hero search
  is allowed only after K3 ships its shards.
- Illustrations are inline SVG, ≤ 3 KiB each.

### 2.4 About / How it works (`/about/`, T1)

1. **What SIG is.** The paragraph from §2.1.
2. **Why it exists.** The line from §2.1, plus the landscape in one short table: "Atlas tells you what an agency adopted;
   Eyes on Flock what Flock's portal says; DeFlock where cameras are; alpr.watch when it is on an agenda; SIG whether those
   agree…" (C5 §7). Each peer is a link, and the table is labelled "Other public resources; SIG does not endorse" (D3 Q4).
3. **How it works in five steps.** A static SVG diagram, one sentence per step, each linked to its precise methodology
   section:
   1. **Collect.** Public sources, each with a recorded rights review.
   2. **Capture.** Keep a dated, hashed copy where the licence allows.
   3. **Extract claims.** Each fact carries its source, date and how directly the source supports it.
   4. **Reconcile.** Match the same agency, vendor or camera across sources; keep every disagreement.
   5. **Publish releases.** Dated, citable and downloadable; corrections are added, never overwritten.
4. **What SIG can and cannot tell you.** The five verbs (§2.2) and the four "is not" lines.
5. **Who runs SIG and how it is checked.**
   - The maintainer model (D-K14-7).
   - What is automated.
   - What is PROVISIONAL, and why (Stream L).
   - That no counsel, editorial board or independent reviewer exists yet (U-013; C6 TH-01; D3 Wave 0).
6. **Independence and costs** (operator text, D-K14-7): who pays, and whether SIG takes money from vendors or agencies.
7. **How to cite, correct and reuse.** Pinned citations, the dispute path, licences per compartment.
8. **Known issues.** A link to J3's issues log.

### 2.5 The methodology entry point: plain layer over precise text (U-004)

The rule: **never rewrite a precise definition to make it plain. Add a plain layer in front of it, and link the two.**

| layer | where | form | owner |
|---|---|---|---|
| L1 plain summary | "In brief" box at the top of `/methodology/`, `/editorial-standards/`, `/visual-language/` (retitled **"How to read SIG"**), `/coverage-metrics/`, each glossary entry | ≤ 80 words; about grade 10 (estimate); one idea per sentence; links to the L2 section | UXK14-4 |
| L2 precise text | today's text, **unchanged** except for removing requirement ids from prose and fixing the honesty issues already routed (F-104, F-129, F-140) | full sections with stable anchors (`#support`, `#reconciliation`, …) | existing pages |
| L3 formal references | a **"Spec references"** `<details>` at the end of each section listing the SIG-* ids it implements; a `/glossary/` entry per term with the plain definition, the precise definition, and "Defined in spec §x" | links resolve publicly only if the spec is published (D-K14-8) | UXK14-4 |

**The glossary** (`/glossary/`, T1) is generated from one source of truth:
- spec **Appendix E** (26 terms, `docs/2_canonical_design_spec.md:8968`);
- the epistemic lexicon (`web/src/lib/epistemic.ts`);
- about 15 site terms: release, compartment, dossier, record, claim, capture, source, mirror, configured / declared /
  observed access, directness, provisional, as-of, pinned citation.

Each entry carries a plain definition (≤ 25 words), the precise definition (verbatim from the spec where one exists), an
example, and "See also". The glossary is not published today, although it is written (NEW-6).

**Term links.**
- On record and reference pages, the first use of a glossary term in `main` is a `<Term>`: a link to `/glossary/#term`.
  Beside it sits a native `popover` definition (a `<button popovertarget>` with an `ⓘ` label and an accessible name).
- This needs no JavaScript: `popover` is HTML. K0's least-power ladder already lists it (§4.6.1).
- Print pages replace popovers with a "Terms used on this page" list at the end.

---

## 3. Copy principles

### 3.1 The ten rules (agent-drafted; for the style guide, SIG-UI-046)

| # | rule | test |
|---|---|---|
| CP-1 | **Answer first.** Each page's first sentence answers the question its persona arrived with (SIG-UI-001's "arrives with"). | review against the D3 journeys |
| CP-2 | **One caveat, where the number is.** A caveat attaches to the figure it qualifies, as a short linked label. A sentence of 8 or more words appears at most once per page. | lint (DR-K14-10) |
| CP-3 | **Plain first, precise one click away.** Glossary link or popover. Never delete precision (U-004). | term-link check (DR-K14-08) |
| CP-4 | **Name things.** Never show a UUID, snake_case key, registry id, raw enum or requirement id in prose (DR-C6-28). Derived display names only (K0 NEW-1). | lint (DR-C6-28) |
| CP-5 | **Say what kind of unknown.** "Not researched", "None found", "Sources disagree" or "Not applicable" — never a bare "unknown" (DR-C6-30). | lint for bare "unknown" |
| CP-6 | **Specific and dated.** Every figure has an as-of; relative time ("12 days old") sits beside an absolute date (SIG-UI-043 rule 4). | component contract |
| CP-7 | **Report, don't characterize.** The six register rules stay binding on hand-written and generated text (SIG-UI-043/046). | existing register gate |
| CP-8 | **Short.** Page intros ≤ 60 words; sentences average ≤ 22 words; design-centre summaries at about grade 10 (DR-C6-28). | readability report (warning only) |
| CP-9 | **Be honest about SIG itself.** No wording implies counsel, a board, human review or a capability the release does not show (U-013; D3 Wave 0). | capability binding (DR-K14-05) |
| CP-10 | **One word per concept.** Use the controlled vocabulary in §3.5. | lint list of banned synonyms |

### 3.2 The one-caveat rule, applied

| caveat today | where it repeats | new home |
|---|---|---|
| "The true population of surveillance devices is unknown… an inventory, not a census or an estimate (SIG-METRIC-008)." | 126× on `/` and on `/coverage-metrics/` | a **"not a census"** label on each count figure, linked to `/glossary/#census`; one "About these figures" note per page |
| "Absence of a row is not evidence of absence." | 3× per dossier; empty states; task pages | once, in the incompleteness banner; each absence chip carries only its kind label, and the popover gives the meaning |
| "Not yet human-reviewed" / review status | the footer "How we know this" on every page | one line in the footer strip; the full text on About; a **Provisional** chip on figures from unevaluated methods |
| "Belief-pinned permalink (reproducible after SIG corrects itself)" | the "Cite this page" block on every page | the "Cite" disclosure in the page header (§3.7); the words "belief" and "ruleset" move into its "Technical details" |
| "One click, no account required" dispute prose | every page | the footer strip link "Dispute or correct this page"; the per-claim compact link stays (SIG-UI-033) |

### 3.3 Before and after (agent-drafted examples)

| surface | today (C2 captures) | proposed |
|---|---|---|
| Dossier headline figure | "Geolocated site observations: 3994 of 3996 evaluable geolocated site observations in TX — Observation-level count from named sources — not a resolved device census (SIG-RECON-058)." | "**3,994** camera locations recorded in **Texas**, from 4 named sources · *not a census* ⓘ · as of 27 Sep 2026 · Sources ›" and, in the popover: "3,994 of 3,996 records have usable coordinates. Counted per source record, not per device." |
| Support glyph | "⊕⊕⊕◯ Support: strongly supported (3 of 4) · 1 evidence class · downgrade: SINGLE_W3_OR_TWO_W2" | "⊕⊕⊕◯ **Strong support** ⓘ" and, in the popover: "3 of 4. One high-tier source, or two mid-tier sources, back this value (reason code `SINGLE_W3_OR_TWO_W2`)." The count and code stay machine-readable in `data-*` attributes and JSON (SIG-UI-003) |
| Unknown field | "Next decision date · unknown" | "Next decision date · ▨ **Not researched** · Help find it ›" |
| Page footer | "How we know this · Artifacts 255 · Tier distribution 2245390×untiered, 2690×W1, 175114×W3 · Independent sources 218 · Date range … · Rules applied p27.3/1.0.0 · Human review Not yet human-reviewed · … Cite this page … As of world 2026-09-27, belief 2026-09-27; ruleset p27.3/1.0.0 …" | "Built from **4 sources** · data as of 27 Sep 2026 · not yet independently reviewed · **How we know this ›** · Dispute or correct ›" (one line; the full module is inside a `<details>`) |
| Home lede | "SIG is an open, vendor-agnostic, temporally versioned record of public surveillance infrastructure…" | the §2.1 sentence |

### 3.4 Epistemic label lexicon (one source of truth: `epistemic.ts`; short, consistent)

| state | short label (≤ 2 words) | symbol | colour role | plain meaning (popover) | precise |
|---|---|---|---|---|---|
| Support 4 / 3 / 2 / 1 / 0 | Confirmed · Strong · Probable · Weak · Unsupported (+ " support") | ⊕⊕⊕⊕ … ◯◯◯◯ | slate ordinal ramp | "How well the evidence backs this value: N of 4." | glossary *Support*; §10.7 |
| Contested | **Contested** | ≠ | raspberry | "Sources disagree about this value; SIG shows the leading value and the others." | *Agreement*; SIG-UI-008 |
| Unresolved | **Unresolved** | ⚠ | raspberry, solid | "Sources disagree and no value can be defended yet; see the range." | §29; SIG-UI-009 |
| Minor disagreement | (no marker; text inside details) | — | none | "Small differences within tolerance." | `CONTESTED_AGREEMENTS` excludes it (`epistemic.ts`) |
| Not researched | **Not researched** | ? on the hatch | absence hatch | "SIG hasn't looked yet." | §9.5 |
| None found | **None found** | ∅ on the hatch | absence hatch | "SIG searched the named sources and found nothing." | §9.5 |
| Evidence of absence | **Stated absent** | ✗ on the hatch | absence hatch | "A source says this does not exist." | §9.5 |
| Current / Aging / Stale / Historical | Current · Aging · Stale · **Historical** + date | stroke: solid · solid 60 % · dashed · dotted | neutral | "How recent the evidence is for this kind of fact. Historical: last evidenced on <date>." | *Currency*; §28.3 |
| Provisional | **Provisional** | ◔ | amber | "Produced by a method not yet independently evaluated; may change." | Stream L; methodology PROVISIONAL |
| Unreviewed | **Not reviewed** | — | neutral chip | "No person outside the project has checked this." | SIG-UI-044 human-review status |
| Superseded / Withdrawn | Superseded · Withdrawn | strike / tombstone | neutral | "Replaced by a later record" / "Removed from publication; reason given." | §16, §45 |
| Directness D1–D6 | Direct · Indirect · Contextual · *Not evidence* | — | neutral text badge | "How directly this kind of document can show this kind of fact." | *Directness*; §10.5 |
| Access kinds | Set up to share · Stated policy · Observed use | line: solid · dashed · double | neutral | "Set up to share ≠ anyone used it." | §12.2; SIG-UI-024 |

**The short labels change display text only.** Stored enums, the JSON and the spec terms are untouched. The "Stated
absent" label for `EVIDENCE_OF_ABSENCE` goes to the operator with the lexicon at D-K14-5.

### 3.5 Controlled vocabulary (one word per concept; CP-10)

| concept | use | do not use in UI copy |
|---|---|---|
| A place SIG publishes a page for | **place** (nav), **dossier** (the document) | jurisdiction code, subject |
| One source's row about a camera | **record** | observation-level record, subject |
| The de-duplicated physical camera | **camera site** | resolved site, asset, entity, subject |
| Where SIG got something | **source** (plus the publisher's name) | registry id, source key, compartment |
| A dated published snapshot | **release** | publication id, belief |
| When the data was taken | **data as of <date>** | as of world / as of belief (these live in Technical details) |
| The rules version | **method version** (in Technical details) | ruleset |
| Evidence strength | **support** | tier, W1–W3 (in Technical details and the glossary) |

### 3.6 Numbers and dates

- **Grouping:** grouped with commas in `en` (3,994; 2,423,200). Tables right-align numbers with
  `font-variant-numeric: tabular-nums`.
- **Precision:** exact counts, never rounded in figures. Prose may say "about 2.4 million" only when the exact figure sits
  beside it.
- **Ratios:** "3,994 of 3,996", never a bare percentage. A percentage is shown only with its numerator and denominator
  (named-denominator rule, §32).
- **Dates:** prose shows "27 Sep 2026"; tables, JSON and the `<time datetime>` attribute keep ISO 8601. Relative age
  ("12 days old") always sits beside the absolute date.
- **Ranges:** "38–42" with an en dash, plus the claim count ("across 2 sources").

### 3.7 Page chrome budget (keeps SIG-UI-033/035/044; amends 044's form)

| block | today | proposed default (visible) | expanded (`<details>`) | spec |
|---|---|---|---|---|
| Release stamp | none (no release id shown anywhere, C2 NEW-4/NEW-29) | page header: "Data as of 27 Sep 2026 · release ce480ab1" | — | SIG-UI-035, DR-C6-31 |
| Cite | an 80–90-word block at the foot of every page | page-header action "Cite" | formatted citation (plain, APA, Chicago, legal), pinned URL, and Technical details (belief time, method version) | SIG-UI-035 (unchanged) |
| How we know this | an 8-field block on every page; the site-wide totals on dossiers (F-105/F-128) | footer strip: "Built from N sources · data as of … · not yet independently reviewed · How we know this ›" | the six SIG-UI-044 fields, **page-specific** (PKG-10) | **SIG-UI-044 amendment** (D-K14-6): "MUST carry … in full on record pages and at least a one-line summary with the full module one action away on all other pages" |
| Dispute | a 17-word sentence | footer strip link + per-claim compact link | — | SIG-UI-033 (unchanged) |

Target: shared chrome that is **visible by default** is ≤ 40 words per page, excluding the navigation link labels
(today it is about 110). The information is the same; only the default visibility changes.

---

## 4. Visual design system

### 4.1 Principles

1. **A record, not a dashboard.** The site should read like a well-set reference work — OWID, OpenSanctions, ProPublica's
   Nonprofit Explorer (K12a ENT-4/ENT-7) — with no KPI wall. White space and type make the hierarchy.
2. **Colour means "look here".**
   - Neutrals carry the structure.
   - The only saturated hues are raspberry for disagreement, amber for provisional, and blue for links and data.
   - This sharpens SIG-UI-006 without breaking it (no green; saturated colour only for state and data).
3. **Every mark is doubled.** Colour is never alone: glyph, texture, stroke style or label always travels with it
   (SIG-UI-005).
4. **The same object always looks the same:** in a table, card, map popup, graph node, print and JSON (SIG-UI-008
   "persistent").
5. **Calm by default, fast always.** No decorative motion or imagery that costs bytes, inside K0's T1 budgets.

### 4.2 Typography

- **Face:** **Public Sans Variable** (OFL-1.1). One self-hosted file covers weights 100–900: `public-sans-latin-wght-normal.woff2`
  = **26,832 B** (measured, `@fontsource-variable/public-sans` 5.3.0).
  - It was designed for public-interest reading and is neutral, legible and wide-numbered.
  - It is served `font-display: optional` with a `size-adjust`ed system fallback, so CLS stays within K0's ≤ 0.02.
  - Tabular figures (`tnum`) must be verified at implementation.
  - **Alternatives measured:**
    - the system stack (0 B; today);
    - IBM Plex Sans (22–24 KB per weight; three files ≈ 69 KB);
    - Inter Variable (48 KB);
    - Source Serif 4 Variable (50 KB) as a heading face — rejected for budget.
  - D-K14-3 decides.
- **Monospace:** the system `ui-monospace` stack, for hashes, ids in Technical details, and code.
- **Scale:** major third (1.25), base 16 px, rounded; **8 steps**, down from 17 literals.

| token | size | use | line-height / weight |
|---|---|---|---|
| `--step--2` | 0.8125 rem (13 px) | legal, micro-labels (**the minimum**; replaces 9.92 px) | 1.4 / 500; uppercase labels +0.06 em |
| `--step--1` | 0.875 rem (14 px) | meta, captions, dense tables, chips | 1.45 / 400–500 |
| `--step-0` | 1 rem (16 px) | body, tables | 1.55 / 400 |
| `--step-1` | 1.25 rem (20 px) | lead paragraph, H4, figure labels | 1.4 / 500 |
| `--step-2` | 1.5 rem (24 px) | H3 | 1.3 / 600 |
| `--step-3` | 1.875 rem (30 px) | H2 | 1.2 / 650 |
| `--step-4` | clamp(2 rem, 1.6 rem + 1.6 vw, 2.5 rem) | H1 (32–40 px) | 1.15 / 700; −0.01 em |
| `--step-5` | clamp(2.25 rem, 1.8 rem + 2.2 vw, 3 rem) | hero tagline; headline figure values | 1.1 / 700; `tabular-nums` |

- **Measure:** prose ≤ **68 ch**. Tables and T2 surfaces may run the full content width.

### 4.3 Colour tokens (light / dark; every pair computed, §13 C5–C8)

**Dark mode** is a set of chosen steps, not an automatic inversion. Dark surfaces are validated as surfaces.

**Neutrals and interaction**

| token | light | dark | contrast (light on `--bg` / dark on `--bg`) | role |
|---|---|---|---|---|
| `--bg` | `#fbfbfc` | `#15181d` | — | page |
| `--surface` | `#ffffff` | `#1d2129` | — | cards, tables |
| `--surface-2` | `#f2f4f7` | `#252a33` | — | table headers, panels |
| `--rule` | `#d5d9e0` | `#343a46` | 1.37 / 1.56 | decorative dividers only |
| `--rule-strong` | `#7e8695` | `#6b7383` | **3.54 / 3.73** | essential boundaries (inputs, chips): WCAG 1.4.11 ≥ 3:1 |
| `--ink` | `#161a21` | `#e8eaef` | **16.87 / 14.78** | text |
| `--ink-muted` | `#5b6270` | `#a3aab8` | **5.93 / 7.62** | secondary text |
| `--link` | `#1c5cab` | `#86b6ef` | **6.41 / 8.43** | links, always underlined; the focus ring |
| focus ring | 3 px `--link` + 2 px `--bg` inner gap | same | ≥ 3:1 on both | WCAG 2.4.7/2.4.11 |

**Epistemic (reserved) and data**

| token | light | dark | contrast (light vs white / dark vs `#15181d`) | used only for |
|---|---|---|---|---|
| `--epi-support-4 … -1` (ordinal) | `#0f172a` `#334155` `#64748b` `#94a3b8` | `#f1f5f9` `#cbd5e1` `#94a3b8` `#64748b` | light end 2.5 / 3.74 (≥ 2:1 ordinal rule) | support chip border, node ring, ⊕ fill. **Validator `--ordinal`: PASS** in both modes (monotone L, ΔL ≥ 0.06, hue spread 9–10°) |
| `--epi-disagree-mark` | `#c7336b` | `#e0578a` | **5.10 / 5.00** | ≠ contested, ⚠ unresolved (solid), contradiction ranges |
| `--epi-disagree-text` | `#a8285a` | `#f58bb0` | **6.74 / 7.80** | "Contested" / "Unresolved" labels |
| `--epi-provisional-mark` | `#b97800` | `#b8860b` | 3.65 / 5.47 | Provisional outline, ◔ |
| `--epi-provisional-text` | `#8a5300` | `#f2c261` | **6.33 / 10.73** | the "Provisional" label |
| `--epi-absence-ink` | `#5a6272` | `#9aa3b5` | 6.13 / 7.02 | **the hatch only** (SIG-UI-007) |
| `--data-1` | `#2a78d6` | `#3987e5` | 4.42 / 4.89 | map points, bars, lines (one series) |
| `--data-seq-100…700` | reference blue ramp `#cde2fb … #0d366b` | the same ramp, anchor flipped | ordinal light end ≥ 2:1 | density bins (SIG-UI-019), choropleths |

**CVD and normal-vision checks (dataviz validator, `--pairs all`)**

| mode | colours | result |
|---|---|---|
| light | raspberry `#c7336b` + amber `#b97800` + data blue `#2a78d6` | **PASS**: worst CVD ΔE 12.3 (deutan), worst normal ΔE 19.8 |
| dark | `#e0578a` + `#b8860b` + `#3987e5` | **PASS**: 11.7 / 20.4 |

Rejected combinations:
- today's magenta `#c2378a` against blue: protan ΔE **5.7**;
- magenta against a separate crimson for "unresolved": normal ΔE **11.3**;
- a blue/violet/orange categorical set in dark mode: violet↔blue protan ΔE **1.9**.

This is why "contested" and "unresolved" share one hue, told apart by glyph and fill, and why there is no red in the
system. Red would also read as alarm, which the neutral register (SIG-UI-043) avoids.

**Categorical data** uses one colour (`--data-1`). Shape, icon, direct labels or small multiples do the rest. The
validator shows that any second SIG-safe hue collides with a reserved hue in dark mode.

**The spec test survives.** Every `--sig-epi-*` hue lies outside the green band [75°, 165°]:
- slate 215–222°;
- raspberry ≈ 337°;
- amber ≈ 39°.

`tests/unit/design-tokens.test.ts` keeps parsing `hsl()`, so the tokens should be written in that notation.

### 4.4 Spacing, shape, elevation

- **Space (4 px base):** `--space-1…9` = 0.25, 0.5, 0.75, 1, 1.5, 2, 3, 4, 6 rem.
- **Radius:** 4 px (chips, inputs), 8 px (cards, panels), 999 px (the release stamp). Borders are 1 px; emphasis is 2 px.
- **Elevation:** flat. Only popovers and menus get a shadow (`0 4px 16px rgb(0 0 0 / .12)`); in dark mode they get a
  `--rule-strong` border instead.

### 4.5 Grid and layout

**Containers**
- `--measure` 68 ch (prose)
- `--content` 72 rem (1152 px)
- `--wide` 90 rem (T2 surfaces)

**Gutters and columns**

| width | gutter | columns |
|---|---|---|
| < 40 rem | 16 px | 4 |
| 40–64 rem | 24 px | 8 |
| ≥ 64 rem | 24 px | 12 |

The header and `main` share one container, which fixes the 168/244 px misalignment (NEW-9).

**Breakpoints:** 40 rem, 64 rem, 80 rem. Everything reflows at 320 px (WCAG 1.4.10; F-116, F-167). Wide tables scroll
inside a labelled container with an edge shadow; the page itself never scrolls sideways.

**Templates** (K13 maps each route to one):

| template | layout | page type (K0) |
|---|---|---|
| **Record** (dossier, entity, source, evidence) | page header band (breadcrumbs, H1, one-sentence summary, actions: Cite · Print · Download · Explore on map/graph, release stamp); then `main` 8 columns + `aside` 4 columns (sticky "On this page", provenance summary, "Other public resources"); one column below 64 rem | T1 (print T0) |
| **Index** (places, sources, research questions, organizations) | header band; a filter row (GET form; `<sig-table>` enhancement); a table or card list with pagination | T1 |
| **Reading** (about, methodology, glossary, editorial, how to read SIG) | one 68 ch column; an "On this page" table of contents at ≥ 80 rem; "In brief" box first | T1 |
| **Explore** (map, graph, search) | full-width app band; a **reserved fixed-height box** holding the static rendition (K0 I-2); a side panel "in view" list; controls in a top row | T2 |
| **Home** | the bespoke sections of §2.3 | T1 |
| **Print** | Letter/A4; a council-brief page 1; a running header and footer | T0 |

### 4.6 Component inventory (visual layer; behaviour comes from K0's kit)

| component | job | page types | key states / variants | spec / source row |
|---|---|---|---|---|
| Site header | identity, ≤ 6 sections, search | all T1/T2 | current section (`aria-current`); mobile `<details>` menu; focus | SIG-UI-049; NEW-9 |
| Footer + provenance strip | licence, dispute, the one-line "How we know this" | all | expanded / collapsed | SIG-UI-033/044; §3.7 |
| Release stamp | "Data as of … · release …" | all | pinned snapshot vs latest view (G3 `/s/<pub>/`) | SIG-UI-035; DR-C6-31 |
| Page header band | breadcrumbs, H1, summary, actions | record, index, reading | with/without actions | K13 |
| Cite disclosure (`<sig-cite>` enhancement) | formatted citations and pinned URL | all | formats; Technical details; "copied" status (JS only) | SIG-UI-035; K0 §4.6 |
| **Figure** (J3 `<Figure>`) | one number with its trail | home, dossier, entity, source, coverage | not a census; Provisional; contested ≠; unavailable (typed absence) | J3 §5.4; SIG-UI-008/014 |
| Stat row | ≤ 6 figures | home, dossier at-a-glance | 1–3 columns | D3 §3c |
| Cards | place, organization, source, task, persona "start here", example | index, home | with/without figure; empty | K4, K11 |
| Table (`<sig-table>` visual) | sortable, sticky header, numbers right-aligned | index, record | sorted column (`aria-sort`), density, scroll container | K9 §6 |
| Support chip | ⊕ glyph + short label + popover | record, table, popup | 0–4 | SIG-UI-003 |
| Field chips (four independent) | resolution · support · agreement · currency | record detail | never fused | SIG-UI-004 |
| Contested marker | ≠ + "Contested" | everywhere a value appears | inline, cell, popup, node | SIG-UI-008 |
| Contradiction range | a plotted range, one labelled dot per claim | record | different-quantity note | SIG-UI-009 |
| Absence chip | the hatch + symbol + label + "Help find it ›" | record, table, map | 4 kinds | SIG-UI-007; DR-C6-30 |
| Status chips | Provisional · Historical (+date) · Not reviewed · Superseded · Withdrawn | anywhere | — | §3.4 |
| Directness / access-kind / licence / mirror badges | neutral text badges | record, source | — | SIG-UI-024; J4; P15 |
| Provenance panel | per claim: source, capture, binding state, view original, directness, review, rights, JSON/API | record | honest "run-level only" state (J3 §5.1) | J3 §5.2 |
| Term + definition popover | a glossary link + `popover` | record, reading | print → terms list | §2.5 |
| Callouts | note · caution (Provisional disclosure) · known issue | any | — | — |
| Incompleteness banner | "N fields have gaps; absence is not evidence of absence" | dossier | neutral style + a count (**not** the contested colour, NEW-2) | SIG-UI-012 |
| Empty state | the typed pattern (§6.4) | any list or section | 8 kinds | K7 NEW-6 |
| Error pages | 404 · 410 (withdrawn, with reason) · 500 · API down | all | search + home + status link | DR-C6-29; F-117, F-160 |
| Map chrome (K1 owns behaviour) | control cluster, legend popover, layer toggles, place search, collapsed attribution "ⓘ OSM…", "In view" list, "Cite this view" | T2 map | reduced motion; dark basemap flavour | K0 §4.9; K12b NEW-8 |
| Graph chrome (K2) | node shape by type, edge style by access kind, neighbour panel, legend, ER-quality note | T2 graph; static SVG on T1 | selected / focused / expanded | SIG-UI-021–025 |
| Timeline | a dated vertical list; world vs belief time labelled | record | — | K12b I-28 |
| Explore bar | "See on map · See in graph · Search within" with `jurisdiction=` / `focus=` | record | — | K0 §4.5 |

### 4.7 Data-visualization conventions

| meaning | primary channel | colour | rule |
|---|---|---|---|
| Support (ordinal 0–4) | ⊕ fill count + short label | slate ordinal ramp | darker = more support; never green; monotone lightness |
| Disagreement | ≠ at every appearance; ⚠ + range where unresolved | raspberry | the only use of raspberry |
| Absence | the hatch + ? ∅ ✗ symbols | absence ink | the only texture in the system |
| Currency | a text date + stroke style (solid → dotted) | neutral | a date always shows; "Historical" edges are dotted in graphs (K12b NEW-2) |
| Provisional | a dashed amber outline + label | amber | on any figure from an unevaluated method (L3) |
| Access kind | line style: configured solid · declared dashed · observed double | neutral ink | independently toggleable (SIG-UI-024); "set up to share ≠ used" |
| Coverage (researched or not) | a desaturated base; the hatch where not researched | neutral | low coverage never reads as low density (SIG-UI-018) |
| Magnitude / density | the sequential blue ramp | `--data-seq` | one hue, light → dark; binned at national zoom (SIG-UI-019) |
| Entity type (graph) | shape + icon (agency ●, vendor ■, product ◆, site ▲, source ⬟, policy or contract ▭) | neutral; selected = `--link` | never colour-coded by type |
| Technology class (map) | icon/shape + legend | `--data-1` | ≤ 1 colour; more classes means more shapes or facets |

**Chart rules**
- One axis; no dual axes.
- Direct labels, not a number on every point.
- Thin marks; 2 px lines; ≥ 8 px markers; a 2 px surface gap between fills.
- A caption with source, as-of and "not a census" where it applies.
- A table equivalent in the same box (K0 I-2).
- Static SVG first. Inline SVG uses CSS variables so it themes; an external SVG `<img>` carries its own
  `prefers-color-scheme` block.
- Every visual prints (K0 §4.10).

### 4.8 Iconography

- **UI icons:** about 20 inline-SVG line icons on a 24 px grid, 1.5 px stroke, `currentColor`:
  - search, menu, close, print, download, cite, external link;
  - info, calendar, RSS, filter, sort, chevron, map, graph, source, document, copy, warning (⚠ remains a glyph).
- **Source:** Lucide (ISC, OSI) inlined at build time, or drawn in-house. They are build-time assets, not runtime
  dependencies (K0 §4.7), and are covered by the `check:licenses` gate (SIG-UI-039).
- **Technology classes:** ~12 in-house icons for the top classes, plus one generic:
  - ALPR;
  - fixed camera / CCTV;
  - face recognition;
  - drone;
  - gunshot detection;
  - real-time crime centre;
  - cell-site simulator;
  - social-media monitoring;
  - body camera;
  - mobile forensics;
  - predictive analytics;
  - camera-sharing registry.
- **Labels:** every icon has a visible text label or an accessible name. Icon fonts are never used.

### 4.9 Motion

- **Default motion** is limited to 120–160 ms colour and opacity transitions on hover and focus.
- **Page transitions** are optional CSS-only cross-document view transitions (`@view-transition`), T1 only.
- **Under `prefers-reduced-motion: reduce`:**
  - no transitions;
  - no `flyTo`/`easeTo` (use `jumpTo`; fixes NEW-10);
  - no animated graph layouts (layouts are precomputed, K0 §4.9);
  - no smooth scrolling.
- **CI:** a Playwright project with `reducedMotion: 'reduce'` runs the T2 journeys.

### 4.10 Dark mode mechanics

- **Token sets:** `:root` holds light; `@media (prefers-color-scheme: dark)` holds dark. Add
  `<meta name="color-scheme" content="light dark">`.
- **No toggle in Round 11.** A toggle needs JavaScript or stored state (D-K14-4). The OS setting is enough.
- **Maps:** the basemap uses Protomaps' dark flavour (K1). Overlay symbols keep ≥ 3:1 against both basemaps
  (K0 §4.9).
- **Print** always forces the light tokens (`@media print`).
- **Images and SVG** use tokens. No white-background PNGs.

### 4.11 Print (with TH-10, K6)

- **Page 1 is a council brief:**
  - place name;
  - "what is recorded / what is unknown" at a glance;
  - next decision date or its typed absence;
  - the 3–5 documents to bring;
  - a QR code for the pinned permalink (a static SVG generated at build).
- **Every page carries** a running footer with the as-of date, release, permalink, licence and page number.
  - Chrome ≥ 131 supports `@page` margin boxes. **Verify** this at implementation; the fallback is a `position: fixed`
    print footer.
- **Terms and gaps:**
  - a "Terms used" list replaces the popovers;
  - hatches print as their symbol + label (tested in greyscale).
- **Hygiene:** no orphan or empty pages (C2 §8).

### 4.12 Brand

- **Name.** Keep **Surveillance Infrastructure Graph (SIG)** as the name, with **surveillancegraph.org** as the
  address (D-K14-2).
  - The name is already in every citation string and in the spec.
  - A rename would break continuity for no gain (**inference**).
- **Logo direction:** a node-link glyph beside the wordmark, in one colour (ink):
  - three nodes;
  - two solid edges;
  - one **dashed** edge, meaning "a link claimed but not yet confirmed".
  - It works at 16 px as a favicon.
  - It uses no epistemic colour, no hatch, and no seal or badge shapes that could suggest a government body.
- **Social cards:** one static card per page type (home, place, organization, source, methodology), generated at build as
  SVG → PNG. Each shows the page title, "data as of" and the wordmark. Per-place cards come later.
- **Favicon set:** SVG + 32 px PNG + 180 px touch icon.
- **Voice:** neutral, specific, plain and dated. No alarm words ("exposed", "secret"), no advocacy (SIG-UI-027b), and no
  exclamation marks. The announcement copy (U-009) follows the same rules, and the operator posts it (D3 §5).

### 4.13 Size and budget (K0)

| item | budget | today / estimate |
|---|---|---|
| Design-system CSS (tokens + components, one file) | ≤ 12 KiB gzip | 4.1 KiB today; + dark tokens, grid and components ≈ 8–10 KiB (**inference**) |
| Font | ≤ 30 KiB, `optional` | 26.2 KiB (Public Sans Variable, Latin) |
| Icons | inline, ≤ 1 KiB each, only those used on the page | — |
| JavaScript | 0 on K14 pages | popovers, menus and cite are HTML; `<sig-cite>` "copy" and `<sig-typeahead>` are K0 T1 elements within ≤ 20 KiB |

The per-page total stays within T1's ≤ 170 KiB (K0 §4.3).

---

## 5. Navigation and information architecture (sketch; K13 finalizes)

### 5.1 Top-level sections (≤ 6 plus a search field; from today's 15 links)

| nav label | contents (routes; K0 page types) | persona entry |
|---|---|---|
| **Places** | the country → state → county/city index (K4, `/dossier/`); dossiers; print briefs | advocate, organizer |
| **Explore ▾** | Map (`/map/`, T2) · Graph (`/explore/`, T2) · Search (`/search/`, T2) | journalist, resident |
| **Organizations** | agencies, vendors, products, contracts, policies (`/entity/**`, K2) | journalist |
| **Sources & data** | Sources (`/sources/**`, K9/K10) · Evidence (`/evidence/**`, K8) · Downloads & API (`/data/**`, J3) · Releases · Status | journalist, developer |
| **Watch** | upcoming decisions and feeds (`/watch/**`, K7) · what changed (K12b I-08) | advocate, organizer |
| **About** | About & how it works · Methodology · Glossary · Editorial standards · How to read SIG (the visual language) · Style guide · Corrections · Known issues · Open questions (`/research-queue/`, K11) · Dispute | everyone; skeptic |

Open questions (the research queue) also appear on every absence chip ("Help find it ›"), in a place's "What we don't
know" section, and on the organizer start-here path. They do not need a top-level slot.

### 5.2 Moving between surfaces ("every page links sideways")

| from | to |
|---|---|
| Place (dossier) | its organizations · its sources ledger (K5) · map with `jurisdiction=` · graph with `jurisdiction=` · watch for the place · open questions for the place · parent/child places (breadcrumbs) · Other public resources |
| Organization | the places it operates in · partners (typed relationship tables) · graph `focus=` · contracts/policies · sources · open questions |
| Map feature popup | the feature page · the place · the operator organization · the source · cite this view |
| Graph node or edge | the organization page · the edge's evidence (≤ 2 clicks, D3 J2) · the source |
| Search result (typed) | a place · organization · source · evidence · open question; zero results → the nearest-record answer (DR-C6-27) |
| Source | the places and organizations it contributes to · runs · captures · downloads · licence |
| Evidence item | the claims it supports → organizations and places · original / "view at source" (J3 §5.3) |
| Figure anywhere | "explain this number" → definition · artifact · rows (J3 §5.4) |
| Open question | its place or organization · "why it matters" · records-request template · the closing condition |
| Watch item | the contract · organization · place · source document · iCal |

### 5.3 Header and footer behaviour

- **Desktop:** one row with the wordmark on the left, then the sections, then a search field (~16 rem) on the right.
  Height ≤ 64 px. The current section carries `aria-current="page"` (a section match counts).
- **Mobile (< 40 rem):**
  - a ≤ 56 px bar with the logo, a search icon linking to `/search/`, and a "Menu" `<details>` that lists the sections;
  - no JavaScript;
  - the H1 starts ≤ 120 px from the top (today 344 px).
- **Record pages:** breadcrumbs (Country › State › County › City) above the H1.
- **Footer:** the same on every page (§2.3 row 8).

---

## 6. First-visit onboarding

### 6.1 "Start here" journeys (home cards; each ends on an honest state)

| card (plain title) | persona | steps (links) | serves (D3 §2) |
|---|---|---|---|
| **"I have a council meeting coming up"** | local advocate (design centre) | 1 Find your place → 2 Read "At a glance" and "What we don't know" → 3 Print the council brief → 4 Bring the listed documents; request the top missing one | A1–A4 |
| **"I'm checking a figure or a claim"** | investigative journalist | 1 Search an agency or vendor → 2 Open its page; follow a figure to its sources → 3 Check whether sources disagree → 4 Cite a pinned URL or download the rows | J1–J4 |
| **"I'm organizing in my area"** | organizer | 1 Find your county or city → 2 See who runs what, and who they share with → 3 Subscribe to upcoming decisions → 4 Pick an open question to help answer | O1–O4 |
| small link: **"I want the data"** | developer / researcher | Downloads & API → data dictionary → licences | C2 P7, P3 |

Rules:
- **Golden place.** Each card's example links use a golden place (C5 §7; D-K14-6 with D3 §4). Until one exists, step 1
  links to the place search, not to a thin page.
- **No dead ends.** A step whose target is empty shows the typed empty state (§6.4), never a dead end.

### 6.2 Example questions that work (generated and tested, never hand-asserted)

A build step (`web/scripts/examples.mjs`, UXK14-6) draws examples from the release using fixed templates. It emits an
example only if its **example contract** holds:
- the target route returns 200;
- the target contains the answer element with ≥ 1 sourced value;
- no UUID or raw-key label appears;
- the phrasing matches the edge semantics.

| template (agent-drafted) | target | emitted only when |
|---|---|---|
| "What is recorded in {state}?" | place dossier | the dossier has ≥ 2 named sources |
| "Which agencies does {vendor} supply?" | vendor page → agencies table | ≥ 3 dated vendor→agency links |
| "Which agencies is {agency} set up to share plate-reader data with?" | agency page → access table | ≥ 1 dated configured-access edge; currency shown (K12b NEW-2) |
| "Where do sources disagree about {place}?" | place → contradictions | ≥ 1 published contradiction |
| "What's up for a decision in {place}?" | watch filtered to the place | ≥ 1 tracked decision |
| "What doesn't SIG know about {place}?" | place → gap view | always valid (typed absences) |

Examples appear as hero chips (3), on the empty search page (6), and on zero-result pages ("Try: …").

### 6.3 Reading keys, not tours

- **Per-page key.** Each record page has a **"How to read this page"** link in its header. It opens a `<details>` key
  that lists **only the symbols present on that page**, generated from the lexicon, each with its one-line meaning and a
  glossary link.
- **No first-visit overlay.** It would need cookies or storage (ADR-134 privacy posture) and would add JavaScript.
- **An annotated page instead.** `/about/how-to-read-a-dossier/` is generated from the golden dossier with numbered
  static callouts. It regenerates each release, so it does not go stale the way screenshots do.

### 6.4 Empty states (the typed pattern)

Every empty state has **five parts**:
1. **State label** — a typed kind, never a bare "empty".
2. **What is missing, and why.**
3. **What exists nearby.**
4. **What you can do.**
5. **When it may change.**

It uses the hatch only when the emptiness *is* absence (SIG-UI-007).

| surface | state | copy draft (agent) |
|---|---|---|
| Dossier section (e.g. "Who else can see the data") | Not researched | "**Not researched.** SIG hasn't looked for data-sharing partners in {place} yet. Nearby: {state} has {n} recorded partners. [Help find them ›] Updated with each release." |
| Search, zero results | No match | "**No record matches "{q}".** SIG has no {city}-level record; the nearest is {state} ({n} records from {sources}). [Open {state} ›] Try: {examples}. A missing result is not evidence that nothing exists." (DR-C6-27) |
| Watch, empty | Not tracked yet | "**No upcoming decisions are tracked yet.** SIG does not yet read contract end dates or council agendas for this place. [See {place}'s contracts ›] [Other public resources: alpr.watch ›]" (K7; D3 Q4) |
| Evidence, none viewable | Not yet published | "**No documents are viewable yet.** SIG recorded {n} captures but has not published per-claim copies. Each source page lists its runs. [Sources ›]" (J3 §5.1; K8) |
| Organization with no relationships | None found / not researched | a typed absence per relationship type, never an empty table |
| Map viewport with no features | Nothing recorded here | "**No records in this area** at this zoom. Coverage here is {covered/not researched} (shaded)." (SIG-UI-018) |
| Filter with no matches | No match | "**No rows match these filters.** [Clear filters]" (no hatch: this is not absence) |
| Downloads unavailable (rights) | Not redistributable | "**This source's data can't be redistributed** ({reason}). [View at source ›]" (J3 §5.3) |
| API down (degraded) | Temporarily unavailable | "**Search is temporarily limited.** Showing name matches only. [Status ›]" (K0 §5.2) |

---

## 7. "Ready to announce" design checklist (feeds D3 §5 / S2)

- [ ] The operator has confirmed the §2.1 statements verbatim. They sit above the fold at 390×844 and 1440×900
      (D-K14-1; D3 Q5).
- [ ] The home page is ≤ 5 screens at 390 px, with ≤ 6 figures, each passing J3's pointer contract (source ≤ 2 clicks,
      as-of, not a census, Provisional where due).
- [ ] Every capability statement is bound to release data. None claims what the release does not show (DR-K14-05).
- [ ] Three start-here paths and all emitted example questions pass their contract on the release to be announced.
- [ ] At least one golden, joined place dossier exists and is the home "See an example" (C5 §7).
- [ ] The copy lints are green:
  - 0 requirement ids, snake_case or UUIDs in prose (DR-C6-28);
  - repeated caveats ≤ 1 per page;
  - visible chrome ≤ 40 words;
  - 0 joined words;
  - 0 ungrouped numbers of 5 or more digits.
- [ ] `/about/`, `/glossary/` and the methodology "In brief" boxes are live. Glossary terms are linked on first use on
      every record page.
- [ ] Tokens are in place: every template renders in light and dark; the contrast tests are green; axe shows 0
      violations in both schemes and both JavaScript states (K0 I-8).
- [ ] Reflow at 320 px has 0 horizontal scroll; the reduced-motion project is green.
- [ ] Brand: logo, favicon set, per-type social cards and unique meta descriptions (with DR-C6-29); branded
      404/410/500 pages.
- [ ] Print: the council brief page 1 passes the council-member test (C2 §8), with the running footer on every page.
- [ ] Visual regression baselines are approved, and the **operator has signed off "beautiful"** on a gallery of every
      template × {light, dark} × {390, 1440} (D-K14-9; D3 §3c: "'Beautiful' is the operator's call").
- [ ] The About page states the maintainer model, the review status and known issues, with operator-approved wording
      (D-K14-7; U-013).
- [ ] A fresh-context agent, given only the home page, can state what SIG is, what it is not and three things it does
      within 2 minutes (D3 §3c). This is recorded as `agent-verified`, never as user-tested (P4).

---

## 8. Draft requirements and acceptance checks (provisional `DR-K14-nn`; K13/T1 assign ids)

| id | requirement (draft) | acceptance |
|---|---|---|
| DR-K14-01 | The home page MUST lead with the confirmed tagline (H1), the one-sentence statement and a GET place search, above the fold at 390×844 and 1440×900; the H1 top ≤ 120 px (mobile) and ≤ 160 px (desktop). | Playwright bounding-box check on both viewports |
| DR-K14-02 | The home page MUST be ≤ 5 viewport heights at 390 px and show ≤ 6 headline figures, each rendered by the J3 `<Figure>` with unit, denominator, as-of, source link and any Provisional or contested flag. | scrollHeight ≤ 5 × 844; figure count; J3 pointer-contract build check |
| DR-K14-03 | The home page MUST offer one start-here path per co-primary persona (advocate, journalist, organizer), each 3–4 linked steps whose targets resolve on the release. | link-resolution test over the three cards |
| DR-K14-04 | Example questions MUST be generated from the release and emitted only when their target satisfies the example contract (§6.2). | `examples.spec.ts`: every emitted example → 200 + answer element + no UUID |
| DR-K14-05 | Every capability statement on home and About MUST come from a capability table bound to release metrics. A capability whose metric is 0 MUST render its "being built" state instead. | unit test over the capability table; a fixture with the watch empty renders "Decision tracking — being built" |
| DR-K14-06 | `/about/` and `/glossary/` MUST exist as T1 pages linked from the header's About section and the footer. About MUST state the maintainer model, the independent-review status, what SIG is not, and how to cite and correct. | route and link test; copy approved by the operator (D-K14-7) |
| DR-K14-07 | Each reference page (methodology, editorial standards, how to read SIG, coverage) MUST open with an "In brief" of ≤ 80 words linking to its precise sections. The precise text MUST NOT lose content. Requirement ids MUST appear only inside "Spec references" disclosures. | word-count test; a diff guard proves the precise sections' text is retained; DR-C6-28 lint |
| DR-K14-08 | The first use of a glossary term in `main` on record and reference pages MUST link to its glossary entry with an HTML `popover` definition. Print pages MUST list the terms used. | built-HTML check against the glossary term list; the print PDF contains "Terms used" |
| DR-K14-09 | Epistemic labels, symbols, plain meanings and precise links MUST come from one lexicon (`epistemic.ts`). Visible text MUST NOT contain raw enum values (`STRONGLY_SUPPORTED`, `BEST_CLAIM_W1`, …) outside Technical details or `code`. | lint over the built HTML; a unit test that every component reads the lexicon |
| DR-K14-10 | No sentence of 8 or more words MAY appear more than once in a page's `main` + footer. Count figures MUST carry the "not a census" label instead of a repeated sentence. | the repeated-sentence lint over every discovered route (K0 UXK0-1) |
| DR-K14-11 | Shared chrome visible by default (header labels excluded; footer, provenance, dispute, cite) MUST be ≤ 40 words. The full SIG-UI-044 module MUST be one action away and MUST be page-specific on record pages. | word-count test with `<details>` collapsed; SIG-UI-044 field test on expand |
| DR-K14-12 | All colours, font sizes, spaces and radii MUST come from `tokens.css`. Text tokens MUST meet ≥ 4.5:1 (large text ≥ 3:1) and essential non-text tokens ≥ 3:1 in both themes. The support ramp MUST be single-hue and lightness-monotone. Reserved hues MUST be used only by their states. | stylelint allow-list; `design-tokens.test.ts` extended (contrast, monotone L, no green band); a grep test that `--epi-disagree-*` appears only in the contested/unresolved/range classes |
| DR-K14-13 | Every template MUST render in a dark theme under `prefers-color-scheme: dark`, declare `color-scheme`, force light for print, and pass axe colour-contrast in dark. | Playwright `colorScheme: 'dark'` project; axe; the computed body background ≠ `#fff` in dark |
| DR-K14-14 | The type scale MUST have ≤ 8 size tokens with a 13 px minimum, prose measure ≤ 70 ch, and tabular numerals for figures and numeric columns. | CSS parse test; computed-style check (max `p` width ≤ 70 ch) |
| DR-K14-15 | With `prefers-reduced-motion: reduce` there MUST be no animated transitions, map easing or animated layouts. | reduced-motion Playwright project; a grep test bans `easeTo`/`flyTo` without a motion guard |
| DR-K14-16 | The header MUST show ≤ 6 sections plus a search field, mark the current section with `aria-current`, share the page grid with `main`, and on mobile collapse into a no-JavaScript `<details>` menu. Record pages MUST show breadcrumbs. | DOM test; the left edges of header and `main` are equal; mobile H1 top (DR-K14-01) |
| DR-K14-17 | Every empty state MUST follow the five-part pattern (§6.4) and use the hatch only when the emptiness is absence. 404/410/500 pages MUST be branded, with search, home and status links. | component test for each `EmptySurface`; error-page e2e (extends DR-C6-29) |
| DR-K14-18 | Visual regression MUST cover every template × {light, dark} × {1440, 390, 320} on the synthetic fixture (no real names, K0 §4.12.6), with canvases masked. A baseline change MUST cite its ticket. | `visual.spec.ts` with `toHaveScreenshot` (maxDiffPixelRatio 0.01); the baseline diff lands in the ticket PR |
| DR-K14-19 | Built text MUST contain no words joined at element boundaries and no ungrouped numbers of 5 or more digits outside code, ids and dates. | lint: regex `[a-z][.?!)][A-Z][a-z]` and a dictionary check for joins; `\b\d{5,}\b` outside `<code>`/`<time>`/URLs = 0 |
| DR-K14-20 | The site MUST ship a logo SVG, a favicon set, a social card per page type and unique titles and meta descriptions. | head-tag test; C2 NEW-27 checks |
| DR-K14-21 | Printed dossiers MUST open with the council-brief page 1 and carry place, as-of, release, permalink and licence on every page, with no orphan pages. | `page.pdf` + PyMuPDF check (C2 §8 method) |
| DR-K14-22 | Design-system CSS MUST be ≤ 12 KiB gzip. The font (if adopted) MUST be ≤ 30 KiB and `font-display: optional`. K14 pages ship 0 KiB JavaScript beyond K0-approved elements. | `budget.spec.ts` (K0 UXK0-2); CLS ≤ 0.02 on T1 |

**Spec interactions (for T1):**
- **SIG-UI-044:** amend the form (D-K14-6).
- **SIG-UI-006:** add "saturated colour means attention; categorical data uses one hue plus shape".
- **SIG-UI-049:** extend with the ≤ 6-section rule and search in the header.
- **SIG-UI-046:** extend with CP-1…CP-10.
- **New:** a glossary MUST (publishing Appendix E).
- **SIG-UI-003/004/005/007/008/009 are unchanged.**

---

## 9. Round-11 ticket outline (for K13/S2 sizing)

| key | ticket | size | depends |
|---|---|---|---|
| UXK14-1 | **Tokens v2:** `tokens.css` (type, colour light and dark, space, radius, motion), migration of `epistemic.css`, the new support ramp, a dedicated disagreement token, the banner restyle (NEW-2/3), stylelint rules, extended `design-tokens.test.ts` (contrast, monotone L, reserved-hue usage), Public Sans self-hosting | M | D-K14-3/5 |
| UXK14-2 | **Layout and chrome:** header (≤ 6 sections, search, `aria-current`, mobile `<details>`), footer + provenance strip, page-header band, release stamp, breadcrumbs, grid/containers, 320 px reflow | M | K13 IA; UXK14-1; G3 release id |
| UXK14-3a/b | **Component kit (visual layer):** Figure/stat, cards, tables, chips/badges, absence, contested, range, provenance-panel shell, callouts, empty states, 404/410/500 | L (split) | UXK14-1; K0 UXK0-4; J3 TX `<Figure>` |
| UXK14-4 | **Copy system:** the lexicon in `epistemic.ts`, `/glossary/` generated from Appendix E + lexicon, `<Term>` + popover, "In brief" boxes, "Spec references" disclosures, chrome copy rewrite, compact cite/HWKT/dispute (SIG-UI-044 amendment), the fix for joined words (`compressHTML`/source whitespace) | M | D-K14-6/8; UXK14-3 |
| UXK14-5 | **Copy lints** in CI: ids/snake/UUID (DR-C6-28), repeated sentences, visible-chrome words, joined words, digit grouping, bare "unknown", readability report | S | UXK0-1 route discovery |
| UXK14-6 | **Home, About, How it works, methodology hub:** capability table bound to the release, persona cards, example-question generator + contract test, "What makes SIG different", golden-example card | M | K13; J3 Figure; golden place (D-K14-6); UXK14-2/4 |
| UXK14-7 | **Brand:** logo SVG, favicon set, per-type social cards (build-time), meta descriptions | S | D-K14-2 |
| UXK14-8 | **Data-viz helpers:** static SVG builders for range, bars, timelines and small graphs using tokens; line styles for access kinds and currency; the provisional outline; legends; table twins; print rules | M | UXK14-1; K2/K6 |
| UXK14-9 | **Print v2:** council-brief page 1, running header and footer (`@page` boxes or fallback), terms list, QR code, greyscale check | S | TH-10; UXK14-3 |
| UXK14-10 | **Test harness:** visual regression (template × theme × viewport), dark and reduced-motion projects, the gallery generator for operator review (written under `docs/build/logs/`, never published) | M | UXK0-2 synthetic fixture |
| UXK14-11 | **Onboarding content:** per-page reading keys, empty-state copy for every `EmptySurface`, the annotated "how to read a dossier" page | S | UXK14-3/4 |
| UXK14-12 | **Announce-readiness review:** run §7, record the results, and prepare the operator gallery + checklist for sign-off (no agent sign-off, P4) | S | all above; D3 §5 |

**Order:**
1. UXK14-1 and UXK14-5 can land first. They unblock every K-row UI and fit beside Wave 0 copy fixes (QW-1…15).
2. Then UXK14-2 and UXK14-3 → UXK14-4 → UXK14-6/7/8/9/11 → UXK14-10 → UXK14-12.
3. K1–K11 tickets consume the kit and do not restyle.

---

## 10. Operator decisions

| id | decision | recommendation |
|---|---|---|
| D-K14-1 | Confirm the tagline, sentence, paragraph and "is not" lines (§2.1), verbatim or edited | confirm, together with D3 Q5 |
| D-K14-2 | The name stays "Surveillance Infrastructure Graph (SIG)" at surveillancegraph.org; logo direction: a node-link glyph with one dashed edge | **yes** |
| D-K14-3 | Typeface: Public Sans Variable (26.2 KiB, OFL) vs the system stack (0 KiB) | **Public Sans**: one consistent identity across operating systems for less than a sixth of the T1 budget |
| D-K14-4 | Dark mode follows the OS setting only (no toggle, no stored preference) in Round 11 | **yes** |
| D-K14-5 | Palette change: support moves to a slate ramp; contested and unresolved share raspberry (no red); amber means provisional; blue means links and data; categorical data uses one hue plus shapes. Approve the lexicon labels (§3.4, including "Stated absent") | **yes** |
| D-K14-6 | Amend SIG-UI-044 to "full on record pages, a one-line summary one action away elsewhere"; the compact cite and dispute forms (SIG-UI-033/035 substance unchanged); the golden place(s) for onboarding (with C5 Q-C5-2 / D3 §4) | **yes**; golden place per D3 |
| D-K14-7 | The About page's "who runs SIG" wording (named, or "a single independent maintainer") and the independence and costs statement | operator writes; agents draft only |
| D-K14-8 | Publish the spec (at least Parts I–V, VIII and Appendix E) as a page per release, so "Spec references" resolve publicly (interacts with D-J3-3, repo private) | **yes**, for "open source scrutiny muster" (U-004) |
| D-K14-9 | The "beautiful" sign-off: the operator reviews a gallery of every template × {light, dark} × {390, 1440} before the announcement | **yes** |

---

## 11. Risks

| id | risk | mitigation |
|---|---|---|
| R-1 | The plain layer drifts from the precise text, and two definitions disagree | one glossary source holds both; "In brief" boxes link their precise anchors; the hostile-reader review covers plain text too (SIG-UI-042/046) |
| R-2 | Simplifying erodes the precision the operator values (U-004) | precise text is retained by rule and guarded by a diff (DR-K14-07); layers are added, never rewritten |
| R-3 | Onboarding over-promises before the data exists (TH-01) | capability binding (DR-K14-05); example contract (DR-K14-04); golden example only when real |
| R-4 | Fewer repeated caveats means readers miss them | the caveat attaches as a label to every figure it qualifies; a lint requires the label on count figures |
| R-5 | Redesign churn collides with K1–K11 feature work | tokens and kit first (UXK14-1/3); K rows consume, never restyle |
| R-6 | Agents cannot judge "beautiful" | the operator gallery sign-off (D-K14-9); peer exemplars as references; objective checks for the rest |
| R-7 | Dark mode doubles QA | automated contrast and axe in dark; visual-regression matrix |
| R-8 | Public Sans reads as "government" (it is the USWDS typeface) | a neutral wordmark, no seals, independence stated on About; the system stack is the fallback option |
| R-9 | Visual-regression flakiness from fonts and canvases | a self-hosted font, masked canvases, the synthetic fixture, a fixed Chrome channel |
| R-10 | A popover or `@page` gap in a browser | the popover also links to the glossary (works everywhere); a fixed-footer fallback for print |

---

## 12. New findings (`findings/incoming/K14.csv`; only items not already in FINDINGS/incoming)

| id | sev | title |
|---|---|---|
| NEW-1 | S2 | Shared page chrome is a median 36 % of each page's words (≥ 50 % on 11 of 41 pages) and repeats undefined jargon on every page; dossiers repeat the absence sentence 3× |
| NEW-2 | S2 | The "contested" colour token also paints the incompleteness banner, bound map-layer controls and speculative access paths, so the reserved disagreement colour means four things |
| NEW-3 | S3 | The support colour ramp is not an ordinal ramp: four hues over 156°, lightness out of order, `probable` 2.50:1 and `withdrawn` 2.85:1 against white |
| NEW-4 | S3 | No dark-mode support: no `prefers-color-scheme` rules or `color-scheme` meta; the current epistemic tokens fall to about 2.5–3.1:1 on a dark surface |
| NEW-5 | S3 | No type scale or measure: 17 font-size literals, 10–15 rendered sizes per page, 9.92 px nav labels on every page, prose lines of about 120–140 characters at 1440 px |
| NEW-6 | S2 | The spec's glossary (Appendix E) is not published, and defined terms appear in the UI with no definition one click away |
| NEW-7 | S3 | HTML compression drops spaces at inline-element boundaries: "concern?Dispute" on 41 of 50 pages, plus "SIGreports", "toresearch", "withnamed", "devicesacross" |
| NEW-8 | S3 | Large numbers are printed without digit grouping (56 numbers of 5 or more digits ungrouped, 0 grouped, across home, dossiers and methodology) |
| NEW-9 | S3 | Header: 15 links, no current-page marker, no search field; the H1 starts 344 px (41 %) down the mobile first screen; header and content columns misaligned |
| NEW-10 | S3 | The map's cluster click animates with `easeTo` regardless of `prefers-reduced-motion`, contradicting the island's own header comment |
| NEW-11 | S2 | The home lede and entry cards promise capabilities the release does not show (upcoming decisions, cost and decision dates, claim-level support/contradiction, a council-ready PDF). This extends F-140/RI-38 to the home page |

---

## 13. Limitations and command log

**Limitations.**
- **Visual review.** "Beautiful" is judged only by rules and exemplars here; the operator decides (D-K14-9). No
  screen-reader or human testing was done (P4).
- **Estimates.** Readability grades use a heuristic syllable counter. Line-length figures assume 0.5 em per character.
  Both are **inference**.
- **Font features.** Public Sans' `tnum` support and Chrome's `@page` margin boxes were not verified.
- **Scope of the copy audit.** It reuses C2's captures of the same release; no new text capture was needed (the drift
  guard is unchanged).
- **Upstream decisions.** The palette validation used the dataviz skill's validator (OKLab ΔE, Machado 2009 CVD model).
  Final token values may shift one step at implementation; the tests in DR-K14-12 bind them. The capability-binding
  thresholds (§2.2, §6.2) are agent-proposed. K1–K3 and K13 (running in parallel) may refine the IA in §5.

**Commands (all read-only; outputs in `docs/build/logs/next-phase/K14/` or the scratchpad).**

| # | when (`date -u`) | command | result |
|---|---|---|---|
| C1 | 22:09:29Z | `git status`; read inputs (META_PLAN, U-ids, K0, K12a, K12b, C2, C6, C5, D3, J3, spec §1, §39–41, App. E, web/src) | clean worktree |
| C2 | 22:12:30Z | `curl -sI` drift guard `/` | 200, `Last-Modified` 27 Sep 01:33:43 GMT, ETag `"6ab87277-14f54"` |
| C3 | 22:12:57Z–22:14:02Z | `node tools/k14.mjs` (Playwright 1.62.1, `channel: chrome`, headless; 17 GET loads ≥ 3 s apart; desktop, iPhone 14, dark, print) | `json/k14_metrics.json`, `shots/*.png`, `loads.tsv` (17 rows) |
| C4 | between C1 and C2 | `python3 copy_audit.py` over `docs/build/logs/next-phase/C2/text/R*_desktop.txt` (50 files) | §1.1; `tools/copy_audit.json` |
| C5 | between C1 and C2 | `python3 contrast.py` (current `--sig-*` tokens vs white and a dark surface) | §1.2, NEW-3/4 |
| C6 | 22:18:31Z | `npm install --userconfig=/dev/null --ignore-scripts` of 5 `@fontsource` packages into the scratchpad; `ls -l` of the Latin woff2 files | Public Sans Variable 26,832 B; Inter 48,256; Source Serif 4 50,824; IBM Plex 22,588–24,252 per weight; all OFL-1.1 |
| C7 | 22:18Z–22:21Z | `node validate_palette.js` (dataviz skill) on current and proposed palettes, `--ordinal` and `--pairs all`, light and dark | §4.3 (current ramp FAIL; proposed PASS) |
| C8 | 22:21Z | `contrast()` from the same script for text and non-text tokens | §4.3 tables |
| C9 | 22:20Z | `grep` of `web/dist/{index,methodology}/index.html` for `concern?<a`, `SIG<strong>` | joined words present in the built HTML (NEW-7) |
| C10 | 22:22:21Z | `curl -sI` drift guard; `shasum -a 256` over the evidence tree | unchanged; `SHA256SUMS` sha256 `e2261b86d988…` |
| C11 | 22:22:29Z | `git diff --stat b051732c HEAD -- web AGENTS.md docs/2_canonical_design_spec.md` | empty |
