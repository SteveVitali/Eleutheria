// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// The focus pane's claim panels behind one lazy boundary (P36.21): the map
// island renders these only when a selected record actually carries embedded
// `sig.statement/1` rows — an initial load with no focus never downloads the
// shared provenance-panel contract (~2.4 KB gzip the /map/ regression bound
// D-P35.51-1 needs back). Behaviour is unchanged: the same FOCUS_PANEL_LIMIT
// bound and the same "remainder on the record page" line, mounted a microtask
// later under <Suspense>.
import type { ReactElement } from "react";
import { panelFromStatement } from "../lib/provenance-panel";
import type { StatementRow } from "../lib/provenance-panel";
import ProvenancePanel from "./ProvenancePanel";

/** The selection pane bounds its panels; the record page carries them all. */
const FOCUS_PANEL_LIMIT = 8;

interface Props {
  statements: StatementRow[];
  /** The record's JSON twin (`…/<id>.json`) — the panel's "Equivalent requests". */
  jsonHref?: string;
  /** The canonical record page the remainder links. */
  recordPageHref?: string;
}

export default function FocusClaimPanels({
  statements,
  jsonHref,
  recordPageHref,
}: Props): ReactElement {
  return (
    <div className="sig-island__focus-panels" data-testid="focus-claim-panels">
      {statements.slice(0, FOCUS_PANEL_LIMIT).map((stmt) => (
        <ProvenancePanel
          key={stmt.claim_id}
          panel={panelFromStatement(stmt, stmt.claim_id, {
            jsonHref,
          })}
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
