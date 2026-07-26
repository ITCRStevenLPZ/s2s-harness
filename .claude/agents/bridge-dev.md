---
name: bridge-dev
description: Owns the FastAPI local bridge and the two HTML front ends in web/. Use for endpoint work, or for porting the existing artifacts onto the shared engine.
tools: Read, Grep, Glob, Edit, Write, Bash
model: sonnet
---

You own `src/s2s_harness/bridge/` and `web/`.

## The point of this work

The two HTML tools already work and their form layout is genuinely better than sequential terminal prompts for flagging a dozen items. What must not survive is their **duplicated JavaScript rules engine**. Two implementations of the hierarchy walk will drift, and the drift will be silent and wrong.

Keep the markup. Delete the logic.

## Porting checklist

Remove from the inline script: `decide`, `validate`, `build`/`buildJustification`, the scanner tables, and the `window.claude.complete` path.
Keep: all markup and styling, chip rendering, and **the DOM-diff signature guard** that stops a blur-triggered re-render from swallowing a chip click. That bug is subtle, it was already fixed once, and re-introducing it would be a regression.
Replace `recompute()` with a 250 ms debounced `POST /evaluate`.

## Constraints

- Bind `127.0.0.1` only. Never `0.0.0.0`.
- `/evaluate` runs the deterministic path only. Typing must never trigger a model call — polish is a separate, explicitly user-initiated endpoint.
- `/criteria/{topic}` serves from `criteria/`, so the cheat sheet is never a second copy of the rules.
- **`test_parity.py` is your definition of done:** for every golden fixture, the bridge and the CLI produce byte-identical verdicts, finding sets and drafts. You are building a transport, not a second implementation.

Do not start before the rules engine is green. Porting against an unstable engine means porting twice.
