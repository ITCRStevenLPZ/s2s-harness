# CLI specification

Version: 1.0.0
Last updated: 2026-07-26

**ID convention:** `CLI-n`, assigned once per command (in the order listed in §Commands) then once per global option (in table order), then once per exit code. Placement is `{CLI-n}` as a trailing tag on the `s2s ...` command lines in the fenced block, and a bare `` `CLI-n` `` value in a dedicated `ID` table column for the Global options and Exit codes tables — both forms are equally greppable via `CLI-[0-9]+`; the difference is only whether the surrounding row already has its own column structure to use. `CLI-16` (`--version`) was filled in from T4-ci-dev's versioning contract; see `VERSIONING.md`. IDs are additive only; no command or option semantics below were changed to add them.

Typer + Rich. The CLI is the primary interface; the HTML front ends are a convenience layer over the same graph.

## Commands

```
s2s conversation      evaluate a ≥4-turn conversation with Model A and Model B   {CLI-1}
s2s clips             compare two single audio responses to one prompt          {CLI-2}
s2s audit FILE        re-audit a saved run, or a justification you wrote by hand {CLI-3}
s2s serve             start the local bridge for the HTML front ends            {CLI-4}
s2s criteria [TOPIC]  print the project criteria (hierarchy, clusters, examples, thresholds)  {CLI-5}
s2s selftest          run the golden fixtures and report                        {CLI-6}
```

## Global options

| Option | Effect | ID |
|---|---|---|
| `--no-llm` | Skip `polish` entirely. The deterministic draft is the output. | `CLI-7` |
| `--dictate` | Record notes from the mic for each side. | `CLI-8` |
| `--notes-a PATH` / `--notes-b PATH` | Transcribe existing audio files instead of typing. | `CLI-9` |
| `--keep-audio` | Do not delete temp recordings. | `CLI-10` |
| `--json` | Emit the full state as JSON on stdout; suppress the pretty view. | `CLI-11` |
| `--out DIR` | Write `run.json` + `justification.md` to DIR. | `CLI-12` |
| `--resume RUN_ID` | Reload a checkpoint and re-run from the first changed input. | `CLI-13` |
| `--lang es\|en` | Force interface language for prompts. Justification output is always English. | `CLI-14` |
| `--strict` | Treat every warning as blocking (useful for self-training). | `CLI-15` |
| `--version` | Print the installed package version to stdout as a bare string (e.g. `0.1.0`) and exit 0 immediately, no other side effects — evaluated before subcommand dispatch, works with no other arguments (`s2s --version`), does not touch config, STT, LLM or any state file. Available on the top-level `s2s` command, not per-subcommand. Source of truth is `importlib.metadata.version("s2s-harness")`, which reads `[project] version` in `pyproject.toml` — never a second hardcoded constant in the CLI layer. See `VERSIONING.md` for the SemVer scheme this value follows. No short form: no other global option in this table has one, so `-V` is deliberately omitted to keep the convention uniform rather than introduce a one-off exception. | `CLI-16` |

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

| Code | Meaning | ID |
|---|---|---|
| 0 | Completed, no blocking errors | `CLI-17` |
| 1 | Completed, blocking errors present (or any warning under `--strict`) | `CLI-18` |
| 2 | Invalid input / state validation failure | `CLI-19` |
| 3 | Provider failure (STT or model) | `CLI-20` |
