# S2S Arena Harness

One engine for both rating workflows on the **Live S2S Arena / Stereo Headphone Check Project**.

| Mode | Input | Question it answers |
|---|---|---|
| `conversation` | A ≥4-turn voice conversation with Model A and Model B | Which conversation would I rather continue? |
| `clips` | Two single audio responses to one prompt | Which clip is the better response? |

Both run the same criteria, the same hierarchy walk, the same contradiction audit, and the same justification builder.

## What it does

You bring your own observations — typed, or dictated and transcribed. The harness:

1. Scans your notes (Spanish or English) and suggests flags you may have forgotten to record.
2. Walks the project hierarchy deterministically: threshold gate first, then Naturalness → Utility → Audio Quality.
3. Audits your own dimension picks against the rules and names every contradiction, with the reason.
4. Drafts the English justification following the required five-part structure, leaving `【bracketed placeholders】` wherever only you can supply the detail.

It does not listen to the clips and it does not decide for you. It checks that what you decided is internally consistent and defensible under the project criteria.

## Quick start

```bash
uv sync
cp .env.example .env          # add GEMINI_API_KEY or GOOGLE_APPLICATION_CREDENTIALS
uv run s2s clips              # interactive clip comparison
uv run s2s conversation       # interactive conversation evaluation
uv run s2s serve              # local bridge for the HTML front ends
```

Dictate your notes instead of typing them:

```bash
uv run s2s clips --dictate                 # record from mic, transcribe, continue
uv run s2s clips --notes-a notes_a.m4a     # transcribe an existing recording
```

Skip the model entirely — the deterministic draft is always complete:

```bash
uv run s2s clips --no-llm
```

## Cost

One model call per evaluation, at the drafting step only, and it is skipped when the audit finds a blocking error. Everything else is plain Python: free, instant, and identical on every run. See `docs/ARCHITECTURE.md` for why the boundary sits where it does.

## Documentation

| Document | Contents |
|---|---|
| `CLAUDE.md` | Project guidance and non-negotiable design rules |
| `docs/BUILD_PLAN.md` | Ordered implementation sequence |
| `docs/ARCHITECTURE.md` | System shape, data flow, token boundary |
| `docs/GRAPH_SPEC.md` | State schema, nodes, edges, checkpointing |
| `docs/RULES_SPEC.md` | Every rule, gate and contradiction check, exhaustively |
| `docs/STT_SPEC.md` | Gemini / GCP speech adapters and phrase hints |
| `docs/CLI_SPEC.md` | Terminal interface contract |
| `docs/BRIDGE_SPEC.md` | Local endpoint and HTML front-end wiring |
| `docs/EVAL_SPEC.md` | Golden fixtures and regression policy |
| `criteria/` | Project source of truth |

## Status

Specifications only. Nothing is implemented yet.
