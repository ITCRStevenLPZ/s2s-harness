"""LangGraph node wrappers over the pure `rules/` functions (Track A) and
the four LLM roles in `s2s_harness.llm` (Track B).

Per `docs/GRAPH_SPEC.md` section 2 and this wave's dual-track extension
(`.claude/team-runs/2026-07-27-wave3b-dual-track/team_findings.md` [T3]):
nodes are thin marshalling adapters. They read `state: EvaluationState`
and return a `dict[str, Any]` partial update; LangGraph merges it. No node
in this package computes a rule, a threshold or a verdict itself -- that
logic lives in `s2s_harness.rules` (Track A) or `s2s_harness.llm` (Track
B). If a node here needs a comment explaining a second responsibility, it
is two nodes.
"""

from __future__ import annotations
