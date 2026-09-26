# Publication opinion drafts (HG-02 / D-LEGAL.1-1)

**Status: operator-adopted analyses, 2026-09-16. NOT legal advice.** The operator
directed that the four scoped HG-02 questions be answered with drafted analyses in
place of engaging counsel (`D-LEGAL.1-1`). Each analysis below restates the
question, examines the safeguards actually built and enforced in code, and records
a determination the operator adopts. **Real counsel review may supersede any row
here — the analyses carry no privilege and no authority beyond the operator's
adoption.** RISK-P0-01 stays open in the risk register as a live risk with its
mitigation, not a resolved one.

---

## 1. ODbL 4.4(b) — produced works vs derivative databases (RISK-P0-01)

**Question:** are SIG's exports and public pages "Produced Works" under ODbL
4.4(b) (attribution-only, no share-alike on the work) or Derivative Databases
(share-alike applies, 4.4(a))?

**Analysis.** ODbL draws the line at whether the output is a *database* containing
a substantial part of the ODbL-licensed contents (4.4(a) — share-alike) or a *work
produced from* the database that is not itself a database (4.4(b) — attribution
only). SIG's architecture already answers this compartment-by-compartment rather
than globally:

- The `osm_physical` export compartment is shipped **as a database** — it is
  labelled `ODbL-1.0`, carries attribution, and remains a separate compartment so
  share-alike never propagates into `sig_graph` or `derived_facts`. This satisfies
  4.4(a) under the strictest reading: if it is a Derivative Database, its licence
  already is ODbL.
- The rendered web pages, dossiers, and map tiles are **produced works**: they
  contain derived *facts rendered for reading*, not a queryable database of ODbL
  contents. Under 4.4(b) they carry attribution (they do — every page renders
  source + licence attribution) and no share-alike obligation attaches to the
  page itself.
- The `sig_graph` and `derived_facts` compartments contain no OSM contents, so no
  ODbL obligation attaches to them at all — compartment separation is the
  structural guarantee, verified by the export tests.

**Determination adopted:** publish-permitting. The compartmented design means the
risk resolves to *correctness of separation*, which is enforced and tested, not a
licence-theory gamble. Residual risk: a future compartment accidentally mixing
ODbL contents into a CC-BY compartment — mitigated by the per-compartment licence
stamping and the export build tests.

## 2. The officer-naming gate (SIG-PUB-007/008/009/010)

**Question:** does the implemented gate suffice for publishing public-employee
names from public records?

**Analysis.** `policy.officer` implements a five-prong conjunctive test (official
conduct; name on the face of an R1/R2 record; record public in its jurisdiction;
the accountability claim fails without the name; proportionality) **plus**
two-independent-reviewer written concurrence, defaulting to no-publish on any
failure. Two categorical carve-outs sit outside the test: home addresses are never
publishable, and routine audit-log rows naming an officer are never ingested.

The gate is strictly stricter than anything required to lawfully republish a name
that already appears on the face of a public record. The residual risk the five
prongs address is not defamation (republishing a true public-record fact is
protected) but *contextual* harm — naming where the claim does not need it — which
prong 4 exists to catch. The concurrence prong is the human check on that
judgement.

**Determination adopted:** the gate suffices as designed. Recorded caveat: the
concurrence prong currently resolves through the sole-maintainer posture
(`concurrence.md` — operator self-concurrence, independence waived), so in
practice the gate defaults to **no-publish for all names** until a second
independent reviewer exists — a *stricter* outcome than the design requires, and
therefore safe.

## 3. Publication tiers + sensitive-coordinate rules (SIG-PUB-011/013, §19.4)

**Question:** do the geospatial publication tiers adequately protect sensitive
coordinates?

**Analysis.** `policy.sensitivity` maps every sensitivity class to a publication
tier (0–3). The enforced rules: a `CandidateAsset` on a residential parcel is
*never* publishable at any tier; higher-sensitivity classes degrade coordinate
precision (jurisdiction-level rather than point); the public API serves tier-0
only through the `sig_read_public` RLS role, so nothing above tier 0 can be
reached by the public surface at all. The rule set is conservative: it errs
toward less precision, and the failure mode of a misclassified asset is
suppression, not exposure.

**Determination adopted:** the tier + precision rules are adequate. The enforced
invariant is structural (RLS + tier stamping at ingest), so a code bug elsewhere
cannot leak a sensitive coordinate through the public role.

## 4. Part VIII on the published surface (SIG-PUB-002/003)

**Question:** does the published surface satisfy Part VIII's prohibitions — no
plate reads, no trip records, no per-person or per-search data?

**Analysis.** Part VIII is enforced *at storage*, not at publication: there is no
schema, predicate, or ingest path for per-plate, per-trip, per-person, or
per-search records — the forbidden-token guard in the connector claim path
(`okc_claim` and peers) refuses claims carrying such literals before they can
enter the spine. The public surface can therefore not leak a category that was
never storable. This is the strongest available posture: not redaction of stored
data, but structural absence.

**Determination adopted:** satisfied by construction. The one live edge is
verbatim-literal publication (`raw_value`): a reviewed clause literal could in
principle contain a name — mitigated by the officer-naming gate's default
no-publish and the reviewed-literal verification that checks each literal against
captured evidence before it is emitted.

---

## Adoption record

| # | Question | Determination | Adopted by | Date |
|---|---|---|---|---|
| 1 | ODbL 4.4(b) produced works | publish-permitting; compartment separation is the guarantee | operator (self-adopted) | 2026-09-16 |
| 2 | Officer-naming gate | suffices; resolves to default-no-publish under sole-maintainer posture | operator (self-adopted) | 2026-09-16 |
| 3 | Publication tiers + coordinates | adequate; enforced structurally via RLS + tier stamping | operator (self-adopted) | 2026-09-16 |
| 4 | Part VIII surface | satisfied by construction — forbidden categories are not storable | operator (self-adopted) | 2026-09-16 |

*These determinations replace the pending-counsel labels on the interim
engineering dispositions (GL-GATE-02). They are the operator's own analyses, not
counsel's. If counsel is ever engaged, their opinion supersedes and this file is
amended to say so.*
