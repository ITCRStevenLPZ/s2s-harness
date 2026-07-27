"""Interactive flow. `docs/CLI_SPEC.md` §Interactive flow.

Order is fixed and load-bearing: **context, then observations while the
audio is fresh, then flags, then picks, then results.** Nothing in this
module may call `render_result`, `render_track_a` or `render_track_b`
before `_collect_picks` has returned -- that would show the rater either
engine's recommendation before their own picks are locked in, which is
the one rule `CLAUDE.md` and `.claude/agents/cli-dev.md` both name first.

`scan()` (per `team_findings.md`, `{GRAPH-3}`) takes the *whole* state, not
one side's notes. This module calls it once per side, immediately after
that side's notes are entered, with the other side's fields still at their
defaults, and keeps only the `Suggestion`s tagged for the side just
entered -- so "shown immediately after notes" (CLI_SPEC) and "scan reads
the whole state" (team_findings.md) are both satisfied without a special
case in the scanner itself.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import ValidationError
from rich.console import Console
from rich.prompt import Confirm, IntPrompt, Prompt

from s2s_harness.cli.dual_track import (
    Submission,
    TrackBResult,
    default_submission,
    override_submission,
)
from s2s_harness.cli.errors import InvalidInputError
from s2s_harness.cli.render import render_suggestions
from s2s_harness.models.state import (
    Mode,
    Pick,
    Picks,
    Preflight,
    ScenarioType,
    Side,
    SideObservation,
    Suggestion,
    TaskContext,
)

_SCENARIO_TYPES: tuple[ScenarioType, ...] = (
    "standard",
    "redteam",
    "premise",
    "instruction",
    "interrupt",
    "emotional",
    "roleplay",
    "creative",
)
_PICK_CHOICES: tuple[str, ...] = ("A", "B", "TIE", "BAD")
_NOISE_CHOICES = ("clean", "slight", "notable")
_PREMISE_CHOICES = ("na", "pushback", "hedged", "accepted")
_SUCCESS_CHOICES = ("pass", "partial", "fail")


def _wrap_validation(exc: ValidationError, *, what: str) -> InvalidInputError:
    return InvalidInputError(f"{what}: {exc}")


def _choice(console: Console, prompt: str, choices: tuple[str, ...], *, default: str) -> str:
    return Prompt.ask(prompt, choices=list(choices), default=default, console=console)


def collect_context(console: Console, *, mode: Mode) -> TaskContext:
    """Step 1 -- context. `docs/CLI_SPEC.md` §Interactive flow item 1."""
    console.rule("Context")
    scenario_type = _choice(console, "Scenario type", _SCENARIO_TYPES, default="standard")
    kwargs: dict[str, object] = {"mode": mode, "scenario_type": scenario_type}
    if mode == "conversation":
        kwargs["scenario"] = Prompt.ask("Assigned scenario / persona", console=console, default="")
    else:
        kwargs["prompt"] = Prompt.ask("Prompt the clips answer", console=console, default="")
    if scenario_type in ("redteam", "premise"):
        kwargs["ground_truth"] = Prompt.ask(
            "Ground truth (the fact the false premise contradicts)", console=console, default=""
        )
    if mode == "conversation":
        console.print("Preflight checklist -- answer honestly, this is not scored:")
        preflight = Preflight(
            headphones=Confirm.ask(
                "  Phase-aligned stereo headphones?", console=console, default=True
            ),
            panning_check=Confirm.ask("  Passed the panning check?", console=console, default=True),
            scenario_read=Confirm.ask(
                "  Read the assigned scenario?", console=console, default=True
            ),
            listened_isolated=Confirm.ask(
                "  Listened to each side in isolation?", console=console, default=True
            ),
            equivalent_prompts=Confirm.ask(
                "  Prompts equally specific on both sides?", console=console, default=True
            ),
            stayed_in_character=Confirm.ask(
                "  Stayed in persona throughout?", console=console, default=True
            ),
            interruption_tested=Confirm.ask(
                "  Tested interruption / correction?", console=console, default=True
            ),
        )
        kwargs["preflight"] = preflight
    try:
        return TaskContext.model_validate(kwargs)
    except ValidationError as exc:
        raise _wrap_validation(exc, what="context") from exc


def collect_side_notes(console: Console, *, side: Side, mode: Mode, label: str) -> SideObservation:
    """Step 2 (per side) -- notes, strongest/weakest moment.

    Scanner suggestions for this side are shown right after, by the
    caller (`run_scan_for_side`), not here -- this function only collects
    the free-form notes a suggestion is generated from.
    """
    console.rule(f"{label} -- notes")
    notes = Prompt.ask(
        f"Notes for {label} (typed; dictation via --dictate wires transcribe)",
        console=console,
        default="",
    )
    best = Prompt.ask(f"{label}'s strongest specific moment", console=console, default="")
    worst = Prompt.ask(f"{label}'s weakest specific moment", console=console, default="")
    kwargs: dict[str, object] = {"side": side, "notes": notes, "best": best, "worst": worst}
    if mode == "conversation":
        turns = IntPrompt.ask(f"Turn count for {label} (minimum 4)", console=console, default=4)
        kwargs["turns"] = turns
        success = _choice(console, f"{label} task success", _SUCCESS_CHOICES, default="pass")
        kwargs["task_success"] = success
    try:
        return SideObservation.model_validate(kwargs)
    except ValidationError as exc:
        raise _wrap_validation(exc, what=f"{label} notes") from exc


def apply_suggestions(
    console: Console,
    side_obs: SideObservation,
    suggestions: list[Suggestion],
) -> SideObservation:
    """Numbered list, accept by number or Enter for none. Never auto-applied,
    `{GRAPH-3}`.
    """
    render_suggestions(console, suggestions)
    if not suggestions:
        return side_obs
    raw = Prompt.ask(
        "Accept suggestions by number (comma-separated), or Enter for none",
        console=console,
        default="",
    )
    if not raw.strip():
        return side_obs
    picked_indexes = {int(tok.strip()) for tok in raw.split(",") if tok.strip().isdigit()}
    error_clusters = list(side_obs.error_clusters)
    threshold_utility = list(side_obs.threshold_utility)
    threshold_audio = list(side_obs.threshold_audio)
    for i, suggestion in enumerate(suggestions, start=1):
        if i not in picked_indexes:
            continue
        if suggestion.kind == "error_cluster" and suggestion.target not in error_clusters:
            error_clusters.append(suggestion.target)
        elif suggestion.kind == "threshold_utility" and suggestion.target not in threshold_utility:
            threshold_utility.append(suggestion.target)
        elif suggestion.kind == "threshold_audio" and suggestion.target not in threshold_audio:
            threshold_audio.append(suggestion.target)
        # "tone" suggestions have no flag field to write to; they inform the
        # rater's own judgement only.
    try:
        return side_obs.model_copy(
            update={
                "error_clusters": error_clusters,
                "threshold_utility": threshold_utility,
                "threshold_audio": threshold_audio,
            }
        )
    except ValidationError as exc:
        raise _wrap_validation(exc, what="accepted suggestions") from exc


def _manual_catalogue_entry(
    console: Console, *, label: str, field_label: str, current: list[str]
) -> list[str]:
    """Manual multi-select for a catalogue field, `docs/CLI_SPEC.md` step 3.

    CLI_SPEC wants error clusters and threshold issues as multi-select
    checklists. `rules/catalog.py` (the mode-aware key/display-string
    source) lives in `rules/`, which `cli/` may not import directly
    (`docs/ARCHITECTURE.md` layer table) -- there is currently no
    `nodes/`-facing accessor for catalogue metadata, so this cannot render
    a labelled checklist of valid keys the way `s2s criteria clusters`
    renders prose. Simplified interim form: shows what is already ticked
    (from accepted scanner suggestions), and accepts additional catalogue
    keys typed by name (see `s2s criteria clusters` / `thresholds` /
    `audio` for the valid vocabulary); final construction still validates
    every key against the closed catalogue and raises `{CLI-19}` on an
    unknown one, so this never silently accepts nonsense. Flagged as a
    gap in `team_findings.md` [T4] -- the real fix is a small `nodes/` or
    `models/`-facing catalogue accessor `cli/` can import.
    """
    if current:
        console.print(f"  {label} {field_label} already ticked: {', '.join(current)}")
    else:
        console.print(f"  {label} {field_label}: none ticked yet")
    raw = Prompt.ask(
        f"Add more {field_label} by key (comma-separated; see 's2s criteria clusters' / "
        "'thresholds' / 'audio'), or Enter for none",
        console=console,
        default="",
    )
    added = [tok.strip() for tok in raw.split(",") if tok.strip()]
    merged = list(current)
    for key in added:
        if key not in merged:
            merged.append(key)
    return merged


def collect_flags(console: Console, side_obs: SideObservation, *, label: str) -> SideObservation:
    """Step 3 -- error clusters and threshold issues as checklists, noise and
    premise handling as single-select. Pre-ticked state carried in from
    `apply_suggestions` is shown as the current default.
    """
    console.rule(f"{label} -- flags")
    error_clusters = _manual_catalogue_entry(
        console, label=label, field_label="error clusters", current=side_obs.error_clusters
    )
    threshold_utility = _manual_catalogue_entry(
        console,
        label=label,
        field_label="utility threshold issues",
        current=side_obs.threshold_utility,
    )
    threshold_audio = _manual_catalogue_entry(
        console, label=label, field_label="audio threshold issues", current=side_obs.threshold_audio
    )
    background_noise = _choice(
        console, f"{label} background noise", _NOISE_CHOICES, default=side_obs.background_noise
    )
    premise_handling = _choice(
        console, f"{label} premise handling", _PREMISE_CHOICES, default=side_obs.premise_handling
    )
    try:
        return side_obs.model_copy(
            update={
                "error_clusters": error_clusters,
                "threshold_utility": threshold_utility,
                "threshold_audio": threshold_audio,
                "background_noise": background_noise,
                "premise_handling": premise_handling,
            }
        )
    except ValidationError as exc:
        raise _wrap_validation(exc, what="flags") from exc


def collect_picks(console: Console, *, mode: Mode, labels: tuple[str, str]) -> Picks:
    """Step 4 -- picks, Naturalness first, then Utility, Audio, Overall.

    This is the last thing the rater does before either engine's opinion is
    shown. Nothing upstream of this function may have rendered a verdict.
    """
    console.rule("Picks")
    console.print(f"Options: A ({labels[0]}), B ({labels[1]}), TIE (Both Good), BAD (Both Bad).")
    naturalness = _choice(
        console, "Naturalness / Engagement / Aesthetics", _PICK_CHOICES, default="A"
    )
    utility = _choice(console, "Utility", _PICK_CHOICES, default="A")
    audio = _choice(console, "Audio Quality", _PICK_CHOICES, default="A")
    overall = _choice(console, "Overall preference", _PICK_CHOICES, default="A")
    try:
        return Picks.model_validate(
            {"naturalness": naturalness, "utility": utility, "audio": audio, "overall": overall}
        )
    except ValidationError as exc:
        raise _wrap_validation(exc, what="picks") from exc


@dataclass(frozen=True)
class SubmissionChoiceContext:
    track_a_verdict: Pick | None
    track_b: TrackBResult | None


def prompt_submission(console: Console, ctx: SubmissionChoiceContext) -> Submission:
    """One keystroke, explicit, recorded. Default is Track A.

    `team_plan.md`: "The rater submits. Default is Track A's verdict.
    Overriding with Track B's is explicit, one keystroke, and recorded.
    Nothing auto-applies."
    """
    if ctx.track_b is None or ctx.track_b.skipped or ctx.track_b.verdict == ctx.track_a_verdict:
        return default_submission(ctx.track_a_verdict)
    choice = Prompt.ask(
        "Submit with [A] Track A's verdict (default) or [B] override with Track B's",
        choices=["A", "B"],
        default="A",
        console=console,
    )
    if choice == "B":
        return override_submission(ctx.track_b)
    return default_submission(ctx.track_a_verdict)
