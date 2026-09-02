// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { defineConfig } from "vitest/config";

// Unit tests cover the pure epistemic logic and the design-system invariants. The
// Playwright e2e/a11y suite (tests/e2e) is driven separately by `test:e2e`, so it
// is excluded here.
export default defineConfig({
  test: {
    globals: true,
    environment: "node",
    include: ["tests/unit/**/*.test.ts"],
  },
});
