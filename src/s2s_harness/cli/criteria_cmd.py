"""`s2s criteria [TOPIC]`, `{CLI-5}`.

"Prints from `criteria/`, not from memory... Zero tokens -- it is a file
read." (`docs/CLI_SPEC.md`). No LLM, no graph, no `EvaluationState` -- this
command only ever parses markdown headings.

Topic reconciliation note: the CLI_SPEC command table's one-line summary
says "(hierarchy, clusters, examples, thresholds)" while the prose body
lists "`s2s criteria hierarchy`, `s2s criteria clusters`, `s2s criteria
examples`, `s2s criteria audio`" -- "thresholds" vs "audio" naming drift
within the spec itself (flagged in `team_findings.md` [T4]). Both are
accepted as topics here rather than guessing which one is the typo:
`thresholds` maps to CRIT-4 ("Threshold breaches"), `audio` to CRIT-5
("Audio tolerance") -- they are two different sections, not aliases of
each other.
"""

from __future__ import annotations

import re
from pathlib import Path

from s2s_harness.cli.errors import InvalidInputError

_PROJECT_CRITERIA = Path("criteria/project-criteria.md")
_WORKED_EXAMPLES = Path("criteria/worked-examples.md")

_TOPIC_KEYWORDS: dict[str, str] = {
    "hierarchy": "Hierarchy",
    "clusters": "Error clusters",
    "thresholds": "Threshold breaches",
    "audio": "Audio tolerance",
}

_HEADING_RE = re.compile(r"^## (.+?)(?:\s*\{CRIT-[0-9.]+\})?\s*$", re.MULTILINE)


def _split_sections(text: str) -> dict[str, str]:
    headings = list(_HEADING_RE.finditer(text))
    sections: dict[str, str] = {}
    for i, match in enumerate(headings):
        start = match.start()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        sections[match.group(1).strip()] = text[start:end].rstrip() + "\n"
    return sections


def render_criteria(topic: str | None, *, repo_root: Path | None = None) -> str:
    root = repo_root or Path.cwd()
    project_path = root / _PROJECT_CRITERIA
    examples_path = root / _WORKED_EXAMPLES
    if not project_path.exists():
        raise InvalidInputError(f"{project_path}: criteria file not found")

    if topic is None:
        return project_path.read_text(encoding="utf-8")

    key = topic.strip().lower()
    if key == "examples":
        if not examples_path.exists():
            raise InvalidInputError(f"{examples_path}: worked examples file not found")
        return examples_path.read_text(encoding="utf-8")

    heading = _TOPIC_KEYWORDS.get(key)
    if heading is None:
        valid = ", ".join(sorted({*_TOPIC_KEYWORDS, "examples"}))
        raise InvalidInputError(f"unknown criteria topic {topic!r}; valid topics: {valid}")

    sections = _split_sections(project_path.read_text(encoding="utf-8"))
    if heading not in sections:
        raise InvalidInputError(f"{project_path}: expected a '## {heading}' section, none found")
    return sections[heading]
