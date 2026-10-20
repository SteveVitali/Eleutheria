// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The data-dictionary contract (P35.39, SIG-TRANSP-016 / J3 §6.5).
 *
 * `dictionary.json` is the generated `sig.data-dictionary/1` document the export
 * emits at its root — every emitted column's description, Frictionless type,
 * nullability, unit and enum source, plus the non-columnar document listing and
 * the generated-ontology citation the enum/slot entries were resolved from.
 * The `/data/dictionary/` page renders it verbatim — never a hand-maintained
 * copy — so the human-readable dictionary can never drift from what the
 * downloads carry.
 */

/** The wire schema id the dictionary carries (emitted by `exports.column_registry`). */
export const DICTIONARY_SCHEMA = "sig.data-dictionary/1";

export interface DictionaryColumn {
  name: string;
  /** The Frictionless Table Schema type (string/integer/number/boolean/…). */
  type: string;
  description: string;
  nullable: boolean;
  /** The measured unit where one applies (seconds, bytes, count). */
  unit?: string;
  /** The vocabulary authority the column's values resolve from. */
  enum_source?: string;
  /** The closed permissible-value set, when the source is enumerable. */
  enum_values?: string[];
}

export interface DictionaryResource {
  name: string;
  title: string;
  description: string;
  /** "table" (columnar) or "document". */
  kind: string;
  /** The generated Table Schema artifact path (`schemas/<res>.tableschema.json`). */
  table_schema: string;
  /** The emitted artifact paths this resource serialises to. */
  paths: string[];
  /** The emitted `sig.<name>/<v>` row schema id, when one exists. */
  schema?: string;
  /** The upstream source ids the resource draws on. */
  sources?: string[];
  columns: DictionaryColumn[];
}

export interface DictionaryDocument {
  path: string;
  media_type?: string;
  schema?: string;
  description?: string;
}

export interface DataDictionary {
  schema: string;
  name: string;
  /** The export build's release id this dictionary documents. */
  version: string;
  created: string;
  /** The generated-ontology citation (version + digest — never hand-copied). */
  ontology: {
    schema_file: string;
    schema_id?: string;
    version?: string;
    metamodel_version?: string;
    sha256: string;
    vocabulary_registry: string;
  };
  resources: DictionaryResource[];
  /** The non-columnar manifest artifacts (descriptors, payloads). */
  documents: DictionaryDocument[];
}

/** Type-guard the page + data layer share — a malformed dictionary is a build error. */
export function isDataDictionary(parsed: unknown): parsed is DataDictionary {
  const o = parsed as Partial<DataDictionary> | null;
  return (
    o !== null &&
    typeof o === "object" &&
    o.schema === DICTIONARY_SCHEMA &&
    Array.isArray(o.resources) &&
    o.resources.every(
      (r) =>
        typeof r === "object" &&
        r !== null &&
        typeof (r as DictionaryResource).name === "string" &&
        Array.isArray((r as DictionaryResource).columns),
    ) &&
    Array.isArray(o.documents)
  );
}
