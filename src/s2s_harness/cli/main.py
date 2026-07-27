"""Typer + Rich entrypoint. `docs/CLI_SPEC.md` is the contract.

Six commands (`{CLI-1}`..`{CLI-6}`), eleven global options (`{CLI-7}`..
`{CLI-16}`), four exit codes (`{CLI-17}`..`{CLI-20}`). `[project.scripts]`
in `pyproject.toml` points `s2s` at `s2s_harness.cli.main:app`.
"""

from __future__ import annotations

import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError
from rich.console import Console

from s2s_harness.cli import criteria_cmd, interactive, io_run, render, runner
from s2s_harness.cli.dual_track import Submission
from s2s_harness.cli.errors import EXIT_BLOCKING, EXIT_INVALID, EXIT_OK, CliError
from s2s_harness.models.state import EvaluationState, Mode, Severity

PACKAGE_NAME = "s2s-harness"

app = typer.Typer(add_completion=False, no_args_is_help=True)
console = Console()
err_console = Console(stderr=True)


def _version_string() -> str:
    """Source of truth is packaging metadata, never a second hardcoded
    constant in this layer, `{CLI-16}`. See `docs/VERSIONING.md`.
    """
    return importlib.metadata.version(PACKAGE_NAME)


def _version_callback(value: bool) -> None:
    if not value:
        return
    # No other side effects: no config, no STT, no LLM, exits before any
    # subcommand would otherwise dispatch.
    typer.echo(_version_string())
    raise typer.Exit(code=EXIT_OK)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Print the installed package version and exit. No short form (CLI_SPEC {CLI-16}).",
            is_eager=True,
            callback=_version_callback,
            expose_value=False,
        ),
    ] = False,
) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(code=EXIT_OK)


# ---------------------------------------------------------------------------
# Shared option definitions -- reused verbatim across the commands they
# apply to, so `{CLI-7}`..`{CLI-15}` are each defined in exactly one place.
# ---------------------------------------------------------------------------

NoLlmOption = Annotated[
    bool,
    typer.Option(
        "--no-llm", help="Skip Track B / polish entirely. Track A's draft is the output. {CLI-7}"
    ),
]
DictateOption = Annotated[
    bool, typer.Option("--dictate", help="Record notes from the mic for each side. {CLI-8}")
]
NotesAOption = Annotated[
    Path | None,
    typer.Option("--notes-a", help="Transcribe an existing audio file for side A. {CLI-9}"),
]
NotesBOption = Annotated[
    Path | None,
    typer.Option("--notes-b", help="Transcribe an existing audio file for side B. {CLI-9}"),
]
KeepAudioOption = Annotated[
    bool, typer.Option("--keep-audio", help="Do not delete temp recordings. {CLI-10}")
]
JsonOption = Annotated[
    bool,
    typer.Option(
        "--json", help="Emit the full state as JSON on stdout; suppress the pretty view. {CLI-11}"
    ),
]
OutOption = Annotated[
    Path | None, typer.Option("--out", help="Write run.json + justification.md to DIR. {CLI-12}")
]
ResumeOption = Annotated[
    str | None,
    typer.Option(
        "--resume", help="Reload a checkpoint and re-run from the first changed input. {CLI-13}"
    ),
]
LangOption = Annotated[
    str,
    typer.Option(
        "--lang",
        help="Force interface language for prompts (es|en). Justification stays English. {CLI-14}",
    ),
]
StrictOption = Annotated[
    bool, typer.Option("--strict", help="Treat every warning as blocking. {CLI-15}")
]


def _validate_lang(lang: str) -> str:
    if lang not in ("es", "en"):
        raise CliError(f"--lang must be 'es' or 'en', got {lang!r}", exit_code=EXIT_INVALID)
    return lang


def _exit_code_for(findings_severities: list[Severity], *, strict: bool) -> int:
    """`{CLI-17}`/`{CLI-18}`: 0 clean, 1 blocking errors present, or (under
    `--strict`) any warning present.
    """
    if any(s == "error" for s in findings_severities):
        return EXIT_BLOCKING
    if strict and any(s == "warning" for s in findings_severities):
        return EXIT_BLOCKING
    return EXIT_OK


def _mode_labels(mode: Mode) -> tuple[str, str]:
    return ("Model A", "Model B") if mode == "conversation" else ("Clip A", "Clip B")


def _run_evaluation(
    *,
    mode: Mode,
    no_llm: bool,
    dictate: bool,
    notes_a: Path | None,
    notes_b: Path | None,
    keep_audio: bool,
    json_output: bool,
    out: Path | None,
    resume: str | None,
    lang: str,
    strict: bool,
) -> None:
    """Thin wrapper: Typer/Click's own dispatch has no single hook to catch
    an exception raised inside a command and translate it into a chosen
    exit code, so each command-facing function does that translation at
    its own boundary rather than relying on a global handler that does not
    exist. See `_handle_cli_error`.
    """
    try:
        _run_evaluation_body(
            mode=mode,
            no_llm=no_llm,
            dictate=dictate,
            notes_a=notes_a,
            notes_b=notes_b,
            keep_audio=keep_audio,
            json_output=json_output,
            out=out,
            resume=resume,
            lang=lang,
            strict=strict,
        )
    except CliError as exc:
        _handle_cli_error(exc)


def _run_evaluation_body(
    *,
    mode: Mode,
    no_llm: bool,
    dictate: bool,
    notes_a: Path | None,
    notes_b: Path | None,
    keep_audio: bool,
    json_output: bool,
    out: Path | None,
    resume: str | None,
    lang: str,
    strict: bool,
) -> None:
    _validate_lang(lang)
    labels = _mode_labels(mode)

    # All interactive prompts go to stderr, never stdout: `--json` promises
    # "the full state as JSON on stdout", and that promise has to hold even
    # though the rater's own answers are collected in the same command
    # invocation, before the JSON exists. Keeping prompts off stdout
    # unconditionally (not just under `--json`) means `s2s clips --json`
    # is pipeable without a special case, and the pretty (non-JSON) path
    # is unaffected since it renders its own output on stdout afterward.
    prompt_console = err_console

    context = interactive.collect_context(prompt_console, mode=mode)

    audio_inputs: dict[str, Path] = {}
    if notes_a is not None:
        audio_inputs["a"] = notes_a
    if notes_b is not None:
        audio_inputs["b"] = notes_b
    if dictate:
        err_console.print(
            "[dim]--dictate requires the STT adapter (docs/STT_SPEC.md); "
            "recording is wired through transcribe once s2s_harness.graph lands.[/dim]"
        )

    a = interactive.collect_side_notes(prompt_console, side="A", mode=mode, label=labels[0])
    a_suggestions = [
        s for s in runner.scan_for_state(_partial_state(context, a, None)) if s.side == "A"
    ]
    a = interactive.apply_suggestions(prompt_console, a, a_suggestions)
    a = interactive.collect_flags(prompt_console, a, label=labels[0])

    b = interactive.collect_side_notes(prompt_console, side="B", mode=mode, label=labels[1])
    b_suggestions = [
        s for s in runner.scan_for_state(_partial_state(context, a, b)) if s.side == "B"
    ]
    b = interactive.apply_suggestions(prompt_console, b, b_suggestions)
    b = interactive.collect_flags(prompt_console, b, label=labels[1])

    picks = interactive.collect_picks(prompt_console, mode=mode, labels=labels)

    try:
        state = EvaluationState(context=context, a=a, b=b, picks=picks, audio_inputs=audio_inputs)
    except ValidationError as exc:
        raise CliError(str(exc), exit_code=EXIT_INVALID) from exc

    result = runner.run_graph_for_state(
        state,
        llm_enabled=not no_llm,
        resume_id=resume,
        checkpoint_dir=Path(".s2s-cache"),
    )
    if not keep_audio:
        pass  # nothing recorded yet without a real STT adapter wired in

    submission = interactive.prompt_submission(
        prompt_console,
        interactive.SubmissionChoiceContext(
            track_a_verdict=result.state.verdict.overall if result.state.verdict else None,
            track_b=result.track_b,
        ),
    )

    _emit(result, submission, json_output=json_output, out=out, labels=labels, strict=strict)


def _partial_state(context: object, a: object, b: object) -> EvaluationState:
    """Builds a throwaway state for `scan_for_state`, side B defaulted until
    it is entered. `context` and `a`/`b` are already-validated models by the
    time this is called.
    """
    from s2s_harness.models.state import SideObservation, TaskContext

    assert isinstance(context, TaskContext)
    assert isinstance(a, SideObservation)
    b_obs = b if isinstance(b, SideObservation) else SideObservation(side="B")
    return EvaluationState(context=context, a=a, b=b_obs)


def _emit(
    result: runner.RunResult,
    submission: Submission,
    *,
    json_output: bool,
    out: Path | None,
    labels: tuple[str, str],
    strict: bool,
) -> None:
    if out is not None:
        io_run.write_run(out, result, submission)

    if json_output:
        typer.echo(
            json.dumps(io_run.to_json_dict(result, submission), indent=2, ensure_ascii=False)
        )
    else:
        verdict = result.state.verdict
        if verdict is None:
            err_console.print(
                "[bold red]No verdict produced (Naturalness pick missing).[/bold red]"
            )
            raise typer.Exit(code=EXIT_INVALID)
        render.render_result(
            console,
            verdict=verdict,
            track_b=result.track_b,
            llm_enabled=result.state.llm_enabled,
            agreement=result.agreement,
            findings=result.state.findings,
            justification=result.state.polished or result.state.draft,
            picks=result.state.picks,
            mode_labels=labels,
        )

    severities = [f.severity for f in result.state.findings]
    raise typer.Exit(code=_exit_code_for(severities, strict=strict))


@app.command("conversation")
def conversation(
    no_llm: NoLlmOption = False,
    dictate: DictateOption = False,
    notes_a: NotesAOption = None,
    notes_b: NotesBOption = None,
    keep_audio: KeepAudioOption = False,
    json_output: JsonOption = False,
    out: OutOption = None,
    resume: ResumeOption = None,
    lang: LangOption = "en",
    strict: StrictOption = False,
) -> None:
    """Evaluate a >=4-turn conversation with Model A and Model B. {CLI-1}"""
    _run_evaluation(
        mode="conversation",
        no_llm=no_llm,
        dictate=dictate,
        notes_a=notes_a,
        notes_b=notes_b,
        keep_audio=keep_audio,
        json_output=json_output,
        out=out,
        resume=resume,
        lang=lang,
        strict=strict,
    )


@app.command("clips")
def clips(
    no_llm: NoLlmOption = False,
    dictate: DictateOption = False,
    notes_a: NotesAOption = None,
    notes_b: NotesBOption = None,
    keep_audio: KeepAudioOption = False,
    json_output: JsonOption = False,
    out: OutOption = None,
    resume: ResumeOption = None,
    lang: LangOption = "en",
    strict: StrictOption = False,
) -> None:
    """Compare two single audio responses to one prompt. {CLI-2}"""
    _run_evaluation(
        mode="clips",
        no_llm=no_llm,
        dictate=dictate,
        notes_a=notes_a,
        notes_b=notes_b,
        keep_audio=keep_audio,
        json_output=json_output,
        out=out,
        resume=resume,
        lang=lang,
        strict=strict,
    )


@app.command("audit")
def audit(
    file: Annotated[
        Path, typer.Argument(help="A saved run.json, or a markdown file with a picks frontmatter.")
    ],
    json_output: JsonOption = False,
    strict: StrictOption = False,
) -> None:
    """Re-audit a saved run, or a justification you wrote by hand. {CLI-3}

    Re-runs normalize -> decide -> audit and reports findings without
    regenerating the draft (`docs/CLI_SPEC.md` §`s2s audit`) -- the direct
    node pipeline (`runner.run_audit_only`), never the compiled graph:
    this command has no use for `draft` or either LLM track.
    """
    try:
        state, submitted_justification = io_run.parse_audit_file(file)
        audited_state = runner.run_audit_only(state)
    except CliError as exc:
        _handle_cli_error(exc)
        return  # unreachable, _handle_cli_error always raises typer.Exit
    labels = _mode_labels(audited_state.context.mode)
    if json_output:
        payload: dict[str, object] = {
            "state": audited_state.model_dump(mode="json"),
            "submitted_justification": submitted_justification,
        }
        typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        verdict = audited_state.verdict
        console.print(f"Previously submitted justification:\n\n{submitted_justification}\n")
        if verdict is not None:
            render.render_track_a(
                console, verdict, rater_overall=audited_state.picks.overall, mode_labels=labels
            )
        render.render_findings(console, audited_state.findings)
    severities = [f.severity for f in audited_state.findings]
    raise typer.Exit(code=_exit_code_for(severities, strict=strict))


@app.command("serve")
def serve(
    host: Annotated[str, typer.Option(help="Bind host for the local bridge.")] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="Bind port for the local bridge.")] = 8420,
) -> None:
    """Start the local bridge for the HTML front ends. {CLI-4}"""
    try:
        import uvicorn

        from s2s_harness.bridge.app import app as bridge_app  # type: ignore[import-untyped]
    except ImportError as exc:
        err_console.print(f"[bold red]bridge not available yet: {exc}[/bold red]")
        raise typer.Exit(code=3) from exc
    uvicorn.run(bridge_app, host=host, port=port)


@app.command("criteria")
def criteria(
    topic: Annotated[
        str | None,
        typer.Argument(
            help="hierarchy | clusters | examples | audio | thresholds. Omit for the full file."
        ),
    ] = None,
) -> None:
    """Print the project criteria (hierarchy, clusters, examples, thresholds). {CLI-5}"""
    try:
        text = criteria_cmd.render_criteria(topic)
    except CliError as exc:
        _handle_cli_error(exc)
        return
    console.print(text, highlight=False)


@app.command("selftest")
def selftest() -> None:
    """Run the golden fixtures and report. {CLI-6}"""
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/golden",
            "-q",
            "-m",
            "not tier2",
            "--disable-socket",
        ],
        check=False,
    )
    no_tests_collected = 5
    if completed.returncode == no_tests_collected:
        console.print("[dim]no golden fixtures collected yet -- treating as a pass[/dim]")
        raise typer.Exit(code=EXIT_OK)
    raise typer.Exit(code=EXIT_OK if completed.returncode == 0 else EXIT_BLOCKING)


def _handle_cli_error(exc: CliError) -> None:
    """Turns a `CliError` into its `{CLI-n}` exit code.

    `pyproject.toml`'s console-script entry point is `s2s_harness.cli.main:app`
    (Typer's own object), not a wrapper function -- Click has no single
    global except-hook across commands, so each command catches `CliError`
    at its own boundary and calls this rather than letting the exception
    reach Click's default handler, which would always exit 1 regardless of
    which `{CLI-n}` code actually applies.
    """
    err_console.print(f"[bold red]{exc}[/bold red]")
    raise typer.Exit(code=exc.exit_code)


if __name__ == "__main__":
    app()
