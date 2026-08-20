# Appendix E — Glossary

Terms are defined as SIG uses them. Where SIG's usage differs from common usage, the difference is
stated, because several of these differences are load-bearing.

| Term | Definition |
|---|---|
| **Agreement** | One of the three epistemic fields (§10.7): how much the admissible evidence disagrees. Independent of *support*. |
| **Artifact** | An addressable thing within a source whose *content may change* but whose identity does not (§10.2). A portal page is one artifact with many captures. |
| **Capability** | What an operator can *do*, expressed `verb.object.scope` (§11.6). Distinct from Technology (what kind of machine) and ConfigurationState (how it is tuned). |
| **Capture** | The immutable bytes SIG obtained at one instant, content-addressed. Never edited; a redaction is a new capture (§10.2). |
| **Claim** | An assertion with a subject, predicate, value, preserved raw value, temporal dimensions, evidence set, and epistemic axes (§10.3.5). The substance of the graph. |
| **Configured access** | The system is *set up* to permit something. Says nothing about whether anyone used it (§12.2). |
| **Contradiction** | A materialized entity recording a disagreement, with a lifecycle and a severity (§31). Resolution never deletes it. |
| **Coverage record** | A queryable record of *absence*, distinguishing "not researched" from "searched and found nothing" and naming the sources searched (§32.1). |
| **Currency (`C`)** | How stale a claim is *relative to its predicate's volatility* (§28.3). Derived at query time, never stored. |
| **Declared policy** | Someone said something is permitted or forbidden. Distinct from configuration and from use (§12.2). |
| **Derivative Database** | An ODbL term. A database built on OSM content such that share-alike attaches (§42.3). |
| **Directness (`D`)** | How directly *this artifact genre* supports *this predicate* (§10.5). `D6` means non-probative — excluded, not down-weighted. |
| **Dossier** | The per-jurisdiction public artifact; the project's primary deliverable (§39.2). |
| **EDTF** | Extended Date/Time Format. How SIG stores uncertain and open-ended dates without inventing precision (§16.7). |
| **Evidence set** | The artifacts bearing on a claim, each with a role — including `contradicts` (§10.3.6). A claim does not have "a source". |
| **Independence class** | A group of claims sharing an upstream origin. Corroboration is counted per class, never per claim (§10.8). |
| **Inference** | A derived fact at L4, in a separate namespace, labelled everywhere, recomputable and droppable (§30). |
| **Observation time (T2)** | When the *source* observed the fact. Never defaulted from publication or retrieval time (§9.2). |
| **Observed use** | Someone actually did something. Distinct from configured access (§12.2). |
| **Produced Work** | An ODbL term: an image, PDF, or printed map — not intended for data extraction. Vector tiles are *not* Produced Works (§42.3). |
| **Reliability (`R`)** | A property of the *publisher and its method*, assigned once per source with written justification (§10.4). Not re-judged per claim. |
| **Resolution** | A stored decision record — value, confidence fields, rationale, supporting and dissenting claims, ruleset version, author (§16.4). Not a view. |
| **Sensitivity class** | `C1`–`C5`, governing published coordinate precision, assessed at the *role* level (§43.3). |
| **Support** | One of the three epistemic fields: how strongly the *winning value* is evidenced. Independent of agreement (§10.7). |
| **Suppression** | Removing material from public surfaces while retaining it internally. A distinct primitive from deletion (§45.4). |
| **Transaction time (T5)** | When SIG recorded a belief, and when it stopped. Closed only when SIG corrects *itself*, never when the world changes (§9.2). |
| **UNRESOLVED** | A legitimate, publishable outcome — not an error and never hidden (§28.5). |
| **Valid time (T1)** | When a fact was true in the world. Never populated by inference at ingestion (§9.2). |
| **Weight (`W`)** | `W0`–`W4`, composed from `R`, `D`, `I`, `C` by a published ordinal table (§10.6). |
| **Windowed predicate** | A measurement *of* a period. It becomes history, not staleness, when the period passes (§28.3). |
