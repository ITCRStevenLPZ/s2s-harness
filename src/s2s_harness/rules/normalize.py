"""Normalization: derive threshold_all / audio_penalized on a side observation.

Implements RULES_SPEC.md section 2, `normalize(side, context) -> side`,
{RULE-5} through {RULE-9}.

Zero LLM calls, zero I/O, zero network, zero clock, zero randomness.
Imports: stdlib, Pydantic (via `models.state`) and `rules.catalog` only,
per CLAUDE.md design rules 1 and 2, and `docs/ARCHITECTURE.md`'s layer
table (`rules/` may import `models/`, never the reverse).
"""

from __future__ import annotations

from s2s_harness.models.state import SideObservation, TaskContext

# RULES_SPEC section 1, "Threshold — utility" / "Threshold — audio":
# the two catalogue keys `normalize` itself is responsible for appending.
# Named here as constants (not re-typed inline at each call site) so the
# two derivation steps below read as "add THIS key", never a bare string
# literal, per CLAUDE.md's no-magic-literals rule for `rules/`.
_NOTABLE_NOISE_KEY = "notable_noise"  # RULES_SPEC section 1, threshold-audio row; {RULE-5}
_FALSE_PREMISE_KEY = "false_premise"  # RULES_SPEC section 1, threshold-utility row; {RULE-6}
_PREMISE_REDTEAM_KEY = "premise_redteam"  # RULES_SPEC section 1, threshold-utility row; {RULE-6}

# RULES_SPEC section 2, step 2: the two scenario types where an accepted
# false premise escalates to a threshold breach. {RULE-6}
_PREMISE_SCENARIO_TYPES = frozenset({"redteam", "premise"})


def normalize(side: SideObservation, context: TaskContext) -> SideObservation:
    """Derive `threshold_all` and `audio_penalized` for one side.

    RULES_SPEC section 2, in order (order matters, per the spec's own
    warning that the draft builder depends on it):

    1. {RULE-5} notable background noise adds `notable_noise` to the
       side's audio-threshold list.
    2. {RULE-6} an accepted false premise, in a redteam/premise scenario,
       adds `premise_redteam` to the utility-threshold list -- but only
       when `false_premise` was not already recorded directly, so the
       same failure is never double-counted under two keys.
    3. {RULE-7} `threshold_all = threshold_utility + threshold_audio`,
       utility first. This list is built with `+`, never `sorted()` or a
       set union, so the order is exactly "utility keys in their
       recorded order, then audio keys in their recorded order" and
       stays deterministic across runs (CLAUDE.md determinism rule).
    4. {RULE-8} `audio_penalized` is `len(threshold_audio) > 0`.

    {RULE-9}: `background_noise == "slight"` triggers none of the above.
    There is no branch for it anywhere in this function -- that absence
    *is* the project's audio tolerance (criteria/project-criteria.md
    "Audio tolerance"), not an oversight. Do not add one.
    """
    threshold_audio = list(side.threshold_audio)
    if side.background_noise == "notable" and _NOTABLE_NOISE_KEY not in threshold_audio:
        # {RULE-5}. Idempotency guard (`not in`) so calling `normalize`
        # twice on an already-normalized side never double-appends; the
        # spec does not require this, but nothing forbids it and it costs
        # nothing to keep `threshold_all` free of duplicate keys.
        threshold_audio.append(_NOTABLE_NOISE_KEY)

    threshold_utility = list(side.threshold_utility)
    if (
        context.scenario_type in _PREMISE_SCENARIO_TYPES
        and side.premise_handling == "accepted"
        and _FALSE_PREMISE_KEY not in threshold_utility
        and _PREMISE_REDTEAM_KEY not in threshold_utility
    ):
        # {RULE-6}. Same idempotency guard as above, plus the spec's own
        # de-duplication condition (`false_premise ∉ threshold_utility`).
        threshold_utility.append(_PREMISE_REDTEAM_KEY)

    # {RULE-7}: concatenation, utility first. Never `sorted()`, never a
    # set -- the draft builder (rules/draft.py) relies on this exact
    # ordering to decide which category to name first.
    threshold_all = threshold_utility + threshold_audio

    # {RULE-8}.
    audio_penalized = len(threshold_audio) > 0

    return side.with_derived(
        threshold_all=threshold_all,
        audio_penalized=audio_penalized,
        threshold_utility=threshold_utility,
        threshold_audio=threshold_audio,
    )
