"""Golden-suite test runner.

Loads every `tests/golden/*.yaml` fixture, runs it through the real
deterministic engine (`normalize` -> `decide` -> `audit` -> `build_draft`),
and asserts the output against each fixture's `expect` block, per the
schema in `docs/EVAL_SPEC.md`.

THE ANTI-DRIFT RULE: every value in an `expect:` block is authored from
`criteria/worked-examples.md` or a `{RULE-n}`/`{EVAL-n}` in the specs --
never from running the engine and pasting its output. This file must never
be edited to make an expectation match whatever the engine currently
produces. A mismatch is a conversation with the engine's owner (T3
`normalize`/`decide`, T4 `audit`, T5 `draft`/`scanner`) and possibly a spec
bug -- see `.claude/team-runs/2026-07-27-phase3-engine/team_plan.md`.

The engine is developed in parallel by other teammates. Fixtures failing,
or failing to even import, while that work is incomplete is expected and
correct per `docs/BUILD_PLAN.md` Phase 3 ("Build the fixtures first").
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.golden._golden_lib import build_initial_state, fixture_paths, load_fixture, run_pipeline

FIXTURE_PATHS = fixture_paths()


def _fixture_id(path: Path) -> str:
    return path.stem


@pytest.mark.parametrize("path", FIXTURE_PATHS, ids=_fixture_id)
def test_golden_fixture(path: Path) -> None:
    data = load_fixture(path)
    fixture_id = data.get("id", path.stem)
    state = build_initial_state(data)
    verdict, findings, draft_text = run_pipeline(state)

    expect = data.get("expect") or {}
    _check_verdict(fixture_id, verdict, expect.get("verdict") or {})
    _check_findings(fixture_id, findings, expect)
    _check_draft(fixture_id, draft_text, expect)
    _custom_checks(fixture_id, findings)


def _check_verdict(fixture_id: str, verdict, expected: dict) -> None:
    if "overall" in expected:
        assert verdict.overall == expected["overall"], (
            f"{fixture_id}: verdict.overall = {verdict.overall!r}, expected {expected['overall']!r}"
        )
    if "driver" in expected:
        assert verdict.driver == expected["driver"], (
            f"{fixture_id}: verdict.driver = {verdict.driver!r}, expected {expected['driver']!r}"
        )
    if "gated" in expected:
        assert verdict.gated == expected["gated"], (
            f"{fixture_id}: verdict.gated = {verdict.gated!r}, expected {expected['gated']!r}"
        )
    if "gated_side" in expected:
        assert verdict.gated_side == expected["gated_side"], (
            f"{fixture_id}: verdict.gated_side = {verdict.gated_side!r}, "
            f"expected {expected['gated_side']!r}"
        )


def _check_findings(fixture_id: str, findings, expect: dict) -> None:
    codes = [f.code for f in findings]
    for code in expect.get("findings_include", []):
        assert code in codes, f"{fixture_id}: expected finding {code!r} missing; got {codes}"
    for code in expect.get("findings_exclude", []):
        assert code not in codes, f"{fixture_id}: unexpected finding {code!r} present; got {codes}"


def _check_draft(fixture_id: str, draft_text: str, expect: dict) -> None:
    for substring in expect.get("draft_contains", []):
        assert substring in draft_text, (
            f"{fixture_id}: draft missing {substring!r}\n--- draft ---\n{draft_text}"
        )
    for substring in expect.get("draft_excludes", []):
        assert substring not in draft_text, (
            f"{fixture_id}: draft unexpectedly contains {substring!r}\n--- draft ---\n{draft_text}"
        )


# Findings/codes in §4.4 Audio, §4.5 Utility and §4.6 Overall coherence --
# the scope RULES_SPEC section 7's {RULE-43} reconciliation note narrows the
# "zero error findings" invariant to. Used only by the `empty_state` check
# below; never asserted against directly by a fixture's own expect block,
# since RULES_SPEC.md is the sole source of this list, not this test file.
_FLAG_AND_PICK_DERIVED_ERROR_CODES = frozenset(
    {
        "AUDIO_BOTH_GOOD_ILLEGAL",
        "AUDIO_PICK_CONTRADICTS",
        "UTILITY_PICK_CONTRADICTS",
        "OVERALL_PREFERS_GATED",
        "DIMENSIONS_CONTRADICT",
        "SUCCESS_FAIL_PREFERRED",
    }
)


def _custom_checks(fixture_id: str, findings) -> None:
    """Assertions the fixed `expect:` schema (id/mode/context/a/b/picks/
    expect{verdict, findings_include, findings_exclude, draft_contains,
    draft_excludes}) cannot express on its own -- a *shape* of the output
    (an exact count, a message substring, a scoped severity check) rather
    than a single code or draft substring. Each one is traced inline to the
    RULE-n/EVAL-n it enforces; nothing here is a fixture-schema extension,
    it is extra Python-level verification alongside the generic checks.
    """
    if fixture_id == "turns_short_and_mismatched":
        # EVAL-10: one error carrying both facts (short AND mismatched),
        # not two separate findings. RULE-16's TURNS_MISMATCH condition
        # ("both >= 4") cannot co-fire with TURNS_BELOW_MIN by construction,
        # but this locks in the exact count and checks the appended
        # mismatch sentence actually landed in the one finding's message.
        below_min = [f for f in findings if f.code == "TURNS_BELOW_MIN"]
        assert len(below_min) == 1, (
            f"{fixture_id}: expected exactly one TURNS_BELOW_MIN finding, got {len(below_min)}"
        )
        assert "differ" in below_min[0].message.lower(), (
            f"{fixture_id}: TURNS_BELOW_MIN message must also carry the mismatch fact per RULE-16"
        )
        assert not any(f.code == "TURNS_MISMATCH" for f in findings), (
            f"{fixture_id}: TURNS_MISMATCH must not co-fire with TURNS_BELOW_MIN"
        )

    if fixture_id == "empty_state":
        # EVAL-12 / RULE-43 (as narrowed by the Wave 2 reconciliation note
        # in RULES_SPEC.md section 7): a state with no flags and no picks
        # produces zero ERROR findings among the flag/pick-derived checks
        # specifically. NOTES_MISSING (section 4.2, unconditional) is
        # expected to fire and is asserted separately via findings_include
        # in the fixture itself.
        fired_scoped_errors = {
            f.code
            for f in findings
            if f.severity == "error" and f.code in _FLAG_AND_PICK_DERIVED_ERROR_CODES
        }
        assert not fired_scoped_errors, (
            f"{fixture_id}: RULE-43 violation, flag/pick-derived error(s) fired on "
            f"empty flags/picks: {sorted(fired_scoped_errors)}"
        )
