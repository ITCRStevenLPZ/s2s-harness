# CLI specification

Typer + Rich. The CLI is the primary interface; the HTML front ends are a convenience layer over the same graph.

## Commands

```
s2s conversation      evaluate a ≥4-turn conversation with Model A and Model B
s2s clips             compare two single audio responses to one prompt
s2s audit FILE        re-audit a saved run, or a justification you wrote by hand
s2s serve             start the local bridge for the HTML front ends
s2s criteria [TOPIC]  print the project criteria (hierarchy, clusters, examples, thresholds)
s2s selftest          run the golden fixtures and report
```

## Global options

| Option | Effect |
|---|---|
| `--no-llm` | Skip `polish` entirely. The deterministic draft is the output. |
| `--dictate` | Record notes from the mic for each side. |
| `--notes-a PATH` / `--notes-b PATH` | Transcribe existing audio files instead of typing. |
| `--keep-audio` | Do not delete temp recordings. |
| `--json` | Emit the full state as JSON on stdout; suppress the pretty view. |
| `--out DIR` | Write `run.json` + `justification.md` to DIR. |
| `--resume RUN_ID` | Reload a checkpoint and re-run from the first changed input. |
| `--lang es\|en` | Force interface language for prompts. Justification output is always English. |
| `--strict` | Treat every warning as blocking (useful for self-training). |

## Interactive flow

Ordered to match how a rater actually works: context first, observations while the audio is fresh, picks last.

1. **Context** — scenario or prompt, scenario type, ground truth when the type embeds a false claim. Conversation mode adds the preflight checklist and turn counts.
2. **Side A, then Side B** — notes (typed or dictated), strongest moment, weakest moment. Immediately after notes, the scanner's suggestions are shown as a numbered list; the rater accepts by number, or presses Enter to accept none. **Never auto-apply.**
3. **Flags** — error clusters and threshold issues as multi-select checklists, pre-ticked with whatever the rater accepted from suggestions. Background noise and premise handling as single-select.
4. **Picks** — Naturalness first (the deciding dimension), then Utility, Audio, Overall. Conversation mode adds task success per side.
5. **Result** — verdict panel, trace, findings, draft.

The rater is never shown the engine's recommendation before making their own picks. Seeing it first would defeat the training purpose — the value is in the gap between their instinct and the rules.

## Output

```
╭─ Rules imply ─────────────────────────────────────────╮
│  Clip A                    Deciding: Threshold — Audio │
│  ✓ Your pick agrees with the rules.                    │
╰────────────────────────────────────────────────────────╯

  → Threshold gate: Clip B crosses the minimum threshold …
  → Naturalness / Engagement is the highest-weight dimension …

  ERROR    AUDIO      You selected Both Good for Audio Quality, but …
  WARNING  EVIDENCE   Fill the 'strongest thing' field for both clips.
  OK       COHERENT   Your overall preference matches the hierarchy outcome.

╭─ Justification (English) ─────────────────────────────╮
│ I prefer Clip A overall because …                      │
╰────────────────────────────────────────────────────────╯
```

Rules for rendering:

- Severity colours: error red, warning amber, info blue, ok green. Findings sorted by severity.
- `【placeholders】` render in inverse amber so they are impossible to miss.
- A blocking error prints `polish skipped — resolve the errors above first` where the polished text would be. This is the token guard made visible.
- `--json` output is the `EvaluationState` dump and is the same payload the bridge returns, so both interfaces are testable with one fixture set.

## `s2s audit`

Takes a saved `run.json`, or a markdown file containing a justification plus a picks block. Re-runs `normalize → decide → audit` and reports findings without regenerating the draft. This is the "check my homework" path: paste what you already submitted, find out what an auditor would flag.

## `s2s criteria`

Prints from `criteria/`, not from memory. `s2s criteria hierarchy`, `s2s criteria clusters`, `s2s criteria examples`, `s2s criteria audio`. Zero tokens — it is a file read.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Completed, no blocking errors |
| 1 | Completed, blocking errors present (or any warning under `--strict`) |
| 2 | Invalid input / state validation failure |
| 3 | Provider failure (STT or model) |
