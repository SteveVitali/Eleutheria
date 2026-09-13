# Study: the sous-surveillance.net → OpenStreetMap camera import

**Requirement:** SIG-CONTRIB-016 (§35.2, §5.3), P18.2 deliverable 3.
**Purpose:** study the already-executed ~12,000-camera import — its **conventions**, its
**community consultation**, and its **outcome** — **before** proposing any SIG-originated
contribution at scale. The machine-readable form of this study is
`connectors/src/connectors/data/osm_import_study.toml`, and the contribution gate that
reads it is `connectors/src/connectors/osm_import_study.py`
(`assert_import_studied_before_scaled_contribution`).

This import is the concrete, already-executed path from a *local activist database* to the
*common geographic substrate* that SIG's whole federation thesis depends on (§5.1, §5.2), and
the strongest available evidence that the thesis works. It is studied here, not repeated on
faith.

## What the outline said, and what is actually true

The outline (OL-5.2-03) states that "a historical French `sous-surveillance.net` dataset of
roughly **12,000 cameras** was imported into OpenStreetMap," inside a section titled **"France
and Belgium: Technopolice."** Both the number and the attribution are imprecise, and are
corrected here rather than repeated (every contradiction stays visible, §3.1):

| Outline claim | Correction (source) |
|---|---|
| ~12,000 cameras | ~**20,000** in the source database; ~**18,000** imported worldwide; **~12,000 is the France-only subset** (F9.6/F9.7). |
| Imported by **Technopolice** | Executed by **`User:Vucod`** (via `User:VucodImport`) with the support of **OpenStreetMap Belgium**; the wiki page is categorised *Import from Belgium*. Technopolice's forum *independently advocated* mapping in OSM (F9.5), but did not run the import; its own Technocarte is a stale 51-commune polygon map (F9.3/F9.7). |
| (completion date absent) | Brussels pilot **March 2020** (authorization granted); **full import finalised March 2025** (F9.6). |

The upstream identifier that survives in OSM is **`ref:sous-surveillance_net`** — the join key
SIG reconciles against, rather than re-importing the activist database into SIG (F9.7).

## Conventions (the import's field crosswalk and conflation rules — F9.12)

The import wiki documents a complete source-field → OSM-tag mapping and a set of conflation
rules that are a **field-tested template** for SIG's own per-source crosswalk and camera
reconciliation (§11.1, §8.6):

- **Base tags** added to every node: `man_made=surveillance` + `surveillance:type=camera`.
- **Upstream identifier preserved** as a namespaced ref: `id_camera → ref:sous-surveillance_net`.
  SIG adopts the `ref:<source>` convention verbatim for `PhysicalAsset.upstream_ids[]`.
- **Semantic field conversions**: `op_name → operator`, `title → name`,
  `direction → camera:direction`, `apparence → camera:type` (with `radar` reclassified to
  `surveillance:type=ALPR`), `op_type=private → surveillance=outdoor`.
- **Distance-banded conflation with an explicit uncertainty band** — the reusable default for
  SIG's §11.1 camera reconciliation:
  - source camera **< 5 m** from an existing OSM camera → **excluded** (duplicate);
  - **5–10 m** → imported with `fixme="This may be a duplicated camera"`;
  - **> 10 m** → imported as a new node.
- **Age-based staleness as a first-class ingestion output** (not a query-time computation):
  `survey:date` older than 10 years → `fixme="This may be disused"`.
- Belgium (Brussels-region) import estimates: ~92.5% direct import (~16k), ~7% excluded (~1k),
  ~0.5% flagged (~100).

## Consultation (how it was proposed, authorized, and communicated — F9.5/F9.6/F9.8)

The import ran as a **formally proposed, community-authorized** OSM import, documented on a wiki
import-plan page (`Import/Catalogue/sous-surveillance.net`):

1. **2019-10** — discussion with sous-surveillance.net and OpenStreetMap Belgium; formal
   proposition to sous-surveillance.net.
2. **2020-03** — import limited to Brussels, authorization granted (changeset 82207370).
3. **2020-09** — authorization granted for the full dataset; communication towards OSM France.
4. **2025-03** — finalized import, ~18,000 cameras worldwide.

The Technopolice mapping forum had, separately, **explicitly resolved in favour of OSM** as the
place to do surveillance mapping, and criticised sous-surveillance.net for consuming OSM tiles
without contributing data back (F9.5, OL-5.2-02) — a documented precedent for SIG's federation
posture.

**The licensing anti-pattern SIG must NOT repeat (F9.8).** The import's permission record is a
single **one-line email extract** pasted into the wiki *Background* section, and the processed
OSM data files were **never linked** (the wiki literally reads *"available [???here???]"*).
This is precisely the informal-permission failure mode SIG's rights model exists to prevent: a
contribution SIG originates must carry a **machine-readable rights record** with a resolved SPDX
expression and a durable link (§42.1), and must go through a **human-mediated workflow with
individual review** (SIG-CONTRIB-015/016b), never a one-line-email import.

## Outcome (the measured result — F9.6/F9.7/F9.10)

- **~20,000** cameras in the source database → **~18,000** imported worldwide (~**12,000**
  France subset), mostly France and Belgium, with smaller counts in Luxembourg, Montréal,
  Seattle, Moscow, and Minsk.
- OSM's global surveillance layer has since grown to **558,645** objects (`surveillance:type=ALPR`
  alone: **144,312**).
- **Density caveat:** France leads the world in per-country OSM surveillance density **largely as
  an artefact of this one import** (F9.10). SIG must annotate coverage with import provenance and
  must not read the French density as uniform completeness — otherwise France looks "well covered"
  and Germany "empty" when the real difference is one 2025 changeset.
- **Assessment:** the activist-database → common-substrate path executed **successfully**, and is
  the strongest available evidence SIG's federation thesis works. SIG therefore **reconciles
  against OSM** through the `ref:sous-surveillance_net` join key rather than re-importing the
  source database, and treats `sous-surveillance.net` as a historical upstream (F9.7/F9.11).

## Consequence for SIG-originated contribution

Because this study is complete, the contribution gate
(`assert_import_studied_before_scaled_contribution`) **permits** a SIG-originated contribution to
be *proposed* — but proposing is not executing. Any bulk contribution remains gated on the full
SIG-CONTRIB-016c requirements and the P16.2 **human-mediated** MapRoulette suggestion workflow
(no direct automated OSM writes, SIG-CONTRIB-014). This ticket studies the precedent; it does not
execute a contribution at scale (that is explicitly out of scope, gated on P16.2).
