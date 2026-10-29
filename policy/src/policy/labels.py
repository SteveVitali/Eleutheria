# SPDX-License-Identifier: Apache-2.0
"""Public entity labels, descriptors, slugs and hashes — K2 §3, ticket P35.29.

ONE derivation everywhere (L-1).  Exporters, the API, release records, pages,
graph nodes, typeahead and map popups all consume this module's output instead
of re-deriving a name — the raw ``cached_canonical_name`` / connector-key /
``"Unnamed …"`` fallbacks are retired by the callers that adopt this file.

The laws the module enforces (K2 §3):

* L-2 — a label is *never* a UUID, a connector key, a source id or a handle.
  Every derivation that runs out of words ends in a typed
  ``"<kind words> #{hash4}"`` fallback (D-K2-5), never at an identifier.
* L-3 — every emitted label carries ``label_basis`` in the closed vocabulary
  ``source_name | source_title | key_name | slug_name | derived | fallback``
  plus ``label_source_id``.
* L-4 — labels are untrusted text: control/format characters stripped,
  whitespace collapsed, capped at ``LABEL_MAX`` characters with a
  word-boundary ellipsis.
* L-5 — source casing is preserved; nothing is title-cased.
* L-6 — every label *and* slug passes the person-name screen before it
  surfaces (Part VIII).  ``policy`` is a leaf package, so the screen is
  **injected**: call sites pass ``person_screen=`` (the exports/api call
  sites pass ``resolution.partner_identity.natural_person_signal``); a site
  that cannot supply one gets the built-in conservative heuristic.  A
  candidate that trips the screen is skipped; when every candidate trips it
  the row's ``part8`` is ``"fallback"``.

The A-10 rule (D-K2-1 = b + c, the operator's word — never re-decided here):
an organisation is labelled when its registry disposition is ``allow``;
anything else emits a typed ``label_state="not_yet_reviewed"`` row (null
label/slug/hash — the absence is a value, not a gap).  ``person`` entities
and entities whose disposition is ``deny`` are ``"withheld"``: no label, no
node, no slug, no URL.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field, replace
from typing import Any

#: K2 §3.2 — list/node labels cap at 80 chars, cut at a word boundary.
LABEL_MAX = 80
#: K11 §3 — name-slugs cap at 56 chars, cut at a token boundary.
SLUG_MAX = 56
#: K11 §3 — the hash is the Crockford-base32 sha256 prefix, 7 chars / 35 bits.
HASH_LEN = 7
#: Disambiguation step 3 / the typed-fallback suffix — first 4 hash chars.
HASH4_LEN = 4

#: L-3 — the closed ``label_basis`` vocabulary.
LABEL_BASES: tuple[str, ...] = (
    "source_name",
    "source_title",
    "key_name",
    "slug_name",
    "derived",
    "fallback",
)

#: Entity kinds the module knows.  ``other`` is the catch-all for typed rows
#: that are not (yet) a public page kind (``system``, ``thing``, …).
KINDS: tuple[str, ...] = (
    "org",
    "site",
    "agency",
    "jurisdiction",
    "program",
    "service",
    "contract",
    "grant",
    "notice",
    "bill",
    "policy",
    "event",
    "request",
    "atlas",
    "portal",
    "person",
    "other",
)

#: K2 §3.2 — the human-readable word for each kind (fallback labels and the
#: descriptor's ``· <kind>`` segment come from here, never from a raw type id).
KIND_WORDS: dict[str, str] = {
    "org": "Organisation",
    "site": "Surveillance camera",
    "agency": "Government body",
    "jurisdiction": "Jurisdiction",
    "program": "Program",
    "service": "Service",
    "contract": "Procurement record",
    "grant": "Grant",
    "notice": "Notice",
    "bill": "Bill",
    "policy": "Policy or ordinance",
    "event": "Agenda item",
    "request": "Records request",
    "atlas": "Data source",
    "portal": "Registry portal",
    "person": "Person",
    "other": "Record",
}

#: K2 §3.2 — entity kind → URL type segment.
URL_TYPES: dict[str, str] = {
    "org": "org",
    "site": "site",
    "agency": "agency",
    "jurisdiction": "place",
    "program": "program",
    "service": "service",
    "contract": "contract",
    "grant": "grant",
    "notice": "notice",
    "bill": "bill",
    "policy": "policy",
    "event": "event",
    "request": "request",
    "atlas": "atlas",
    "portal": "portal",
    "person": "person",
    "other": "entity",
}

#: Typed label states.  ``None`` = a normal labelled row.
LABEL_STATES: tuple[str, ...] = ("not_yet_reviewed", "withheld")

#: ``entity_type`` → kind, for typed entities (P35.14b).  Connector-side keys
#: still land in ``_KIND_PREFIXES`` below for untyped rows.
KIND_BY_ENTITY_TYPE: dict[str, str] = {
    "organisation": "org",
    "organization": "org",
    "person": "person",
    "system": "other",
    "thing": "other",
    "camera": "site",
    "site": "site",
    "deployment": "site",
    "physical_asset": "site",
    "candidate_asset": "site",
}

#: ``entity_key``-scheme prefix → kind.  Subject keys minted by the ER pass
#: (``atlas:``, ``contract:``, …) classify the entity even when ``entity_type``
#: is not yet populated; connector keys (``organization:``, ``ops_*:``) do the
#: same for untyped subjects.  Order matters only where one string prefixes
#: another — none do (``ops_organization:`` ≠ ``organization:``).
_KIND_PREFIXES: tuple[tuple[str, str], ...] = (
    ("ops_organization:", "site"),
    ("ops_deployment:", "site"),
    ("registry:", "atlas"),
    ("agency:", "agency"),
    ("department:", "agency"),
    ("platform:", "portal"),
    ("atlas:", "atlas"),
    ("jurisdiction:", "jurisdiction"),
    ("program:", "program"),
    ("service:", "service"),
    ("organization:", "org"),
    ("organisation:", "org"),
    # P36.30 (K2 GX-04): portal/federal procurement notices type as the K2
    # "procurement notice" kind — the prefix the connector subjects mint
    # under (`procurement_notice:<source>:<id>` → entity_type contract in
    # the sink map, the notice kind on the public surface).
    ("procurement_notice:", "notice"),
    ("notice:", "notice"),
    ("contract:", "contract"),
    ("award:", "contract"),
    ("grant:", "grant"),
    ("bill:", "bill"),
    ("policy:", "policy"),
    ("ordinance:", "policy"),
    ("statute:", "policy"),
    ("regulation:", "policy"),
    ("event:", "event"),
    ("meeting:", "event"),
    ("agenda:", "event"),
    ("request:", "request"),
    ("foia:", "request"),
    ("pra:", "request"),
)

#: Crockford base32 (K11 §3 — no I/O/U/1/0 ambiguity).
_CROCKFORD = "0123456789abcdefghjkmnpqrstvwxyz"

#: The person-shaped heuristic used when a call site cannot inject the real
#: screen — deliberately conservative (two+ capitalised words that look like a
#: given/family pair, honorifics, sole-trader phrasing).
_PERSON_WORDS = re.compile(
    r"\b(mr|mrs|ms|dr|miss)\b\.?\s|\b[a-z][a-z]+,?\s+(dba|sole|trading)\b",
    re.IGNORECASE,
)
_INITIAL_NAME = re.compile(
    r"^(?:[A-Z][a-z]+(?:[-'][A-Z][a-z]+)?\s+){1,2}[A-Z][a-z]+(?:[-'][A-Z][a-z]+)?"
    r"(?:\s+(?:Jr|Sr|II|III|IV)\.?)?$"
)
_ORG_SIGNAL = re.compile(
    r"\b(inc|llc|llp|ltd|corp|co|company|group|systems?|services?|county|city|"
    r"state|department|dept|office|agency|authority|board|commission|district|"
    r"sheriff|police|university|college|school|foundation|institute|center|"
    r"centre|association|solutions?|technologies|tech|labs|government|gov)\b",
    re.IGNORECASE,
)


def _default_person_screen(text: str) -> bool:
    """Conservative last-resort person-shape check (call sites inject the real one)."""
    if _PERSON_WORDS.search(text):
        return True
    if _ORG_SIGNAL.search(text):
        return False
    return bool(_INITIAL_NAME.match(text.strip()))


# ---------------------------------------------------------------------------
# Text hygiene (L-4/L-5)
# ---------------------------------------------------------------------------


def sanitize_label(text: str, *, limit: int = LABEL_MAX) -> str:
    """Strip control/format chars, collapse whitespace, cap at ``limit``.

    Word-boundary truncation: the cut never lands mid-token and the result
    (with the ellipsis) never exceeds ``limit``.
    """
    cleaned = "".join(
        ch for ch in text if unicodedata.category(ch) not in ("Cc", "Cf", "Cs") and ch not in "﻿"
    )
    cleaned = " ".join(cleaned.split())
    if len(cleaned) <= limit:
        return cleaned
    head = cleaned[: limit - 1].rstrip()
    if " " in head:
        head = head[: head.rfind(" ")].rstrip(" ,;:—–-")
    return head + "…"


# ---------------------------------------------------------------------------
# Hash + slug primitives (K11 §3)
# ---------------------------------------------------------------------------


def _crockford(number: int, length: int) -> str:
    """``number`` as Crockford base32, left-padded to ``length`` digits."""
    digits = []
    for _ in range(length):
        digits.append(_CROCKFORD[number & 0x1F])
        number >>= 5
    return "".join(reversed(digits))


def entity_hash(entity_id: str, *, length: int = HASH_LEN) -> str:
    """Crockford base32 of ``sha256(canonical UUID text)``, ``length`` chars.

    ``length`` is in ``5-bit`` digits: the 7-char form covers 35 bits; a slug-
    registry collision extends it (the caller passes ``length + 1``), and the
    issued value is frozen — extension never rewrites an issued hash.
    """
    digest = hashlib.sha256(entity_id.encode("utf-8")).digest()
    bits = int.from_bytes(digest, "big")
    return _crockford(bits >> (256 - 5 * length), length)


def hash4(entity_id: str) -> str:
    """First ``HASH4_LEN`` hash chars — the ``#{hash4}`` tie-break."""
    return entity_hash(entity_id)[:HASH4_LEN]


_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _ascii_tokens(text: str) -> list[str]:
    folded = unicodedata.normalize("NFKD", text)
    ascii_text = folded.encode("ascii", "ignore").decode("ascii")
    return _TOKEN_RE.findall(ascii_text.lower())


def name_slug(label: str, *, state_slug: str | None = None) -> str | None:
    """``<name-slug>`` per K11 §3 — ASCII-folded ``[a-z0-9]+`` tokens.

    ``state_slug`` (the K4 display slug of the state, e.g. ``usa-tx``) appends
    when the entity is placed; the whole cuts at ``SLUG_MAX`` on a token
    boundary.  Returns ``None`` when the label folds to nothing — the caller
    must then emit no slug (never fall back to an identifier).
    """
    tokens = _ascii_tokens(label)
    if not tokens:
        return None
    slug = "-".join(tokens)
    if state_slug:
        state = state_slug.strip().lower()
        if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", state):
            slug = f"{slug}-{state}"
    if len(slug) > SLUG_MAX:
        cut = slug[:SLUG_MAX]
        if "-" in cut:
            cut = cut[: cut.rfind("-")]
        slug = cut
    return slug or None


def entity_url_key(url_type: str, slug: str, hash_value: str) -> str:
    """``<name-slug>--<hash>`` — the joined url-key."""
    return f"{slug}--{hash_value}"


def entity_url(url_type: str, slug: str, hash_value: str) -> str:
    """``/entity/<type>/<name-slug>--<hash>/`` — hash authoritative, slug cosmetic."""
    return f"/entity/{url_type}/{slug}--{hash_value}/"


# ---------------------------------------------------------------------------
# Facts + result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LabelFacts:
    """The export-snapshot inputs a derivation reads.

    ``fields`` maps predicate id → first public-tier claim value (sanitization
    happens here, never downstream); ``extra`` carries shape that has no
    predicate (the derived-entity name index, site technology class, the
    site's registry-place slug).  ``identifiers`` are candidate
    ``(scheme, value)`` pairs for the ``key_name`` derivation — schemes whose
    values are handle-like (``sourceid:``, ``serialno:``, ``platformid:``,
    ``wikipediaid:``) are never label sources.
    """

    entity_id: str
    entity_key: str | None = None
    entity_type: str | None = None
    sig_id: str | None = None
    kind: str | None = None
    disposition: str | None = None
    canonical_name: str | None = None
    place: str | None = None
    component_id: str | None = None
    identifiers: tuple[tuple[str, str], ...] = ()
    fields: Mapping[str, str] = field(default_factory=dict)
    extra: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EntityLabel:
    """One ``sig.entity-label/1`` row (labels/<compartment>.jsonl shape)."""

    entity_id: str
    sig_id: str | None
    kind: str
    url_type: str | None
    label: str | None
    descriptor: str | None
    label_basis: str | None
    label_source_id: str | None
    place_jkey: str | None
    slug: str | None
    hash: str | None
    url: str | None
    disambiguator: str | None
    component_id: str | None
    part8: str  # "pass" | "fallback"
    label_state: str | None = None  # "not_yet_reviewed" | "withheld" | None
    subject_key: str | None = None
    # Derivation hints for the disambiguation pass — never serialized.
    label_key: str | None = field(default=None, repr=False)
    source_hint: str | None = field(default=None, repr=False)
    place_hint: str | None = field(default=None, repr=False)

    def row(self) -> dict[str, Any]:
        """The emitted ``sig.entity-label/1`` object (hints excluded)."""
        out: dict[str, Any] = {
            "entity_id": self.entity_id,
            "sig_id": self.sig_id,
            "kind": self.kind,
            "url_type": self.url_type,
            "label": self.label,
            "descriptor": self.descriptor,
            "label_basis": self.label_basis,
            "label_source_id": self.label_source_id,
            "place_jkey": self.place_jkey,
            "slug": self.slug,
            "hash": self.hash,
            "url": self.url,
            "disambiguator": self.disambiguator,
            "component_id": self.component_id,
            "part8": self.part8,
            "subject_key": self.subject_key,
        }
        if self.label_state is not None:
            out["label_state"] = self.label_state
        return out


#: Identifier schemes whose values are source ids or handles (K2 §3.2) —
#: never a ``key_name`` source, never a fallback label.
BLOCKED_KEY_SCHEMES: frozenset[str] = frozenset(
    {"sourceid", "serialno", "platformid", "wikipediaid", "wikidataid", "handle"}
)


def kind_from_key(subject_key: str | None) -> str | None:
    """Entity kind from an ``entity_key``/``subject_key`` prefix."""
    if not subject_key:
        return None
    for prefix, kind in _KIND_PREFIXES:
        if subject_key.startswith(prefix):
            return kind
    return None


def kind_for(entity_type: str | None, subject_key: str | None = None) -> str:
    """Resolve the label kind: declared ``entity_type``, else key prefix, else ``other``."""
    if entity_type and entity_type in KIND_BY_ENTITY_TYPE:
        return KIND_BY_ENTITY_TYPE[entity_type]
    keyed = kind_from_key(subject_key)
    return keyed if keyed is not None else "other"


def _first(facts: LabelFacts, *predicates: str) -> str | None:
    """First non-empty (post-sanitize) field value across ``predicates``."""
    for pred in predicates:
        raw = facts.fields.get(pred)
        if raw is None:
            continue
        text = sanitize_label(str(raw))
        if text:
            return text
    return None


def _key_label(facts: LabelFacts) -> str | None:
    """``key_name`` derivation — a clean slug/key fragment, never a handle.

    Reads the entity's identifier pairs first (scheme-aware, handle schemes
    blocked), then the minted ``entity_key``'s final segment when it is a
    non-identifier word (``platform:okla-city-council`` →
    ``okla city council`` stays a slug fragment — the derivation *unslugs* it
    into words and marks the basis ``key_name``, per K2 the key itself never
    surfaces raw).
    """
    for scheme, value in facts.identifiers:
        if scheme.lower() in BLOCKED_KEY_SCHEMES:
            continue
        text = sanitize_label(str(value))
        if text and not text.startswith(("/", "uuid:", "subject:")):
            return text
    if facts.entity_key:
        frag = facts.entity_key.split(":", 1)[-1]
        words = " ".join(_ascii_tokens(frag))
        if words:
            return " ".join(w for w in words.split(" ") if w)
    return None


def _candidates(kind: str, facts: LabelFacts) -> list[tuple[str, str, str | None]]:
    """``(text, basis, source_id)`` candidates in the §3.2 precedence order."""
    f = facts
    extra = f.extra or {}
    out: list[tuple[str, str, str | None]] = []

    def field_text(*preds: str) -> str | None:
        return _first(f, *preds)

    if kind == "org":
        if f.canonical_name:
            out.append((f.canonical_name, "source_name", None))
        out.append(
            (field_text("organization_legal_name", "legal_name", "name") or "", "source_name", None)
        )
        out.append((field_text("organization_identifier", "identifier") or "", "key_name", None))
        if f.place:
            out.append((f"Organisation registered in {f.place}", "derived", None))
        out.append((_key_label(f) or "", "key_name", None))
    elif kind == "site":
        out.append((field_text("camera_name") or "", "source_name", None))
        out.append((field_text("agency_name") or "", "source_name", None))
        tech = str(extra.get("technology") or extra.get("technology_class") or "")
        tech_words = " ".join(_ascii_tokens(tech)) or "surveillance"
        if f.place:
            out.append((f"{tech_words} camera in {f.place}", "derived", None))
        elif extra.get("site_id") or f.extra.get("site_key"):
            out.append((f"{tech_words} camera site", "derived", None))
        out.append((_key_label(f) or "", "key_name", None))
    elif kind == "agency":
        out.append((field_text("agency_name") or "", "source_name", None))
        if f.canonical_name:
            out.append((f.canonical_name, "source_name", None))
        if f.place:
            out.append((f"Government body · {f.place}", "derived", None))
        out.append((_key_label(f) or "", "key_name", None))
    elif kind == "jurisdiction":
        out.append((field_text("country", "jurisdiction_name", "name") or "", "source_name", None))
        if extra.get("registry_name"):
            out.append((str(extra["registry_name"]), "source_name", None))
        out.append((_key_label(f) or "", "key_name", None))
    elif kind == "program":
        out.append((field_text("program_name", "name") or "", "source_name", None))
        out.append((_key_label(f) or "", "key_name", None))
    elif kind == "service":
        out.append((field_text("name", "service_name", "program_name") or "", "source_name", None))
        out.append((_key_label(f) or "", "key_name", None))
    elif kind == "contract":
        out.append(
            (field_text("title", "contract_title", "description") or "", "source_title", None)
        )
        seller = field_text("seller", "vendor")
        if seller:
            out.append((f"{seller} contract", "derived", None))
        buyer = field_text("buyer", "awarding_agency", "agency_name")
        if buyer:
            out.append((f"{buyer} procurement", "derived", None))
        out.append((_key_label(f) or "", "key_name", None))
    elif kind == "grant":
        out.append((field_text("title", "program_name", "description") or "", "source_title", None))
        recip = field_text("recipient", "recipient_name")
        if recip:
            out.append((f"{recip} grant", "derived", None))
        funder = field_text("funder", "funding_agency", "funding_program_name")
        if funder:
            out.append((f"{funder} grant", "derived", None))
        out.append((_key_label(f) or "", "key_name", None))
    elif kind == "notice":
        out.append((field_text("title", "description") or "", "source_title", None))
        frag = (f.entity_key or "").split(":", 1)[-1] if f.entity_key else ""
        words = " ".join(_ascii_tokens(frag))
        if words:
            out.append((words, "key_name", None))
        parts = [
            _first(f, "notice_type") or "Notice",
            _first(f, "agency_name", "target_agency", "platform"),
            _first(f, "posted_date", "publication_date", "filed_date"),
        ]
        out.append((" · ".join(p for p in parts if p), "derived", None))
        out.append((_key_label(f) or "", "key_name", None))
    elif kind == "bill":
        cite = field_text("bill_identifier", "citation", "bill_external_id", "external_id")
        if cite:
            session = field_text("bill_session", "session")
            out.append((f"{cite}" + (f" ({session})" if session else ""), "key_name", None))
        out.append((field_text("bill_title", "title") or "", "source_title", None))
        out.append((_key_label(f) or "", "key_name", None))
    elif kind == "policy":
        cite = field_text("ordinance_citation", "citation")
        if cite:
            out.append((cite, "key_name", None))
        body = field_text("enacting_body", "jurisdiction", "target_agency")
        if f.place or body:
            place = f.place or body
            out.append((f"{place} ordinance", "derived", None))
        out.append((_key_label(f) or "", "key_name", None))
    elif kind == "event":
        out.append((field_text("title", "description") or "", "source_title", None))
        body = field_text("agency_name", "platform", "target_agency")
        day = field_text("meeting_date", "event_date", "filed_date", "posted_date")
        if body or day:
            out.append(
                (
                    "Agenda item" + (f" · {body}" if body else "") + (f" · {day}" if day else ""),
                    "derived",
                    None,
                )
            )
        out.append((_key_label(f) or "", "key_name", None))
    elif kind == "request":
        status = field_text("response_status", "records_response_status", "status")
        day = field_text("response_date", "request_date", "filed_date")
        if f.place or status or day:
            parts = ["Records request", f.place, status, day]
            out.append((" · ".join(p for p in parts if p), "derived", None))
        out.append((_key_label(f) or "", "key_name", None))
    elif kind == "atlas":
        out.append((field_text("source_name", "name", "title") or "", "source_name", None))
        if f.canonical_name:
            out.append((f.canonical_name, "source_name", None))
        out.append((_key_label(f) or "", "key_name", None))
    elif kind == "portal":
        out.append(
            (field_text("platform", "platform_name", "name", "title") or "", "source_name", None)
        )
        if f.canonical_name:
            out.append((f.canonical_name, "source_name", None))
        out.append((_key_label(f) or "", "key_name", None))
    else:  # program/service/other fallback handled by shared tail
        if f.canonical_name:
            out.append((f.canonical_name, "source_name", None))
        out.append((field_text("name", "title", "description") or "", "source_title", None))
        out.append((_key_label(f) or "", "key_name", None))

    return [(t, b, s) for (t, b, s) in out if t and str(t).strip()]


def _looks_person_shaped(text: str, screen: Callable[[str], bool] | None) -> bool:
    fn = screen if screen is not None else _default_person_screen
    try:
        return bool(fn(text))
    except Exception:  # a screen never crashes a label — fail closed instead
        return True


def derive_label(
    facts: LabelFacts,
    *,
    person_screen: Callable[[str], bool] | None = None,
) -> EntityLabel:
    """The ONE derivation.  See module docstring for the law.

    ``facts.disposition`` is the *effective* outcome of the shared publication
    gate (``allow`` / ``deny`` / registry-pending ``None``); the caller runs
    the gate, this module never re-decides eligibility.
    """
    kind = facts.kind if facts.kind in KINDS else kind_for(facts.entity_type, facts.entity_key)

    def row(**kw: Any) -> EntityLabel:
        return EntityLabel(
            entity_id=facts.entity_id,
            sig_id=facts.sig_id,
            kind=kind,
            subject_key=facts.entity_key,
            component_id=facts.component_id,
            **kw,
        )

    # person — never public: no label, page, node or slug (K2 §3.2).
    if kind == "person":
        return row(
            url_type=None,
            label=None,
            descriptor=None,
            label_basis=None,
            label_source_id=None,
            place_jkey=None,
            slug=None,
            hash=None,
            url=None,
            disambiguator=None,
            part8="fallback",
            label_state="withheld",
        )
    url_type = URL_TYPES.get(kind, "entity")
    place_jkey = _place_jkey(facts)
    # The publication gate already ran — this module only *renders* its outcome.
    if kind == "org" and facts.disposition == "deny":
        return row(
            url_type=url_type,
            label=None,
            descriptor=None,
            label_basis=None,
            label_source_id=None,
            place_jkey=None,
            slug=None,
            hash=None,
            url=None,
            disambiguator=None,
            part8="fallback",
            label_state="withheld",
        )
    if kind == "org" and facts.disposition != "allow":
        # A-10: every non-allowed org is a typed "not yet reviewed" row.
        return row(
            url_type=url_type,
            label=None,
            descriptor=f"{KIND_WORDS[kind]} · not yet reviewed",
            label_basis=None,
            label_source_id=None,
            place_jkey=place_jkey,
            slug=None,
            hash=None,
            url=None,
            disambiguator=None,
            part8="fallback",
            label_state="not_yet_reviewed",
        )

    part8 = "pass"
    label: str | None = None
    basis: str | None = None
    source_id: str | None = None
    for text, cand_basis, cand_src in _candidates(kind, facts):
        clean = sanitize_label(text)
        if not clean:
            continue
        if _looks_person_shaped(clean, person_screen):
            part8 = "fallback"  # L-6: screen tripped — do not form the label
            continue
        label, basis, source_id = clean, cand_basis, cand_src
        break

    if label is None:
        # L-2 / D-K2-5: the typed fallback — words + short hash, never an id.
        part8 = "fallback"
        label = f"{KIND_WORDS[kind]} #{hash4(facts.entity_id)}"
        basis = "fallback"
    # L-6 again on the slug: the slug derives from the label, which already
    # passed the screen — but re-screen the slugged text for defence in depth.
    slug = name_slug(label, state_slug=_state_slug(place_jkey))
    hash_value = entity_hash(facts.entity_id)
    url = entity_url(url_type, slug, hash_value) if slug else None

    unplaced = place_jkey is None
    descriptor = f"{label} · {KIND_WORDS[kind]}" + (" · unplaced" if unplaced else "")
    return row(
        url_type=url_type,
        label=label,
        descriptor=descriptor,
        label_basis=basis,
        label_source_id=source_id,
        place_jkey=place_jkey,
        slug=slug,
        hash=hash_value,
        url=url,
        disambiguator=None,
        part8=part8,
        label_key=label.casefold(),
        source_hint=_first(facts, "source_name", "platform", "agency_name"),
        place_hint=facts.place,
    )


# ---------------------------------------------------------------------------
# Deterministic disambiguation (K2 §3.4)
# ---------------------------------------------------------------------------


def resolve_disambiguators(labels: Iterable[EntityLabel]) -> list[EntityLabel]:
    """Apply the §3.4 sequence within each ``(kind, label)`` collision group.

    ``label → label · {place} → label · {source} → label#{hash4}`` — pure
    function of the emitted rows: same release inputs, same suffixes.  Every
    group's members end with pairwise-distinct full display labels; when the
    ``{place}``/``{source}`` steps cannot separate a group, ``#{hash4}``
    always can (hash collisions are slug-registry concerns, handled by
    extension — the *display* disambiguator uses hash4 deterministically).
    """
    rows = list(labels)
    groups: dict[tuple[str, str | None], list[EntityLabel]] = {}
    for r in rows:
        if r.label is None:
            continue
        groups.setdefault((r.kind, r.label_key or r.label.casefold()), []).append(r)

    resolved: dict[int, EntityLabel] = {}
    for members in groups.values():
        if len(members) == 1:
            resolved[id(members[0])] = members[0]
            continue
        members.sort(key=lambda m: m.entity_id)  # deterministic order
        # Step 1 — `· {place}`: only where every member's place differs.
        places = {m.place_hint for m in members}
        if len(places) == len(members) and None not in places:
            for m in members:
                resolved[id(m)] = _with_disambig(m, f" · {m.place_hint}")
            continue
        # Step 2 — `· {source}`.
        sources = {m.source_hint for m in members}
        if len(sources) == len(members) and None not in sources:
            for m in members:
                resolved[id(m)] = _with_disambig(m, f" · {m.source_hint}")
            continue
        # Step 3 — `#{hash4}`.
        for m in members:
            resolved[id(m)] = _with_disambig(m, f" #{hash4(m.entity_id)}")
    # Input order preserved; non-colliding rows pass through untouched.
    return [resolved.get(id(r), r) for r in rows]


def _with_disambig(m: EntityLabel, suffix: str) -> EntityLabel:
    label = sanitize_label(f"{m.label}{suffix}")
    slug = name_slug(label, state_slug=_state_slug(m.place_jkey))
    url = (
        entity_url(m.url_type or "entity", slug, m.hash or entity_hash(m.entity_id))
        if slug
        else None
    )
    return replace(
        m,
        label=label,
        disambiguator=suffix.strip(),
        slug=slug,
        url=url,
        descriptor=f"{label} · {KIND_WORDS.get(m.kind, 'Record')}"
        + (" · unplaced" if m.place_jkey is None else ""),
        label_key=label.casefold(),
    )


# ---------------------------------------------------------------------------
# Place helpers
# ---------------------------------------------------------------------------


_JKEY_RE = re.compile(r"^[a-z0-9_.-]+:[A-Za-z0-9._-]+$")
#: ISO 3166-1 alpha-2 → alpha-3 for the suffix display slug.  The corpus is
#: US-dominant today; unknown alpha-2s honestly omit the suffix rather than
#: guessing (recorded in the run ledger — JUR registry display slugs land later).
_ALPHA2_TO_3: dict[str, str] = {
    "us": "usa",
    "ca": "can",
    "mx": "mex",
    "gb": "gbr",
    "ie": "irl",
    "fr": "fra",
    "de": "deu",
    "es": "esp",
    "pt": "prt",
    "it": "ita",
    "nl": "nld",
    "be": "bel",
    "lu": "lux",
    "ch": "che",
    "at": "aut",
    "dk": "dnk",
    "se": "swe",
    "no": "nor",
    "fi": "fin",
    "is": "isl",
    "pl": "pol",
    "cz": "cze",
    "sk": "svk",
    "hu": "hun",
    "ro": "rou",
    "bg": "bgr",
    "gr": "grc",
    "hr": "hrv",
    "si": "svn",
    "ee": "est",
    "lv": "lva",
    "lt": "ltu",
    "ua": "ukr",
    "tr": "tur",
    "il": "isr",
    "au": "aus",
    "nz": "nzl",
    "jp": "jpn",
    "kr": "kor",
    "cn": "chn",
    "in": "ind",
    "sg": "sgp",
    "hk": "hkg",
    "tw": "twn",
    "za": "zaf",
    "br": "bra",
    "ar": "arg",
    "cl": "chl",
    "co": "col",
    "pe": "per",
}


def _place_jkey(facts: LabelFacts) -> str | None:
    """The entity's canonical place key (K4 ``jkey`` form), or None.

    ``extra['place_jkey']`` wins (callers pass the placement/registry jkey
    there while ``facts.place`` stays the *display* name used in label text);
    otherwise accepts the registry jkey families in ``place``/``entity_key``
    directly and normalises the minted subject-key form
    ``jurisdiction:iso.3166-2:US-OK`` → ``iso3166-2:US-OK``.
    """
    explicit = (facts.extra or {}).get("place_jkey") if facts.extra else None
    for cand in (explicit, facts.place, facts.entity_key):
        if not cand or not isinstance(cand, str):
            continue
        jkey = cand
        if jkey.startswith("jurisdiction:"):
            rest = jkey.split(":", 1)[1]
            jkey = rest.replace("iso.3166-1:", "iso3166-1:").replace("iso.3166-2:", "iso3166-2:")
        if _JKEY_RE.match(jkey) and jkey.split(":", 1)[0] in (
            "iso3166-1",
            "iso3166-2",
            "us.census.geoid.county",
            "us.census.geoid.place",
        ):
            return jkey
    return None


def _state_slug(place_jkey: str | None) -> str | None:
    """K4 display slug of the state for the slug suffix, or None."""
    if not place_jkey:
        return None
    scheme, _, code = place_jkey.partition(":")
    if scheme == "iso3166-2" and "-" in code:
        country, _, sub = code.partition("-")
        alpha3 = _ALPHA2_TO_3.get(country.lower())
        return f"{alpha3}-{sub.lower()}" if alpha3 else None
    if scheme == "iso3166-1":
        return _ALPHA2_TO_3.get(code.lower())
    if scheme == "jurisdiction":
        # subject-key form `jurisdiction:iso.3166-2:US-OK`
        if code.startswith("iso.3166-2:") and "-" in code:
            country, _, sub = code.rsplit(":", 1)[-1].partition("-")
            alpha3 = _ALPHA2_TO_3.get(country.lower())
            return f"{alpha3}-{sub.lower()}" if alpha3 else None
        if code.startswith("iso.3166-1:"):
            return _ALPHA2_TO_3.get(code.rsplit(":", 1)[-1].lower())
    return None


__all__ = [
    "BLOCKED_KEY_SCHEMES",
    "EntityLabel",
    "HASH4_LEN",
    "HASH_LEN",
    "KIND_BY_ENTITY_TYPE",
    "KIND_WORDS",
    "KINDS",
    "LABEL_BASES",
    "LABEL_MAX",
    "LABEL_STATES",
    "LabelFacts",
    "SLUG_MAX",
    "URL_TYPES",
    "derive_label",
    "entity_hash",
    "entity_url",
    "entity_url_key",
    "hash4",
    "kind_for",
    "kind_from_key",
    "name_slug",
    "resolve_disambiguators",
    "sanitize_label",
]
