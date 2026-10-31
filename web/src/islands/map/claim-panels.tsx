// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.37 — the Preact twin of `components/FocusClaimPanels.tsx` +
// `components/ProvenancePanel.tsx` for the /map/ app (SIG-UI-083/097). The
// React originals still serve the not-yet-migrated /network/ island; this is
// the same `sig.provenance-panel/1` contract and the same markup, ported —
// divergent wording would be a defect, not a variant (UXR-33). Loaded lazily
// by MapApp only when a selected record carries embedded statements.
/** @jsxImportSource preact */
import type { ComponentChildren, JSX } from "preact";
import {
  FIELD_LABELS,
  NOT_PUBLISHABLE,
  NOT_RECORDED,
  panelFromStatement,
  UNAVAILABLE,
} from "../../lib/provenance-panel";
import type { ProvenancePanelData, StatementRow } from "../../lib/provenance-panel";

function Field({ label, children }: { label: string; children: ComponentChildren }): JSX.Element {
  return (
    <div className="pp-field">
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

export function PreactProvenancePanel({
  panel,
  anchor = true,
}: {
  panel: ProvenancePanelData;
  anchor?: boolean;
}): JSX.Element {
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
          {src.href && src.id !== NOT_RECORDED ? <a href={src.href}>{sourceInner}</a> : sourceInner}
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
            <a href={upstream.href} rel="nofollow noopener">{upstreamInner}</a>
          ) : (
            upstreamInner
          )}
        </Field>
        <Field label={FIELD_LABELS[7]}>
          {vo.href ? (
            <a href={vo.href} rel="nofollow noopener">{vo.label}</a>
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
            <a href={equiv.json_href}><code>{equiv.json_href}</code></a>
          ) : (
            <span>JSON twin: {UNAVAILABLE}</span>
          )}
          {" · "}
          {equiv.api_href ? (
            <a href={equiv.api_href}><code>{equiv.api_href}</code></a>
          ) : (
            <span>API: {equiv.api_status || UNAVAILABLE}</span>
          )}
        </Field>
        <Field label={FIELD_LABELS[15]}>
          {panel.dispute_href ? <a href={panel.dispute_href}>Report a correction</a> : UNAVAILABLE}
        </Field>
      </dl>
    </details>
  );
}

const FOCUS_PANEL_LIMIT = 8;

export default function FocusClaimPanels({
  statements,
  jsonHref,
  recordPageHref,
}: {
  statements: StatementRow[];
  jsonHref?: string;
  recordPageHref?: string;
}): JSX.Element {
  return (
    <div className="sig-island__focus-panels" data-testid="focus-claim-panels">
      {statements.slice(0, FOCUS_PANEL_LIMIT).map((stmt) => (
        <PreactProvenancePanel
          key={stmt.claim_id}
          panel={panelFromStatement(stmt, stmt.claim_id, { jsonHref })}
          anchor={false}
        />
      ))}
      {statements.length > FOCUS_PANEL_LIMIT && recordPageHref && (
        <p className="sig-island__note">
          {statements.length - FOCUS_PANEL_LIMIT} more claim
          {statements.length - FOCUS_PANEL_LIMIT === 1 ? "" : "s"} on{" "}
          <a href={recordPageHref}>the released record</a>.
        </p>
      )}
    </div>
  );
}

export { NOT_PUBLISHABLE, NOT_RECORDED, UNAVAILABLE };
