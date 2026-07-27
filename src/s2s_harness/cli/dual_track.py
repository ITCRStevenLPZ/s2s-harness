"""Track B presentation types.

`EvaluationState` (`src/s2s_harness/models/state.py`, STATE-9..STATE-17) has
no `judge` / Track B fields as of this file: no teammate owns `models/`
this wave (see the Wave 3b team roster -- T1 owns `llm/client.py` and
`llm/providers/`, T2 owns the four `llm/` role modules, T3 owns `nodes/`
and `graph.py`, T4 (this package) owns `cli/`, T5 owns governance and
tests). That is a real spec gap, not an oversight to route around
silently: flagged in `team_findings.md` [T4] for the lead to assign.

Until `models/state.py` gains first-class Track B fields, these dataclasses
are the CLI-local stand-in. `render.py` and `runner.py` both depend on this
module rather than on ad-hoc dicts, so there is exactly one place to update
(and then delete, migrating callers to the real model fields) once that
gap closes. Nothing here is persisted as part of `EvaluationState` itself;
`--json` nests it alongside the state dump, see `runner.py`'s `RunResult`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from s2s_harness.models.state import Pick, Suggestion

Confidence = Literal["low", "medium", "high"]

SubmissionChoice = Literal["track_a", "track_b_override"]


@dataclass(frozen=True)
class TrackBResult:
    """The `judge` LLM role's output, shown beside Track A's verdict.

    Mirrors `Verdict` (`STATE-13`) in shape (`verdict`, `driver`) so the two
    tracks render as directly comparable panels, plus `reasoning` and
    `confidence`, which Track A has no equivalent of by design (Track A's
    equivalent of "reasoning" is its `trace`).
    """

    verdict: Pick | None
    driver: str
    reasoning: str
    confidence: Confidence
    suggestions: list[Suggestion] = field(default_factory=list)
    skipped_reason: str = ""

    @property
    def skipped(self) -> bool:
        return bool(self.skipped_reason)

    def to_dict(self) -> dict[str, object]:
        return {
            "verdict": self.verdict,
            "driver": self.driver,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "suggestions": [s.model_dump(mode="json") for s in self.suggestions],
            "skipped_reason": self.skipped_reason,
        }


@dataclass(frozen=True)
class Agreement:
    """Whether Track A and Track B landed on the same overall pick.

    Disagreement is the product, not an error state (`team_plan.md`
    "Disagreement is the product"). This type only records the fact; it is
    `render.py`'s job to present it as an invitation to think rather than a
    malfunction.
    """

    agrees: bool
    track_a: Pick | None
    track_b: Pick | None

    @classmethod
    def compute(cls, track_a: Pick | None, track_b: TrackBResult | None) -> Agreement:
        if track_b is None or track_b.skipped:
            return cls(agrees=True, track_a=track_a, track_b=None)
        return cls(agrees=track_a == track_b.verdict, track_a=track_a, track_b=track_b.verdict)

    def to_dict(self) -> dict[str, object]:
        return {"agrees": self.agrees, "track_a": self.track_a, "track_b": self.track_b}


@dataclass(frozen=True)
class Submission:
    """What the rater actually submitted.

    Default is always Track A (`docs/CLI_SPEC.md` predates Track B, but
    `team_plan.md` "The rater submits" is explicit: Track A's verdict is
    the default, overriding it with Track B's is one explicit keystroke,
    and it is recorded here, never auto-applied).
    """

    choice: SubmissionChoice
    verdict: Pick | None

    def to_dict(self) -> dict[str, object]:
        return {"choice": self.choice, "verdict": self.verdict}


def default_submission(track_a_verdict: Pick | None) -> Submission:
    return Submission(choice="track_a", verdict=track_a_verdict)


def override_submission(track_b: TrackBResult) -> Submission:
    return Submission(choice="track_b_override", verdict=track_b.verdict)
