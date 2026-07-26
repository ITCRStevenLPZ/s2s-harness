"""Deterministic rules engine.

Zero LLM calls, zero I/O, zero network, zero clock, zero randomness.
Imports stdlib and Pydantic only. See docs/RULES_SPEC.md for the contract
this package implements and CLAUDE.md rule 1 for why that boundary is
enforced by a separate import-boundary test rather than convention alone.
"""
