"""Rich rendering layer. `docs/CLI_SPEC.md` §Output and §Rendering.

Pure presentation: every function here takes already-decided data (a
`Verdict`, a `TrackBResult`, a list of `Finding`) and prints it. Nothing in
this module calls the graph, prompts the rater, or decides anything --
that split keeps the rendering testable with hand-built fixtures, without
a live engine.
"""

from __future__ import annotations

import re

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from s2s_harness.cli.dual_track import Agreement, TrackBResult
from s2s_harness.models.state import Finding, Pick, Picks, Severity, Suggestion, Verdict

_LabelMap = dict[Pick | None, str]


def _label_map(mode_labels: tuple[str, str]) -> _LabelMap:
    return {
        "A": mode_labels[0],
        "B": mode_labels[1],
        "TIE": "Both Good",
        "BAD": "Both Bad",
        None: "(none)",
    }


# Severity colours, `docs/CLI_SPEC.md` §Rendering: "error red, warning amber,
# info blue, ok green." Rich has no built-in "amber" name; approximated with
# an explicit hex so the intent (amber, not a generic yellow) is on the page.
_SEVERITY_STYLE: dict[Severity, str] = {
    "error": "bold red",
    "warning": "bold #e8a33d",
    "info": "bold blue",
    "ok": "bold green",
}
_SEVERITY_ORDER: dict[Severity, int] = {"error": 0, "warning": 1, "info": 2, "ok": 3}

# Inverse amber for placeholders -- "impossible to miss."
_PLACEHOLDER_STYLE = "black on #e8a33d bold"
_PLACEHOLDER_RE = re.compile(r"【[^】]*】")  # 【...】, exact guarded token


def sorted_findings(findings: list[Finding]) -> list[Finding]:
    """error -> warning -> info -> ok, per `{GRAPH-6}` / CLI_SPEC §Output."""
    return sorted(findings, key=lambda f: _SEVERITY_ORDER[f.severity])


def placeholder_text(raw: str) -> Text:
    """Render a string with every `【...】` span in inverse amber."""
    text = Text()
    pos = 0
    for match in _PLACEHOLDER_RE.finditer(raw):
        text.append(raw[pos : match.start()])
        text.append(match.group(0), style=_PLACEHOLDER_STYLE)
        pos = match.end()
    text.append(raw[pos:])
    return text


def render_findings(console: Console, findings: list[Finding]) -> None:
    if not findings:
        console.print("  (no findings)")
        return
    for finding in sorted_findings(findings):
        style = _SEVERITY_STYLE[finding.severity]
        line = Text()
        line.append(f"  {finding.severity.upper():<8} ", style=style)
        line.append(f"{finding.label:<10} ", style=style)
        line.append_text(placeholder_text(finding.message))
        console.print(line)


def _driver_panel(
    *, title: str, verdict_label: str, deciding: str, note: Text, style: str
) -> Panel:
    body = Table.grid(padding=(0, 2))
    body.add_column()
    body.add_column()
    body.add_row(Text(f"Verdict: {verdict_label}", style="bold"), Text(f"Deciding: {deciding}"))
    body.add_row(note, "")
    return Panel(body, title=title, border_style=style, expand=False)


def _rater_agreement_note(rater_pick: Pick | None, engine_pick: Pick | None) -> Text:
    """ "✓ Your pick agrees with the rules." / the disagreement form --
    `docs/CLI_SPEC.md` §Output worked example. This is the original
    single-track callout; Track B gets its own version of the same idea.
    """
    if rater_pick is None:
        return Text("(no pick recorded yet)", style="dim")
    if rater_pick == engine_pick:
        return Text("Your pick agrees.", style="bold green")
    return Text("Your pick differs from this track.", style="bold #e8a33d")


def render_track_a(
    console: Console,
    verdict: Verdict,
    *,
    rater_overall: Pick | None,
    mode_labels: tuple[str, str],
) -> None:
    labels = _label_map(mode_labels)
    verdict_label = labels.get(verdict.overall, str(verdict.overall))
    gate_note = ""
    if verdict.gated and verdict.gated_side:
        gate_note = f" (threshold-gated against {labels.get(verdict.gated_side)})"
    note = Text()
    note.append_text(_rater_agreement_note(rater_overall, verdict.overall))
    note.append(f"  Deterministic, reproducible.{gate_note}", style="dim")
    console.print(
        _driver_panel(
            title="Track A -- Rules engine",
            verdict_label=verdict_label,
            deciding=verdict.driver,
            note=note,
            style="cyan",
        )
    )
    for line in verdict.trace:
        console.print(f"  → {line}")


def render_track_b(
    console: Console,
    track_b: TrackBResult | None,
    *,
    llm_enabled: bool,
    rater_overall: Pick | None,
    mode_labels: tuple[str, str],
) -> None:
    if track_b is None:
        message = (
            "Track B did not run (--no-llm)."
            if not llm_enabled
            else "Track B ran but produced no usable verdict this time (see findings for why)."
        )
        console.print(
            Panel(
                Text(message, style="dim"),
                title="Track B -- LLM judge",
                border_style="dim",
                expand=False,
            )
        )
        return
    if track_b.skipped:
        console.print(
            Panel(
                Text(f"Track B skipped: {track_b.skipped_reason}", style="dim"),
                title="Track B -- LLM judge",
                border_style="dim",
                expand=False,
            )
        )
        return
    labels = _label_map(mode_labels)
    verdict_label = labels.get(track_b.verdict, str(track_b.verdict))
    note = Text()
    note.append_text(_rater_agreement_note(rater_overall, track_b.verdict))
    note.append("\n")
    note.append_text(placeholder_text(track_b.reasoning))
    console.print(
        _driver_panel(
            title=f"Track B -- LLM judge (confidence: {track_b.confidence})",
            verdict_label=verdict_label,
            deciding=track_b.driver,
            note=note,
            style="magenta",
        )
    )


def render_agreement(
    console: Console,
    agreement: Agreement,
    verdict: Verdict,
    track_b: TrackBResult | None,
    *,
    mode_labels: tuple[str, str],
) -> None:
    """Disagreement is the product, not an error state -- surface it as an
    invitation to think, never as a malfunction. `team_plan.md` "Disagreement
    between tracks is the product."
    """
    if track_b is None or track_b.skipped:
        return
    labels = _label_map(mode_labels)
    if agreement.agrees:
        console.print(
            Panel(
                Text("Track A and Track B agree on the overall pick.", style="bold green"),
                border_style="green",
                expand=False,
            )
        )
        return
    body = Text()
    body.append("Track A and Track B disagree.\n\n", style="bold #e8a33d")
    body.append(f"Track A says {labels.get(agreement.track_a)}, deciding on {verdict.driver}.\n")
    body.append(f"Track B says {labels.get(agreement.track_b)}, weighing: {track_b.reasoning}\n\n")
    body.append(
        "This gap is exactly what the tool is for. Sit with it before you "
        "submit -- ask which one missed something the other one caught.",
        style="italic",
    )
    console.print(Panel(body, title="Where they differ", border_style="#e8a33d", expand=False))


def render_justification(console: Console, *, text: str, blocking: bool) -> None:
    if blocking:
        console.print(
            Panel(
                Text("polish skipped -- resolve the errors above first", style="bold red"),
                title="Justification (English)",
                border_style="red",
                expand=False,
            )
        )
        return
    console.print(
        Panel(
            placeholder_text(text),
            title="Justification (English)",
            border_style="green",
            expand=False,
        )
    )


def render_result(
    console: Console,
    *,
    verdict: Verdict,
    track_b: TrackBResult | None,
    llm_enabled: bool,
    agreement: Agreement,
    findings: list[Finding],
    justification: str,
    picks: Picks,
    mode_labels: tuple[str, str],
) -> None:
    """The full Result step (`docs/CLI_SPEC.md` §Interactive flow, step 5).

    Only ever called after the rater has already entered picks -- see
    `interactive.py`. Never call this, or any function in this module, to
    show the rater a recommendation before that point.
    """
    blocking = any(f.severity == "error" for f in findings)
    rater_overall = picks.overall
    console.rule("Result")
    render_track_a(console, verdict, rater_overall=rater_overall, mode_labels=mode_labels)
    console.print()
    render_track_b(
        console,
        track_b,
        llm_enabled=llm_enabled,
        rater_overall=rater_overall,
        mode_labels=mode_labels,
    )
    console.print()
    render_agreement(console, agreement, verdict, track_b, mode_labels=mode_labels)
    console.print()
    render_findings(console, findings)
    console.print()
    render_justification(console, text=justification, blocking=blocking)


def render_suggestions(console: Console, suggestions: list[Suggestion]) -> None:
    """Numbered scanner-suggestion list, `{GRAPH-3}`. Never auto-applied --
    the caller (`interactive.py`) is responsible for prompting for a
    selection and only then mutating state.
    """
    if not suggestions:
        console.print("  (scanner found nothing to suggest)")
        return
    for i, suggestion in enumerate(suggestions, start=1):
        console.print(f"  [{i}] {suggestion.kind}: {suggestion.target}  -- “{suggestion.evidence}”")
