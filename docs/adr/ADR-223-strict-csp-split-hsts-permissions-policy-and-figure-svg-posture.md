# ADR-223 — the strict CSP is a meta ∩ header split; HSTS, the `/map/`-only geolocation exception, and the dedicated figure-SVG policy (P36.19)

- Date: 2026-10-28
- Status: accepted
- Ticket: P36.19 (UXK0-3, manifest row 359 — on `r11/P36.19-csp-hsts-permissions-policy`)
- Base: `r11/P36.18-layout-and-chrome`
- Requirement stamps: SIG-UI-096 (owner — strict CSP + HSTS, adopted by
  UXR-A01), SIG-UI-039 (the T-page contract), SIG-UI-040 (ADR-155 page-type
  posture), SIG-ENG-042 (unverified surfaces fail), SIG-UI-066 (one static
  figure kit, dedicated SVG response policy), SIG-UI-D08 (strict CSP + HSTS)
- Supersedes: nothing — this records the first owned decision on the response
  security layer; K0 §4.8's rows are the contract this implements.

## Context

K0 §4.8 fixes the response-security posture verbatim: a strict Content
Security Policy with per-page hashes and no `'unsafe-inline'`/`'unsafe-eval'`
on normal pages, a stricter `default-src 'none'` row for T0 record/print
pages, HSTS, a deny Permissions-Policy everywhere with `geolocation=(self)`
on `/map/` only, and a dedicated policy for standalone figure SVGs —
`default-src 'none'; style-src 'unsafe-inline'; img-src data:; sandbox`
plus `nosniff`. The site is `output: "static"` Astro (SIG-UI-037): a build
produces files, not responses — no static artifact can emit an HTTP header
by itself, and no static nginx config can name a *per-page* set of script
hashes (each page's inline bootstrap scripts hash differently). The question
the row owned: how to realise K0's served-response posture honestly on a
static host.

## Decision

1. **The CSP is a document-meta ∩ response-header split, and the
   intersection is K0's policy verbatim.** `security.csp` in
   `web/astro.config.mjs` makes Astro emit a per-page
   `<meta http-equiv="Content-Security-Policy">` carrying that page's tracked
   `sha384` hashes for its inline `<script>`/`<style>` elements — the
   authoritative per-document policy (`default-src 'self'`,
   `script-src 'self' <hashes>`, `style-src 'self' <hashes>`,
   `img-src 'self' data: blob:`, `connect-src 'self'`,
   `worker-src 'self' blob:`, `font-src 'self'`, `object-src 'none'`,
   `base-uri 'none'`, `form-action 'self'`,
   `script-src-attr 'none'`, `style-src-attr 'none'`). The served header —
   `ops/web/sig-security.conf` via the `$sig_csp` map — carries only the
   meta-inexpressible and hash-independent guards:
   `frame-ancestors 'none'; object-src 'none'; base-uri 'none';
   form-action 'self'; script-src-attr 'none'; style-src-attr 'none'`.
   A header `default-src`/`script-src 'self'` is deliberately absent: a
   'self' there would deny the hashed inline bootstrap the meta lawfully
   admits (both policies must pass), and a static host has no way to name
   per-page hashes. The browser enforces the intersection — which is K0
   §4.8's served posture.
2. **T0 gets K0's `default-src 'none'` row by build-time rewrite.** The
   `sig-page-types` `astro:build:done` hook already classifies every emitted
   route against the ADR-155 registry; for each T0 route it rewrites the
   emitted meta (`src/lib/csp.ts` `tightenT0Document`) to
   `default-src 'none'`, dropping `script-src`/`connect-src`/`worker-src`
   and `blob:` from `img-src`. The effective T0 policy (meta ∩ header) is
   K0's record/print row verbatim. `csp.spec.ts` asserts the tightened
   shape on every discovered T0 route — a page that misses the patch fails
   the gate.
3. **`style-src-attr 'none'` is load-bearing and needs no exception.** Every
   `style=""` attribute in `src/` moved to token-backed classes (the map
   island's mount-height reservation became the generated
   `--k0…--k24` class table — a build naming a 27th licence-compartment row
   fails loud rather than under-reserving); React/MapLibre set CSSOM
   properties, never the attribute. `securitypolicyviolation` e2e legs prove
   an injected `style=` attribute, `<style>` element, `<script>` element and
   `eval()` are each blocked and each reported; a CSP-free control proves
   the harness detects.
4. **Client code renders text only; the ban is a CI grep.** K0 §4.8's
   untrusted-labels rule is `web/scripts/check-unsafe-dom.mjs` wired into
   `npm run check` as `check:dom`: `innerHTML`, `outerHTML`,
   `insertAdjacentHTML`, `document.write`, `dangerouslySetInnerHTML` and
   MapLibre `setHTML` are banned in `web/src/**` (comments stripped first —
   the ban is on use). The MapLibre popups build their disclosure DOM with
   `textContent`/`createElement` and hand it to `.setDOMContent`.
5. **The served security headers are one shared static fragment.** Both
   nginx shapes (`ops/web/nginx.conf` release template, `nginx-legacy.conf`)
   define the same two `map $uri` blocks — `$sig_csp` (uniform policy
   default, dedicated figure policy on `*.svg` under every tree, keyed on
   the request so the policy follows the bytes, never a location block) and
   `$sig_permissions_policy` (`geolocation=(self)` on `/map/` URIs only;
   `geolocation=(), camera=(), microphone=(), payment=(), usb=(),
   interest-cohort=(), browsing-topics=()` everywhere else) — and include
   `sig-security.conf` at server scope and inside every location that
   declares its own `add_header` (nginx inheritance drops the server set
   there — the same rule `sig-headers.conf` exists for). HSTS is
   `max-age=63072000; includeSubDomains`; `nosniff` moved into the fragment
   as the single source. The `release_*.conf`/`chrome_*.conf` fragment
   surfaces, the promoted-map gate, the withdrawal barrier, cache posture
   and byte-range serving are unchanged.
6. **`preload` is deliberately absent from the HSTS value.** Submitting the
   origin to the browser preload lists is a public-origin commitment the
   launch row owns, not a template default.
7. **Static-export honesty is part of the decision.** The meta tag is a real
   enforcement layer (CSP meta is honoured for everything except
   `frame-ancestors`, `sandbox` and `report-*` — exactly the directives the
   header carries), and the served-header claims are made only about what
   `sig-security.conf` + the maps emit. Engineering claims name the layer;
   hosted verification stays `prepared_not_executed` per the ticket's
   `live_verification=false`.

## Consequences

- The intersection being the policy means neither half alone names K0's
  rows; the e2e proves the intersection on real bytes (zero violations on
  the hydrated `/map/` island included) and the ops/composed suites pin the
  header values on real responses.
- A future page type or a per-route policy exception lands in exactly one
  place per layer: `src/lib/csp.ts` for the document meta,
  `$sig_csp`/`$sig_permissions_policy` for the served headers.
- A standalone `.svg` response under ANY served tree (`/r/`, `/s/`, the
  latest view, the legacy flat tree) carries the figure policy — P36.27's
  static figure kit ships into a policy that already exists.
- Re-introducing a `style=""`, `innerHTML`, `setHTML` or
  `dangerouslySetInnerHTML` is a build failure (`check:dom` + the CSP
  sweep), not a review comment.

## Alternatives considered

- **Per-page hashed `Content-Security-Policy` headers generated into the
  conf generation** (`conf/<gen>/csp.conf` naming each route's hashes).
  Rejected for this row — it binds the served config to a generated
  per-route hash manifest (a new generation artifact, a new render path,
  drift surface between the built pages and the served map) to gain the
  header-vs-meta redundancy; the meta ∩ header split reaches the identical
  effective policy with zero generated config. Recorded as the natural
  revisit path if a defence-in-depth header copy is ever wanted.
- **`default-src 'self'` uniform header and no T0 tightening.** Rejected —
  it would loosen K0's T0 row (`'self'` permits same-origin scripts the T0
  contract forbids) and would *break* the hashed bootstrap (a header
  `script-src 'self'` without the page's hashes denies inline scripts the
  meta admits). Verified against real bytes before settling.
- **A `location ~ \.svg$` block for the figure policy.** Rejected — nginx
  regex locations beat prefix locations, so `/r/<pub>/figure.svg` would
  resolve against the wrong root; the `$sig_csp` map keys on the request
  and never touches routing.
- **`unsafe-eval` on the page policy for MapLibre workers.** Rejected —
  not needed: the built island draws under the strict policy (the
  zero-violation e2e navigates the hydrated map).

## Revisit trigger

- A runtime dependency that legitimately needs `eval`, inline attributes or
  a third-party origin lands (needs a new ADR amending the posture and
  ADR-155's registry story).
- The conf-generation machinery gains a per-route CSP artifact — then the
  header can carry per-page hashes as defence-in-depth; this ADR is amended
  by its successor.
- The launch row decides the HSTS `preload` submission — the token is added
  by that decision, not by default.
- A second route acquires a legitimate geolocation need — the
  `$sig_permissions_policy` map is extended per-route and this ADR amended.
- Browser behaviour changes around `securitypolicyviolation` dispatch —
  the eval leg proves both the block (the `__cspEval=0` sentinel) and the
  event under the planted hash-admitted policy.
