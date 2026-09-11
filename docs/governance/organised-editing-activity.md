# Organised Editing activity — SIG operator attribution

- **Spec:** docs/2_canonical_design_spec.md §35.2 (SIG-CONTRIB-016d/016e/016g),
  §42.3a (SIG-LIC-007a/007b/007c)
- **OSM wiki namespace:** `Organised Editing/Activities/SIG operator attribution`
- **Status:** Registered in the OSM Organised Editing activities list (2026-09-08)
- **Machine-checked source:** `tasks/src/tasks/data/organised_editing.toml`, loaded and
  validated by `tasks.contribution.organised_editing_activity` (a disclosure missing any
  required field cannot be constructed)

This is SIG's **Organised Editing activity page**, published to satisfy the OSM
**Organised Editing Guidelines**. Escaping the Automated Edits Code of Conduct by
keeping a human in the loop (see ADR-055) does **not** escape the Organised Editing
Guidelines: a SIG-run task challenge directing volunteers at the orphaned-device
backlog is *"a sizeable, substantial, coordinated editing initiative"* and is squarely
in their scope (SIG-CONTRIB-016d). The disclosures below are the ones the guidelines
require. They are single-sourced from the data table above so this page and the
executable disclosure cannot drift.

## Coordinating organisation and contact

- **Coordinating organisation:** The SIG project (Surveillance Infrastructure Graph).
- **Contact:** `osm-contact@sig.example`.
- **MapRoulette account holder:** SIG maintainers (shared org account
  `SIG_operator_attribution`); credentials held by the maintainer group. Challenge
  creation requires authentication, and the account falls under this disclosure
  (SIG-CONTRIB-015b).
- **MapRoulette API documentation (located, SIG-CONTRIB-015b):**
  `https://maproulette.org/docs/swagger-ui/index.html`.

## Changeset hashtag (SIG-CONTRIB-016e)

Every edit originating from a SIG task carries the declared hashtag
**`#sig_operator_attribution`** (the MapRoulette `checkinComment`). This is both the
compliance disclosure and the measurement instrument for the §7 leverage metric
*"SIG-originated operator-attribution suggestions accepted upstream"*: because the
hashtag is public, SIG's contribution stream is auditable by any third party —
including SIG's critics — which is what makes the metric credible. The hashtag is
declared in code as `tasks.contribution.CHANGESET_HASHTAG`, and the disclosure asserts
the two agree.

## Goal and why it is pursued

Add `operator=*` attribution to orphaned surveillance-device nodes — the
~116,800-device backlog — from public contracts and records, one human-reviewed
decision per device. OSM's ODbL share-alike posture and the federation compact (P5)
both oblige SIG to give its operator attributions back in a form OSM contributors can
use (SIG-CONTRIB-017); the licence and the mission point the same way.

## Timeframe

Ongoing from 2026-09, reviewed each quarter.

## Non-standard tools, with usage conditions (SIG-CONTRIB-016d)

| Tool | Usage conditions |
|---|---|
| MapRoulette cooperative challenge | Free, community-run; `cooperativeType=tags` proposes a specific tag change a mapper accepts / rejects / edits **in their own account**. |
| SIG task engine + contribution builder | Apache-2.0, open source; builds suggestions only and **never writes to OSM** (SIG-CONTRIB-014). |

## Data sources, with their licences and usage conditions (SIG-CONTRIB-016d; SIG-LIC-007c)

Only sources whose terms permit deriving an OSM edit may appear here — the
contribution-path licence gate of SIG-CONTRIB-016f
(`policy.licensing.assert_contribution_permitted`) blocks any that do not.

| Data source | Licence | Usage conditions |
|---|---|---|
| OpenStreetMap (Overpass) | ODbL-1.0 | Relicensable to OSM's own ODbL-1.0; attribution © OpenStreetMap contributors. |
| SIG operator-attribution subset (contributed upstream) | CC0-1.0 | Dual-licensed CC0-1.0 for OSM contribution (SIG-LIC-007a); satisfies OSM's no-added-copyright import rule. |
| Public procurement contracts and agency records | CC0-1.0 | Facts about public infrastructure derived from public records; contributable as CC0 (SIG-LIC-007a). |

**Attribution expectation (SIG-LIC-007b).** SIG's attribution expectations for the
contributed subset are limited to what OSM offers — mention on the OSM
contributors/activity wiki page and source information in changesets — and SIG has
decided **in advance** that these are acceptable, recording that decision here rather
than discovering the constraint at contribution time.

## Participating accounts (SIG-CONTRIB-016d)

The identified participating account is `SIG_operator_attribution`. Individual
volunteer mappers are **not** listed: they apply edits in their own accounts, with their
own judgment (SIG-CONTRIB-015), and are not directed en masse.

## Metrics used (SIG-CONTRIB-016g)

SIG measures **task outcomes, not contributor rankings**: suggestions accepted /
rejected / edited upstream, and devices resolved. There are **no** contributor
leaderboards or per-mapper rankings, consistent with §33.6's prohibition on volume
gamification.

## What keeps this compliant

SIG proposes; a human decides. Every change is reviewed individually by the mapper who
applies it, in their own account — so it is not an automated edit (ADR-055,
SIG-CONTRIB-016b), and the design objective is to minimise the human cost per
resolution (~one decision per device), never to maximise write volume (SIG-CONTRIB-017a).
