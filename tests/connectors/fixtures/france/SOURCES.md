# France/Belgium fixture provenance — `tests/connectors/fixtures/france/`

Every fixture below is a **committed excerpted capture** — never fetched live by
the test suite (live egress runs only through `sig-connectors run --mode live`
behind the loader gate; the flipped France sources run live on operator command,
and `declarationcamera_be` stays targetless — the register sits behind Belgian
eID, HG-04).

| fixture | upstream | shape |
|---|---|---|
| `decp_marches.json` | DECP national open-data marchés (data.gouv.fr, Licence Ouverte 2.0) | Curated JSON payload (F9.16 verbatim structure) |
| `madada_records.json` | MaDada records-request contexts | Curated JSON payload |
| `raa_prefectures.json` | Arrêtés préfectoraux | Curated JSON payload |
| `raa_index.csv` (P25.5) | The national RAA index CSV (`static.data.gouv.fr`, ODbL-1.0) | Semicolon-delimited `titre;url;departement;mise_a_jour` — the observed upstream header; a mix of arrêté rows, a recueil/bulletin row the titre pattern excludes, an http-only row `require_https` drops, and a malformed row counted `malformed` |
| `madada_feed.atom` (P25.5) | The platform's own Atom feed of successful requests (`madada.fr/feed/...`) | Atom 1.0 with request-text-like `<title>`/`<content>`/`<author>` present so the tests prove the adapter suppresses them — only atom id, timestamps, and the request-event link may surface |
| `sample_document.pdf` | A document-capture placeholder PDF | Non-text-bearing; exercises the artifact-only path |

## P25.5 adapter notes

- `raa_index.csv` is parsed **strictly**: a changed header or non-CSV shape is
  `ContentDrift`, never an empty selection. Resolved children are bounded
  (`france_belgium_vocab.toml [raa_index]` — `max_documents=8`, https-only,
  departement-pattern). Child PDF bytes in tests are built by
  `tests/support.py::minimal_pdf`.
- `madada_feed.atom` entries carry deliberately request-text-like fields
  (`title`/`content`/`author`) — the `[madada_feed]` contract names them
  `never_emit`, and `test_madada_feed_emits_cada_contexts_and_never_request_text`
  proves no request text reaches an emitted row.
