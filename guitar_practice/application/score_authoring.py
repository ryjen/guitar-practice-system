"""Application orchestration and text syntax for deterministic score authoring."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from guitar_practice.application.ports import JsonDocumentStore
from guitar_practice.domain import score, score_authoring, score_realization


class ScoreAuthoringInputError(ValueError):
    """Human-facing score authoring syntax is invalid or ambiguous."""


def _slug(value: str) -> str:
    safe = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return safe[:48] or "section"


def _label(value: str) -> str:
    words = re.sub(r"[-_]+", " ", value).strip()
    return words.title() or "Section"


def parse_form_spec(spec: str) -> tuple[score_authoring.FormSection, ...]:
    if not isinstance(spec, str) or not spec.strip():
        raise ScoreAuthoringInputError("form specification must be non-empty")

    counts: dict[str, int] = {}
    result: list[score_authoring.FormSection] = []
    for token in spec.split():
        if ":" not in token:
            raise ScoreAuthoringInputError(
                "form sections must use <name>:<bars>, for example verse:12"
            )
        raw_name, raw_bars = token.rsplit(":", 1)
        if not raw_name.strip():
            raise ScoreAuthoringInputError("form section name must be non-empty")
        try:
            bars = int(raw_bars)
        except ValueError as exc:
            raise ScoreAuthoringInputError("form section bar count must be an integer") from exc
        if bars <= 0:
            raise ScoreAuthoringInputError("form section bar count must be positive")

        base = _slug(raw_name)
        occurrence = counts.get(base, 0) + 1
        counts[base] = occurrence
        section_id = base if occurrence == 1 else f"{base}-{occurrence}"
        label = _label(raw_name)
        if occurrence > 1:
            label = f"{label} {occurrence}"
        result.append(score_authoring.FormSection(section_id, label, bars))
    return tuple(result)


def parse_chord_grid(spec: str) -> tuple[tuple[str, ...], ...]:
    if not isinstance(spec, str) or not spec.strip():
        raise ScoreAuthoringInputError("chord grid must be non-empty")
    raw = spec.strip()
    if raw.startswith("|"):
        raw = raw[1:]
    if raw.endswith("|"):
        raw = raw[:-1]
    cells = raw.split("|")
    if not cells:
        raise ScoreAuthoringInputError("chord grid must contain at least one bar")
    return tuple(tuple(cell.strip().split()) for cell in cells)


@dataclass(frozen=True)
class ScoreAuthoring:
    documents: JsonDocumentStore

    def replace_form(self, source: str, spec: str, output: str) -> dict[str, Any]:
        document = dict(self.documents.read(source))
        result = score_authoring.replace_form(document, parse_form_spec(spec))
        self.documents.write(output, result)
        return result

    def replace_chords(
        self,
        source: str,
        spec: str,
        output: str,
        *,
        section: str | None = None,
    ) -> dict[str, Any]:
        document = dict(self.documents.read(source))
        score.validate(document)
        if section is None:
            start_bar, end_bar = 1, len(document["bars"])
        else:
            resolved = score_realization.resolve_section(document, section)
            start_bar = int(resolved["start_bar"])
            end_bar = int(resolved["end_bar"])
        result = score_authoring.replace_harmony(
            document,
            start_bar=start_bar,
            end_bar=end_bar,
            bars=parse_chord_grid(spec),
        )
        self.documents.write(output, result)
        return result
