# Implementation target

Nothing here yet. Build in the order set by `docs/BUILD_PLAN.md`.

```
models/    Pydantic state schema            → GRAPH_SPEC §1   · graph-architect
rules/     deterministic engine, pure       → RULES_SPEC      · rules-engine-dev
nodes/     LangGraph node wrappers          → GRAPH_SPEC §2   · graph-architect
stt/       speech provider adapters         → STT_SPEC        · stt-engineer
cli/       Typer entrypoint                 → CLI_SPEC        · cli-dev
bridge/    FastAPI local endpoint           → BRIDGE_SPEC     · bridge-dev
graph.py   topology                         → GRAPH_SPEC §3   · graph-architect
```

`rules/` imports stdlib and Pydantic only. `nodes/polish.py` is the sole file permitted to call a language model.
