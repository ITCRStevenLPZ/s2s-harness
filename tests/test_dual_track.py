"""Wave 3b (2026-07-27) coverage for the dual-track architecture: a Track B
disagreement case and a total-degradation case, per T5's Task 4 in
`.claude/team-runs/2026-07-27-wave3b-dual-track/team_plan.md`.

WHY THESE ARE NOT `tests/golden/*.yaml` FIXTURES. `tests/golden/_golden_lib.py`
wires a fixture straight through `normalize -> decide -> audit -> build_draft`
(`s2s_harness.rules.*` only) and asserts against `EvaluationState` +
`Verdict`/`Finding`/`draft` -- the Track A pipeline, exclusively. There is
no field anywhere to hold a Track B (`judge`) verdict: `JudgeVerdict` is
deliberately never written to `EvaluationState.verdict` (see
`src/s2s_harness/llm/judge.py`'s own docstring -- a `judge_verdict`-shaped
field is node/state design work), and `src/s2s_harness/models/` is guarded
off-limits for every teammate this wave (`team_plan.md`'s "Do not touch"
list), so no one on this team can add that field this wave regardless of
file ownership. Forcing a "Track B disagreement" fixture into the
`tests/golden/*.yaml` + `expect:` shape would silently misrepresent what
that suite tests -- exactly the anti-pattern `tests/golden/COVERAGE.md`'s
own audit log repeatedly calls out ("a matrix that silently drifts is worse
than no matrix"). These two tests instead call Track A (via
`tests/golden/_golden_lib.run_fixture`, reusing a real fixture rather than
inventing new state-construction code) and Track B's landed role functions
(`s2s_harness.llm.judge.judge`, `.interpret.interpret`, `.suggest.suggest`,
`.polish.polish`) side by side, directly. See `tests/golden/COVERAGE.md`'s
"Wave 3b dual-track coverage" section for the full reconciliation.

All four LLM roles are `async def role(state[, draft]) -> Outcome`, calling
the shared `s2s_harness.llm.client.complete()` facade and catching its one
exception type, `LlmDegraded`, propagating `exc.reason` verbatim into their
own `Outcome.skipped_reason` (each role module's own docstring: "never
remapped to a generic local reason"). `complete()` raises
`LlmDegraded("disabled", ...)` itself when no provider is configured
(`S2S_LLM_PROVIDER` unset) -- its own documented "legitimate
Track-A-only steady state," not a mock. Both tests below are Tier-1-safe:
no network, no real provider.

NOTE ON STABILITY (T5, for whoever next edits this file): this file's
target API inside `src/s2s_harness/llm/` changed three times while it was
being written in the same wave (bare `(state)` -> explicit `(state,
client, *, model)` -> back to bare `(state[, draft])`). The version below
matches the shape `uv run mypy src/s2s_harness/llm/` reports clean against
as of this commit. If these tests start failing on a signature mismatch,
re-read the relevant role module's docstring first -- it is usually
explicit about which shape is current and why.

Uses `s2s_harness.llm.reset_client_cache` (T2's public test-only hook,
`client.py`'s own docstring: "Test-only escape hatch... Production code
never calls this") to inject a stub client for the disagreement case and
to force the "no provider configured" path for the degradation case,
rather than reaching into `s2s_harness.llm.client`'s private module
globals directly.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from s2s_harness.llm import reset_client_cache
from s2s_harness.llm.client import LLMOutcome
from s2s_harness.llm.interpret import interpret
from s2s_harness.llm.judge import _DRIVER_LABELS, judge
from s2s_harness.llm.polish import polish
from s2s_harness.llm.suggest import suggest
from tests.golden._golden_lib import GOLDEN_DIR, build_initial_state, load_fixture, run_fixture

# ex1_houseplant: Track A's verdict is deterministic and well-known
# (overall=A, driver="Naturalness / Engagement", see the fixture's own
# `expect:` block) and its notes are already bilingual (b.notes is
# Spanish), so reusing it also carries the project's EN/ES coverage
# convention into this file without inventing new fixture text.
_FIXTURE_PATH = GOLDEN_DIR / "ex1_houseplant.yaml"

# `LlmDegraded("disabled", ...)` is what `s2s_harness.llm.client.complete()`
# raises when no client is configured (`reset_client_cache(None,
# resolved=False)` plus `S2S_LLM_PROVIDER` unset -> `_get_client()` returns
# `None`); every role now propagates `exc.reason` verbatim, so this is the
# one string all four `Outcome.skipped_reason`s converge on below.
_REASON_DISABLED = "disabled"


@dataclass
class _StubClient:
    """Duck-typed to `LLMClient`'s `.complete()`/`.provider_name` shape,
    injected via `reset_client_cache` -- no network, no cache, no SDK.
    `provider_name` must be a real `LLMProviderName` because `complete()`
    uses it to look up a default model string when the caller passes
    `model=None`.
    """

    response_text: str
    provider_name: str = "openrouter"

    def complete(self, **_kwargs: Any) -> LLMOutcome:
        return LLMOutcome(ok=True, text=self.response_text, skipped_reason="", cached=False)


def test_track_b_disagreement_is_surfaced_not_forced_to_agree() -> None:
    """`team_plan.md`: "Disagreement between tracks is the product, not a
    bug. Surface it." This proves the two tracks are computed
    independently and CAN differ for the same input -- `judge` does not
    read or depend on Track A's `state.verdict` (`judge.py`'s own
    docstring).
    """
    data, track_a_verdict, _findings, _draft = run_fixture(_FIXTURE_PATH)
    assert track_a_verdict.overall == "A"
    assert track_a_verdict.driver == "Naturalness / Engagement"

    state = build_initial_state(data)
    assert state.llm_enabled is True

    disagreeing_payload = {
        "overall": "B",
        "driver": "Utility",
        "confidence": 0.62,
        "reasoning": (
            "Clip B's organized rundown answers the question more completely; "
            "I weigh that over Clip A's warmer tone."
        ),
        "gated": False,
        "gated_side": None,
    }
    assert disagreeing_payload["driver"] in _DRIVER_LABELS

    stub_client = _StubClient(response_text=json.dumps(disagreeing_payload))
    reset_client_cache(stub_client, resolved=True)
    try:
        outcome = asyncio.run(judge(state))
    finally:
        # Do not leak the stub into whichever test runs next in this
        # process -- back to "re-resolve from env on next use."
        reset_client_cache(None, resolved=False)

    assert outcome.skipped_reason == ""
    assert outcome.value is not None
    assert outcome.value.overall == "B"
    assert outcome.value.overall != track_a_verdict.overall, (
        "the two tracks must be able to disagree -- if this ever equals "
        "track_a_verdict.overall by construction rather than by the "
        "stubbed payload, the test is no longer exercising disagreement"
    )


def test_all_llm_roles_degrade_and_track_a_still_completes(monkeypatch: Any) -> None:
    """CLAUDE.md design rule 3 (amended Wave 3b): "The deterministic draft
    (Track A) is always produced, whether or not any LLM role runs... it
    now applies to all four roles." This is the literal degradation case
    from `team_plan.md` Phase E: every LLM call fails (here: no provider
    configured, `complete()`'s own documented degrade path) and Track A
    still produces a complete result.
    """
    reset_client_cache(None, resolved=False)
    monkeypatch.delenv("S2S_LLM_PROVIDER", raising=False)

    data, track_a_verdict, findings, draft = run_fixture(_FIXTURE_PATH)
    assert track_a_verdict.overall == "A"
    assert draft.strip() != ""
    assert "【" not in draft  # no placeholder markers for this fully-specified fixture
    assert any(f.code == "OVERALL_COHERENT" for f in findings)

    state = build_initial_state(data)
    # `polish`'s own gate ({GRAPH-8}) skips with skipped_reason="no_verdict"
    # when `state.verdict is None` -- true here because `build_initial_state`
    # only sets context/a/b/picks, not the rules-engine's computed verdict
    # (`run_fixture` returns that separately; it does not write it back).
    # Set it explicitly so this test isolates the variable it is actually
    # about -- LLM provider absence -- not an unrelated upstream gate that
    # would fire regardless of Track B's availability.
    state = state.model_copy(update={"verdict": track_a_verdict})

    interpret_outcome = asyncio.run(interpret(state))
    assert interpret_outcome.value is None
    assert interpret_outcome.skipped_reason == _REASON_DISABLED

    suggest_outcome = asyncio.run(suggest(state))
    assert suggest_outcome.value is None
    assert suggest_outcome.skipped_reason == _REASON_DISABLED

    judge_outcome = asyncio.run(judge(state))
    assert judge_outcome.value is None
    assert judge_outcome.skipped_reason == _REASON_DISABLED

    polish_outcome = asyncio.run(polish(state, draft))
    assert polish_outcome.used_llm is False
    assert polish_outcome.skipped_reason == _REASON_DISABLED
    assert polish_outcome.text == draft, (
        "polish must fall back to the exact Track A draft, silently, per "
        "CLAUDE.md design rule 3 and the recovered HTML fallback contract "
        "(team_findings.md [T2]: 'silently discard the model output and "
        "re-render the deterministic draft')"
    )


def test_fixture_still_loads_the_way_this_file_assumes() -> None:
    """Guards this file's two tests above against `ex1_houseplant.yaml`
    changing shape out from under them -- a fast, specific failure here
    beats a confusing failure inside the tests that actually matter.
    """
    data = load_fixture(_FIXTURE_PATH)
    assert data["id"] == "ex1_houseplant"
    assert data["mode"] == "clips"
