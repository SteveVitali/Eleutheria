# Copy batch 01 — agent-drafted page sentences awaiting operator verbatim confirmation

<!-- Created by P35.38a (row 203), the first 11A row that needed the file
     (SEED-13b convention, contract "Notes"; B-2 "Batches + notice allowance",
     round 10, 2026-10-01T04:32:16Z). Append-only: rows are never deleted or
     edited in place — a correction is a new row superseding the old id, and a
     status change is recorded in the confirmation log below with a `date -u`
     stamp. -->

## Convention

- Each drafted sentence of public page copy is appended below with its **page**,
  the exact **text** (as it will render — markup contributes no text), its
  **sha256** (UTF-8, no trailing newline — `printf '%s' '<text>' | shasum -a 256`,
  the ADR-168 hash convention), and a **status**.
- **Status vocabulary:** `pending` = agent-drafted, awaiting the operator's
  verbatim confirmation · `confirmed` = the operator confirmed these words
  verbatim at a copy-batch sitting (recorded in the confirmation log below with
  a `date -u` stamp). An agent never confirms — the confirmation is the
  operator's words, recorded verbatim (OM-07/08).
- **Binding:** a row's `id` names where the sentence lives on its page. The id
  `title` binds the page's `BaseLayout` `title` prop (the `<h1>`/`<title>`);
  every other id is carried in a page element's `data-copy` attribute — an
  element holding several sentences lists its ids in order, space-separated.
  `tests/unit/test_data_collection_page.py` fails if a row's text drifts from
  the page, if a sentence ships untracked, or if a hash does not verify.
- Ids are page-scoped (the `page` column namespaces them) and never reused.
- **Shipping rule:** only `confirmed` sentences may ship (B-2); republish #1
  (P34.17's L2) refuses a `pending` sentence.

## Rows

| id | page | text | sha256 | status |
|---|---|---|---|---|
| title | /data-collection/ | How SIG collects data | 1c5d16258cd76dd4b5777c2091214b5dd73f5e3d77c8a6c828ae749aea936187 | pending |
| DC-02 | /data-collection/ | SIG — the Surveillance Infrastructure Graph — is an open, evidence-first record of public surveillance infrastructure, built by fetching public records. | f6bb30491ce43f2e61830a5dfcc03f058e26dc7395066f67a55579f87426856a | pending |
| DC-03 | /data-collection/ | This page is the explanation the crawler's contact URL points to: what it fetches, how it identifies itself, how it treats robots.txt, and how to ask it to stop. | 545ee87c41a94f48eefb65db622f8270dfb8b9d2d5df738895e183a1ae5aa8a5 | pending |
| DC-04 | /data-collection/ | What SIG fetches | 9905fd6c5463d37c5684f7256400ceb75fe21b04ed51f9dbeb4601f9c3c0ed6d | pending |
| DC-05 | /data-collection/ | SIG fetches public records only — pages, documents, datasets and APIs that a public body or a transparency project publishes openly. | 6427a101302c913dbe112799ee558613caef1a0aed8b12fb29b7bd3b4327aefb | pending |
| DC-06 | /data-collection/ | It never collects licence-plate reads, trip histories or other per-person data: those are excluded by design, not filtered out afterwards. | 083a465740a93ea0fdbb1a95d93f17baf3f639a5ea104f27c93b554bf87e981d | pending |
| DC-07 | /data-collection/ | How the crawler identifies itself | 9041ff31e0cc9c330bf68bfadb6f833649b457f29a2b2cfe375c1adeadc4d815 | pending |
| DC-08 | /data-collection/ | Every request carries a User-Agent header of the form name/version (+https://surveillancegraph.org/data-collection/), where name is the connector doing the fetch — for example osm/1.0.0 or the project fallback SIG. | c4706342058113887278f7bafed9fb669493ca30d3f05aca1d2a4eeeb5a2a88e | pending |
| DC-09 | /data-collection/ | SIG never impersonates a browser and never rotates or disguises its agent to get past a block. | 840b3d8acccea387fa4a1c611cec89d2969eb35c150b86b59dc1b24e769181a6 | pending |
| DC-10 | /data-collection/ | How robots.txt is treated | 3954c8a945d240b87e6c8a4ffc77fd83ee319a38c14a630ae2421f678d8cd0e0 | pending |
| DC-11 | /data-collection/ | For every host it fetches, SIG retrieves and records the host's robots.txt and classifies the answer per RFC 9309. | 8f1a556592a17460913f4ab031d360adced6e1ce7b936bf6541d5a119dabbc6a | pending |
| DC-12 | /data-collection/ | Under a recorded operator decision (GL-GATE-08 — ADR-088 and ADR-168), a Disallow, or a policy that cannot be retrieved, does not by itself stop the fetch; the fetch is marked robots_disregarded in SIG's record, so the refusal stays visible instead of being silently bypassed. | bc9de25a46b53b3491c65ba83378bd4df5c08e48009dad91302d8e90f338a701 | pending |
| DC-13 | /data-collection/ | Robots.txt is not the access control: the binding check is a fail-closed rights review per source, and a source is never fetched before its rights record permits it. | 33e3ffdaf931b4761da77bfb6f6bec7d9864db1dadd36b4d1da71cd9583116c6 | pending |
| DC-14 | /data-collection/ | Rate limits | 6ed021f7e822e17d4a0fa21539b0b1d801e04c244ad6b1f15fa79968a4e5b7fc | pending |
| DC-15 | /data-collection/ | SIG fetches slowly — at least one second between requests to one host by default, and longer wherever a published crawl-delay or a documented API budget demands it. | e1d9e699c8fac05ae1501893a0212f848d06abdce38276316c08a678cec61727 | pending |
| DC-16 | /data-collection/ | An HTTP 429, 503 or 504 answer is met with bounded backoff and retry; a bot-management challenge is recorded, never defeated or worked around. | 97a631b5a2bad48c1bc1ffedc2860c83a660d2ceb337c8c3f447738d93de3c66 | pending |
| DC-17 | /data-collection/ | Ask SIG to stop | 2bc5db01badf5baad1fa1cdeff3d9bccc3910e7e0a682f96b409bf19321f3b20 | pending |
| DC-18 | /data-collection/ | To ask SIG to stop fetching a site you operate, open a request through this site's dispute channel. | 12dd33406e5944a7ebae65e1de2e611216537b57106cb99114d475bb2a2c4a99 | pending |
| DC-19 | /data-collection/ | SIG does not publish an e-mail address; the dispute page is the project's contact route and states its own operating status. | cfdb5eecfc8cb0e7fe83d1b42b920134143b00db2b58b3a409250d5b09f59474 | pending |

## Confirmation log

<!-- The operator's verbatim confirmation lands here at the copy-batch sitting:
     one line per sitting naming the rows confirmed, the operator's words
     verbatim, and a `date -u` stamp. Nothing is written until that sitting. -->
