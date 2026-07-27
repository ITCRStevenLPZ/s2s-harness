"""Exit-code contract. `{CLI-17}`..`{CLI-20}` (`docs/CLI_SPEC.md` Exit codes).

Every command funnels its failures through `CliError`, so `main.py` has one
place that turns an exception into an exit code, rather than each command
guessing a number.
"""

from __future__ import annotations

from typing import Literal

ExitCode = Literal[0, 1, 2, 3]

EXIT_OK: Literal[0] = 0  # {CLI-17} completed, no blocking errors
EXIT_BLOCKING: Literal[1] = 1  # {CLI-18} blocking errors present (or a warning under --strict)
EXIT_INVALID: Literal[2] = 2  # {CLI-19} invalid input / state validation failure
EXIT_PROVIDER: Literal[3] = 3  # {CLI-20} provider failure (STT or model)


class CliError(Exception):
    """Carries the exit code a command should terminate with.

    Raised deliberately by CLI code (never by a bare `except Exception`) so
    the mapping to `{CLI-17}`..`{CLI-20}` stays visible at the raise site.
    """

    def __init__(self, message: str, *, exit_code: ExitCode) -> None:
        super().__init__(message)
        self.exit_code: ExitCode = exit_code


class InvalidInputError(CliError):
    """{CLI-19} -- malformed rater input or a saved file that fails validation."""

    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=EXIT_INVALID)


class ProviderError(CliError):
    """{CLI-20} -- an STT or LLM provider failed and no side effect completed."""

    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=EXIT_PROVIDER)


class EngineUnavailableError(ProviderError):
    """The compiled graph (`s2s_harness.graph`, owned by the graph-architect
    role this wave) is not importable yet or raised during a run.

    Mapped to `{CLI-20}` (provider failure) rather than a fifth exit code:
    from the rater's chair, "the evaluation engine could not run" and "the
    speech or LLM provider could not run" are the same experience -- the
    command could not produce a verdict and nothing was submitted. See
    team_findings.md [T4] for why this reuses CLI-20 instead of inventing a
    new code CLI_SPEC does not define.
    """
