# P37.72 — SIG-GOV-017 analysis: the 'My location' map-pan control (D-K1-7)

**Written first, before the control.** Ticket
`docs/tickets/442_P37.72__my-location-map-pan-control.md` · plan row 442 ·
catalog `R11-K13-MAP-08` · design `K1-map.md` §4.1/§4.2. Date: 2026-11-08 (`date -u`).

**Operator decision (verbatim, never re-decided):**
`D-K1-7 [B-44] = yes (2026-10-01T04:51:39Z; operator chose it over 'no') ·
SIG-GOV-017 is not waived: the ticket first writes a GOV-017 analysis; the
control only pans the map (browser-only geolocation after a click; never sent
to SIG; no 'cameras near you' list, count, alert or proximity notice) · if the
analysis finds it cannot comply -> IN-TICKET PAUSE and the question (waive
GOV-017 for it, or drop it) returns to the operator` — the plan cell. Ratification:
`feedback/RATIFICATION_LOG.md` round 18 — **"D-K1-7 'My location' approved
(operator chose it over the recommendation)."**

## The rule under analysis

`docs/2_canonical_design_spec.md` §46.3:

> **SIG-GOV-017 (MUST).** SIG MUST NOT build: a real-time device-liveness
> feed; a per-person lookup; an "is a camera watching me right now" surface;
> or individual-officer tracking as a product (SIG-API-012, non-goals N1/N3).

The same prohibition is declared in SIG's own voice in
`docs/governance/anti-misuse-statement.md` and enforced structurally in
`api/src/api/prohibitions.py` (the refused-route patterns the P34.48
coverage verdict cites).

## The bounded build under test

Exactly what the plan cell bounds — nothing more:

- A button in the `/map/` chrome. On an **explicit click only** it calls
  `navigator.geolocation.getCurrentPosition` once and pans the map to the
  returned position. No watch, no repeat, no request on load or hydration.
- The position **never leaves the browser**: it is not sent to SIG, not
  logged, not stored, not written to the URL beyond the zoom-rounded `at=`
  viewport token every pan already writes (`viewportDecimals`, §3.4 —
  1–4 decimals by zoom, the same rounding a manual pan produces).
- **No marker** is drawn at the position — the control pans; it does not
  plot the viewer.
- **No 'cameras near you' list, count, alert or proximity notice** of any
  kind — no copy keyed to the person, no distance-from-viewer figure, no
  notification, no badge.
- `Permissions-Policy` already scopes `geolocation=(self)` to `/map/` alone
  (`ops/web/nginx.conf` `$sig_permissions_policy`, P36.19/ADR-156); every
  other route denies the capability. The page CSP `connect-src` allows only
  `'self'` + the SIG tile origin — a send would need new wiring an e2e
  network assertion guards.

## Analysis against the four prohibitions

**1. A real-time device-liveness feed — not built.** The surface shows the
published release: static observations with `first_seen`/`last_seen` dates.
Nothing in the dataset carries a real-time status and nothing in the control
creates one. The button adds a viewport change, never a data feed.

**2. A per-person lookup — not built.** SIG never receives the position; a
lookup over the viewer requires data SIG does not hold and structurally
cannot hold (browser-only API, `connect-src 'self'` + tile origin, the
network-leak e2e). The request/response cycle is between the browser and the
browser's own geolocation service — SIG is not a party.

**3. An "is a camera watching me right now" surface — not built, and the
hardest clause, analysed honestly.** The risk a reader will name: after the
pan, the In-view list and its `N records in view` line reflect a frame
centred near the viewer — could that read as "cameras near me"? Weighed:

- The list and count are **viewport functions**, unchanged since P36.37 —
  "records in view", never "near you". They produce identical output after a
  manual pan to one's street, a place-search jump (K1 §4.2), or the §4.2
  coordinates parse (P37.19's scope: `"41.4959, -94.5205"` jumps locally, no
  request). The control adds **no person-keyed computation**: nothing is
  computed relative to the viewer — everything is computed relative to the
  frame, which the viewer has always been able to set arbitrarily. The
  pre-existing distance column is distance-to-viewport-centre, recomputed
  for every frame; one pixel of drag moves the "centre" off the person.
- "Watching me right now" requires liveness the release cannot express:
  records are dated published observations, not feeds; a record's presence
  in the frame is a statement about the frame, never about the viewer.
- **Marginal capability is zero**: typing one's own coordinates or panning
  to one's street reaches the same view today. The button removes typing;
  it does not open a new information surface.
- Copy stays honest: the button announces "stays in this browser", the
  failure note says the map stays put. Nothing says or implies "near you".

**4. Individual-officer tracking as a product — not built.** No person
entity is involved, displayed, or resolved; officer naming stays
default-deny (SIG-PUB-008 stands).

## Residual tension, stated (SIG-GOV-019's posture)

Self-locating a map of published surveillance infrastructure makes a
self-check marginally easier — the same honest tension §46.3's GOV-019
paragraph names for the project as a whole. The mitigation here is the
bound itself: the control is a convenience affordance over information the
release already carries and the frame already exposes; it creates neither a
feed nor a person-keyed answer. The alternative — infrastructure that
watches the public while remaining unlocatable-by-it — is the condition the
project exists to remedy, and a map that refuses to frame the viewer's own
street would not remove the records from the frame, only the convenience.

## Compliance contract (what the build + tests pin)

1. Geolocation is requested **only on an explicit click** — never on load,
   hydration, or any programmatic path.
2. One-shot `getCurrentPosition`, `enableHighAccuracy: false`; no
   `watchPosition` anywhere in the codebase.
3. No position marker; no "near you"/proximity copy; no distance-from-viewer
   figure; no alert, badge, or persistence beyond the existing rounded `at=`.
4. No request may carry the returned coordinates — pinned by an e2e network
   assertion (`map-mylocation.spec.ts` collects every request URL and fails
   if the position appears in any).
5. Denial/unavailability shows honest copy and leaves the map where it is.
6. Any future proposal to add a marker, a proximity list/count/label,
   distance-to-viewer, persistence, or any send returns here — a fresh
   GOV-017 analysis and the operator, never an edit of this verdict.

## Verdict

**The control as bounded complies with SIG-GOV-017.** None of the four
prohibited surfaces is built; the person-keyed signal a prohibited surface
would need is one SIG never receives and cannot compute on. Build the
map-pan control under the contract above — no pause, no waiver sought.
