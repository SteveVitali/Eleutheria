# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""SIG `api` package — the hand-written, versioned §37 public read API (P14.1).

:func:`api.app.create_app` builds the FastAPI app over an :class:`api.store.ReadStore`;
``sig-api serve`` runs it against the demo store.
"""

__version__ = "0.1.0"

from .app import API_VERSION, create_app  # noqa: E402  (version must precede app import)
from .store import InMemoryStore, ReadStore  # noqa: E402

__all__ = ["API_VERSION", "InMemoryStore", "ReadStore", "create_app", "__version__"]
