"""Typer + Rich terminal interface. `docs/CLI_SPEC.md` is the contract.

Layering (`docs/ARCHITECTURE.md`): this package may import `s2s_harness.nodes`,
`s2s_harness.graph` and `s2s_harness.models` only. It must never import
`s2s_harness.rules` directly -- the deterministic engine is reached through
the graph, never around it.
"""

from __future__ import annotations
