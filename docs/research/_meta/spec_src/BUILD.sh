#!/bin/sh
# Assemble the canonical spec from ordered section files.
set -eu
# Resolve the source tree, not the caller's cwd or one developer's other checkout.
SOURCE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$SOURCE_DIR/../../../.." && pwd)
out="$ROOT/docs/2_canonical_design_spec.md"
: > "$out"
for f in "$ROOT"/docs/research/_meta/spec_src/[0-9]*.md; do
  cat "$f" >> "$out"
  printf '\n' >> "$out"
done
wc -l "$out"
