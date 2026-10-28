// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The one `<ProvenancePanel>` renderer (P35.36, R11-K13-TX-08a / J3 §5.1–5.2,
 * K13 §7 W1 / UXR-33, SIG-TRANSP-011) — the TypeScript twin of
 * `exports.provenance_panel.panel_html`.
 *
 * One contract in (`sig.provenance-panel/1` — built once per claim by
 * `lib/provenance-panel.ts`), one markup out: a zero-JS `<details>` disclosure
 * whose `<dl>` carries J3 §5.2's verbatim field set in order. React renders it
 * to static HTML at build time on content pages (no client directive ⇒ no
 * shipped script), and the same component mounts inside the `/network/` and
 * `/map/` islands — UXR-33's "one contract" rule: a divergent wording on any
 * surface is a defect, not a variant.
 *
 * The `#claim-<id>` anchor (J3 §5.1) lives on the panel itself — `anchor`
 * writes `id="claim-<claim_id>"`. Surfaces that repeat a claim (edge lists,
 * focus panes) pass `anchor={false}` so an id never duplicates within one
 * document; the claim's canonical anchor surface is its record page / claim
 * viewer.
 */

import type { ReactElement, ReactNode } from "react";
// P36.23 (UXK14-3b): the panel's visual shell rides the component itself, so
// every mount — the static shell or a React island — carries the same styles.
import "../styles/provenance.css";
import {
  FIELD_LABELS,
  NOT_PUBLISHABLE,
  NOT_RECORDED,
  UNAVAILABLE,
} from "../lib/provenance-panel";
import type { ProvenancePanelData } from "../lib/provenance-panel";

interface Props {
  panel: ProvenancePanelData;
  /** Write `id="claim-<claim_id>"` — only on the claim's canonical surface. */
  anchor?: boolean;
}

function Field({ label, children }: { label: string; children: ReactNode }): ReactElement {
  return (
    <div className="pp-field">
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

export default function ProvenancePanel({ panel, anchor = true }: Props): ReactElement {
  const claimId = panel.claim_id;
  const [src, capture, upstream, vo, epi, con, equiv] = [
    panel.source,
    panel.capture,
    panel.upstream,
    panel.view_original,
    panel.epistemic_review,
    panel.contradictions,
    panel.equivalent_requests,
  ];

  const sourceInner = <code>{src.id}</code>;
  const upstreamInner = <code>{upstream.display}</code>;

  return (
    <details
      className="provenance-panel"
      data-provenance-panel
      data-binding-state={panel.binding_status}
      {...(anchor && claimId ? { id: `claim-${claimId}` } : {})}
    >
      <summary>
        Provenance — <code>{claimId}</code> · {panel.binding_status}
      </summary>
      <dl>
        <Field label={FIELD_LABELS[0]}>
          {src.href && src.id !== NOT_RECORDED ? (
            <a href={src.href}>{sourceInner}</a>
          ) : (
            sourceInner
          )}
          {src.name ? <span className="mut"> {src.name}</span> : null}
        </Field>
        <Field label={FIELD_LABELS[1]}>{panel.binding_text}</Field>
        <Field label={FIELD_LABELS[2]}>{capture.retrieved_at}</Field>
        <Field label={FIELD_LABELS[3]}>
          <code>{capture.digest}</code>
        </Field>
        <Field label={FIELD_LABELS[4]}>{capture.byte_size}</Field>
        <Field label={FIELD_LABELS[5]}>{capture.media_type}</Field>
        <Field label={FIELD_LABELS[6]}>
          {upstream.href ? (
            <a href={upstream.href} rel="nofollow noopener">
              {upstreamInner}
            </a>
          ) : (
            upstreamInner
          )}
        </Field>
        <Field label={FIELD_LABELS[7]}>
          {vo.href ? (
            <a href={vo.href} rel="nofollow noopener">
              {vo.label}
            </a>
          ) : (
            vo.label
          )}
          {vo.note ? <span className="mut"> ({vo.note})</span> : null}
        </Field>
        <Field label={FIELD_LABELS[8]}>{panel.extraction}</Field>
        <Field label={FIELD_LABELS[9]}>{panel.directness}</Field>
        <Field label={FIELD_LABELS[10]}>
          {epi.reliability} / {epi.integrity} — {epi.review}
        </Field>
        <Field label={FIELD_LABELS[11]}>{con.display}</Field>
        <Field label={FIELD_LABELS[12]}>{panel.supersession}</Field>
        <Field label={FIELD_LABELS[13]}>
          {panel.rights.spdx} — {panel.rights.attribution}
        </Field>
        <Field label={FIELD_LABELS[14]}>
          {equiv.json_href ? (
            <a href={equiv.json_href}>
              <code>{equiv.json_href}</code>
            </a>
          ) : (
            <span>JSON twin: {UNAVAILABLE}</span>
          )}
          {" · "}
          {equiv.api_href ? (
            <a href={equiv.api_href}>
              <code>{equiv.api_href}</code>
            </a>
          ) : (
            <span>API: {equiv.api_status || UNAVAILABLE}</span>
          )}
        </Field>
        <Field label={FIELD_LABELS[15]}>
          {panel.dispute_href ? (
            <a href={panel.dispute_href}>Report a correction</a>
          ) : (
            UNAVAILABLE
          )}
        </Field>
      </dl>
    </details>
  );
}

export { NOT_PUBLISHABLE, NOT_RECORDED, UNAVAILABLE };
