# Contributor safety policy

*Adopts docs/2_canonical_design_spec.md §34.3 (SIG-CONTRIB-005…008). This is the
safety **policy**; the contributor *system* — tiers, onboarding, revert mechanics,
anti-poisoning — is built later (P16.1, §34.1/34.2/34.4).*

People who contribute observations to SIG take on real risk. The infrastructure
this project documents is deployed by agencies and vendors that have already
applied takedown pressure to peer projects. SIG's obligation is to make
contributing as safe as the work allows — starting with collecting as little
about contributors as possible.

## Data minimisation — what SIG does not store (SIG-CONTRIB-005)

**What is not stored cannot be subpoenaed.** This is a design requirement, not a
preference. SIG **does not collect or retain**:

- **precise contributor geolocation** beyond the submitted observation itself;
- **contributor real names** as a requirement of contributing;
- **device identifiers**;
- **IP logs beyond a short operational window.**

The short operational window for abuse-prevention logs is the **PII-minimisation
window**: any IP or transient operational identifier is retained only long enough
to mitigate active abuse and is then discarded, never archived. The default for
every contributor-linked field is: do not collect it; if it must be collected to
function, expire it on the shortest window that works.

## Pseudonymity (SIG-CONTRIB-006)

**Pseudonymous contribution is fully supported**, including at the
trusted-reviewer tier. A contributor is never required to reveal a legal identity
to reach any level of trust in the project. Reputation attaches to a pseudonym,
not to a real name.

## Know-your-rights and no interference (SIG-CONTRIB-007)

SIG publishes **know-your-rights guidance for lawful photography in public**, and
this guidance is **jurisdiction-aware** — the rules differ by place, and the
guidance says so rather than offering a single false global answer.

SIG **explicitly instructs contributors not to trespass, not to tamper, and not
to interfere** (non-goal N5). Every observation SIG wants can be made lawfully,
from public space. Nothing in this project asks a contributor to break the law or
to touch, obstruct, or disable equipment, and any submission that appears to have
required doing so is out of scope.

## If a contributor is detained, arrested, or harassed (SIG-CONTRIB-008)

SIG maintains a **published policy for what it does if a contributor is detained,
arrested, or harassed in connection with contributing.** It states:

- **Who to contact** — a named, monitored contact path for contributors in
  trouble, and the legal-defence resources SIG has identified in advance
  (SIG-GOV-013).
- **What SIG will disclose** — SIG will resist compelled disclosure to the extent
  the law allows, and because of the data-minimisation posture above there is, by
  design, very little for SIG to disclose in the first place.
- **What SIG will not disclose** — SIG will not voluntarily hand over
  contributor-identifying information, and does not retain the categories of data
  (precise location history, device ids, durable IP logs) that would make a
  contributor identifiable.
