#!/bin/sh
# Assemble the canonical spec from ordered section files.
ROOT=/Users/stevenvitali/Eleutheria
out="$ROOT/docs/2_canonical_design_spec.md"
: > "$out"
for f in "$ROOT"/docs/research/_meta/spec_src/[0-9]*.md; do
  cat "$f" >> "$out"
  printf '\n' >> "$out"
done
wc -l "$out"
