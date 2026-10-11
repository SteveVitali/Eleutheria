<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
     carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42. -->

# SIG-ONTO-060 scope-list amendment proposal (P35.14a — proposal only, not applied)

**Status:** proposal, **not applied**. Widening a closed vocabulary relaxes a MUST-shaped
list, and a relaxation of a closed list needs operator words — this document carries the
evidence and the proposed amendment; `capability.yaml` and the spec source are unchanged.

## Evidence — the realised enum vs the declared scope list

Read from `ontology/vocab/capability.yaml` (the ontology's own realised capability
enum, 45 slugs at v1, `verb.object.scope` grammar, §11.6 / SIG-ONTO-023).

Declared scope list (§11.6 / §13.2, mirrored in `capability.yaml`'s `scopes:`):

```
own, partner, state, region, national, commercial, subject
```

Realised scopes in the 45 committed slugs:

```
account, autonomous, commercial, custom, federal, logical, national, officer,
own, partner, physical, private_camera, public, region, required, rf, state,
subject, to_federal, to_partner, to_vendor
```

**15 of the 45 realised slugs use scopes outside the declared list:**

| slug | realised scope |
|---|---|
| `alert.hotlist.federal` | federal |
| `alert.hotlist.custom` | custom |
| `view.livestream.private_camera` | private_camera |
| `view.livestream.officer` | officer |
| `control.ptz.private_camera` | private_camera |
| `dispatch.uas.autonomous` | autonomous |
| `extract.device.logical` | logical |
| `extract.device.physical` | physical |
| `extract.cloud.account` | account |
| `locate.handset.rf` | rf |
| `disclose.results.to_partner` | to_partner |
| `disclose.bulk.to_vendor` | to_vendor |
| `disclose.audit.public` | public |
| `disclose.results.to_federal` | to_federal |
| `audit.case_code.required` | required |

The conflict is structural, not editorial: the closed scope axis cannot express
*direction* (`to_partner`, `to_federal`, `to_vendor` — who receives, which is the
civil-liberties question in `disclose.*`), *subject classes* (`private_camera`,
`officer`, `account`), or *substrates* (`logical`, `physical`, `rf`, `autonomous`,
`required`, `custom`, `federal`, `public`). The vocabulary already realised the
richer grammar; the spec's shorter list is the part that is wrong.

## Proposed amendment (for operator decision)

Replace the closed scope enumeration in §11.6 (and its §13.2 restatement) with:

> Scopes: `own`, `partner`, `state`, `region`, `national`, `commercial`,
> `subject`, `federal`, `custom`, `officer`, `private_camera`, `account`,
> `logical`, `physical`, `rf`, `autonomous`, `public`, `required`, plus the
> directed set `to_partner`, `to_federal`, `to_vendor`. Directed scopes
> (`to_*`) name the *recipient* of a `disclose`-class capability and MUST NOT be
> conflated with the undirected jurisdiction scopes.

The amendment is a relaxation: it widens what a conforming slug may name, and it
is exactly the set the committed vocabulary already uses — it introduces no new
scope atom beyond the realised enum. Under the repository's own rules a closed-
list relaxation is a **waiver-shaped change requiring operator words**
(SIG-ENG-041 / ADR-150's spec-amendment posture): the spec source
(`docs/research/_meta/spec_src/`) is edited only after the operator approves,
and the change is recorded in an ADR — never silently applied by a ticket.

## Non-application record

- `ontology/vocab/capability.yaml`'s `scopes:` field is left as committed
  (`own, partner, state, region, national, commercial, subject`); the 15
  out-of-list slugs are the existing realised vocabulary and were registered
  under earlier tickets — this row changes nothing about them.
- No spec source is edited (`docs/2_canonical_design_spec.md` is generated;
  the proposal above is the artifact the operator decides on).
- Decision requested: approve the scope-list widening exactly as proposed, or
  direct a narrower restructuring (e.g. splitting direction from jurisdiction
  into a second axis — a larger grammar change, also operator's call).
