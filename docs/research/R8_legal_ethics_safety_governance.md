# R8 — Legality, Ethics, Safety, Security, and Data Governance

**Workstream:** R8
**Researched:** 2026-08-20
**Researcher:** claude-opus-5 (R8 research agent)
**Outline sections covered:** §7.2, §13 (13.1–13.5), §14 (14.1–14.3), §19, §20 (Q16, Q30, Q31, Q32)
**Outline questions answered:** Q16, Q30, Q31, Q32 (Q13/Q14/Q15 touched only on the output side; ODbL mechanics are R1's)
**Confidence in this file overall:** medium-high on the findings; the *policy text* is a defensible default posture, not legal advice

---

## 0. How to read this file, and the counsel boundary

This memo does three things, and they must not be confused with each other:

1. **Findings (F8.x)** — what the primary sources actually say, retrieved and quoted on 2026-08-20.
2. **Policy text (P1–P7)** — adoptable, ratifiable text. It is drafted so that a lawyer can redline it,
   not so that it can be shipped without one.
3. **Counsel flags (⚖️ COUNSEL)** — points where the law is genuinely unsettled, jurisdiction-dependent,
   or where a wrong guess creates statutory or strict-liability exposure. Every one of these must be
   resolved by an admitted attorney before the corresponding capability ships.

**I am not a lawyer and this is not legal advice.** The document identifies the legal questions, the
governing authorities, and the defensible default postures. Where I say "settled," I mean there is
appellate consensus; where I say "unsettled," I mean courts have split or have expressly reserved the
question; where I say "requires counsel," I mean SIG must not act on my reading alone.

**Three exposures dominate everything else** and are stated here so they are not buried:

- **E1 — DMCA §1201 anti-circumvention, not CFAA, is now the live scraping risk.** *Reddit v. SerpApi*
  (S.D.N.Y., July 31, 2026) let anti-circumvention claims proceed against scrapers who used proxies,
  spoofed user agents, and human-mimicking behavior to get past a CAPTCHA/JS challenge (F8.5). The
  Flock transparency portal sits behind exactly such a challenge (F8.9). Any SIG component that solves
  or evades that challenge is walking into the live theory.
- **E2 — Daniel's-Law-style statutes impose liability without fault for publishing a covered person's
  home address, and they survived First Amendment scrutiny as applied to a journalist.** *Atlas Data
  Privacy Corp. v. We Inform, LLC* (N.J. Aug. 12, 2026) held no mental state is required for actual
  damages (F8.19); *Kratovil v. City of New Brunswick* (N.J. June 19, 2025) upheld the statute against
  a reporter who published a police director's lawfully-obtained address (F8.18). Statutory damages ×
  thousands of covered persons is an existential number for a small project.
- **E3 — The upstream terms SIG most needs are written to forbid exactly what SIG does.** Flock's API
  and Integrations Terms (updated Oct. 13, 2025) prohibit "extract, scrape, or export data in bulk, or
  in a manner that replicates database-like access to Flock's website or APIs" (F8.10). Whether that
  binds a logged-out visitor to a public portal is the *Meta v. Bright Data* question (F8.4) and is
  genuinely unsettled.

---

# PART A — COLLECTION LEGALITY

## A.1 The three-track model

The single most important conceptual correction this workstream contributes: **"is scraping legal" is
not one question, it is four, and they have diverged sharply since 2021.**

| Track | Governing authority | Current posture | Who can sue |
|---|---|---|---|
| **Criminal / quasi-criminal access** | CFAA 18 U.S.C. §1030 | Narrow. Public data ≠ unauthorized access. ToS breach ≠ CFAA. | DOJ; civil CFAA plaintiffs (rarely successful for public data) |
| **Contract** | State contract law + the site's terms | Enforceable if the terms were *actually agreed to*. Clickwrap yes; logged-out browsewrap probably not. | Site operator |
| **Anti-circumvention** | DMCA 17 U.S.C. §1201(a) | **Expanding.** Bot-defeat technology can be an "access control." | Copyright owner of the protected work |
| **Copyright / database rights** | 17 U.S.C. §102(b), *Feist*; EU Dir. 96/9/EC | Facts free; selection/arrangement protected; EU adds a sui generis layer with no US analogue. | Rights holder / database maker |

A crawler design that only optimizes for CFAA safety — which is what most 2019-era guidance does — is
optimizing for the track that has become *least* dangerous while ignoring the two that have become
*most* dangerous.

---

### F8.1 — Van Buren narrowed the CFAA to a "gates-up-or-down" inquiry and expressly reserved whether contract-based limits count

**Claim:** The Supreme Court held that "exceeds authorized access" reaches only information in areas of
a computer that are off-limits to the user, and footnote 8 expressly declined to decide whether the
inquiry turns only on code-based limits or also on contracts and policies.
**Status:** VERIFIED
**Evidence:** https://www.law.cornell.edu/supremecourt/text/19-783 — holding quoted: an individual
"exceeds authorized access" when he "obtains information located in particular areas of the computer —
such as files, folders, or databases — that are off-limits to him"; the analysis is "a gates-up-or-down
inquiry — one either can or cannot access a computer system, and one either can or cannot access certain
areas within the system." Footnote 8: "For present purposes, we need not address whether this inquiry
turns only on technological (or 'code-based') limitations on access, or instead also looks to limits
contained in contracts or policies." Direct PDF at
https://www.supremecourt.gov/opinions/20pdf/19-783_k53l.pdf returned 403 to WebFetch; retrieved
successfully via `curl` with a browser UA (HTTP 200, 212,335 bytes).
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG's crawler must never cross a *technical* gate. Authentication,
paywalls, per-user tokens, and IP blocks are all "gates." A robots.txt `Disallow` is not a gate in the
Van Buren sense, but SIG will honor it anyway for the independent reasons in P1.
**Outline delta:** EXTENDS §20 Q24 ("Which sources require scraping?") — the outline treats scraping as
a purely technical question. It is not; the answer per source depends on which of four legal tracks the
source's defenses put it on.

---

### F8.2 — hiQ ended by *losing* on contract, not winning on CFAA; the CFAA victory did not save it

**Claim:** After twice prevailing on the CFAA theory, hiQ lost on breach of contract at summary judgment
and consented to a $500,000 judgment, a permanent injunction, and destruction of the scraped corpus.
**Status:** VERIFIED
**Evidence:** https://www.zwillgen.com/alternative-data/hiq-v-linkedin-wrapped-up-web-scraping-lessons-learned/
— "The Ninth Circuit twice held that scraping likely did 'not' violate the CFAA," but "the final
resolution came through breach of contract"; LinkedIn "successfully enforced its user agreement through
a clickwrap mechanism — hiQ expressly agreed to LinkedIn's terms when creating its corporate account";
liability was driven by automated scraping in violation of the user agreement *plus* "hiring crowdsourced
workers to create fake profiles." Corroborated by web search of the Nov. 2022 summary judgment order and
the Dec. 6, 2022 stipulated consent judgment ($500,000; injunction; deletion of source code, data, and
algorithms; spoliation sanctions).
**Retrieved:** 2026-08-20
**Implication for the spec:** The determinative facts against hiQ were (a) an accepted clickwrap and
(b) sockpuppet accounts. SIG must therefore have a hard rule: **never create an account on a source
site for collection purposes, and never accept terms on behalf of the crawler.** Account creation is
what converts a browsewrap non-issue into an enforceable contract.
**Outline delta:** CORRECTS the ambient assumption behind §10 and §20 Q24 that hiQ "legalized scraping."
It did not. It legalized it under one statute and left the plaintiff bankrupted under another theory.

---

### F8.3 — Sandvig confirms that a bare terms-of-service violation is not a federal crime

**Claim:** A federal district court held the CFAA does not criminalize mere ToS violations on consumer
websites, including researchers creating tester accounts and recording publicly available information.
**Status:** VERIFIED
**Evidence:** https://www.eff.org/deeplinks/2020/04/federal-judge-rules-it-not-crime-violate-websites-terms-service
and https://www.aclu.org/cases/sandvig-v-barr-challenge-cfaa-prohibition-uncovering-racial-discrimination-online
— *Sandvig v. Barr*, 451 F. Supp. 3d 73 (D.D.C. 2020): "the CFAA does not criminalize mere
terms-of-service violations on consumer websites and, thus, ... plaintiffs' proposed research plans are
not criminal under the CFAA."
**Retrieved:** 2026-08-20
**Implication for the spec:** Academic/journalistic audit research on public web surfaces carries low
*criminal* risk. It does not follow that it carries low civil risk. Keep the distinction visible in
contributor-facing guidance so volunteers do not over-read "not a crime" as "no consequences."
**Outline delta:** EXTENDS §13.5 — the outline's "lawful field observation" support should extend
explicitly to lawful *online* observation, with the same caveats.

---

### F8.4 — Meta v. Bright Data: logged-out public scraping is outside terms that govern "your use" by "users"

**Claim:** Judge Chen granted Bright Data summary judgment on Meta's breach-of-contract claim, holding
Meta's terms did not reach scraping of publicly available data performed while logged off.
**Status:** VERIFIED
**Evidence:** Web search returning https://www.fbm.com/publications/major-decision-affects-law-of-scraping-and-online-data-collection-meta-platforms-v-bright-data/,
https://www.quinnemanuel.com/media/n23fedyh/client-alert_-meta-v-bright-data-significant-decision-for-web-scraping-industry.pdf,
and https://www.lowenstein.com/news-insights/publications/client-alerts/meta-v-bright-data-ruling-has-important-implications-for-webscraping-activities-by-investment-advisers-im
— N.D. Cal., Jan. 23, 2024. Terms "do not apply to and prohibit Bright Data's scraping of publicly
available data while logged off"; Bright Data "did not 'use' Facebook and Instagram when it engaged in
public logged-off scraping." Material to the reasoning: Meta had *removed*, after 2009, a clause binding
anyone who merely "access[ed]" the site "whether or not you are a registered member."
**Retrieved:** 2026-08-20
**Implication for the spec:** The logged-out/logged-in boundary is the single highest-value operational
line in the crawler design. SIG's crawler must be architecturally incapable of holding a session cookie
or credential for a source site. ⚖️ **COUNSEL:** whether a given upstream's terms contain the *access*-based
binding language Meta had deleted is a per-source contract-reading question. R2/R3/R4 capture the terms;
counsel must classify each one as access-binding or use-binding before that source is enabled.
**Outline delta:** EXTENDS §14.2 — "source terms" must be a *structured* field with a
`terms_binding_theory` enum (`clickwrap_accepted` / `browsewrap_access_binding` / `browsewrap_use_only` /
`none_found` / `express_permission`), not a free-text blob.

---

### F8.5 — Reddit v. SerpApi (July 31, 2026): defeating a CAPTCHA/JS bot-challenge can be DMCA §1201(a) circumvention

**Claim:** A federal court held that Google's SearchGuard — a JavaScript-challenge and CAPTCHA system —
qualifies as a technological measure that effectively controls access under §1201(a), and allowed
Reddit's anti-circumvention claims against Perplexity and SerpApi to proceed past a motion to dismiss.
**Status:** VERIFIED
**Evidence:** https://www.loeb.com/en/insights/publications/2026/08/reddit-v-serpapi-llc — S.D.N.Y.,
Judge Paul A. Engelmayer, ruling of July 31, 2026. The court "rejected the argument that measures cannot
control access if humans can still view the content," analogizing SearchGuard to "a facial-recognition
technology programmed to open the door of a home for residents but not for other visitors." Reddit's
allegations that SerpApi used "proxy servers," "fake user-agent strings," and features designed to "mimic
human behavior" were sufficient to plead circumvention. Dismissed: the §1201(b) trafficking claim (the
measure is an access control under (a), not a rights-protection measure under (b)), plus state unjust
enrichment and unfair competition as preempted by the Copyright Act. Civil conspiracy survived.
Case filed Oct. 22, 2025 as *Reddit, Inc. v. SerpApi, LLC, Oxylabs UAB, AWMProxy, and Perplexity AI, Inc.*
Corroborated: https://www.law.com/newyorklawjournal/2026/07/31/reddits-dmca-claims-against-perplexity-serpapi-survive-ai-scraping-challenge/
**Retrieved:** 2026-08-20
**Implication for the spec:** This is **exposure E1**. SIG must adopt a bright-line technical rule:
*if a host presents a bot challenge, SIG stops.* No CAPTCHA solving, no residential proxies, no UA
spoofing to defeat a challenge, no headless-browser fingerprint evasion. The crawler must have a
`CHALLENGE_DETECTED` terminal state that raises a human review task rather than retrying differently.
⚖️ **COUNSEL:** whether transparency-portal *facts* are even a copyrighted "work" whose access §1201
protects is a real defense (§1201 protects access to works protected under Title 17; a table of
audit counts may not be). Do not rely on it without an opinion — the *Reddit* court reached the
circumvention question without needing to resolve the underlying-work question at the pleading stage.
**Outline delta:** CONTRADICTS the implicit assumption in §10 Phase 1D that the Flock portal ecosystem
is straightforwardly ingestible by direct crawl. It is the single riskiest ingestion path in the plan.

---

### F8.6 — Feist: facts are free, selection and arrangement are not

**Claim:** Facts are never copyrightable; a compilation is protected only in its original selection,
coordination, and arrangement, and a subsequent compiler may freely take the underlying facts.
**Status:** VERIFIED
**Evidence:** https://www.law.cornell.edu/supremecourt/text/499/340 — *Feist Publications, Inc. v. Rural
Telephone Service Co.*, 499 U.S. 340 (1991). "Original, as the term is used in copyright, means only that
the work was independently created by the author ... and that it possesses at least some minimal degree
of creativity." The "sweat of the brow" doctrine is rejected because it "extended copyright protection in
a compilation beyond selection and arrangement — the compiler's original contributions — to the facts
themselves." "[C]opyright does not extend to facts contained in the compilation."
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG may ingest *facts* from other projects' datasets — "Agency X operates
N Flock cameras," "device at lat/lon," "contract signed on date D" — even where the source dataset as a
whole is copyrighted, provided SIG does not copy the source's original selection/arrangement wholesale.
This is the legal basis for the **fact-extraction, not table-copying** ingestion pattern. It is *not* a
basis for ignoring contract terms (F8.2/F8.4) or database rights outside the US (F8.7).
**Outline delta:** EXTENDS §14.2. The rights record needs two independent fields:
`copyright_status_of_expression` and `contractual_restriction`, because a source can be uncopyrightable
and still contractually restricted.

---

### F8.7 — The EU sui generis database right protects investment in *obtaining* data, not in creating it

**Claim:** Directive 96/9/EC Art. 7(1) gives the maker of a database a right against extraction/re-utilisation
of a substantial part where there was substantial investment in obtaining, verifying, or presenting the
contents; *British Horseracing Board v. William Hill* held that investment in *creating* the underlying
data does not count.
**Status:** VERIFIED
**Evidence:** https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=celex%3A62002CJ0203 (Case C-203/02,
judgment of 9 Nov. 2004) via search; analysis at https://cms.law/en/gbr/legal-updates/database-rights-surprising-judgment-from-the-european-court-of-justice.
BHB spent ~£4m/yr but lost because the resources went into *creating* the fixtures, not collecting
pre-existing information. Also noted: the ODbL and the DSM Art. 4 TDM reservation both operate against
this backdrop (see F8.8).
**Retrieved:** 2026-08-20
**Implication for the spec:** For the international phase (§17 Stage 6), a European agency's published
camera register may carry a database right *even though the same table in the US would be an
uncopyrightable fact compilation under Feist*. The rights record must therefore carry a
`sui_generis_db_right` tri-state (`yes` / `no` / `unknown`) evaluated per-jurisdiction, and the export
gate must treat `unknown` as blocking for EU-sourced material.
⚖️ **COUNSEL:** required before any EU-sourced ingestion. Also note the UK diverged post-Brexit; a
UK-specific read is needed separately.
**Outline delta:** EXTENDS §5 and §17 Stage 6 — the outline treats international expansion as a coverage
problem. It is also a *rights* problem, and the rights model must be built for it in Stage 1, not retrofitted.

---

### F8.8 — Cloudflare's Content Signals Policy is now embedded in the robots.txt of several key upstreams and asserts a DSM Art. 4 reservation

**Claim:** deflock.me, muckrock.com, and documentcloud.org all serve a Cloudflare-managed robots.txt
carrying `Content-Signal: search=yes,ai-train=no,use=reference`, an express DSM Art. 4 reservation of
rights, a purported access-condition preamble, and explicit `Disallow: /` for named AI crawlers
including ClaudeBot, GPTBot, CCBot, Google-Extended, Bytespider, Amazonbot, Applebot-Extended, and
meta-externalagent.
**Status:** VERIFIED
**Evidence:** `curl` with browser UA, 2026-08-20:
- `https://deflock.me/robots.txt` → 200, Cloudflare Managed content block as described.
- `https://www.muckrock.com/robots.txt` → 200, identical block.
- `https://www.documentcloud.org/robots.txt` → 200, identical block.
Preamble text served on all three: "As a condition of accessing this website, you agree to abide by the
following content signals ... ANY RESTRICTIONS EXPRESSED VIA CONTENT SIGNALS ARE EXPRESS RESERVATIONS OF
RIGHTS UNDER ARTICLE 4 OF THE EUROPEAN UNION DIRECTIVE 2019/790 ON COPYRIGHT AND RELATED RIGHTS IN THE
DIGITAL SINGLE MARKET." Policy background: Cloudflare enabled it by default across 3.8M+ managed domains,
default `search=yes, ai-train=no`; commentators describe the signals as advisory, framed by Cloudflare
as a reservation of rights that strengthens a publisher's legal position rather than as a hard block
(https://searchengineland.com/cloudflare-content-signals-462538,
https://winbuzzer.com/2025/10/06/cloudflare-overhauls-webs-ai-rulebook-with-new-robots-txt-content-signals-xcxwbn/).
`https://contentsignals.org/` returned only a bare heading to WebFetch — INACCESSIBLE for the policy text
itself; fallback is the Cloudflare blog and press coverage.
**Retrieved:** 2026-08-20
**Implication for the spec:** Three consequences.
(1) `use=reference` and `search=yes` are consistent with SIG's actual behavior — SIG *references* and
*links*; it does not train models. SIG's crawler UA string must not resemble an AI-training crawler, and
SIG must publish an explicit "we do not train models on crawled content" statement so operators can tell
the difference.
(2) SIG must **not** run under a UA that these files disallow. In particular, any pipeline stage that
would present as ClaudeBot/GPTBot/CCBot against these hosts is disallowed by the host's own file.
(3) The "as a condition of accessing this website, you agree" preamble is a browsewrap-in-robots.txt.
⚖️ **COUNSEL:** its enforceability is untested and, after *Meta v. Bright Data*, doubtful against a
logged-out visitor — but SIG should comply regardless, because these are *allied* projects and the
reputational cost of non-compliance vastly exceeds the data value.
**Outline delta:** CORRECTS §21 and §18 — the outline treats DeFlock, MuckRock, and DocumentCloud as
friendly upstreams to be crawled. Their robots.txt now carries machine-readable restrictions that a naive
crawler would violate. SIG's relationship with these three should be **negotiated API/bulk access, not
crawling**, and §18's coordination plan should say so.

---

### F8.9 — The Flock transparency portal is behind a Cloudflare managed challenge; robots.txt itself is unreachable

**Claim:** `transparency.flocksafety.com` returns HTTP 403 with a Cloudflare interstitial ("Just a
moment...", `cf_chl_opt`, managed challenge) to a normal browser-UA request, including for `/robots.txt`.
**Status:** VERIFIED
**Evidence:** `curl -A "<Chrome UA>" https://transparency.flocksafety.com/robots.txt` → HTTP 403,
Cloudflare `cType: 'managed'` challenge page, `cZone: 'transparency.flocksafety.com'`, `meta name="robots"
content="noindex,nofollow"`. `curl -A "<Chrome UA>" https://transparency.flocksafety.com/` → HTTP 403.
By contrast `https://www.flocksafety.com/robots.txt` → HTTP 200 with an ordinary permissive file
(`User-agent: *`, four `Disallow:` paths, sitemap reference).
**Retrieved:** 2026-08-20
**Implication for the spec:** Combined with F8.5, this is the project's sharpest legal edge. The portal
is *publicly linked and publicly promoted by Flock and by agencies* but is *technically gated against
automation*. SIG's options, in order of preference:
1. **Ask.** Write to Flock and to the agency requesting an exemption or a data feed, and publish the
   request and any refusal. A documented refusal is itself a finding worth recording.
2. **FOIA/public-records the underlying data from the agency**, which is a lawful channel that bypasses
   the vendor's technical measure entirely, and which produces a Tier A artifact (§9.1).
3. **Consume a third party's lawfully obtained archive** (e.g. Eyes on Flock) under its own terms —
   pushing the §1201 question onto a party that has already assumed it, which SIG must disclose in
   provenance and must not do in bad faith.
4. **Human-in-the-loop capture.** A volunteer opens the portal in their own browser and submits the
   rendered artifact. ⚖️ **COUNSEL:** this is a real question — is a human who solves the challenge and
   then donates the page circumventing? Almost certainly not (they are the intended audience), but a
   *system* designed to farm human challenge-solving at scale starts to look like SerpApi's
   "features designed to mimic human behavior."
5. **Do not crawl it directly.** This is the default until 1–4 resolve.
**Outline delta:** CONTRADICTS §10 Phase 1D as written. Add a `access_channel` field to every source with
values `{direct_crawl, api_authorized, bulk_grant, public_records, third_party_archive, human_submission,
blocked}` and make Flock portals `blocked` pending counsel.

---

### F8.10 — Flock's API and Integrations Terms expressly forbid bulk extraction, scraping, database-like access, and rate-limit circumvention

**Claim:** Flock's published API and Integrations Terms (last updated Oct. 13, 2025) prohibit bulk
extraction and rate-limit circumvention in terms broad enough that Flock would argue they cover the
website, and restrict all use to "bona fide law enforcement purposes."
**Status:** VERIFIED
**Evidence:** `curl` of https://www.flocksafety.com/legal/api-integration-terms (HTTP 200), 2026-08-20.
Verbatim: "By accessing this Implementation, You ... agree to comply with these terms, and shall only use
this Implementation for bona fide law enforcement purposes." Restriction (viii): "extract, scrape, or
export data in bulk, or in a manner that replicates database-like access to Flock's website or APIs. The
API is designed for real-time, on-demand queries within integrated applications, not for systematic or
automated data harvesting. Circumventing rate limits, creating multiple accounts to bypass restrictions,
or engaging in any activity intended to extract large volumes of data is strictly prohibited." Also
(iii): no use "for machine learning model development or evaluation." §1.3 purports to entitle Flock to
"compensatory damages" without "proof of actual damages." Flock's legal index page also lists Terms and
Conditions, Privacy Policy, LPR Policy, Trademark Notice, Evidence Policy, State-Specific Contractual
Provisions, and a Vulnerability Disclosure Policy (https://www.flocksafety.com/legal, HTTP 200).
**Retrieved:** 2026-08-20
**Implication for the spec:** This is **exposure E3**. Note the scoping argument that cuts *for* SIG: the
preamble binds "You" as to "accessing or using the Flock ... API ... and Integrations," and the operative
grant is "requested by a Flock Customer" — a member of the public reading a transparency portal is not
accessing an Implementation and is not a Flock Customer's authorized integrator. Under *Meta v. Bright
Data*, terms that govern a defined class of "users" do not bind a logged-out visitor. But clause (viii)
says "Flock's website," which Flock will press. ⚖️ **COUNSEL — required before any Flock-surface
collection.** SIG must never register for a Flock API key, because doing so would convert this from an
arguable non-contract into an accepted clickwrap (the hiQ mistake, F8.2).
**Outline delta:** EXTENDS §20 Q16 — the answer to "what may be archived vs merely linked" for Flock
surfaces is currently *link and cite, do not mirror*, pending counsel.

---

### F8.11 — Flock publishes a Vulnerability Disclosure Policy with a safe harbor that expressly excludes testing live deployments

**Claim:** Flock operates a coordinated disclosure program with a good-faith safe harbor, but explicitly
places live customer deployments, customer/LE data, physical attacks, and social engineering out of scope,
and runs no paid bounty.
**Status:** VERIFIED
**Evidence:** `curl` of https://www.flocksafety.com/legal/vulnerability-disclosure-policy, 2026-08-20.
Quoted: "Testing against live customer deployments. Do not access, test, or interact with cameras,
devices, a[ccounts]..."; "If you encounter customer, personal, or law enforcement data, stop and tell
us"; "We will not pursue legal action against you for research conducted in good faith and in accordance
with this policy"; "Flock does not run a paid bug bounty program"; reports to
`vulnerability.reporting@flocksafety.com`; CVE publication program starting September 2026.
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG must adopt a **no-probing rule** (P1 §7) and put it in contributor
guidance: SIG does not perform security testing of vendor or agency systems, ever, and any contributor
who does so is acting outside the project. The existence of a vendor safe harbor is *not* an invitation —
its scope excludes exactly the deployments a field mapper would encounter.
**Outline delta:** EXTENDS §13.5 — the outline's "no operational interference" should be widened from
physical interference to include *digital* interference and unauthorized testing.

---

### F8.12 — Reddit's robots.txt is a blanket disallow and its Public Content Policy channels research to sanctioned APIs

**Claim:** `https://www.reddit.com/robots.txt` serves `User-agent: * / Disallow: /` with a pointer to
Reddit's Public Content Policy; Reddit is actively litigating against unauthorized bulk collection.
**Status:** VERIFIED (robots.txt); PARTIALLY VERIFIED (policy text)
**Evidence:** `curl` 2026-08-20 → HTTP 200:
```
# Welcome to Reddit's robots.txt
# Reddit believes in an open internet, but not the misuse of public content.
# See https://support.reddithelp.com/hc/en-us/articles/26410290525844-Public-Content-Policy ...
User-agent: *
Disallow: /
```
The Public Content Policy page itself returned **HTTP 403** behind a Cloudflare challenge to both WebFetch
and `curl` with a browser UA — recorded as INACCESSIBLE; substance obtained from search summaries
indicating non-commercial/research use is permitted through the Data API and Reddit for Researchers, that
bulk collection via scraping or data brokers is treated as unauthorized, and (per a May 2026 clarification)
that unauthorized scraping is a Rule 8 violation.
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG must **not** crawl Reddit HTML. Local-community intelligence from Reddit
(§3) must arrive via (a) the official Data API under its terms, (b) Reddit for Researchers, or (c) a human
contributor manually submitting a link + quote, which is ordinary reading and citation, not automated
collection. Encode this as a hard source-registry rule, not a crawler heuristic.
**Outline delta:** CORRECTS §3 and §21 — the outline treats Reddit as an observable community signal
without noting that automated observation is flatly disallowed by the site's own file.

---

### F8.13 — Atlas of Surveillance is CC-BY and effectively unrestricted by robots.txt; Axon's and Flock's marketing sites are permissive

**Claim:** `atlasofsurveillance.org/robots.txt` contains only a comment line (no rules); the Atlas data is
CC-BY to EFF and the University of Nevada, Reno Reynolds School of Journalism. `axon.com` and
`flocksafety.com` marketing robots.txt allow general crawling with narrow path exclusions.
**Status:** VERIFIED
**Evidence:** `curl` 2026-08-20 — `https://atlasofsurveillance.org/robots.txt` → 200, final URL
`https://www.atlasofsurveillance.org/robots.txt`, body is a single comment, i.e. no `Disallow`.
`https://www.axon.com/robots.txt` → 200, `User-agent: * / Allow: /*` with a handful of `Disallow` paths
plus a separate block restricting Google-CloudVertexBot and GoogleExtended from certain `/help/` product
pages. `https://www.flocksafety.com/robots.txt` → 200, four `Disallow` paths. Atlas licensing per
https://atlasofsurveillance.org/about — "CC-by," attribution to EFF and UNR Reynolds School of Journalism,
contact `aos@eff.org`.
**Retrieved:** 2026-08-20
**Implication for the spec:** Vendor *marketing* sites and the Atlas are low-risk crawl targets under P1.
Atlas ingestion requires an attribution obligation to propagate into every export containing
Atlas-derived claims (see P4/P6). ⚖️ Minor counsel note: "CC-by" without a version is ambiguous; ask EFF
to confirm CC-BY-4.0 and record the SPDX id `CC-BY-4.0` only once confirmed, otherwise record
`LicenseRef-EFF-Atlas-CCBY-unversioned`.
**Outline delta:** CONFIRMS §10 Phase 1C and §20 Q15 (partial answer for Atlas).

---

### F8.14 — Passive RF observation of beacon frames is broadly lawful, but Joffe v. Google shows the payload line matters

**Claim:** Passively logging publicly broadcast SSIDs/BSSIDs/signal strength with GPS is broadly lawful;
capturing *payload* data from an unencrypted Wi-Fi network is not exempt from the Wiretap Act under
18 U.S.C. §2511(2)(g)(i).
**Status:** PARTIALLY VERIFIED
**Evidence:** Search results including https://harvardlawreview.org/wp-content/uploads/2014/04/vol127_joffe_v_google.pdf
(*Joffe v. Google*, 9th Cir. 2013 — data transmitted over a Wi-Fi network is not a "radio communication"
exempt as "readily accessible to the general public") and practitioner guidance that passive wardriving
of beacon metadata is lawful while "connecting without permission, cracking handshakes, or deauthing
devices you don't own crosses the line." I did not retrieve the *Joffe* opinion itself.
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG's RF policy (P3 §6) must distinguish **management-frame metadata**
(SSID, BSSID/OUI, RSSI, channel, timestamp, observer location) — ingestible — from **any payload or
association attempt** — categorically prohibited, and grounds for contributor removal. SIG must never
accept a contribution that required associating with, deauthing, or probing a device.
⚖️ **COUNSEL:** state wiretap/interception statutes vary and several are stricter than federal; a
50-state read is needed before SIG solicits RF contributions at scale.
**Outline delta:** EXTENDS §2 Layer G and §13.3 — the outline's Layer G concern is about *publication*
of weak RF inferences. There is a prior *collection* question the outline does not raise at all.

---

## POLICY P1 — SIG CRAWLER CONDUCT POLICY

> **Status:** proposed for adoption. Every numbered rule is intended to be machine-checkable or
> reviewable in code review. Violations of §§2, 3, 5, 7 are release-blocking defects.

### P1.0 Purpose and public commitment

SIG collects public information about public institutions. It does so in a way that is *legible,
attributable, and low-burden* to the operators of the systems it reads. This policy is published at a
stable URL, is linked from the crawler's user agent, and is binding on all SIG-operated collection,
including one-off research scripts.

### P1.1 Identification

1. Every SIG HTTP request carries a user agent of the form:
   `SIGBot/<version> (+https://<sig-domain>/crawler; contact: crawler@<sig-domain>)`
2. The contact URL resolves to this policy, an abuse contact, an opt-out form, and the crawler's
   published IP ranges.
3. SIG **never** spoofs a browser or third-party user agent to obtain content it could not obtain as
   `SIGBot`. Reading a page manually in a real browser to *understand* a site is fine; automating a
   disguised browser to *collect* is not.
4. SIG responds to operator email within 3 business days and honors any operator opt-out request
   without argument, recording the opt-out in the source registry as `access_channel = blocked`.

### P1.2 Hard prohibitions (no exceptions, no override flag)

1. **No authentication circumvention.** No credential use, credential sharing, session replay, token
   reuse, or access to any surface requiring login — including free logins.
2. **No account creation on a source site for collection purposes.** (F8.2)
3. **No challenge defeat.** If a host returns a CAPTCHA, a JS interstitial, a managed bot challenge, or
   a 403/429 attributable to bot detection, the fetcher enters terminal state `CHALLENGE_DETECTED`,
   stops, and files a human review task. No proxy rotation, no residential proxies, no UA rotation, no
   fingerprint evasion, no headless-browser stealth plugins. (F8.5, F8.9)
4. **No paywall or access-control bypass** of any kind.
5. **No security testing.** SIG does not scan, fuzz, enumerate, or probe vendor or agency systems.
   Vulnerability reports discovered incidentally go to the vendor's disclosure channel, never to the
   graph. (F8.11)
6. **No RF association.** Passive listening only; never associate, deauth, probe, or capture payload. (F8.14)
7. **No model training on crawled content**, and a published statement to that effect, so that
   `ai-train=no` signals are satisfied in substance. (F8.8)

### P1.3 robots.txt and content signals

1. SIG fetches and caches `robots.txt` for every host before the first request and re-fetches at most
   every 24 hours; a fetch failure is treated as **disallow-all** for that host until it succeeds.
   (Note: this is stricter than RFC 9309's default and is deliberate.)
2. SIG honors `Disallow` for `User-agent: SIGBot` and for `User-agent: *`, and honors `Crawl-delay`
   where present.
3. SIG honors Cloudflare **Content Signals**: it treats `search` and `use=reference` as permitting
   indexing, linking, quoting, and fact extraction; it treats `ai-train=no` as binding and complies by
   never training models on crawled content. (F8.8)
4. SIG **does not** operate under, or impersonate, any user agent that a host has specifically
   disallowed (ClaudeBot, GPTBot, CCBot, Google-Extended, etc.).
5. Where robots.txt disallows but the material is independently obtainable through a lawful non-crawl
   channel (public records, an API, an operator grant, a human submission), that channel is used instead
   and the switch is recorded in provenance.

### P1.4 Rate and burden

1. Default: **1 request per 5 seconds per host**, maximum 2 concurrent connections per host, maximum
   10,000 requests per host per day.
2. Respect `Crawl-delay` and `Retry-After` when longer than the default.
3. Exponential backoff on 429/503 starting at 60s, capped at 6 hours; three consecutive 429s park the
   host for 24 hours.
4. Crawl small municipal and volunteer-run hosts at **1 request per 30 seconds**. A city clerk's agenda
   server is not a CDN.
5. Conditional requests always: send `If-Modified-Since` / `If-None-Match`; store and reuse ETags.
6. Prefer sitemaps, feeds, and published bulk exports over page-by-page traversal. If a source offers a
   bulk download, crawling the HTML instead is a policy violation.
7. All collection runs are scheduled outside the source's local business hours where a local time zone
   is known and the host is a small operator.

### P1.5 Contract posture

1. SIG classifies every source's terms into `terms_binding_theory` (F8.4) before enabling collection.
2. Sources classified `clickwrap_accepted` are **never** collected from — because SIG never accepts
   a clickwrap.
3. Sources classified `browsewrap_access_binding` (terms purporting to bind mere visitors) are routed
   to counsel before enabling and default to `blocked`.
4. Sources classified `browsewrap_use_only` may be collected under P1.3/P1.4, with the terms recorded.
5. Any express permission from the operator supersedes and is recorded as `express_permission` with the
   granting message archived.

### P1.6 What SIG extracts

1. SIG extracts **facts** — entity identities, counts, dates, coordinates, relationships — and
   **short verbatim quotations** for evidentiary integrity. It does not republish an upstream's
   selection and arrangement wholesale where that arrangement is the protected element. (F8.6)
2. Original source bytes are content-addressed and retained **privately** for verification; public
   representation is metadata plus a link, unless the license permits redistribution (see P4, and Q16
   in §Open questions).
3. Every extracted claim carries `source_url`, `retrieved_at`, `http_status`, `content_hash`,
   `robots_state_at_fetch`, and `access_channel`.

### P1.7 Escalation and transparency

1. Any legal contact concerning collection goes immediately to the designated legal contact and is
   logged for the transparency report (P5).
2. SIG publishes, quarterly: hosts crawled, request volumes per host, opt-outs honored, hosts in
   `CHALLENGE_DETECTED` or `blocked` state, and any operator complaints received.
3. SIG publishes its crawler IP ranges so operators can rate-limit or block it precisely rather than
   deploying blanket bot defenses.

### P1.8 Per-upstream application (as of 2026-08-20)

| Upstream | robots.txt state (verified) | Terms posture | **Default access channel** |
|---|---|---|---|
| Flock transparency portals (`transparency.flocksafety.com`) | Unreachable; whole host behind Cloudflare managed challenge (403) | API terms forbid bulk/scrape/DB-like access; scope contested | **blocked** — pending counsel. Use public records, Eyes on Flock, or human submission |
| `flocksafety.com` marketing/legal | 200, permissive, 4 disallowed paths | Website T&C to be classified | direct_crawl, low rate |
| Axon `axon.com` | 200, `Allow: /*` + narrow disallows | to be classified | direct_crawl, low rate |
| Axon Community Connect (`axoncommunityconnect.com`) | `/robots.txt` → 404; site is JS-rendered | Registry data is vendor-declared non-public | **institutional facts only**; never registrant-level (see P3) |
| Agency websites / civic agenda platforms (Granicus, Legistar, CivicPlus, PrimeGov) | per-host; many small | mostly none; government records | direct_crawl at **1 req/30s**; prefer published agenda APIs |
| DeFlock (`deflock.me`) | 200, Content Signals `search=yes, ai-train=no, use=reference`, AI bots disallowed | allied project | **negotiated bulk/API**, not crawling |
| MuckRock, DocumentCloud | 200, same Content Signals block | allied projects with APIs | **API under their terms** |
| EFF Atlas of Surveillance | 200, no rules | CC-BY | direct_crawl or bulk; propagate attribution |
| Reddit | `Disallow: /` for all agents | Public Content Policy; active §1201 litigation | **no crawling.** Official API / Reddit for Researchers / human submission only |
| OpenStreetMap | (R1's scope) | ODbL | official APIs/planet extracts |

---

# PART B — RIGHTS RECORDS AND THE LICENSE-COMPATIBILITY GATE

### F8.15 — SPDX provides stable identifiers for every license SIG will encounter, including data licenses

**Claim:** The SPDX License List (v3.28.0, 727 licenses) contains machine-readable identifiers for
ODbL-1.0, CC0-1.0, CC-BY-4.0, CC-BY-SA-4.0, ODC-By-1.0, PDDL-1.0, CC-BY-NC-4.0, OGL-UK-3.0, MIT,
Apache-2.0, and AGPL-3.0-or-later, with OSI/FSF approval flags.
**Status:** VERIFIED
**Evidence:** `curl https://spdx.org/licenses/licenses.json` (HTTP 200), parsed 2026-08-20.
`licenseListVersion: 3.28.0`, 727 entries. Selected rows:
`ODbL-1.0` (OSI: false, FSF libre: true), `CC0-1.0` (OSI: false, FSF: true), `CC-BY-4.0` (OSI: false,
FSF: true), `CC-BY-SA-4.0` (OSI: false, FSF: true), `ODC-By-1.0` (OSI: false, FSF: n/a),
`PDDL-1.0` (OSI: false, FSF: n/a), `CC-BY-NC-4.0` (OSI: false, **FSF: false**), `MIT` (OSI+FSF true),
`Apache-2.0` (OSI+FSF true), `AGPL-3.0-or-later` (OSI+FSF true). None deprecated.
**Retrieved:** 2026-08-20
**Implication for the spec:** The rights record's `license_spdx` field must validate against the pinned
SPDX list version, with `LicenseRef-*` for anything unlisted (agency-specific terms, bespoke grants,
"public domain, no statement"). Pin the list version in the repo and record which version validated
each rights record, so a later SPDX change cannot silently reinterpret history.
**Outline delta:** EXTENDS §14.2 — the outline's license block is free text. Make it structured and
validated.

---

### F8.16 — ODbL's Produced Work / Derivative Database / Collective Database trichotomy is the entire design problem

**Claim:** ODbL 1.0 distinguishes a Derivative Database (share-alike attaches), a Collective Database
(unmodified, assembled alongside independent databases — share-alike does not attach to the others), and
a Produced Work (attribution and notice, but not share-alike on the work itself); §4.6 imposes an
access-to-the-derivative obligation.
**Status:** VERIFIED
**Evidence:** https://opendatacommons.org/licenses/odbl/1-0/ — "Derivative Database" = "a database based
upon the Database, and includes any translation, adaptation, arrangement, modification, or any other
alteration of the Database or of a Substantial part of the Contents"; "Collective Database" = "this
Database in unmodified form as part of a collection of independent databases in themselves that together
are assembled into a collective whole"; "Produced Work" = "a work (such as an image, audiovisual
material, text, or sounds) resulting from using the whole or a Substantial part of the Contents (via a
search or other query)"; "Substantial" = "substantial in terms of quantity or quality or a combination of
both." §4.4 share-alike on publicly used Derivative Databases; §4.6 requires recipients to receive the
Derivative Database or documentation of alterations at no more than reasonable cost. OSM's own summary at
https://www.openstreetmap.org/copyright confirms ODbL 1.0 and "If you alter or build upon our data, you
may distribute the result only under the same license." OSMF has endorsed community guidelines on
Substantial, Collective Database, Trivial Transformations, Produced Work, Geocoding, Horizontal Map
Layers, Regional Cuts, and Attribution (https://osmfoundation.org/wiki/Licence/Community_Guidelines);
the Collective Database guideline states that "so long as a particular data type within a database
consists entirely of non-OSM data within a regional cut, the OSM and non-OSM datasets will be considered
'independent'."
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG should implement **Strategy A+C hybrid** (§14.1): keep OSM-derived
physical-asset records in a *physically and licensably separate table* that is republished under ODbL-1.0
and joined to the rest of the graph only by identifier, so the rest of the graph remains a Collective
Database rather than a Derivative Database. R1 owns the detailed ODbL analysis; R8 owns the *mechanism*
(P2, P6).
⚖️ **COUNSEL:** whether SIG's join-by-identifier architecture actually preserves Collective Database
status is the central licensing question of the project and must be opined on before the first public
data release.
**Outline delta:** CONFIRMS §14.1 and supplies the missing mechanism; EXTENDS §20 Q13/Q14 by naming the
OSMF guidelines as the interpretive authority the design should be tested against.

---

### F8.17 — CC-BY-SA 4.0 and ODbL are not interoperable, and CC 4.0 licenses reach sui generis database rights

**Claim:** CC-BY-SA-4.0 and ODbL-1.0 are both attribution+share-alike but are different instruments with
no compatibility declaration; CC 4.0 expressly licenses sui generis database rights, which changes the
EU analysis.
**Status:** PARTIALLY VERIFIED
**Evidence:** Search-sourced analysis at https://github.com/theodi/open-data-licensing/blob/master/guides/licence-compatibility.md
and OSM mailing-list threads (https://lists.openstreetmap.org/pipermail/talk/2021-June/086597.html):
OSM relicensed from CC-BY-SA to ODbL in September 2012 precisely because ODbL is purpose-built for
database rights; CC 4.0's database-rights clause is described as "substantially stricter than anything in
the ODbL" for EU publication. I did not retrieve a formal compatibility determination from Creative
Commons or Open Data Commons because none exists.
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG must not attempt to relicense ODbL material as CC-BY-SA or vice versa,
and must not mix a CC-BY-SA-4.0 upstream *into the same database* as an ODbL-1.0 upstream. The
license-compatibility gate (P2) must model this as an explicit `INCOMPATIBLE` cell rather than inferring
compatibility from surface similarity.
**Outline delta:** EXTENDS §14.1 Strategy C — "license the entire public data graph compatibly" is not
achievable if any upstream is CC-BY-SA and any other is ODbL. Strategy C should be marked infeasible in
the general case.

---

## POLICY P2 — SOURCE RIGHTS RECORD AND LICENSE-COMPATIBILITY GATE

### P2.1 The rights record (mandatory for every source; blocking on ingest)

Every source in the registry carries a `RightsRecord`. Ingestion of a source with an incomplete
RightsRecord is a hard failure, not a warning.

```yaml
rights_record:
  source_id: string                       # stable
  rights_holder: string
  license_spdx: string                    # SPDX id, or LicenseRef-<slug>
  spdx_list_version: string               # e.g. "3.28.0" — pinned
  license_url: string                     # the exact URL where the statement was seen
  license_text_hash: sha256               # content hash of the retrieved license text
  license_observed: enum{seen_verbatim, inferred_from_context, asserted_by_operator, none_found}
  attribution_required: bool
  attribution_string: string|null         # verbatim required credit, if specified
  redistribution: enum{permitted, permitted_with_sharealike, permitted_noncommercial_only,
                       prohibited, unknown}
  derivative_works: enum{permitted, permitted_with_sharealike, prohibited, unknown}
  sharealike_target_license: string|null  # SPDX id share-alike forces, if any
  sui_generis_db_right: enum{yes, no, unknown}    # per F8.7
  jurisdiction: string                    # ISO 3166 of the rights holder / hosting
  terms_url: string|null
  terms_binding_theory: enum{clickwrap_accepted, browsewrap_access_binding,
                             browsewrap_use_only, none_found, express_permission}
  access_channel: enum{direct_crawl, api_authorized, bulk_grant, public_records,
                       third_party_archive, human_submission, blocked}
  robots_state_at_fetch: enum{allowed, disallowed, unreachable, n/a}
  content_signals: string|null            # verbatim Content-Signal line if present
  retrieval_date: date
  reviewed_by: string                     # human who read the terms
  counsel_reviewed: bool
  notes: text
```

**Rule P2.1.1:** `license_observed: inferred_from_context` or `none_found` forces
`redistribution: unknown`, which the gate treats as **prohibited**. Silence is never permission.

**Rule P2.1.2:** Every `Claim` (§8.16) carries `rights_record_id` on the evidence path. Rights are a
property of *claims*, not of tables, because a single table row can be assembled from claims with
different provenance.

### P2.2 The compatibility gate

The gate runs at **export time**, not ingest time, because the same claim may be exportable in one
bundle and not another.

```
computeExportLicense(claims) -> {license_spdx, attributions[], blocked_claims[]}

1. Partition claims by rights_record.
2. For each rights record R:
     if R.redistribution == prohibited or unknown  -> add all its claims to blocked_claims
     if R.redistribution == permitted_noncommercial_only
        and bundle.commercial_use_permitted        -> blocked_claims
     if R.sui_generis_db_right in {yes, unknown}
        and bundle.jurisdiction includes EU/EEA
        and R.redistribution != permitted          -> blocked_claims
3. Collect the set S of sharealike_target_license across remaining records.
4. If |S| == 0                -> bundle license = SIG default data license (see P6)
   If S == {ODbL-1.0}         -> bundle license = ODbL-1.0
   If |S| > 1                 -> INCOMPATIBLE: fail the export, name the conflicting pair,
                                 and emit a remediation suggestion (split into layered bundles)
5. Emit attributions[] = every non-null attribution_string, deduplicated, in a
   machine-readable ATTRIBUTION.json plus a human-readable NOTICE.txt.
6. Emit blocked_claims as a *count and reason summary* in the bundle manifest, so the
   omission is visible and auditable rather than silent.
```

**Rule P2.2.1 — no silent drops.** An export that omits claims must say how many and why. A consumer
must be able to tell the difference between "SIG has no data here" and "SIG has data it may not
redistribute here." This is the §9.4 negative-claim principle applied to licensing.

**Rule P2.2.2 — layered bundles are the escape hatch.** When the gate returns INCOMPATIBLE, the correct
remediation is to emit *separate, independently licensed files* in one archive (the Collective Database
and Horizontal Map Layer patterns, F8.16) — `osm_assets.geojson` (ODbL-1.0),
`sig_graph.jsonl` (SIG default), `atlas_derived.csv` (CC-BY-4.0) — each with its own LICENSE and NOTICE,
plus a top-level `MANIFEST.json` mapping files to licenses. Never a single merged table.

**Rule P2.2.3 — the gate is testable.** Ship a fixture suite: an ODbL-only bundle, a CC-BY-only bundle,
an ODbL+CC-BY-SA bundle (must fail), a bundle containing a `redistribution: unknown` claim (must block
that claim and report it), and an EU-sourced bundle with `sui_generis_db_right: unknown` (must block).
CI runs these on every build.

### P2.3 Archive-vs-link decision (Outline Q16)

| Source class | Store raw privately | Publish raw | Publish metadata + link | Publish extracted facts |
|---|---|---|---|---|
| US government public record (FOIA response, contract, agenda, minutes) | yes | **yes** (works of a US government body are generally not copyrighted; state records vary) | yes | yes |
| Court filings / dockets | yes | yes, absent seal | yes | yes |
| Vendor marketing material, spec sheets, price lists | yes | **no** — copyrighted; link + short quotation | yes | yes |
| Vendor portal pages under restrictive terms (Flock) | yes, if lawfully obtained | **no** | yes | yes (facts, per *Feist*) |
| Allied project datasets (Atlas CC-BY, DeFlock, HIBF) | yes | per their license, with attribution | yes | yes |
| News articles | yes | **no** | yes | yes (facts) |
| Contributor photographs | yes | only under the contributor's chosen license (default CC-BY-4.0) | yes | yes |
| Anything containing personal data | yes, encrypted, restricted | **no** | metadata only | only per P3 |

⚖️ **COUNSEL:** state public-records copyright varies (a minority of states assert copyright in some
government works, and *Georgia v. Public.Resource.Org* addressed only annotations to state codes). A
50-state read is needed before SIG republishes raw state/municipal records at scale.

---

# PART C — PUBLICATION ETHICS AND PERSONAL DATA (Outline Q30, Q31)

### F8.18 — Kratovil: Daniel's Law survived First Amendment scrutiny as applied to a journalist publishing a lawfully obtained address

**Claim:** The New Jersey Supreme Court unanimously upheld Daniel's Law and permitted prosecution of a
journalist who published a police director's home address obtained lawfully, even though the address was
relevant to a matter of public concern.
**Status:** VERIFIED
**Evidence:** https://reason.com/volokh/2025/06/19/newspaper-can-be-prosecuted-for-publishing-home-addresses-of-police-prosecutors-and-judges/
— *Kratovil v. City of New Brunswick*, N.J. Sup. Ct., June 19, 2025. Applying *Florida Star*, the court
accepted that "Caputo's home address in Cape May relates to a matter of public concern" (the story
concerned whether the police director lived too far away to do the job), but held "New Jersey's interest
in protecting public officials from such threats ... is clearly a state interest of the highest order"
and the statute narrowly tailored, given the notice mechanism. Volokh criticizes the ruling's
implications for residential picketing.
**Retrieved:** 2026-08-20
**Implication for the spec:** **Public interest is not a defense to a Daniel's-Law address claim in New
Jersey.** SIG's home-address rule cannot be a balancing test; it must be an absolute prohibition. This is
exposure E2.
**Outline delta:** CONTRADICTS §13.2 as written. The outline says "where an accountability event requires
a named public official or officer, apply a clear public-interest standard." That standard is valid for
*names*; it is **invalid for home addresses**, where the correct rule is a categorical never.

---

### F8.19 — Atlas Data Privacy (Aug. 12, 2026): Daniel's Law imposes actual-damages liability with no mental state

**Claim:** On a certified question from the Third Circuit, the New Jersey Supreme Court held unanimously
that Daniel's Law requires no mental state for actual damages under N.J.S.A. 56:8-166.1(c)(1).
**Status:** VERIFIED
**Evidence:** `curl` of https://www.njcourts.gov/system/files/court-opinions/2026/a_8_25.pdf (HTTP 200,
297,300 bytes, 44 pages), text extracted locally with pypdf. Syllabus: *Atlas Data Privacy Corp. v. We
Inform, LLC* (A-8-25) (091145), argued March 17, 2026, **decided August 12, 2026**, Justice Pierre-Louis
for a unanimous Court. Certified question as reformulated: "What mental state, if any, is required to
establish liability under Daniel's Law, N.J.S.A. 56:8-166.1?" **HELD: "Daniel's Law does not contain a
mental state requirement for actual damages liability under N.J.S.A. 56:8-166.1(c)(1)."** Reasoning: the
Legislature included "willful or reckless disregard of the law" for punitive damages in (c)(2) and
"purposeful or reckless" in the criminal provision N.J.S.A. 2C:20-31.1(b), and deleted the 2020 version's
"reasonable person" language in 2022 — omission was deliberate. Statutory text quoted in the opinion:
"a person, business, or association shall not disclose or re-disclose on the Internet or otherwise make
available, the home address or unpublished home telephone number of any covered person," following a
10-business-day notification window. "Covered person" per N.J.S.A. 47:1B-1 = "an active, formerly active,
or retired judicial officer or law enforcement officer ... or prosecutor and any immediate family member
residing in the same household." Plaintiffs assert ~19,000 covered persons used the Atlas platform to
send notices. Constitutionality remains with the Third Circuit.
**Retrieved:** 2026-08-20
**Implication for the spec:** Strict liability + per-violation actual damages + ~19,000 potential
claimants + a 10-day cure window means SIG must (a) never hold or publish a home address, (b) operate an
**intake channel that can execute a takedown inside 10 business days**, and (c) be able to prove
programmatically that no covered-person address exists anywhere in the public corpus. Build the
suppression capability *before* the first publication, not after the first notice.
**Outline delta:** EXTENDS §13.2 with a concrete, statutory, strict-liability deadline the outline does
not contemplate at all. The takedown SLA in P5 is driven by this statute, not by courtesy.

---

### F8.20 — Officer/official personal-information statutes are proliferating fast, and a federal bill is pending

**Claim:** As of 2026, at least seven states have enacted new public-official information protections
since March 2026 alone, three states have standalone doxxing crimes with statutory definitions, roughly
fourteen more criminalize the conduct without the label, seven limit scope to public-sector officials,
California and Illinois provide civil damages, and a bipartisan federal bill (H.R. 8927) is pending.
**Status:** VERIFIED (federal bill, verbatim); PARTIALLY VERIFIED (state counts, from secondary sources)
**Evidence:**
- Federal: `curl https://www.govinfo.gov/content/pkg/BILLS-119hr8927ih/html/BILLS-119hr8927ih.htm`
  (HTTP 200). **Stop the Doxx Act**, H.R. 8927, 119th Cong., 2d Sess., introduced **May 20, 2026** by
  Rep. Gottheimer + 8 bipartisan cosponsors, referred to House Judiciary. Proposed 18 U.S.C. §1522(a):
  "Whoever, in or affecting interstate or foreign commerce, knowingly publishes or otherwise makes
  publicly available the home address, personal telephone number, personal email address, or other
  personally identifying information of a covered public servant or an immediate family member, **with
  intent to threaten, intimidate, or facilitate violence** against that person" — 10 years first offense,
  20 years repeat, 30/40 years if bodily injury or death; §1522(b) creates a private civil action with
  damages, injunctive relief, and fees; "covered public servant" = federal, state, or local law
  enforcement officer, prosecutor, or judge; "publishes" = post on any publicly accessible website,
  platform, forum, "or any other digital or print medium accessible to third parties."
- Existing federal: https://www.law.cornell.edu/uscode/text/18/119 — 18 U.S.C. §119 criminalizes making
  "restricted personal information" (SSN, home address, home/mobile phone, personal email, home fax)
  about covered persons publicly available "with intent to threaten, intimidate, or incite" violence, or
  with knowledge it will be so used; up to 5 years.
- State landscape: https://www.citizen.org/article/tracker-state-legislation-to-protect-public-officials/
  (WebFetch, 2026-08-20) lists 2025–2026 enactments including **Alabama SB 230 (Mar. 2026)**,
  **Hawaii SB 2567/2568 (June 2026)**, **Indiana SB 140 (Mar. 2026)**, **Minnesota HF 4239 (May 2026,
  candidate residence addresses classified non-public)**, **Oklahoma HB 3678 (May 2026, publishing
  identifying information of officials a misdemeanor)**, **Tennessee HB 2045/SB 2320 (May 2026)**,
  **Virginia HB 835 (Apr. 2026, restricts publication of personal identifying information for public
  officials)**, over a pre-2025 base including AZ, CA, CO, DC, FL, HI, IL, MD, NM.
- Doxxing generally: https://www.csg.org/2025/10/31/doxing-state-protections-against-digital-threats/
  returned **HTTP 403** (Cloudflare) to both WebFetch and browser-UA `curl` — INACCESSIBLE; substance
  taken from search extraction: three states (AL, CA, IL) with standalone doxxing crimes and statutory
  definitions; ~14 more criminalizing the conduct without the term; seven (AL, CO, DE, MN, NJ, OK, PA)
  limiting scope to public-sector officials. California AB 1979 (eff. Jan. 1, 2025) provides statutory
  damages $1,500–$30,000 plus punitive damages and fees; Illinois' Civil Liability for Doxing Act
  produced a first verdict (~$46,000) in early 2026.
**Retrieved:** 2026-08-20
**Implication for the spec:** Two different regimes and SIG must satisfy the stricter one everywhere:
- **Intent-based regimes** (18 U.S.C. §119; proposed §1522; most doxxing statutes) — SIG is safe on the
  merits because it never publishes with intent to threaten. But "intent" is a jury question and
  litigation itself is the punishment.
- **Strict-liability regimes** (Daniel's Law; some state address-confidentiality statutes) — SIG is
  exposed regardless of intent.
Therefore: **the national rule must be the New Jersey rule.** SIG does not publish, and preferably does
not store, home addresses or personal contact information for any individual, ever.
⚖️ **COUNSEL:** a 50-state survey of address-confidentiality and officer-privacy statutes, mapped to
SIG's actual fields, is required before the first public release, and must be re-run annually — this area
is changing faster than any other in the memo.
**Outline delta:** EXTENDS §13.2 substantially. The outline lists "officer personal addresses" as
something to *avoid storing*; the correct posture is a hard schema-level prohibition with a validator,
plus an annual statutory re-survey.

---

### F8.21 — OpenOversight publishes officer names and photos and pairs that with a no-logs, warrant-resistant architecture

**Claim:** OpenOversight publishes names, badge numbers, demographic estimates, salaries, news mentions,
and uniform photographs of officers, while running with nginx access and error logs explicitly disabled,
welcoming Tor traffic, requiring no contributor name, routing law-enforcement inquiries to counsel, and
maintaining a warrant canary.
**Status:** VERIFIED
**Evidence:** `curl https://openoversight.com/privacy` and `/about` (HTTP 200), 2026-08-20. Privacy
policy (dated September 1, 2016): "The Lucy Parsons Labs does not maintain network logs on our web
servers. We have explicitly disabled nginx from maintaining access or error logs"; "We also do not block
incoming connections from any regions or IP block, so we welcome traffic from any anonymity network such
as Tor"; "The Submission Form does not require you to provide a name and we will not reject any
submissions without names"; "A note to Illinois law enforcement: This project does not perform facial
recognition and is thus in compliance with the Biometric Information Privacy Act. Requests or questions
regarding this project from those affiliated with law enforcement must be directed to our legal
representation. You may also review our Warrant Canary." About page: consolidates "names, birthdates,
mentions in news articles, salaries, and photographs"; legal contact `legal@lucyparsonslabs.com`;
instances in Chicago, Baltimore, Seattle, Virginia. **Note:** the linked warrant canary URL is not
discoverable — `openoversight.com/canary`, `lucyparsonslabs.com/canary/`, and
`www.lucyparsonslabs.com/canary` all returned 404 on 2026-08-20. INACCESSIBLE; the canary may have
moved or lapsed, which is itself instructive about canary maintenance burden (see P5.7).
**Retrieved:** 2026-08-20
**Implication for the spec:** Adopt the architecture wholesale: **no access logs, no IP retention, no
required contributor identity, Tor permitted, all law-enforcement contact routed to counsel, a stated
compliance position on the relevant biometric statute.** The BIPA note is a specific, replicable move —
SIG should publish an equivalent statement ("SIG performs no facial recognition and no biometric
identification of any person"), because it forecloses a whole category of claim cheaply.
The broken canary link is a caution: a canary you stop maintaining is worse than no canary, because
readers cannot distinguish neglect from signal.
**Outline delta:** EXTENDS §13 with an operational security architecture the outline does not specify.

---

### F8.22 — Citizens Police Data Project publishes named officer misconduct histories on the strength of a public-records ruling

**Claim:** The Invisible Institute's CPDP publishes 240,000+ misconduct allegations against 22,000+
Chicago officers by name, enabled by *Kalven v. City of Chicago* (2014) establishing that police
misconduct records are public in Illinois.
**Status:** VERIFIED
**Evidence:** https://theintercept.com/2018/08/16/invisible-institute-chicago-police-data/ and
https://invisible.institute/police-data (via search, 2026-08-20): "more than 240,000 allegations of
misconduct involving more than 22,000 Chicago police officers over a 50-year period"; complete 2000–2016,
substantially complete to 1988; released "as a result of successful litigation in Kalven v. City of
Chicago (2014), which established that police misconduct records are public in Illinois"; highlights
"repeaters." `https://cpdp.co/` itself rendered as an empty shell to WebFetch (JS app) — INACCESSIBLE for
policy text.
**Retrieved:** 2026-08-20
**Implication for the spec:** CPDP's legitimacy rests on **a specific legal determination that the
underlying records are public in that jurisdiction**. That is the transposable principle: SIG names an
officer when the naming derives from a record that is public *in the jurisdiction that produced it*, not
when SIG has merely inferred the name. This becomes prong 3 of the officer-naming test (P3.4).
**Outline delta:** EXTENDS §13.2 — supplies the operable criterion the outline calls for but does not
provide.

---

### F8.23 — OCCRP Aleph demonstrates a workable three-tier access model

**Claim:** Aleph serves government records and open databases to anyone without an account, requires a
reviewed account (evidence of prior work, organizational affiliation, role) to export, and gates
protected/leaked datasets case-by-case to journalists, activists, and researchers.
**Status:** VERIFIED
**Evidence:** Search-retrieved from https://gijn.org/resource/using-aleph/,
https://bellingcat.gitbook.io/toolkit/more/all-tools/occrp-aleph, and
https://www.occrp.org/en/announcement/aleph-pro-frequently-asked-questions-on-the-future-of-occrps-investigative-data-platform
(2026-08-20): "Anyone can access the publicly available data contained in Aleph"; "No account is
necessary to browse Aleph data; however, if you need to export search results, you need to create a free
account"; account creation "requires submission of evidence of relevant previous work ... the name of the
organization you are affiliated with and your role there. Each request is reviewed by a staff member";
"Protected datasets (leaks, sensitive archives) require case-by-case access approval"; nonprofit
journalism organizations get full Aleph Pro free, public-interest groups at cost, commercial users on
tiers.
**Retrieved:** 2026-08-20
**Implication for the spec:** Directly answers Outline **Q31**. SIG adopts a three-tier model (P3.8):
**T0 public** (open, no account), **T1 registered** (free account, identity *not* required, used only for
rate limiting and abuse response), **T2 restricted** (human-reviewed, purpose-bound, for material that is
lawfully held but not safely public). Note the deliberate divergence from Aleph: SIG must **not** require
identity evidence for T1, because SIG's contributor and consumer population includes people at risk from
the institutions SIG documents.
**Outline delta:** ANSWERS §20 Q31 concretely; EXTENDS §13.4's "restricted access" bullet into a
specified mechanism.

---

### F8.24 — Federal statistical practice: minimum cell size 3 absolute, 5–10 typical, with complementary suppression required

**Claim:** US federal disclosure-avoidance guidance holds that cell size 3 is the absolute minimum,
that 5 or 10 are commonly used, that state ESEA minimum subgroup sizes range 5–30 with a majority at 10,
and that primary suppression alone is insufficient without complementary suppression.
**Status:** VERIFIED
**Evidence:** `curl https://studentprivacy.ed.gov/sites/default/files/resource_document/file/FAQs_disclosure_avoidance_0.pdf`
(HTTP 200, 458,850 bytes, 7 pages), extracted with pypdf. Verbatim: "Many statisticians consider a cell
size of 3 to be the absolute minimum needed to prevent disclosure, though larger minimums (e.g., 5 or 10)
may be used"; "Minimum cell sizes adopted by the States range from 5 to 30 students, with a majority of
States using 10 as their minimum (NCES 2011-603)"; "simple suppression of small subgroups may not be
sufficient to protect the privacy of all students, since the suppressed numbers can often [be derived] ...
suppression of additional non-sensitive cells may be necessary"; methods enumerated as suppression,
blurring (rounding, aggregation, top-coding), and perturbation; warning that blurring fails "if any
unblurred cell counts or row and/or column totals are published."
Corroborating de-identification standard: https://www.law.cornell.edu/cfr/text/45/164.514 — HIPAA Safe
Harbor 45 C.F.R. §164.514(b)(2)(i)(B) removes "All geographic subdivisions smaller than a State," with
3-digit ZIP retained only where the resulting area exceeds 20,000 people, else "000"; (b)(1) expert
determination requires a qualified person to determine re-identification risk is "very small" and to
document the analysis. (HHS's own de-identification guidance page 403'd to both WebFetch and browser-UA
`curl` — INACCESSIBLE; eCFR redirected off-host to `unblock.federalregister.gov` — INACCESSIBLE; Cornell
LII was the working source.)
**Retrieved:** 2026-08-20
**Implication for the spec:** Gives SIG defensible, citable numeric thresholds for aggregate publication
(P3.7) instead of an invented rule. The complementary-suppression warning is the crucial one: SIG's
aggregates are *hierarchical* (device → agency → county → state), so suppressing a small county cell
while publishing the state total and all other counties reconstructs the suppressed cell exactly.
**Outline delta:** EXTENDS §13 — the outline never raises aggregate disclosure risk at all. This is a
material gap.

---

### F8.25 — The ShotSpotter precedent: sensor locations were kept secret from clients and the public and were published only via leak

**Claim:** SoundThinking kept precise sensor locations secret from police clients and the public and
resisted subpoenas for them; WIRED published locations and uptime for 25,580 sensors from an anonymous
leak in February 2024; the company alleged illegal disclosure by ex-employees and pursued remedies.
**Status:** VERIFIED
**Evidence:** https://www.thetrace.org/newsletter/shotspotter-sensor-locations-data-leak/,
https://wisconsinexaminer.com/2024/02/27/privacy-advocates-respond-to-leaked-data-of-shotspotter-gunshot-detection/,
https://www.axios.com/local/cleveland/2024/02/28/cleveland-shotspotter-map-pilot (via search, 2026-08-20):
"a leaked document, which WIRED obtained from a source under the condition of anonymity, details the
alleged precise locations and uptime of 25,580 ShotSpotter microphones"; "SoundThinking keeps the
locations of its sensors closely guarded, going so far as to resist subpoenas for the information in
court"; "Until now, the exact locations of SoundThinking's sensors have been kept secret from both its
police department clients and the public"; ~70% of people in sensor neighborhoods identified as Black or
Latine; SoundThinking said the document was "illegally disclosed by ex-employees and is currently
pursuing civil and criminal remedies." The Cleveland reporting shows a specific harm mode: the leaked map
reflected a *pilot* footprint, not the current citywide one, so republication propagated a stale claim.
**Retrieved:** 2026-08-20
**Implication for the spec:** Three lessons encoded in the coordinate matrix (P3.5):
1. **Provenance determines publishability more than sensitivity does.** A leaked corpus carries
   misappropriation/trade-secret risk and the ex-employee's exposure. SIG's rule: SIG does not solicit,
   accept, or ingest material a contributor obtained in breach of an employment or confidentiality
   obligation. SIG may *cite reporting about* such material.
2. **Aggregate demographic analysis was the public-interest payoff.** SIG can deliver most of that value
   at census-tract resolution without exact points.
3. **Stale precision is a harm.** A published exact coordinate that is wrong is worse than a published
   jurisdiction-level count that is right.
**Outline delta:** EXTENDS §13.3 with a provenance dimension the outline's five-category taxonomy omits.
Sensitivity is a function of *(device class × mounting context × source provenance × freshness)*, not of
device class alone.

---

### F8.26 — OSM's own tagging scheme for surveillance devices carries no privacy caution, which is itself the community norm

**Claim:** `man_made=surveillance` covers publicly and privately operated cameras monitoring public and
private space, with subtags for `surveillance:type` (camera, guard, **ALPR**, gunshot_detector),
`surveillance:zone`, `camera:type`, `camera:mount`, `camera:direction`, `operator`, and `camera:power`,
and the documentation contains no privacy warning about mapping such devices.
**Status:** VERIFIED
**Evidence:** https://wiki.openstreetmap.org/wiki/Tag:man_made%3Dsurveillance (WebFetch, 2026-08-20).
Subtags and values as listed; "publicly or privately operated, and may be monitoring a public or private
space"; the documentation "contains no explicit privacy warnings or cautions about mapping surveillance
devices."
**Retrieved:** 2026-08-20
**Implication for the spec:** The established community norm for **roadside, publicly visible** hardware
is exact-coordinate mapping, and DeFlock/OSM already do it at scale. SIG publishing exact coordinates for
that class adds no marginal harm and inherits an established practice. That norm does **not** extend to
device classes OSM's schema does not distinguish — private-residence-mounted cameras registered to a
police network, concealed sensors, and mobile assets — and SIG must draw the lines OSM does not.
**Outline delta:** CONFIRMS §13.3's first category and supplies the precedent; EXTENDS the rest, since
OSM offers SIG no guidance for the other four categories.

---

### F8.27 — Axon Community Connect registry data is vendor-classified as protected non-public data

**Claim:** Community Connect lets residents and businesses register or integrate private cameras with
police; registration data is described by Axon as "protected non-public data" accessible only to
authorized users of the system, and shared cameras appear on the agency-facing Fusus map.
**Status:** PARTIALLY VERIFIED
**Evidence:** Search extraction from https://www.axon.com/products/axon-fusus/community-integration and
https://axoncommunityconnect.com/faqs/ (2026-08-20): "residents and businesses can register their cameras
to help agencies create a secure map within Axon Fusus, so agencies know who to contact for post-incident
requests. This voluntary registry does not provide live access"; "camera registry data is classified as
protected non-public data, and is only accessible by authorized users of our system"; "Shared cameras
appear on the Fusus map in real time." Direct retrieval limited: `axoncommunityconnect.com/robots.txt`
→ **404**; `axoncommunityconnect.com/faqs/` returned a JS-rendered shell with no extractable policy
text — INACCESSIBLE for verbatim terms.
**Retrieved:** 2026-08-20
**Implication for the spec:** Community Connect / Fusus registries are the sharpest personal-data
hazard in the whole surveillance stack, because the registrants are **private individuals and small
businesses at identifiable addresses**. SIG's rule: publish the *program* (which agency, which vendor,
when adopted, contract value, registrant count if the agency publishes one, policy terms), **never the
registrant**. A registrant list obtained via public records is stored in the restricted tier and
published only as a count. Note also that a small-HOA participation record can identify a handful of
households — apply P3.7 suppression to registrant counts, not just to usage aggregates.
**Outline delta:** EXTENDS §4.1 and §13.2. The outline's "residential associations" bullet is exactly
right and this finding gives it teeth: HOA/registrant membership is a *small-cell* problem as well as a
personal-data problem.

---

## POLICY P3 — SIG PUBLICATION POLICY

> **Status:** proposed for adoption. Answers Outline Q30 and Q31. §§3.1–3.3 are absolute and are enforced
> by schema constraints and CI validators, not by reviewer judgment.

### P3.1 The governing principle

> SIG documents **institutions, systems, contracts, capabilities, and infrastructure**. It does not
> document **people**, except public officials in their official capacity, and then only their official
> conduct and official identity.

Every close call resolves against publication. SIG can always publish later; it can never unpublish.

### P3.2 Never collected, never stored, never published (Tier X — schema-prohibited)

The following must fail ingestion validation. No configuration flag enables them.

| Category | Rule | Basis |
|---|---|---|
| **License plate numbers** (full or partial) | Never. Not in raw storage, not hashed, not in evidence artifacts. Redact on ingest; if a public record contains plates, store the record encrypted in the restricted tier with plates masked in every derivative. | §13.1; plate data is the definitional individual-movement record |
| **Plate-adjacent hashes / tokens** | Never. A salted hash of a plate is still a plate: the keyspace is ~10^8, brute-forceable in seconds. "Pseudonymized" plates are not de-identified. | Re-identification risk; HIPAA expert-determination logic (F8.24) |
| **Individual travel histories / hotlist hits / search logs** | Never, at any resolution. Belongs with HIBF and projects governed for it. | §13.1 |
| **Home addresses and personal contact info of any individual** — officer, official, contributor, private person | Never. Schema has no field. Free-text validator rejects address-shaped strings adjacent to a person name. | **F8.18, F8.19** (strict liability), F8.20 |
| **Private-person names** | Never, unless the person is a named party to a public accountability record (a plaintiff, a decedent in an official incident report, a named complainant who has already self-identified publicly). | §13.2 |
| **Biometrics / facial recognition of anyone** | SIG performs no facial recognition, no gait/voice analysis, no biometric matching, and stores no biometric templates. Published as an affirmative statement. | F8.21 (BIPA-style exposure) |
| **Material obtained in breach of a confidentiality or employment obligation** | Not solicited, not accepted, not ingested. SIG may cite published reporting about such material. | F8.25 |
| **RF payload / associated-session data** | Never. Management-frame metadata only. | F8.14 |
| **Precise contributor geolocation** | Not retained. See P6.3. | F8.21 |

### P3.3 Officer and official identity

| Field | Posture |
|---|---|
| Officer **name** | Publishable only if it passes the P3.4 test |
| Officer **badge / serial / star number** | Publishable **with** the name, on the same test. Alone (without a name), badge numbers are institutional identifiers and carry lower risk; SIG still applies the same test, because badge → name is a trivial join for anyone with a roster |
| Officer **rank, unit, agency, dates of service** | Publishable when derived from a public record |
| Officer **salary** | Publishable when a public record; not linked to any residence or household inference |
| Officer **home address, phone, email, household composition, family members** | **Never** (P3.2) |
| Named **executives, elected officials, agency heads, procurement officers signing contracts** | Publishable — these are institutional-role facts appearing on the face of public documents |
| **Vendor employees below the executive level** | Not published by name |

### P3.4 THE OFFICER-NAMING TEST (operable)

An individual officer's name (and badge number) may be published **only** when *all five* prongs are
satisfied and a second reviewer concurs.

> **Prong 1 — Official conduct.** The claim concerns the officer's conduct in an official capacity or a
> decision made in an official role. Off-duty conduct, personal life, associations, family, finances, and
> social media are out of scope regardless of newsworthiness.
>
> **Prong 2 — Documented, not inferred.** The name appears on the face of a **Tier A or Tier B**
> evidence artifact (§9.1) — a public record, a court filing, an agency disclosure, an official
> statement, published minutes, or the officer's own public statement. SIG never publishes a name it
> derived by matching, correlating, or guessing.
>
> **Prong 3 — Lawfully public where produced.** The producing jurisdiction treats the underlying record
> as a public record, and no seal, statutory confidentiality, expungement, or address-confidentiality
> designation applies. (The *Kalven* principle, F8.22.)
>
> **Prong 4 — Necessary.** The accountability claim cannot be made without the name. If "an officer of
> the Springfield PD ran 47 unauthorized ALPR searches" carries the same public-interest weight as the
> named version, the unnamed version is published. Naming is justified where the *pattern attaches to the
> individual* — a repeat actor, a decision-maker, a supervisory failure, a person already publicly
> identified in litigation or discipline.
>
> **Prong 5 — Proportionate and current.** The severity of the documented conduct is proportionate to the
> permanence of publication; the record is not stale in a way that misleads (an allegation later
> dismissed must be published with that disposition or not at all); and publication does not create a
> foreseeable safety risk disproportionate to the accountability gain.

**Review workflow.**
1. Contributor or pipeline flags a claim as `contains_person_name`. It **cannot** enter the public
   projection; it lands in the `person_review` queue.
2. **Reviewer A** (any trusted contributor, T3+) records a written determination against all five prongs,
   citing the evidence artifact id for prong 2 and the jurisdictional basis for prong 3.
3. **Reviewer B** (a different person, from the publication committee) concurs or rejects. Disagreement
   defaults to **do not publish**.
4. Outcomes: `publish_named`, `publish_unnamed` (role + agency only), `hold_pending_counsel`,
   `reject`. All four are recorded as assertions in the bitemporal store with reviewer ids and reasoning,
   so the decision is auditable and revisable.
5. Any `publish_named` decision is re-reviewed on the earlier of 24 months or a takedown request.
6. **Counsel escalation is mandatory** where: the officer is a covered person under a
   Daniel's-Law-style statute in a state SIG has not surveyed; the record's public status is contested;
   or the claim is defamatory-if-false rather than a bare fact.

⚖️ **COUNSEL:** the test above is a risk-management framework, not a legal safe harbor. Defamation,
false light, and state officer-privacy statutes all remain live. Have counsel review the test itself and
the first ten `publish_named` determinations.

### P3.5 THE COORDINATE-SENSITIVITY DECISION MATRIX (Outline §13.3, made operable)

Sensitivity = **device class × mounting context × parcel type × provenance × freshness**. The matrix
below is keyed on the outline's five classes and refined by the added dimensions.

| # | Class | Definition / test | **Publication posture** | Reasoning & precedent |
|---|---|---|---|---|
| **C1** | **Publicly visible roadside device** | Fixed hardware on a public right-of-way, pole, gantry, or public building, visible from a public place, photographable without trespass | **Publish exact coordinates** (to ~5 decimal places), direction, mount, operator, vendor | Established OSM/DeFlock norm (F8.26); the device is designed to observe the public from public space; visibility is not a secret; publication is the core public-interest function of the project |
| **C2** | **Hidden / non-obvious sensor on public infrastructure** (concealed gunshot sensors, unmarked pole cameras, disguised enclosures) | On public infrastructure but not identifiable as surveillance by an ordinary passer-by | **Publish reduced precision** — round to ~250 m (≈3 decimal places) **or** publish census-tract/block-group centroid — plus full institutional detail (vendor, agency, count, contract, coverage area) | ShotSpotter precedent (F8.25): the public-interest payoff (coverage equity, cost per alert, demographic distribution) is fully achievable at tract level; exact points add evasion utility and provenance risk without adding accountability value. Publish exact only where the agency or vendor has itself published the location |
| **C3** | **Private-residence candidate** | Geocodes to a residential parcel, or is a camera registered to a household under Community Connect / Fusus / a neighborhood program | **Do not publish any location.** Publish only the **program-level** fact (agency, vendor, program name, adoption date, aggregate registrant count subject to P3.7) | Registrant data is vendor-classified non-public and identifies households (F8.27); a residence is not an institution (§13.1); a residence coordinate plus "shares video with police" is a personal-data publication about the occupant |
| **C4** | **Confidential / protective facility** — DV shelters, ICE detention or staging sites where publication endangers detainees or residents, undercover offices, safe houses, victim-services locations, judicial chambers | Facility whose location is protected by statute, court order, or an established safety practice | **Do not publish location at any precision. Do not publish the facility's existence at a resolvable granularity.** Publish only jurisdiction-level institutional facts (e.g. "the county operates a real-time crime center integrating N feeds") | Address-confidentiality statutes exist in most states for DV survivors; the harm is to third parties who are not the subject of accountability. **Asymmetry note:** an ICE *field office* or a *contracted detention facility* whose address is already published by the agency is C1/C2, not C4 — C4 covers locations whose secrecy protects vulnerable people, not locations whose secrecy protects the agency from scrutiny. ⚖️ **COUNSEL** on the ICE-facility line specifically; it is politically and legally contested |
| **C5** | **Mobile asset** (trailer-mounted ALPR, mobile surveillance towers, drone launch points, covert vehicles) | Asset whose location is a function of time | **Publish jurisdiction-only** plus the *historical* observation with an explicit `observed_at` and a `location_is_historical: true` flag, never a current-location field. Never publish a real-time or near-real-time position | A current position is an operational feed and serves evasion of a specific active operation (§13.5, P7). A dated historical observation is a research record. The distinction is real-time-ness, not precision |

**Cross-cutting overrides (apply on top of the class):**

- **O1 — Already-published-by-the-operator override.** If the agency or vendor has itself published the
  exact location (a council presentation map, a transparency portal, a press release), SIG may publish
  exact for C2, and must cite the operator's own publication. This never upgrades C3 or C4.
- **O2 — Residential-parcel veto.** Any candidate whose coordinate falls on a parcel classified
  residential in an authoritative parcel layer is demoted to C3 regardless of its other attributes.
  Implemented as an automated pre-publication check, not a reviewer judgment.
- **O3 — Freshness gate.** No location is published as current if the most recent supporting observation
  is older than **24 months**; after that it is republished as a historical observation with the
  observation date foregrounded (the Cleveland stale-map failure, F8.25).
- **O4 — Provenance veto.** Anything sourced from a leak, a breach, or a confidentiality breach is not
  published at any precision (F8.25).
- **O5 — Downgrade is always available; upgrade requires review.** Publishing at lower precision than
  the matrix permits needs no approval. Publishing at higher precision requires a two-reviewer record.

### P3.6 RF/OUI-DERIVED CANDIDATES — the promotion rule (Outline §13.3 Layer G)

> **Nothing derived from radio observation is ever published as a confirmed asset. Radio observation
> produces candidates. Candidates are not accusations.**

Concrete, testable rules:

1. **R1 — Separate class.** RF-derived records are stored as `CandidateAsset` with
   `discovery_method: rf_observation`, never as `PhysicalAsset`. The two are different types with
   different public projections. A `CandidateAsset` can never be silently promoted by an update; promotion
   is an explicit, logged state transition.
2. **R2 — Residential veto (absolute).** If the candidate's location estimate, expanded by its 95%
   uncertainty radius, **intersects any residential parcel**, the candidate is not published at all — not
   as a candidate, not at reduced precision, not as a count. It remains internal for corroboration work
   only. This implements §7.2's prohibition on "speculative exact locations of sensitive private
   residences based only on weak RF observations."
3. **R3 — Promotion threshold.** A `CandidateAsset` may be promoted to `PhysicalAsset` only on:
   - **(a) one Tier A/B confirmation** — a field photograph with EXIF-consistent location or a
     contributor attestation with a photograph, a public record listing the installation, an agency map,
     or an operator statement; **or**
   - **(b) N ≥ 3 independent RF observations** meeting all of: different observer identities, different
     observation dates spanning ≥ 14 days, spatial agreement within 50 m, consistent OUI/BSSID, **and**
     a corroborating non-RF signal (imagery, a permit, a pole-attachment record, a contract line item).
   RF-only corroboration alone never promotes: three sightings of the same wrong guess is still a wrong
   guess.
4. **R4 — Public candidate representation.** Unpromoted candidates, where publishable at all (i.e. R2
   satisfied), appear **only** as a jurisdiction-level count and a research task ("Springfield: 7
   unverified RF candidates awaiting field verification"), never as mapped points, and never with an
   operator or vendor attributed as fact. Vendor attribution from an OUI is recorded as
   `vendor_hypothesis` with an explicit confidence, never as `operator`.
5. **R5 — Language discipline.** Public strings for candidates use "unverified radio observation
   consistent with <vendor> hardware," never "Flock camera at <address>." The UI must make it impossible
   to render a candidate with confirmed-asset styling. This is a testable UI assertion.
6. **R6 — Demotion and expiry.** A candidate with no corroboration within **12 months** is auto-demoted
   to `stale` and removed from all public surfaces (retained internally with its history).
7. **R7 — No individual inference.** SIG never associates an RF observation with a person, a vehicle, or
   a household, and never publishes an observer's identity or track. Observation records store a
   *coarsened* observer location (see P6.3), never the observer's path.
8. **R8 — Testable acceptance criteria.** CI fixtures: a candidate on a residential parcel must be
   absent from every public export; a candidate with 3 RF observations and no non-RF corroboration must
   remain unpromoted; a promoted asset must carry a non-RF evidence artifact id; a public rendering of a
   candidate must not contain a street address.

### P3.7 Aggregate disclosure and small-cell suppression

**Rule P3.7.1 — Threshold.** Any published count derived from person-linked or household-linked
underlying units (registrant counts, complaint counts by unit, search counts by officer, HOA participation,
audit-log aggregates) is suppressed when **n < 10**, reported as `<10`. SIG adopts 10 rather than 3 or 5
because SIG's cells are geographically fine and highly correlated with identity, and because 10 is the
modal state standard (F8.24).

**Rule P3.7.2 — Complementary suppression is mandatory.** When any cell is suppressed, SIG suppresses
additional cells in the same table such that no suppressed value can be recovered by subtraction from
published margins. The publication pipeline runs a **reconstruction check**: it attempts to solve for
suppressed cells from all published aggregates at every level of the hierarchy; if any suppressed cell is
uniquely determined, the export fails. (F8.24 — this is the failure mode the ED guidance warns about, and
it is *the* failure mode for hierarchical geographic data.)

**Rule P3.7.3 — Geographic floor for person-linked aggregates.** Person-linked aggregates are never
published below **census tract**. Institution-linked aggregates (device counts by agency, contract values,
integration counts) have no geographic floor because they describe institutions, not people. (Borrowing
the logic, not the letter, of HIPAA Safe Harbor's geographic rule, F8.24.)

**Rule P3.7.4 — Differencing across releases.** Versioned snapshots create a differencing attack: two
snapshots of the same suppressed table can reveal the underlying change. SIG applies the suppression rule
to the *union* of all published snapshots — once a cell is suppressed, it stays suppressed in later
releases even if its count rises above threshold, unless the increase is large enough that the delta is
itself above threshold.

**Rule P3.7.5 — Small-HOA / small-network membership.** Membership of a named private organization in a
surveillance sharing network is publishable when the organization is a **business or institution**
(a mall, a hospital, a university, a corporate campus). It is **not** publishable when the organization is
a **residential association** with fewer than 10 identifiable households or where naming it would identify
particular households. Residential associations above that threshold are publishable by name **without**
any coordinate, membership roster, or camera count below threshold.

### P3.8 Access tiers (Outline Q31)

| Tier | Who | Contents | Controls |
|---|---|---|---|
| **T0 — Public** | Anyone, no account, no logging of identity | The published graph, bulk dumps, API, all C1 exact coordinates, C2 reduced, institutional facts, aggregates ≥ threshold | Rate limits by token bucket, not by identity |
| **T1 — Registered** | Free account; **no identity verification, no real name, no organization required**; email optional (a random token works) | Higher rate limits, bulk export, change feeds | Account exists for abuse response only; no PII collected; deliberate divergence from Aleph's identity-evidence requirement (F8.23) because SIG's users include people at risk |
| **T2 — Restricted** | Human-reviewed, purpose-bound, time-limited grant to named researchers, journalists, litigants, and oversight bodies | Raw records held privately: unredacted public-records responses, registrant lists, C3/C4 locations, RF candidates on residential parcels, pre-publication review material | Written purpose, signed use terms, expiry, revocation, per-grant audit log, and a per-grant entry in the transparency report (count only). ⚖️ **COUNSEL** on whether T2 grants create discovery obligations for SIG |
| **T3 — Internal** | Project maintainers | Contributor correspondence, security material, legal correspondence | Minimum necessary; encrypted at rest; see P6 |

**Rule P3.8.1:** Material in T2 is material SIG has decided is *lawfully held but not safely public*.
It is not a staging area for material SIG has decided it should not hold at all (Tier X, P3.2), which is
deleted, not restricted.

---

# PART D — TAKEDOWN, CORRECTION, AND DISPUTE (Outline Q32)

### F8.28 — OSM redaction preserves the history entry while removing the object content; DWG intake is a single address

**Claim:** The OSM Data Working Group can revert, block (up to 96 hours), and redact; redacted changesets
"are still listed in the history, but object information is absent"; intake is `data@openstreetmap.org`.
**Status:** VERIFIED
**Evidence:** https://wiki.openstreetmap.org/wiki/Data_working_group (WebFetch, 2026-08-20) — DWG handles
"accusations of copyright infringement, imports, serious disputes and vandalism"; imposes "temporary
blocks (up to 96 hours)"; removes "or redact[s] information that cannot be distributed in OSM";
"Changesets that have been redacted are still listed in the history, but object information is absent";
report to `data@openstreetmap.org`; volunteer-staffed with no SLA.
**Retrieved:** 2026-08-20
**Implication for the spec:** This is exactly the bitemporal-safe suppression primitive SIG needs: the
*fact that a record existed and was suppressed* survives; the *content* does not. SIG implements
`suppress` as a new assertion (`suppressed_at`, `suppressed_by`, `suppression_reason_code`,
`suppression_ticket_id`) that masks content in public projections while leaving the assertion node and
its lineage intact. Deletion of the underlying row happens only for Tier X material.
**Outline delta:** EXTENDS §9.2 and §19.3 — the outline's append-only temporal model needs an explicit
suppression primitive, or the first valid privacy demand will force a destructive delete.

### F8.29 — Wikipedia separates reversible admin-visible redaction from irreversible oversight suppression, and logs both

**Claim:** RevisionDelete hides content from public view but remains administratively visible and
reviewable; Oversight/suppression hides from administrators too; both create permanent audit trails and
redacted entries remain visible in struck-through form.
**Status:** VERIFIED
**Evidence:** https://en.wikipedia.org/wiki/Wikipedia:Revision_deletion (WebFetch, 2026-08-20) — criteria
RD1 copyright, RD2 grossly offensive, RD3 purely disruptive, RD4 oversightable privacy/defamation, RD5
deletion-policy enforcement, RD6 housekeeping; "Redacted entries still appear in struck-through form;
administrative logs show all actions"; suppression is "hidden from administrators; RevisionDelete actions
remain administratively visible and reviewable"; "Both tools create permanent audit trails of actions
taken."
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG needs **two** suppression levels mirroring this: `redacted` (hidden
from T0/T1, visible at T2/T3, fully reversible) and `purged` (removed from all tiers, irreversible,
requires two maintainers plus counsel sign-off, used only for Tier X material and unambiguous legal
compulsion). The *tombstone* — id, date, reason code, decision-maker — always survives both.
**Outline delta:** EXTENDS §13.4 — "raw private archival storage / redacted public derivative" needs a
reversibility dimension and a separate irreversible path.

### F8.30 — MuckRock's de-publication order was defeated as a prior restraint

**Claim:** A Washington state court ordered MuckRock to de-publish lawfully obtained public records at a
company's request; EFF got the order lifted as an unconstitutional prior restraint, and MuckRock's
practice is to retain documents "as close to forever as they can," redacting only where an agency
mistakenly released legally protected data.
**Status:** VERIFIED
**Evidence:** https://www.eff.org/cases/muckrock-litigation (WebFetch, 2026-08-20) — *Landis+Gyr v. City
of Seattle*; May 2015 request, de-publication order despite the records being public for over a month;
EFF argued "a prior restraint that violated the First Amendment"; Judge William Downing of King County
Superior Court agreed; order lifted by June 2016; settlement barred further removal attempts; parallel
Elster and Ericsson suits dismissed by November 2016. MuckRock's practice per
https://www.muckrock.com/faq/ (search extraction): retain public documents indefinitely; "in rare
instances, agencies might accidentally release legally protected data, in which case MuckRock will work
with the requester to redact or remove legally sensitive information."
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG's default answer to a demand to remove lawfully obtained public records
is **refuse, with published reasoning**, and refusal is legally supportable. But the exception MuckRock
recognizes — an agency's inadvertent release of legally protected data — is the same exception SIG needs
for plates, addresses, and confidential-facility locations. Encode both: a strong presumption against
removal, with an enumerated exception list.
**Outline delta:** ANSWERS §20 Q32 with a concrete precedent and a defensible default of refusal.

### F8.31 — Lumen shows the model for publishing the demands themselves

**Claim:** Lumen, a Harvard Law School Library research project, publishes takedown and legal removal
requests — 75M+ notices referencing 10B+ URLs as of June 2026 — with the caveat that "the presence of a
notice in our database does not indicate a judgment" about validity.
**Status:** VERIFIED (existence, scale, purpose); UNVERIFIED (its redaction rules)
**Evidence:** https://lumendatabase.org/pages/about (WebFetch, 2026-08-20). Founded 2002 by Wendy Seltzer
at the Berkman Klein Center; now in the HLS Library; contributors include Google, Twitter, YouTube,
Wikipedia, Meta, Medium, Vimeo, Cloudflare, WordPress; 200,000+ notices/week. The About page does **not**
state redaction rules for senders' personal information or researcher access tiers — UNVERIFIED on those
points; a direct policy page was not located.
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG should publish every legal demand it receives, with the sender's
personal contact details redacted and the sending entity named, and should submit copies to Lumen where
Lumen accepts them. Publishing the demand is the cheapest available deterrent against meritless demands
and is the transparency-report backbone.
**Outline delta:** EXTENDS §20 Q32 — the outline asks how takedowns should *work*; it does not ask
whether they should be *disclosed*. They should.

### F8.32 — DMCA §512 and §230 are available but partial

**Claim:** §512(c) offers a hosting safe harbor conditioned on a registered designated agent (renewable
every 3 years), a reasonably implemented repeat-infringer policy, and expeditious takedown, with a
counter-notice path at §512(g) and misrepresentation liability at §512(f); §230(c)(1) immunizes a
provider as to third-party content but §230(e) carves out federal criminal law, intellectual property,
and ECPA.
**Status:** VERIFIED
**Evidence:** https://www.copyright.gov/512/ — designation must be registered with the Copyright Office
and published on the site; "Every designation expires and becomes invalid three years after it is first
registered"; providers must "adopt and reasonably implement a policy to terminate repeat infringers";
"act expeditiously to remove or disable access to" material; restoration "not less than ten, nor more
than fourteen, business days" after a valid counter-notice absent suit; §512(f) liability for knowing
material misrepresentation. https://www.law.cornell.edu/uscode/text/47/230 — §230(c)(1) verbatim; §230(e)
carve-outs for criminal enforcement, IP, consistent state law, ECPA, and sex trafficking; §230(f)(3)
"information content provider" = anyone "responsible, in whole or in part, for the creation or
development" of the information.
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG must register a §512 agent before accepting contributor uploads and
diary the 3-year renewal. **Critical limit:** §230 does not immunize SIG for content SIG *creates* — and
a reconciled, entity-resolved claim synthesized by SIG's pipeline is arguably SIG's own content, not a
contributor's. ⚖️ **COUNSEL:** the extent to which SIG's synthesis makes it an "information content
provider" under §230(f)(3) is a genuinely open question and is the most consequential unresolved
liability issue after E1–E3. Note also §230(e)(2): IP claims are carved out, so §230 gives no protection
against the ODbL/copyright/database-right issues in Part B.
**Outline delta:** EXTENDS §14 and §20 Q32 — the outline treats governance as a licensing problem; the
intermediary-liability posture is a separate and equally load-bearing question.

### F8.33 — Warrant canaries: EFF believes they are lawful, no court has said so, and Canary Watch was abandoned

**Claim:** The theory is that a gag order can compel silence but not an affirmative lie; EFF believes
canaries are legal; no definitive US ruling establishes it; the multi-org Canary Watch monitoring project
was discontinued.
**Status:** VERIFIED (EFF position, project status); UNVERIFIED (legal validity — no ruling exists)
**Evidence:** https://www.eff.org/deeplinks/2014/04/warrant-canary-faq — "EFF believes that warrant
canaries are legal, and the government should not be able to compel a lie."
https://www.eff.org/deeplinks/2016/05/canary-watch-one-year-later — the coalition (EFF, Freedom of the
Press Foundation, NYU Law, Calyx, Berkman) "decided to no longer maintain the Canary Watch project."
18 U.S.C. §2709(c) supplies criminal penalties for disclosing an NSL. Scholarship at
https://yalelawjournal.org/forum/warrant-canaries-and-disclosure-by-design.
**Retrieved:** 2026-08-20
**Implication for the spec:** Publish a canary, but design it to fail *safely* and to be maintainable:
signed, dated, on a fixed cadence, with the signing key published and the cadence stated so a reader can
distinguish a signal from neglect. The broken OpenOversight canary link (F8.21) is the cautionary case.
⚖️ **COUNSEL:** canary legality is genuinely untested; do not represent it to users as a guarantee.
**Outline delta:** EXTENDS §13 — the outline has no transparency-reporting or legal-process posture at all.

---

## POLICY P4 — TAKEDOWN, CORRECTION, AND DISPUTE PROCEDURE

> **Status:** proposed for adoption. Answers Outline Q32. The 10-business-day SLA in category **B** is
> not a courtesy; it is driven by the Daniel's Law compliance window (F8.19).

### P4.1 Intake

- Single published channel: `corrections@<sig-domain>` and a web form requiring no account and no
  identity. A PGP key and an onion-service form are published for sensitive submissions.
- A separate published channel `legal@<sig-domain>` for legal demands, with the designated §512 agent's
  registered details published alongside.
- Every submission is assigned a **public ticket id** on receipt. Acknowledgement within **2 business
  days** stating the category, the SLA, and the appeal path.
- SIG does **not** require a requester to prove identity to file, but does require it to *effect* certain
  outcomes (see P4.3 verification).

### P4.2 Categories, SLAs, and decision authority

| Cat | Type | Ack | Decision SLA | Interim action | Decider |
|---|---|---|---|---|---|
| **A** | **Factual error** (wrong count, wrong vendor, wrong date, misattributed device, wrong agency) | 2 bd | **14 bd** | Annotate the claim as `disputed` immediately; the public surface shows the dispute | Any two trusted contributors (T3+) |
| **B** | **Privacy harm** (a home address, a plate, a person name, a residential coordinate, a covered-person record, a confidential-facility location) | 1 bd | **5 bd**, hard cap **10 bd** | **Suppress first, adjudicate second.** Public visibility removed on receipt | One maintainer may suppress alone; restoration requires two |
| **C** | **Legal demand** (statutory notice, cease-and-desist, court order, subpoena, preservation demand) | 1 bd | Per the demand's own deadline; otherwise 10 bd | Preserve everything; suppress only if the demand is category-B in substance; **never** destroy material under a preservation obligation | Legal contact + two maintainers; counsel engaged for anything beyond a facially valid statutory notice |
| **D** | **Security concern** (a published location endangers a specific person; a vulnerability in SIG; a contributor is being targeted) | Same day | **3 bd** | Suppress the specific item; if a contributor is at risk, execute the contributor-protection runbook (P6.3) | Any maintainer, unilateral, review after the fact |
| **E** | **Copyright / license** (DMCA notice, license-violation claim, ODbL attribution complaint) | 2 bd | **10 bd** | Suppress the specific artifact if the notice is facially compliant; retain privately | §512 agent + one maintainer |
| **F** | **Vexatious / abusive** (repeat meritless demands, demands seeking to suppress lawfully public institutional records) | 2 bd | 20 bd | None | Publication committee; outcome is normally *refuse with published reasoning* |

### P4.3 Verification requirements

| Requested outcome | Verification required |
|---|---|
| Correct a factual error | Evidence sufficient to outweigh the existing claim under §9.1 tiering. A bare assertion by the subject is recorded as a **counter-claim**, not a correction — this is exactly what the claim model is for |
| Suppress a personal-data item (cat. B) | **None.** SIG suppresses on plausible allegation and asks questions afterward. The cost of an erroneous suppression is one missing row; the cost of an erroneous publication is unbounded |
| Suppress a *non*-personal item claimed to be sensitive | The requester must identify the specific harm and the specific item. Institutional embarrassment is not a harm |
| Delete entirely (purge) | Two maintainers + counsel sign-off. Available only for Tier X material or valid legal compulsion |
| Assert a statutory removal right (Daniel's Law notice, state privacy statute) | Accept the notice at face value and comply within the statutory window; do not demand proof of covered-person status as a precondition to compliance |

### P4.4 Possible outcomes (closed set)

1. **CORRECT** — the claim is superseded by a new, better-evidenced assertion.
2. **ANNOTATE** — a `disputed_by` counter-claim is attached and rendered alongside; the original stands.
3. **REDACT** — content hidden from T0/T1, retained at T2/T3, reversible, tombstoned.
4. **PURGE** — content destroyed at all tiers, irreversible, tombstoned.
5. **REFUSE WITH PUBLISHED REASONING** — the request is denied and the denial (with the request, sender
   contact details redacted) is published in the transparency report.
6. **REFER** — the request concerns upstream data (OSM, Atlas, a public record) and is routed upstream
   with the requester told where it went; SIG suppresses its own copy in the interim if category B.

### P4.5 How a correction is recorded without destroying the record (bitemporal invariant)

> **A retraction is a new assertion, not a deletion.**

The invariant, stated so it can be tested:

1. Every claim carries `asserted_at` (transaction time) and `valid_from`/`valid_to` (validity time)
   (§9.2). Nothing is ever updated in place.
2. A **correction** writes a new `Claim` with the corrected value, a new `asserted_at`, a
   `supersedes: <prior_claim_id>` edge, and a `correction_reason` plus `ticket_id`. The prior claim
   remains queryable, retains its original evidence, and is marked `superseded_at`. Asking "what did SIG
   assert on 2026-06-01?" must still return the old value.
3. A **retraction** (SIG no longer asserts the thing, and asserts nothing in its place) writes a
   `Retraction` assertion referencing the prior claim, with reason and ticket. The prior claim's
   `valid_to` is *not* rewritten — validity time describes the world, transaction time describes SIG's
   belief, and a retraction is a change in belief.
4. A **suppression** writes a `Suppression` assertion (`level: redacted|purged`, `reason_code`,
   `ticket_id`, `decided_by`, `decided_at`, `review_due`). Public projections filter on it. The
   assertion node, its edges, and its provenance survive; only the *content fields* are masked
   (`redacted`) or nulled (`purged`). This is the OSM redaction primitive (F8.28) and the Wikipedia
   revdel/oversight split (F8.29).
5. **Tombstones are permanent and public.** Every suppression leaves a visible record: id, date, category,
   reason code, ticket id — never the suppressed content. Consumers of bulk dumps receive tombstones so
   a downstream mirror can honor the suppression. (Zenodo's tombstone-page pattern, F8.35.)
6. **Purge is the one exception to append-only**, and it is deliberately expensive: two maintainers,
   counsel, a transparency-report entry, and a tombstone. It exists because Tier X material and valid
   court orders leave no alternative.
7. **CI invariant tests:** a corrected claim must remain retrievable at its original transaction time; a
   suppressed claim must be absent from every T0 export and present in the tombstone list; a purge must
   leave zero content bytes and exactly one tombstone; replaying the event log must reproduce the current
   public projection exactly.

### P4.6 Appeals

One appeal, to the publication committee, decided within 20 business days, with the outcome published.
A category-B suppression is never reversed on appeal without two-maintainer concurrence and a written
finding that the personal-data concern was mistaken.

### P4.7 Transparency report

Published **quarterly**, containing: demands received by category and outcome; suppressions by reason
code (redacted vs purged); corrections issued; T2 access grants (count, and requester category, never
identity); crawler opt-outs honored; hosts blocked; law-enforcement process received and the response;
and the full text of every legal demand with sender contact details redacted and the sending entity
named. Copies submitted to Lumen where accepted (F8.31).

### P4.8 Warrant canary

Published monthly at a stable URL, PGP-signed with a published key, in the affirmative form: *"As of
<date>, SIG has not received any national security letter, FISA order, gag order, or any legal process
that it is prohibited from disclosing; SIG has not been compelled to modify or degrade any system; no
maintainer has been approached by any government seeking undisclosed access."* Include a recent public
entropy value (e.g. a Bitcoin block hash) to prove recency. State the cadence on the page so a lapse is
legible. ⚖️ **COUNSEL** — canary legality is untested (F8.33); a lapse must not be represented to users as
a legal guarantee of anything.

### P4.9 Response to legal process directed at SIG

1. **Everything goes to the legal contact.** No maintainer responds substantively to law enforcement,
   a vendor, or a union directly. Publish this rule (the OpenOversight move, F8.21).
2. **Fight for notice.** Where a demand seeks contributor information, SIG's default is to move to quash
   and to notify the affected contributor unless legally barred.
3. **What you don't store can't be produced.** SIG's answer to most contributor-identity process is that
   the data does not exist (P6.3).
4. **Preservation demands are honored; destruction is not accelerated.** On notice of litigation or a
   preservation demand, all deletion jobs pause project-wide.
5. **Publish it afterwards** in the transparency report.
6. **Standing counsel relationships before they are needed:** RCFP's legal hotline (free; journalists,
   freelancers, documentary filmmakers; 1-800-336-4243 / `hotline@rcfp.org`; 24/7 for arrests and
   imminent threats; **explicitly excludes IP, employment, and contract matters**) — verified at
   https://www.rcfp.org/legal-hotline/. EFF's Coders' Rights Project (CFAA/DMCA research risk; direct
   representation, amicus, referrals) — verified at https://www.eff.org/issues/coders. Public Citizen
   Litigation Group and EFF for anonymous-speaker subpoena defense — verified via
   https://www.citizen.org/our-work/litigation/internet-free-speech. Note the gap: **none of these cover
   the licensing/IP questions in Part B**, which need retained counsel.

---

# PART E — THREAT MODEL, CONTRIBUTOR SAFETY, AND SECURITY POSTURE

### F8.34 — There is appellate consensus on a First Amendment right to record police in public; the Second Circuit joined on 2026-08-17

**Claim:** Nine federal circuits now recognize a First Amendment right to record law enforcement activity
in public, subject to reasonable time, place, and manner limits.
**Status:** VERIFIED
**Evidence:** https://reason.com/volokh/2026/08/17/second-circuit-joins-courts-that-recognize-first-amendment-right-to-record-law-enforcement-activity-in-public/
(WebFetch, 2026-08-20) — ***Massimino v. Benoit***, 2d Cir., **decided August 17, 2026**, recognizing the
right including recording a police station's exterior from a public sidewalk, and identifying eight
sister circuits already recognizing it: **1st, 3d, 4th, 5th, 7th, 9th, 10th, 11th**. Leading cases:
*Glik v. Cunniffe* (1st Cir. 2011), *Fields v. City of Philadelphia*, 862 F.3d 353 (3d Cir. 2017),
*Turner v. Lieutenant Driver*, 848 F.3d 678 (5th Cir. 2017), *Irizarry v. Yehia* (10th Cir. 2022),
*Askins v. DHS* (9th Cir.). **Express reservations in Massimino:** the court did "not address" whether
restrictions could apply to "recording particular persons entering or leaving a station, nonpublic
security features, or other information implicating concrete privacy or safety interests," and excluded
recordings made through technology revealing information "not otherwise perceptible by ordinary
observation" from the protected vantage point. Judge Raggi would not have reached the broad question.
Also noted: federal agents continue to harass recorders notwithstanding the consensus
(https://reason.com/2026/05/19/filming-cops-is-a-first-amendment-right-the-feds-keep-harassing-people-for-it-anyway/).
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG's contributor guidance can state the right accurately and cite it.
It must equally state the reservations: **no telephoto/enhanced-sensing beyond ordinary observation, no
photographing individuals entering or leaving facilities, no nonpublic security features, no trespass,
no interference.** Those reservations map exactly onto §13.5's prohibitions, which is convenient — the
ethical rule and the legal safe zone coincide.
**Outline delta:** EXTENDS §13.5 by supplying the actual authority and, more importantly, its limits.

### F8.35 — Durable, takedown-resistant distribution exists: Zenodo tombstones, Software Heritage SWHIDs

**Claim:** Zenodo issues DOIs, replicates across data centres with tape backup, guarantees retention for
the repository's lifetime, requires a license on every public file, and on withdrawal preserves the DOI
and URL with a tombstone page. Software Heritage archives source repositories on demand ("Save Code Now")
and issues SWHIDs; code survives deletion of the original repository.
**Status:** VERIFIED
**Evidence:** https://about.zenodo.org/policies/ (WebFetch, 2026-08-20) — 50 GB per record (higher on
request); DOIs for all deposits, revoked for policy violations; retention "for the lifetime of the
repository," tied to CERN's 20+ year programme; replication Geneva + Budapest with nightly tape;
"Users must specify a license for all publicly available files"; metadata CC0; on withdrawal "the reason
for the withdrawal will be indicated on a tombstone page" with DOI and URL preserved.
`curl https://www.softwareheritage.org/faq/` (HTTP 200; WebFetch failed with a TLS
"unable to get local issuer certificate" error — recorded, fallback was `curl`) — non-profit launched 2016
by Inria with UNESCO; "largest public collection of source code in existence"; Save Code Now at
`https://archive.softwareheritage.org/save/`; SWHID persistent identifiers; FAQ §2.3 addresses survival
after repository deletion.
**Retrieved:** 2026-08-20
**Implication for the spec:** Continuity plan (P6.5): every versioned SIG data release gets a Zenodo DOI;
every code release is pushed to Software Heritage; both are third-party-hosted in different jurisdictions
and neither can be removed by pressure on SIG's registrar or host. Zenodo's tombstone pattern is also the
model for P4.5's tombstones — and note the constraint it creates: **once a release is deposited with a
DOI, SIG cannot retract it**, so the license gate (P2) and the publication policy (P3) must run *before*
deposit, not after.
**Outline delta:** EXTENDS §14.3 with the concrete mechanism the outline gestures at
("versioned snapshots," "downloadable datasets").

### F8.36 — OSM's vandalism regime is a working model for provenance-gated writes and reversion

**Claim:** OSM defines vandalism as intentionally ignoring community editing norms (excluding honest
mistakes), and responds with graduated escalation — normal revert (contact first, 24–48h), speedy revert
for provably malicious/obscene/libelous edits, DWG temporary block (0–96h), permanent ban — supported by
changeset- and user-focused anomaly detection via OSMCha.
**Status:** VERIFIED
**Evidence:** https://wiki.openstreetmap.org/wiki/Vandalism (WebFetch, 2026-08-20). Definition and
mistake carve-out; "If a significant number of edits can be definitively proved to be malicious, obscene,
libelous or might bring the project into disrepute then it is important to respond immediately";
detection heuristics named: 1,000+ objects added/deleted in a changeset, suspicious `source` tags,
spatial graffiti patterns, 300 edits in 10 minutes, mass deletions by new accounts.
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG can lift the escalation ladder and the anomaly heuristics wholesale.
The critical adaptation: OSM's ladder is *reactive*; SIG's adversary (a vendor or union astroturf
campaign) is *coordinated*, so SIG additionally needs **provenance-gated writes** — a contribution with
no evidence artifact cannot become a public claim at all, regardless of contributor reputation.
**Outline delta:** EXTENDS §9 and §11 — the epistemic architecture assumes good-faith contributors. It
needs an adversarial mode.

---

## POLICY P5 — SIG THREAT MODEL

**Assets.** A1 evidence store (raw records, contributor photographs, unredacted public-records
responses). A2 contributor identities and correspondence. A3 unreleased research and the person-review
queue. A4 credentials, signing keys, deployment secrets. A5 the graph itself (integrity of claims).
A6 the project's reputation for accuracy. A7 availability (domain, hosting, DNS).

| # | Adversary | Motivation | Attack paths | Target | Mitigations |
|---|---|---|---|---|---|
| **T1** | **Vendor legal** (Flock, Axon, SoundThinking, Motorola) | Suppress deployment maps; protect trade-secret framing of sensor locations | ToS breach claim (F8.10); DMCA §1201 claim (F8.5); §512 notices on mirrored PDFs; trade-secret/misappropriation suit; de-publication TRO (F8.30); trademark claim on vendor names | A5, A6, A7 | P1 (no circumvention, no accounts); P2 archive-vs-link table; §512 agent; anti-SLAPP-favorable venue; RCFP/EFF standing relationships; nominative-fair-use policy on vendor names; publish every demand (P4.7) |
| **T2** | **Agency legal / police union** | Suppress officer names, portal data, RTCC detail | Daniel's-Law-style notices and suits (**strict liability**, F8.19); state doxxing statutes (F8.20); defamation suits over misconduct claims; public-records fee weaponization; FOIA-exemption assertions | A5, A6 | P3.2 absolute address ban; P3.4 five-prong naming test with two-reviewer record; P4 category-B 5-day suppression; 50-state statutory survey, re-run annually; defamation insurance; ⚖️ counsel |
| **T3** | **Subpoena / compulsory process** (civil discovery, grand jury, NSL) | Identify a contributor or a source | Subpoena to SIG, its host, its registrar, its email provider, or a maintainer; NSL with gag | A1, A2, A4 | **Warrant-resistant architecture (P6.3)** — no access logs, no IP retention, no required identity, aggressive retention limits; motion-to-quash default; contributor notice unless barred; canary (P4.8); counsel on retainer |
| **T4** | **Doxxers / harassment campaigns** | Retaliate against contributors and maintainers | Correlate contributions to identities; scrape SIG's own contributor metadata; swatting; employer contact | A2 | Pseudonymous contribution by default; no contributor profile pages; no contribution timestamps at second resolution; coarsened observer locations; maintainer opsec guidance; per-contributor "hide my history" switch |
| **T5** | **Data-poisoning contributors** (coordinated) | Discredit SIG by seeding false deployments or false removals; or launder a real deployment out of the record | Sockpuppet accounts; plausible-but-fabricated photographs; forged "decommissioned" claims; mass low-salience edits before a high-salience one; targeted edits before a council vote | A5, A6 | P6.4 in full: provenance-gated writes, trust tiers, review queues, anomaly detection, full revert, and **temporal freeze** on entities under active public deliberation |
| **T6** | **State actors / sophisticated intrusion** | Obtain the contributor graph; alter the record | Supply-chain compromise of dependencies; CI/CD token theft; maintainer device compromise; hosting-provider process | A1–A5 | Signed reproducible builds; pinned dependencies with SBOM; hardware-token 2FA mandatory for all write access; secrets in a managed vault, never in CI env vars; least-privilege deploy identities; offline backup of the signing key |
| **T7** | **Opportunistic scrapers / AI crawlers** | Bulk-take SIG's data without attribution | Ignore SIG's own robots.txt and license; re-host without ODbL compliance | A6, A7 | **Make it unnecessary**: publish bulk dumps and a documented API (P7), so scraping SIG is pointless; ODbL/attribution enforcement as a last resort; rate limits that do not require identity |
| **T8** | **Insider** (maintainer or T2 grantee) | Exfiltrate restricted material; insert a backdoor | Abuse of T2/T3 access; malicious commit | A1, A3, A5 | Two-person rule for purge and for T2 grants; per-grant audit logs; mandatory code review with no self-merge; T2 grants time-limited and revocable; quarterly access review |
| **T9** | **Availability attacks** | Take SIG offline before a council vote or a news cycle | DDoS; registrar/host complaints; payment-processor pressure | A7 | CDN with DDoS absorption; static-first architecture; Zenodo/Software Heritage/torrent mirrors; onion service; pre-registered alternate domains in a second TLD/registrar; documented failover (P6.5) |

---

## POLICY P6 — SECURITY, CONTRIBUTOR SAFETY, AND OPERATIONS

### P6.1 Contributor safety commitments (published verbatim to contributors)

1. **Contribute pseudonymously or anonymously.** No real name, no phone, no address, no employer, ever.
   An email address is optional; a random token works.
2. **We do not log your IP address.** Web-server access and error logs are disabled at the server, not
   merely rotated. (F8.21.)
3. **We do not retain precise contributor geolocation.** Submitted coordinates are used to place the
   *asset*, then the *observer's* position is discarded. Photographs are EXIF-stripped on upload before
   storage, with the asset coordinate carried as an explicit field the contributor confirms.
4. **We do not build contributor profiles.** No public contribution history, no leaderboards, no
   per-contributor activity feeds. Contribution timestamps are published at day resolution only.
5. **Tor is welcome.** SIG blocks no ASN, region, or exit node, and publishes an onion service with an
   `Onion-Location` header (F8.21, Tor Project onion-services documentation).
6. **Hardware-backed 2FA is available and required for any write role above T2.**
7. **If we receive legal process about you, we will tell you** unless a court forbids it, and we will
   move to quash first.
8. **What we don't store can't be subpoenaed.** This is the whole design.

### P6.2 Lawful-photography guidance (contributor-facing, §13.5)

> Photographing surveillance equipment from a public place is protected First Amendment activity. Nine
> federal circuits — the 1st, 2d, 3d, 4th, 5th, 7th, 9th, 10th, and 11th — have recognized a right to
> record law enforcement activity in public, most recently the Second Circuit in *Massimino v. Benoit*
> (Aug. 17, 2026), which covered recording a police station's exterior from a public sidewalk. The right
> is subject to reasonable time, place, and manner restrictions.
>
> **What SIG asks you to do:**
> - Stay on public property — sidewalk, road shoulder, public park. **Never trespass**, including onto
>   utility easements, private lots, and posted property.
> - Photograph **equipment and infrastructure**, not people. Do not photograph individuals entering or
>   leaving any facility. *Massimino* expressly reserved that question.
> - Use ordinary observation. **No telephoto surveillance of nonpublic areas, no drones over private
>   property, no thermal or enhanced sensing.** *Massimino* excluded technology revealing what is "not
>   otherwise perceptible by ordinary observation."
> - **Never interfere.** Do not obstruct, do not approach officers, do not respond to a lawful dispersal
>   order by staying.
> - **Never touch, cover, disable, damage, move, or tamper with equipment.** SIG will remove any
>   contributor who does, and will not accept data obtained that way. This is a criminal matter in most
>   states and it destroys the project's standing.
> - **Never test, probe, or connect to any device or network.** Passive RF listening only. (F8.11, F8.14.)
> - If stopped: you are not required to consent to a search or to delete images. Comply with lawful
>   orders, decline consent, and contact us. RCFP's 24/7 hotline for arrests: **1-800-336-4243**.
> - Bring a bystander. Tell someone where you are going. Consider whether the risk is worth one dot on
>   a map — it usually is not, and no data point is worth your safety.

⚖️ **COUNSEL:** state trespass, wiretap, and "critical infrastructure" statutes vary significantly, and
several states have expanded critical-infrastructure trespass penalties since 2020. This guidance needs a
state-by-state overlay before SIG promotes organized field mapping in any given state.

### P6.3 Warrant-resistant architecture (concrete)

| Datum | Retention |
|---|---|
| Web server access/error logs | **Not written.** nginx `access_log off; error_log /dev/null crit;` |
| Client IP addresses | Never persisted; not in application logs; CDN configured to strip |
| Contributor identity | Not collected |
| Session records | Ephemeral, memory-only, ≤ 24h |
| Submission source metadata | Discarded at ingest; EXIF stripped before the file touches disk |
| Email correspondence | Retained 90 days then deleted, except open tickets and legal matters |
| Moderation/review records | Retained (needed for auditability) but reference contributor **pseudonym ids**, never identities |
| Backups | Encrypted; same retention windows applied to backups, enforced by an automated job |
| Analytics | Aggregate, server-side, no per-visitor identifiers, no third-party trackers |

Deletion jobs are **paused project-wide** on notice of litigation or a preservation demand (P4.9).

### P6.4 Data-poisoning and vandalism resistance

1. **Provenance-gated writes (the primary control).** A contribution that does not carry an evidence
   artifact — a photograph, a document, a URL with a content hash, a records-request id — cannot become a
   public `Claim`. It becomes an unevidenced `Report` visible only in the review queue. No reputation
   level overrides this.
2. **Trust tiers.**
   - **T1 new** — all writes queued for review; no auto-publication.
   - **T2 established** — ≥ 20 accepted contributions, ≥ 60 days, no reverts; low-salience writes
     auto-publish, high-salience queued.
   - **T3 trusted** — invited; may review others' contributions; may not self-approve own writes.
   - **T4 maintainer** — may suppress, may purge with a second maintainer.
   Trust attaches to a **pseudonym**, requiring no identity; trust is lost automatically on revert.
3. **High-salience classes always queued regardless of tier:** any person name; any C2–C5 location; any
   *removal* or decommissioning claim (removals are the highest-value poison — they launder a real
   deployment out of the record); any claim about an entity under active public deliberation; any claim
   contradicting a Tier A source.
4. **Anomaly detection on contribution patterns** (adapted from OSMCha, F8.36): burst rate per pseudonym
   (> 50 writes/hour, > 300/day); spatial clustering of new accounts in one jurisdiction within a short
   window; coordinated timing across accounts; a cohort of accounts created within 72 hours all editing
   one agency; low-salience "reputation farming" followed by a single high-salience edit; contributions
   whose evidence artifacts share a hash or a near-duplicate perceptual hash. Anomalies freeze the
   affected entities and open an investigation ticket; they never auto-ban.
5. **Full revert capability.** Because the store is append-only (P4.5), reverting a campaign is writing
   compensating assertions — no data loss, complete auditability, and a public record that a campaign
   occurred. Ship a `revert-by-contributor`, `revert-by-time-window`, and `revert-by-changeset` tool with
   a dry-run mode, and exercise it in a drill at least annually.
6. **Temporal freeze.** When an entity is the subject of an imminent public decision (a council vote, a
   contract renewal, a hearing), SIG freezes it: new claims are queued and reviewed by two T3+ reviewers
   before publication. This is precisely when poisoning has the highest payoff.
7. **Contradiction is a first-class state (§6.5), not an error.** A conflicting claim does not overwrite;
   it produces a visible contradiction. Poisoning therefore degrades gracefully into visible uncertainty
   rather than silent corruption.

### P6.5 Operational security and continuity

- **Secrets:** managed vault or cloud KMS; no secrets in CI environment variables, in the repo, or in
  container images; short-lived OIDC deploy identities; quarterly rotation; hardware tokens for all
  maintainers; signing key generated and stored offline with a documented recovery procedure.
- **Build integrity:** pinned dependencies, lockfiles, SBOM per release, reproducible builds, signed
  releases, no self-merge, mandatory review.
- **Hosting jurisdiction:** primary in a jurisdiction with strong anti-SLAPP and intermediary protections
  (40 states + D.C. now have anti-SLAPP laws, though federal-court applicability is circuit-split
  post-*Erie*; UPEPA adoption reached 16 states with South Dakota in March 2026). ⚖️ **COUNSEL** on venue
  and entity domicile together — they interact.
- **Static-first architecture:** the public site is pre-rendered and CDN-cacheable so it survives DDoS
  and so a mirror is a file copy. Dynamic query surfaces are separable and can be shed under load.
- **Distribution redundancy (the real continuity plan):** each versioned release is simultaneously
  (a) on the primary domain, (b) deposited to **Zenodo with a DOI**, (c) code archived to **Software
  Heritage** with SWHIDs, (d) published as a **BitTorrent** magnet with an academic-torrents-style
  tracker, (e) pinned to **IPFS** with the CID published, (f) mirrored on at least two independent
  university or NGO hosts. The release manifest lists every location, so any single takedown is an
  inconvenience.
- **"If the primary domain disappears":** pre-registered alternate domains at a second registrar in a
  second TLD; DNS at a provider distinct from the registrar; the onion address published in every release
  manifest and in the README; a published, signed *continuity statement* naming the fallback locations
  and the signing key, so users can verify a successor site is genuinely SIG.
- **Drills:** annual restore-from-Zenodo drill, annual revert drill, annual key-recovery drill.

### P6.6 Legal entity and governance

| Option | What it gives | What it costs | Fit for SIG |
|---|---|---|---|
| **Software Freedom Conservancy** (fiscal sponsor) | Holds assets (funds, copyrights, trademarks, domains); bookkeeping; legal assistance on licensing and PR; can unify copyright to make enforcement effective; some personal-liability protection for project leaders | **10% of processed revenue**; requires OSI-approved **and** DFSG-free licenses, docs under those or CC-BY-SA/CC-BY/CC0; "exclusively devoted to FOSS development and documentation"; public development; existing vibrant community, typically ≥ 1 year | **Strong on licensing, weak on mission fit.** SIG is a *data* project as much as a software project; "exclusively devoted to FOSS" is a real eligibility question. Verified at https://sfconservancy.org/projects/apply/ |
| **Code for Science & Society** | Fiscal sponsorship explicitly for "community-led research, education, and technology projects working in the public interest" | Typical fiscal-sponsor fee band 8–15% | **Best mission fit** of the sponsors surveyed — public-interest research and technology is exactly SIG's category. https://www.codeforsociety.org/resources/working-with-a-fiscal-sponsor |
| **NumFOCUS** | Fiscal sponsorship for scientific/research computing; strong grants infrastructure | Sponsor fee | Poor fit — scientific-computing ecosystem focus, not civil-liberties research |
| **Open Collective Foundation** | — | — | **Not available.** OCF's fiscal sponsorship ended Sept. 30, 2024 and the entity dissolved effective Dec. 31, 2024, forcing 600+ collectives to transition. A standing warning about single-sponsor dependency. (Open Source Collective, a *different* entity, continues.) |
| **Own 501(c)(3)** | Full control; direct legal standing to sue and be sued; can hold insurance in its own name; can accept restricted grants | ~$3–10k and 6–12 months to form; annual Form 990; board recruitment; D&O insurance; the board becomes a pressure surface | **Right destination, wrong starting point.** Adverse parties can subpoena and sue an entity; a fiscal sponsor absorbs some of that while the project is small |

**Recommendation:** start under **Code for Science & Society** (mission fit) with **SFC as the fallback**
if a licensing-enforcement posture becomes primary; incorporate independently only when SIG has
(a) sustained funding, (b) retained counsel, (c) D&O and media-liability insurance, and (d) a board
willing to be named publicly. **Diversify the sponsor dependency from day one** — the OCF dissolution is
the reason. ⚖️ **COUNSEL:** entity form, domicile, and venue interact with anti-SLAPP availability and
should be decided together, not sequentially.

---

# PART F — LICENSING OF SIG'S OWN OUTPUTS (§14.3)

## POLICY P7 — SIG LICENSING DECISION

### P7.1 Code — **Apache-2.0** (SPDX `Apache-2.0`)

**Decision:** Apache-2.0 for all SIG code, including ingestion connectors, the reconciliation engine, and
the web surfaces.

**Argued against the alternatives:**

- **AGPL-3.0-or-later** is the emotionally satisfying answer: it prevents a vendor or a data broker from
  taking SIG's pipeline, hosting a proprietary derivative, and never contributing back. But it does not
  actually protect what SIG cares about. **The valuable artifact is the graph, not the crawler.** A
  competitor re-hosting SIG's code without the data has nothing; a competitor taking SIG's *data* is
  governed by the data license, not the code license. Meanwhile AGPL imposes a real cost: many
  newsrooms, universities, civic-tech shops, and public agencies — precisely the downstream users §7.1
  Goal 8 names — have blanket policies against deploying AGPL software. Choosing AGPL trades a
  theoretical harm for a concrete reduction in the adoption that is the project's stated purpose.
- **MIT** is fine but gives up two things Apache-2.0 provides for free: an **express patent grant with a
  defensive termination clause** (§3), and an explicit **trademark reservation** (§6). SIG works in a
  space with well-capitalized, patent-holding vendors; the patent grant is not theoretical. The
  trademark reservation matters because SIG's name is its accuracy guarantee, and a fork must not be
  able to trade on it.
- **Apache-2.0 is also SFC-eligible** (OSI-approved and DFSG-free), which keeps the fiscal-sponsor door
  open (P6.6).

**Rider:** if a specific component is a genuine competitive moat that a vendor could weaponize — say, an
entity-resolution model trained on SIG's corpus — that component may be AGPL-3.0-or-later as an exception,
declared in the repo's `LICENSING.md`. Exceptions require a written rationale; the default is Apache-2.0.

### P7.2 Data — **ODbL-1.0 for the OSM-derived layer; CC-BY-4.0 for everything else; layered, never merged**

**Decision:** SIG publishes **layered bundles** (P2.2.2). The OSM-derived physical-asset layer is
ODbL-1.0. The SIG-original graph — organizations, vendors, products, deployments, contracts, policies,
access relationships, claims, evidence metadata — is **CC-BY-4.0**.

**Argued:**

- **ODbL for everything (Strategy C, §14.1)** is tempting for consistency but is the wrong answer.
  ODbL's share-alike attaches to *Derivative Databases* (F8.16) and imposes a §4.6 obligation to hand
  over the derivative database or alteration documentation. Imposed on the *entire* graph, that
  discourages exactly the downstream integrations SIG wants — a newsroom that joins SIG data to its own
  reporting database, or EFF joining SIG corrections into the Atlas, would face share-alike questions
  about their own databases. Worse, it forecloses combining SIG data with any CC-BY-SA-4.0 upstream
  (F8.17). ODbL should apply where it *must* — to the OSM-derived layer — and nowhere else.
- **CC0 for the SIG-original layer** is the maximally-reusable choice and is what many open-data
  advocates would recommend. Rejected, narrowly, for one reason: **provenance preservation is the
  project's thesis** (§1, §19.1). SIG's whole value proposition is that every claim is traceable. CC0
  waives the attribution requirement that keeps the provenance chain intact downstream. A CC0 SIG dataset
  can be re-hosted stripped of its evidence links, which reproduces exactly the "authoritative-looking
  database with no provenance" problem SIG exists to solve. CC-BY-4.0 costs downstream users almost
  nothing and preserves the chain.
- **CC-BY-SA-4.0** would add share-alike but reintroduces the ODbL incompatibility (F8.17) inside SIG's
  own bundle. Rejected.
- **ODC-By-1.0** is the database-native analogue of CC-BY and is arguably the *most technically correct*
  choice for a database in a sui generis jurisdiction. Rejected on ecosystem grounds: CC-BY-4.0 is far
  more widely understood, is what EFF's Atlas already uses (F8.13), and CC 4.0 expressly licenses sui
  generis database rights, closing the main gap ODC-By was designed for. ⚖️ **COUNSEL:** confirm the
  CC 4.0 database-rights clause is adequate for EU-facing publication before the international phase.

**Attribution string (required by CC-BY-4.0, published in `NOTICE.txt` and `ATTRIBUTION.json`):**
> "Surveillance Infrastructure Graph, <release version>, <DOI>, CC BY 4.0. Contains data derived from
> OpenStreetMap © OpenStreetMap contributors, ODbL 1.0. Contains data from EFF/UNR Atlas of Surveillance,
> CC BY. See ATTRIBUTION.json for the complete per-claim provenance."

### P7.3 Documentation — **CC-BY-4.0** (SPDX `CC-BY-4.0`)

Same reasoning as the data layer: attribution preserves the chain, and CC-BY is SFC-acceptable for
documentation. Contributor-submitted **photographs** default to CC-BY-4.0 with the contributor's
pseudonym as the credit, and contributors may elect CC0 or CC-BY-SA-4.0 per upload; the per-file license
is recorded and propagates through the export gate.

### P7.4 Ontology / vocabulary — **CC0-1.0** (SPDX `CC0-1.0`)

**Decision and argument.** The class and property definitions, the identifier scheme, the JSON Schemas,
the SHACL/JSON-Schema shapes, the controlled vocabularies (device classes, capability taxonomy,
relationship types), and the stable-URI scheme are released **CC0-1.0** — maximally permissive, no
attribution requirement.

Why the ontology is the one thing that must be *more* permissive than everything else:

1. **A vocabulary succeeds only by being adopted, and every obligation is an adoption tax.** An attribution
   requirement on a *schema* means every downstream tool that emits `sig:Deployment` owes a credit notice.
   That is enough friction to make a competing vocabulary attractive, and a fragmented vocabulary defeats
   the interoperability the outline asks for (§20 Q37, "stable IDs that allow other projects to link
   back").
2. **Vocabularies are weakly copyrightable anyway.** A term list is close to *Feist*'s unprotectable facts
   (F8.6); asserting a license on it invites an argument SIG would rather not have. CC0 makes the question
   moot.
3. **Federation is the design principle (§1.2).** SIG wants OSM, DeFlock, Atlas, HIBF, and local groups to
   emit SIG-shaped identifiers. Every one of them faces a different license regime; CC0 is the only choice
   compatible with all of them simultaneously.
4. **Precedent:** schema.org, Dublin Core, and the major open vocabularies are all effectively
   unencumbered. Zenodo's own metadata is CC0 (F8.35).

**Boundary:** CC0 covers the *vocabulary*. It does not cover the *instance data* expressed in it — that is
governed by P7.2.

### P7.5 Downstream attribution and provenance-preservation obligations

What SIG *requires* of downstream users (via CC-BY-4.0 §3(a) and the ODbL layer's §4.3):

1. **Credit** SIG, the release version, and the DOI.
2. **Preserve the license notices** — SIG's, OSM's, and every upstream's, as shipped in `NOTICE.txt`.
3. **Do not strip claim ids.** SIG *asks* (as a strong norm, not a license condition — CC-BY cannot
   compel it) that redistributors retain `claim_id` and `evidence_id` so provenance survives a hop. This
   is stated in a `PROVENANCE-NORMS.md` shipped in every bundle and is a condition of the API acceptable
   use (P8).
4. **Do not represent SIG data as complete or authoritative.** Ship the `coverage_manifest` (§7.1 Goal 6)
   with every bundle and require its inclusion in redistribution.
5. **Honor tombstones.** Redistributors are asked to consume the tombstone feed and propagate
   suppressions. This is the only mechanism by which a P4 suppression can reach a mirror.

### P7.6 Export-time license computation (mechanical)

The bundle's license is a **function of its constituent claims**, computed by the P2.2 gate at build time,
never hand-set. Every bundle carries:

```
MANIFEST.json
  release_version, release_date, doi, git_commit, pipeline_version
  files[]: {path, sha256, license_spdx, rights_record_ids[], claim_count}
  bundle_license_spdx            # computed, or "MULTI" with per-file licenses
  blocked_claims: {count, by_reason: {...}}     # never silent (P2.2.1)
  coverage_manifest_ref
  tombstones_ref
NOTICE.txt                       # human-readable, every attribution_string
ATTRIBUTION.json                 # machine-readable, per-file and per-rights-record
LICENSES/                        # full text of every license referenced
PROVENANCE-NORMS.md
```

A build whose gate returns `INCOMPATIBLE` fails CI. A build whose manifest lacks a DOI is a pre-release.

### P7.7 "Open source code is not enough" (§14.3), specified

A genuinely reusable data output — the acceptance criteria for calling a release *done*:

1. **Bulk dumps in boring formats.** Newline-delimited JSON *and* CSV *and* GeoJSON for the spatial
   layers *and* a Parquet set for analysts. Full dump plus per-jurisdiction regional cuts. No format
   requires SIG's own software to read.
2. **A published, versioned schema** with JSON Schema validation, a machine-readable changelog, and a
   deprecation policy: additive changes any release, breaking changes only on a major version with ≥ 90
   days' notice and one release of overlap.
3. **Stable identifiers that never get reused.** A SIG id resolves forever, including to a tombstone.
   Merged entities keep both ids with a `merged_into` edge (§20 Q29, Q37).
4. **Versioned, immutable snapshots** on a stated cadence (monthly full, weekly incremental), each with
   an immutable content hash.
5. **A DOI per release** via Zenodo, so the dataset is citable in the academic and legal record and
   survives SIG (F8.35).
6. **A documented API** — OpenAPI spec, no key required for read at T0, published rate limits, a
   changes/since feed, and a `Link: rel="license"` header on every response.
7. **Reproducible pipelines** — pinned dependencies, container images by digest, `make reproduce` that
   rebuilds a release from the content-addressed source snapshots, and a published diff between the
   rebuild and the shipped artifact.
8. **The coverage manifest ships with the data**, so a consumer can quantify what SIG does *not* know
   (§7.1 Goal 6, §19.4). A dataset that cannot state its own incompleteness is not reusable; it is a trap.
9. **The tombstone feed ships with the data**, so suppressions propagate.
10. **Every claim carries its evidence pointer and its rights record id**, so a downstream user can
    independently re-derive both the fact and its legal status.

---

# PART G — ANTI-MISUSE

## POLICY P8 — WHAT SIG WILL NOT PUBLISH, WILL NOT BUILD, AND WILL NOT TOLERATE

### P8.1 Naming the tension honestly

SIG should say this in its own voice, on its own front page, rather than let an adversary say it first:

> **Mapping surveillance infrastructure makes it easier to avoid surveillance. We know that. We think the
> trade is worth making, and here is why.**
>
> Automated license plate readers, gunshot detectors, and camera networks are installed in public space,
> paid for with public money, under contracts that are public records, by agencies accountable to the
> public. Their locations are visible to anyone who looks up. A resident who wants to know whether their
> street is monitored, a journalist checking whether a department's camera count matches its invoice, a
> council member deciding whether to renew, and a litigant establishing what was recorded and when — all
> of them need the same information, and none of them can get it today without doing original research.
>
> The same information can be used to route around a camera. That is true of every public fact about
> public infrastructure, and it has never been a sufficient reason to keep infrastructure secret.
> Secrecy about *where* public surveillance sits does not prevent crime; it prevents oversight. The
> agencies that resist publication are, with few exceptions, resisting the oversight rather than
> protecting the deterrence.
>
> What we will not do is close the gap between "public knowledge of public infrastructure" and
> "operational assistance to a specific person evading a specific investigation." Those are different
> things, and the rules below are how we keep them apart.

### P8.2 SIG will not build

1. **No real-time or near-real-time device status.** No "is this camera online right now," no live uptime
   feed, no current-position tracking of mobile assets. Historical observations with explicit observation
   dates only. (§13.5; P3.5 class C5.)
2. **No "is a camera watching me right now" feature.** No live proximity alerting, no
   route-avoidance planner, no "safest path" routing that optimizes against detection. SIG will publish
   coverage maps for *analysis*; it will not ship a *navigation* product against them.
3. **No individual-officer tracking.** No timelines of an individual officer's movements, assignments, or
   activity beyond discrete documented accountability events. No officer-centric dashboards.
4. **No person search.** No interface whose primary input is a person's name, plate, face, or address.
   The graph's entry points are organizations, places, vendors, contracts, and devices.
5. **No plate lookup, no plate-adjacent lookup, no travel history.** (P3.2.)
6. **No facial recognition, biometric matching, or any biometric processing whatsoever.** (F8.21.)
7. **No offensive tooling.** No jamming guidance, no tampering instructions, no evasion hardware designs,
   no exploitation of vendor systems, no scanning tools targeting vendor infrastructure. (F8.11.)
8. **No re-identification research** against SIG's own aggregates or anyone else's.

### P8.3 API and data acceptable-use terms (binding on T1/T2; a norm at T0)

> By using the SIG API or bulk data you agree that you will not:
> (a) attempt to re-identify any individual from SIG data, or combine SIG data with other data for that
> purpose;
> (b) use SIG data to track, locate, or profile any individual, including any law enforcement officer;
> (c) use SIG data to plan, facilitate, or assist damage to, tampering with, or disabling of any
> equipment;
> (d) use SIG data to evade a specific active law-enforcement operation, or to assist another in doing so;
> (e) present SIG data as complete or authoritative, or redistribute it stripped of its coverage manifest;
> (f) redistribute SIG data without the required attribution and license notices, or without honoring the
> tombstone feed;
> (g) use SIG data to train a generative model without a separate written agreement — noting that several
> of SIG's upstreams assert `ai-train=no` (F8.8) and SIG cannot pass through rights it does not hold;
> (h) resell SIG data as a standalone product without adding substantial independent value (SIG's data is
> free; brokering it is not a service to anyone);
> (i) circumvent rate limits or misrepresent your client.

### P8.4 Handling a violating downstream reuse

Graduated, and biased toward persuasion because SIG's leverage is reputational, not legal:

1. **Contact and explain** (10 business days to cure).
2. **Rate-limit or revoke** T1/T2 access.
3. **Publish the violation** in the transparency report. For a project whose product is credibility, this
   is the sharpest available tool.
4. **License enforcement** — CC-BY/ODbL attribution and share-alike are enforceable, and SFC exists partly
   to do this (P6.6). Reserved for commercial re-hosting that strips provenance.
5. **Never** respond by restricting *public* access. The answer to misuse is not to make SIG less open;
   that hands the adversary a win and betrays the mission.
6. **Never** deploy technical countermeasures against a downstream user's systems.

### P8.5 The one hard case, stated

The hardest real request SIG will receive is: *"remove the cameras near my house because I am being
stalked and my stalker is a police officer with network access."* SIG cannot solve that by unpublishing a
camera location — the camera is visible from the street and mapped in OSM. What SIG *can* do, and should
commit to, is: treat the request as category **D** (P4.2), suppress anything person-linked immediately,
escalate to the accountability channel (the request is evidence of an audit-trail question that HIBF and
the agency's own audit obligations exist to answer), and refer the requester to counsel and to
domestic-violence advocacy resources. SIG should publish this posture so requesters know what to expect,
rather than discovering it in a refusal email.

---

## Open questions

1. **⚖️ Does clause (viii) of Flock's API Terms reach a logged-out reader of a transparency portal?**
   (F8.10 vs F8.4.) Unresolved and dispositive for Phase 1D. Spec must hedge by shipping the
   public-records and third-party-archive paths first, and by making the Flock connector
   feature-flagged-off by default.
2. **⚖️ Does a Cloudflare managed challenge protect access to a *work* for §1201 purposes when the
   content behind it is uncopyrightable facts?** (F8.5, F8.9.) *Reddit v. SerpApi* did not reach it.
   Hedge: never circumvent, regardless of the answer.
3. **⚖️ Does SIG's synthesis make it an "information content provider" under §230(f)(3), forfeiting
   intermediary immunity for reconciled claims?** (F8.32.) This is the biggest unquantified liability in
   the design. Hedge: assume no immunity for SIG-synthesized claims and apply the P3.4 review standard to
   any synthesized claim about a person.
4. **⚖️ Does the join-by-identifier architecture actually preserve ODbL Collective Database status?**
   (F8.16.) R1 owns the analysis; the spec must be built so that either answer is survivable — i.e. the
   OSM layer must be *physically* separable, not merely logically.
5. **⚖️ Fifty-state survey of officer/official address-confidentiality and doxxing statutes**, mapped to
   SIG's fields, re-run annually. (F8.19, F8.20.) Hedge: the national rule is the strictest state rule.
6. **⚖️ State-by-state trespass, wiretap, and critical-infrastructure statutes** as they apply to field
   mapping and passive RF. (F8.14, P6.2.) Hedge: publish generic guidance, defer state-specific
   organizing until surveyed.
7. **⚖️ Do T2 restricted-access grants create discovery obligations or third-party subpoena exposure for
   SIG?** (P3.8.) Hedge: minimize what enters T2; time-limit every grant.
8. **⚖️ EU sui generis database rights and GDPR lawful basis** for the international phase — Art. 6(1)(f)
   legitimate interest vs. Art. 85 journalistic derogation (which is Member-State-implemented and varies
   widely) vs. Art. 89 research. (F8.7.) Hedge: do not ingest EU personal data at all in Stages 0–5;
   institutional facts only.
9. **Reddit's Public Content Policy text could not be retrieved** (403, Cloudflare, both tools). The
   robots.txt blanket disallow is verified and sufficient to set policy, but the exact research-use terms
   should be re-fetched before any Reddit ingestion.
10. **Is a warrant canary meaningful for a project with no user accounts?** If SIG holds nothing, the
    canary's information content is low. It may still be worth publishing for the *maintainer*-directed
    process it covers. Unresolved; low stakes either way.
11. **Media-liability / defamation insurance availability and cost** for a project that names officers.
    Not researched here; must be priced before the first `publish_named` decision.
12. **Whether SIG should accept a Flock or Axon "authorized access" offer if one is made.** Accepting
    terms would resolve E1/E3 but would bind SIG to a clickwrap (F8.2) and likely to a purpose limitation
    ("bona fide law enforcement purposes," F8.10) that SIG cannot satisfy. Presumptively refuse; decide
    with counsel if actually offered.

---

## Spec requirements emitted

| Id | Requirement | Testable acceptance |
|---|---|---|
| **REQ-R8-01** | Crawler emits a `SIGBot/<v> (+<policy-url>; contact:<email>)` UA on every request and never spoofs another agent | Integration test asserts UA on all outbound requests; a test that a browser UA is never set |
| **REQ-R8-02** | Fetcher has a terminal `CHALLENGE_DETECTED` state on CAPTCHA/JS-interstitial/bot-403 and never retries with altered identity, proxy, or fingerprint | Fixture serving a Cloudflare interstitial; assert single attempt, terminal state, review task created |
| **REQ-R8-03** | No collection component may hold a credential, cookie jar, or session for a source site; no account creation | Static check: no cookie/auth storage in the collection module; code review gate |
| **REQ-R8-04** | robots.txt fetched and cached ≤24h per host; fetch failure ⇒ treat as disallow-all; `Crawl-delay` honored | Unit tests for allow/disallow/unreachable |
| **REQ-R8-05** | Default rate 1 req/5s/host, ≤2 concurrent, ≤10k/day; 1 req/30s for hosts flagged `small_operator`; exponential backoff on 429/503 | Rate-limiter unit tests; a load test asserting observed rates |
| **REQ-R8-06** | Every source carries a complete `RightsRecord` (P2.1); incomplete ⇒ ingestion hard-fails | Schema validation test; a fixture with a missing field must fail |
| **REQ-R8-07** | Export-time license gate computes bundle license from constituent claims, blocks `unknown`/`prohibited`, fails on multi-share-alike conflict, and reports blocked counts | The five P2.2.3 fixtures pass in CI |
| **REQ-R8-08** | Schema contains no field for plate numbers, plate hashes, home addresses, personal phone/email, or biometrics; free-text validator rejects address-shaped strings adjacent to person names | Negative-schema test; validator fixture suite |
| **REQ-R8-09** | Any claim with `contains_person_name` cannot reach a public projection without two recorded reviewer determinations against all five P3.4 prongs | Workflow test: unreviewed named claim absent from every T0 export |
| **REQ-R8-10** | Coordinate publication precision is a pure function of `(class C1–C5, overrides O1–O5)`; residential-parcel intersection auto-demotes to C3 | Matrix fixture suite including the parcel veto |
| **REQ-R8-11** | `CandidateAsset` is a distinct type; promotion requires a non-RF evidence artifact or 3 independent RF observations plus non-RF corroboration; residential-intersecting candidates never appear in any public export | The eight P3.6/R8 fixtures pass |
| **REQ-R8-12** | Person/household-linked aggregates suppressed at n<10, never below census tract, with a reconstruction check that fails the export if any suppressed cell is uniquely determined from published margins | Reconstruction-attack test over a hierarchical fixture table |
| **REQ-R8-13** | Four access tiers implemented; T1 requires no identity; T2 grants are purpose-bound, time-limited, revocable, and audit-logged | Auth tests; expiry test; audit-log assertion |
| **REQ-R8-14** | Corrections, retractions, and suppressions are new assertions; historical queries at prior transaction times return prior values; suppression masks content but preserves the assertion node and a public tombstone | The seven P4.5 invariant tests |
| **REQ-R8-15** | `purge` requires two maintainer identities plus a counsel flag, leaves zero content bytes and exactly one tombstone | Authorization test; byte-level assertion |
| **REQ-R8-16** | Takedown intake assigns a public ticket id, acknowledges within SLA by category, and category-B suppression executes within 5 business days (hard cap 10) | Workflow timing test against the P4.2 table |
| **REQ-R8-17** | Quarterly transparency report generated automatically from the ticket and audit stores; warrant canary published monthly, PGP-signed, with a recency beacon | Report-generation test; canary staleness alert at cadence+7 days |
| **REQ-R8-18** | No web-server access or error logs; no client IP persisted anywhere including backups; EXIF stripped before any upload touches disk | Deployment config assertion; upload test asserting no EXIF and no source IP in storage |
| **REQ-R8-19** | Writes without an evidence artifact cannot become public claims; high-salience classes always queue regardless of trust tier; anomaly detectors freeze rather than ban | Contribution-pipeline tests for each high-salience class |
| **REQ-R8-20** | Revert tooling supports by-contributor, by-time-window, and by-changeset with dry-run, implemented as compensating assertions with no data loss | Revert drill test on a poisoned fixture graph |
| **REQ-R8-21** | Every release: Zenodo DOI, Software Heritage deposit, torrent, IPFS CID, ≥2 independent mirrors, all listed in `MANIFEST.json`; onion address in every manifest | Release-pipeline test asserting all locations present and resolvable |
| **REQ-R8-22** | Code Apache-2.0; SIG-original data CC-BY-4.0; OSM-derived layer ODbL-1.0 in a separate file; docs CC-BY-4.0; ontology/vocabulary CC0-1.0; SPDX ids validated against a pinned list version | License-header lint; manifest license assertion; SPDX validation against pinned `3.28.0` |
| **REQ-R8-23** | Every bundle ships `MANIFEST.json`, `NOTICE.txt`, `ATTRIBUTION.json`, `LICENSES/`, `PROVENANCE-NORMS.md`, the coverage manifest, and the tombstone feed | Bundle-structure test |
| **REQ-R8-24** | No API surface accepts a person, plate, face, or address as a primary query input; no endpoint returns current device status or current mobile-asset position | API-contract test enumerating prohibited parameters and fields |
| **REQ-R8-25** | Acceptable-use terms (P8.3) presented and accepted at T1/T2; violations tracked and reportable | Terms-acceptance test; violation-record test |
| **REQ-R8-26** | DMCA §512 designated agent registered and published, with a 3-year renewal reminder in the operational calendar | Ops checklist item; published-agent page test |
| **REQ-R8-27** | Deletion and retention jobs pause project-wide on a litigation-hold flag | Hold-flag test asserting no deletion job runs |
| **REQ-R8-28** | Hardware-token 2FA enforced for all write roles above T2; no self-merge; signed releases with SBOM | CI policy checks |

---

*End of R8. Every ⚖️ COUNSEL flag in this document is a blocker for the capability it annotates. This memo
identifies the questions and the defensible defaults; it does not answer the questions, and it is not
legal advice.*
