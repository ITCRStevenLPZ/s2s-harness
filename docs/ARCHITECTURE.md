# Architecture

Version: 1.1.0
Last updated: 2026-07-26

## Shape

One LangGraph graph, two entry schemas. The mode (`conversation` | `clips`) selects which validations run and which vocabulary the renderer uses ("Model A" vs "Clip A", turns vs no turns). Everything downstream of `normalize` is mode-agnostic.

```
                    ┌──────────────┐
  typed notes ─────▶│    ingest    │
  audio files ─────▶│              │
                    └──────┬───────┘
                           │  audio present?
                    ┌──────▼───────┐
                    │  transcribe  │  Gemini / GCP · only node that touches audio
                    └──────┬───────┘
                    ┌──────▼───────┐
                    │     scan     │  regex signals → suggested flags        0 tokens
                    └──────┬───────┘
                    ┌──────▼───────┐
                    │  normalize   │  derive threshold sets, apply inversions 0 tokens
                    └──────┬───────┘
                    ┌──────▼───────┐
                    │    decide    │  threshold gate → hierarchy walk         0 tokens
                    └──────┬───────┘
                    ┌──────▼───────┐
                    │    audit     │  contradiction + completeness findings   0 tokens
                    └──────┬───────┘
                    ┌──────▼───────┐
                    │    draft     │  deterministic justification             0 tokens
                    └──────┬───────┘
                           │  blocking errors? ──yes──▶ skip polish
                    ┌──────▼───────┐
                    │    polish    │  ◀── the only LLM call in the system
                    └──────┬───────┘
                    ┌──────▼───────┐
                    │    render    │  stdout · markdown · JSON
                    └──────────────┘
```

## Why the token boundary sits there

The project criteria are a decision procedure, not a judgement call. "Both Good on Audio Quality is illegal when either side has a noticeable artifact" is an `if` statement. "A side that breaches the threshold while the other is clean should not be preferred" is an `if` statement. Handing those to a language model would make the verdict non-reproducible, unauditable, and expensive, in exchange for nothing.

What a model *is* good at is the last mile: turning `evidence_a`, `evidence_b`, a driver and a flag list into a paragraph that reads like a person wrote it. That is one call, on already-decided content, with a hard instruction not to add facts.

Three consequences:

- **Reproducibility.** Re-run any past evaluation and the verdict, the trace and the findings are byte-identical. Only the prose can vary.
- **Auditability.** When the harness says "your Overall contradicts your Naturalness pick", you can point at the exact rule in `docs/RULES_SPEC.md` that fired. There is no "the model thought so".
- **Cost.** An evaluation with `--no-llm` costs nothing. A normal one costs a single short completion. A blocked one (audit found a hard error) costs nothing, because polishing a justification that should not be submitted is waste.

### Draft-hash caching

`polish` is keyed on `sha256(deterministic_draft + mode + polish_prompt_version)`. Fixing an unrelated field, re-running, and producing the same deterministic draft returns the cached polished text without a second call. Cache lives in `.s2s-cache/` (gitignored) and is content-addressed, so it never goes stale incorrectly.

## Layer boundaries

| Layer | May import | May not |
|---|---|---|
| `rules/` | stdlib, Pydantic | anything doing I/O, network, or model calls |
| `models/` | Pydantic | everything else |
| `nodes/` | `rules/`, `models/`, `stt/` | CLI or bridge code |
| `stt/` | provider SDKs, `models/` | `rules/` |
| `cli/`, `bridge/` | `nodes/`, `models/` | `rules/` directly — go through the graph |

`rules/` being pure is what makes the golden fixtures meaningful: they call the engine with a fixture state and assert on the verdict, with no mocking of anything.

## Data flow in one sentence

Raw observations (typed or spoken) become a validated `EvaluationState`; the engine derives a `Verdict` and a list of `Finding`s from it without ever consulting a model; the draft builder turns those into English; the model, optionally and once, makes that English better.

## What is deliberately absent

- **No database.** Each evaluation is a run. Records are written as JSON + markdown to `runs/` if the rater asks; nothing persists otherwise.
- **Deprecated (local-only scope; superseded for hosted deployment by `docs/DEPLOY_SPEC.md` DEPLOY-9 through DEPLOY-15).** Originally: "No auth, no multi-user. Single rater, local machine." This remains exactly true when the bridge runs locally via `s2s serve` — nothing about local usage changed. It is superseded only for the Cloud Run hosted deployment, which is still single-rater (multi-user support is still absent, see `docs/DEPLOY_SPEC.md` DEPLOY-26) but requires an app-level API key because the surface is no longer loopback-only. See `docs/DEPLOY_SPEC.md` for the full hosted-deployment auth and network posture.
- **No clip audio analysis in the default path.** See `docs/STT_SPEC.md` §6. Unchanged by hosting; `docs/DEPLOY_SPEC.md` DEPLOY-26 confirms this stays binding in the deployed configuration.
- **No agent framework at runtime.** The `.claude/agents/` roster is for *building* this repo with Claude Code. The shipped application is a graph, not an agent swarm — agents add nondeterminism and cost to a problem that has neither.
