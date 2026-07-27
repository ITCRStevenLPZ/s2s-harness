"""LLM role: `polish` -- deterministic draft + observations -> one
polished paragraph, falling back to the draft silently on any failure.

Dual-track architecture (CLAUDE.md design rule 2, amended Wave 3b):
`polish` is one of four sanctioned Track B call sites, and remains "the
only one of the four that touches the draft's *text*" (CLAUDE.md,
amended rule 2). It never adds a fact, never changes Track A's verdict,
and never introduces an observation absent from the rater's notes
(CLAUDE.md design rule 4, amended -- unchanged in substance for this
role, which is where the rule originated).

Recovered prompt contract (`team_findings.md` "[T2] Prompt contract
re-verified against the HTML source directly"), read in full from
`web/conversation.html:1115-1266` and `web/clips.html:730-834` before
Wave 3d deletes them: hierarchy with threshold gating, audio tolerance,
error-cluster enumeration, scenario inversion, a numbered five-part
justification structure, sentence-count bounds (5-9 conversation, 4-8
clips), English/first-person/plain-prose/no-bullets/no-headings, "use
ONLY the observations supplied", the exact `【...】` placeholder form,
"Return only the paragraph, nothing else", and a silent fallback to the
deterministic draft on exception OR an empty/whitespace response.

Reconciliation with `docs/GRAPH_SPEC.md` `{GRAPH-8}`'s "system prompt
from `criteria/`" instruction: the system prompt below is built from
`criteria/project-criteria.md` clause text (CRIT-1, CRIT-2, CRIT-4,
CRIT-5, CRIT-6, CRIT-7, CRIT-9) plus `rules/catalog.py` display strings,
not a transliteration of the JS `RULES_DIGEST`/`RULES` constants. Every
constraint those JS strings state that criteria is silent on -- sentence
counts, "no bullets, no headings", "Return only the paragraph", the
bracket form -- is a prose-generation mechanic, not a project rule, and
is preserved verbatim below as an engineering constant, cited to the
recovered HTML rather than to a `CRIT-n`.

`{GRAPH-8}` skip conditions (`llm_enabled=False`, any `error`-severity
finding, `verdict.overall is None`) are implemented here as the module's
own gate, since they are cheap pure checks on `EvaluationState` this
module already receives in full -- the node wrapper (`nodes/polish.py`,
T3's file) is a thin caller, not a second place those checks are
re-implemented. Cache-hit handling (`sha256(draft + mode +
PROMPT_VERSION)`) is `llm.client.complete`'s responsibility (T1); a cache
hit is a successful, fast completion here, not a skip -- see
`team_findings.md` for the reconciliation note flagged to T3/T5 on
`{GRAPH-8}`'s literal wording listing a cache hit alongside the three
genuine skip conditions.

Wired against `s2s_harness.llm.client.complete()`, the async facade T1
built for the four LLM roles -- not the lower-level `LLMClient`. No
`client`/`model` parameter; `complete()` resolves the process-wide
provider and model from environment, and already strips the response and
raises `LlmDegraded("empty_response", ...)` itself on a blank one, so
this module does not repeat that check -- it only adds the
placeholder-preservation check, which is specific to this role.
`LlmDegraded.reason` (T1's canonical `LLMSkipReason`) is propagated
verbatim on provider failure.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from s2s_harness.llm.client import LlmDegraded, complete
from s2s_harness.models.state import EvaluationState, Mode
from s2s_harness.rules import catalog

PROMPT_VERSION = "1.0.0"

# "disabled", "blocking_errors" and "no_verdict" are this module's own
# pre-call gate reasons ({GRAPH-8}) -- they never reach `complete()`, so
# they are not part of T1's `LLMSkipReason` vocabulary. On provider
# failure, `exc.reason` (T1's canonical vocabulary) is used directly
# instead of a local constant. "placeholder_dropped" is this role's own
# post-hoc business check, same reasoning.
REASON_DISABLED = "disabled"
REASON_BLOCKING_ERRORS = "blocking_errors"
REASON_NO_VERDICT = "no_verdict"
REASON_PLACEHOLDER_DROPPED = "placeholder_dropped"

# {RULE-24}'s exact bracket pair, matching rules/draft.py's _GAP_OPEN /
# _GAP_CLOSE. Not imported (private to that module) -- reproduced here
# only to *detect* the pattern in already-built draft text, never to
# construct a new placeholder (this module never invents one; it only
# ever passes through gaps the deterministic draft already contains).
_GAP_PATTERN = re.compile("【[^】]*】")

# Recovered from web/conversation.html RULES_DIGEST / web/clips.html
# RULES (see module docstring) -- prose-generation mechanics, not a
# criteria clause, hence not a CRIT-n citation.
_SENTENCE_BOUNDS: dict[Mode, str] = {
    "conversation": "5 to 9 sentences",
    "clips": "4 to 8 sentences",
}


@dataclass(frozen=True)
class PolishOutcome:
    """`text` is always populated -- either the polished paragraph or the
    original `draft`, per CLAUDE.md design rule 3 ("The deterministic
    draft is always produced... The model is an enhancement, never a
    dependency"). `used_llm` distinguishes the two cases; `skipped_reason`
    is non-empty exactly when `used_llm` is `False` and a gate or
    degradation caused the fallback -- an empty `skipped_reason` with
    `used_llm=False` never occurs.
    """

    text: str
    used_llm: bool
    skipped_reason: str = ""


# ---------------------------------------------------------------------------
# Gates -- {GRAPH-8}
# ---------------------------------------------------------------------------


def _gate_reason(state: EvaluationState) -> str | None:
    if not state.llm_enabled:
        return REASON_DISABLED
    if any(f.severity == "error" for f in state.findings):
        return REASON_BLOCKING_ERRORS
    if state.verdict is None or state.verdict.overall is None:
        return REASON_NO_VERDICT
    return None


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


def _artifact_noun(mode: Mode) -> str:
    return "conversation" if mode == "conversation" else "clip"


def _catalogue_glossary(mode: Mode) -> str:
    profile = catalog.profile_for(mode)
    cluster_lines = [
        f"  {catalog.ERROR_CLUSTERS[key].display(mode)}"
        for key in profile.error_clusters
        if catalog.ERROR_CLUSTERS[key].scored_as is None
    ]
    return "\n".join(cluster_lines)


def _build_system_prompt(mode: Mode) -> str:
    noun = _artifact_noun(mode)
    sentence_bounds = _SENTENCE_BOUNDS[mode]
    return (
        "You are rewriting an already-complete deterministic justification "
        "draft into better prose for the Live S2S Arena / Stereo "
        "Headphone Check project. You may not add a fact, change the "
        "preference, or introduce an observation absent from the draft "
        "and the structured notes below -- you are improving how it "
        "reads, not what it claims.\n\n"
        f"PROJECT NORTH STAR (CRIT-1): a spontaneous, natural, "
        f"aesthetically pleasing {noun}, like talking to a friend, not "
        "querying an assistant.\n\n"
        "HIERARCHY (CRIT-2): Naturalness/Engagement/Aesthetics > Utility "
        "> Audio Quality. Utility and Audio Quality must clear a basic "
        "threshold -- no misinformation, no hallucination, no jarring "
        "audio errors (CRIT-4). A side that breaches that threshold "
        "while the other is clean should not be preferred unless the "
        "draft explicitly argues, with evidence, that the breach is "
        "minor and naturalness still wins.\n\n"
        "AUDIO TOLERANCE (CRIT-5): slight room tone or faint \"air\" is "
        "NOT a penalty; clicks, pops, cutoffs, distortion and dropouts "
        "ARE. State explicitly whether audio was penalized.\n\n"
        "ERROR CLUSTERS to name explicitly when the draft or notes "
        f"mention them (CRIT-6):\n{_catalogue_glossary(mode)}\n\n"
        "SCENARIO AWARENESS (CRIT-7): in hallucination-fishing / "
        "redteam / false-premise scenarios, a side that rejects or "
        "corrects the false claim is SUCCEEDING, not failing.\n\n"
        "JUSTIFICATION STRUCTURE, required (CRIT-9): 1) a clear overall "
        "preference; 2) which level of the hierarchy drove the decision "
        "and why; 3) specific observable evidence from BOTH sides; 4) an "
        "explicit statement of threshold issues observed or not "
        "observed, including whether audio was penalized; 5) explicit "
        "naming of any error clusters, with the trade-off explained if "
        "the preferred side carries one. Written in English, first "
        f"person, {sentence_bounds}, plain prose, no bullet points, no "
        "headings.\n\n"
        "HARD CONSTRAINTS:\n"
        "- Use ONLY the observations supplied below -- never invent a "
        "detail, a turn number, a quote or a behavior that is not in the "
        "draft or the notes.\n"
        "- Where the draft already contains a bracketed placeholder in "
        "the exact form 【like this】, preserve it VERBATIM, "
        "character for character, in your rewrite -- never fill it in, "
        "reword it, or drop it.\n"
        "- Keep the rater's voice: first person, plain, specific, no "
        "marketing language.\n"
        "- Return only the paragraph, nothing else."
    )


def _build_user_prompt(state: EvaluationState, draft: str) -> str:
    mode = state.context.mode

    def block(side: str) -> str:
        obs = state.a if side == "A" else state.b
        return (
            f"SIDE {side}\n"
            f"  Notes: {obs.notes or '(none provided)'}\n"
            f"  Strongest moment: {obs.best or '(not specified)'}\n"
            f"  Weakest moment: {obs.worst or '(not specified)'}\n"
            f"  Error clusters flagged: {obs.error_clusters or 'none'}\n"
            f"  Utility-threshold flags: {obs.threshold_utility or 'none'}\n"
            f"  Audio-threshold flags: {obs.threshold_audio or 'none'}\n"
            f"  Background noise: {obs.background_noise}\n"
            f"  Premise handling: {obs.premise_handling}\n"
        )

    task_line = (
        f"Scenario: {state.context.scenario or '(not provided)'}"
        if mode == "conversation"
        else f"Prompt: {state.context.prompt or '(not provided)'}"
    )
    verdict = state.verdict
    verdict_line = (
        f"RULE-ENGINE OUTCOME -- overall {verdict.overall}, driven by {verdict.driver}."
        if verdict is not None
        else "RULE-ENGINE OUTCOME -- undetermined."
    )
    return (
        f"Mode: {mode}\n"
        f"Scenario type: {state.context.scenario_type}\n"
        f"{task_line}\n\n"
        f"{block('A')}\n{block('B')}\n"
        f"{verdict_line}\n\n"
        "RULE-BASED DRAFT (use as the skeleton; improve the prose, do "
        f"not add facts):\n{draft}"
    )


# ---------------------------------------------------------------------------
# Placeholder preservation -- CLAUDE.md design rule 4
# ---------------------------------------------------------------------------


def _gaps_preserved(draft: str, polished: str) -> bool:
    """Every `【...】` span in `draft` must appear verbatim in `polished`.
    Belt-and-suspenders on top of the prompt instruction -- Tier 2's real
    -model assertion (CLAUDE.md rule 2: "the Tier 2 real-model assertion")
    checks this against a live response; this function is the same check
    made a hard runtime gate so a prompt regression degrades to the draft
    instead of shipping a justification that silently dropped a required
    rater action.
    """
    for gap_span in _GAP_PATTERN.findall(draft):
        if gap_span not in polished:
            return False
    return True


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def polish(state: EvaluationState, draft: str) -> PolishOutcome:
    """`polish` role. `draft` is passed explicitly (rather than read from
    `state.draft`) so a caller can polish a freshly-built draft before it
    is written back into state, matching `docs/GRAPH_SPEC.md`'s node
    order (`draft` writes `state.draft`, then `polish` reads it) without
    this module reaching into `state.draft` and risking a stale value if
    a caller ever calls this before that write lands. No
    `client`/`model` parameter -- `complete()` resolves the process-wide
    provider and model from environment itself.

    Degrades to `PolishOutcome(text=draft, used_llm=False,
    skipped_reason=...)` on any gate failure, provider failure, an empty
    response, or a response that drops a required `【placeholder】` --
    silently, per CLAUDE.md design rule 3 and the recovered HTML fallback
    contract. Never raises.
    """
    gate_reason = _gate_reason(state)
    if gate_reason is not None:
        return PolishOutcome(text=draft, used_llm=False, skipped_reason=gate_reason)

    mode = state.context.mode
    system = _build_system_prompt(mode)
    user = _build_user_prompt(state, draft)

    try:
        response = await complete(
            role="polish",
            system=system,
            user=user,
            prompt_version=PROMPT_VERSION,
        )
    except LlmDegraded as exc:
        return PolishOutcome(text=draft, used_llm=False, skipped_reason=exc.reason)

    if not _gaps_preserved(draft, response.text):
        return PolishOutcome(
            text=draft, used_llm=False, skipped_reason=REASON_PLACEHOLDER_DROPPED
        )

    return PolishOutcome(text=response.text, used_llm=True)
