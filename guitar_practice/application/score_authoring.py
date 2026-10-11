"""Application orchestration and text syntax for deterministic score authoring."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from guitar_practice.application.ports import JsonDocumentStore
from guitar_practice.domain import score, score_authoring, score_realization


class ScoreAuthoringInputError(ValueError):
    """Human-facing score authoring syntax is invalid or ambiguous."""


_STANDARD_GUITAR_TUNING = [
    {"string": 6, "pitch": {"step": "E", "alter": 0, "octave": 2}},
    {"string": 5, "pitch": {"step": "A", "alter": 0, "octave": 2}},
    {"string": 4, "pitch": {"step": "D", "alter": 0, "octave": 3}},
    {"string": 3, "pitch": {"step": "G", "alter": 0, "octave": 3}},
    {"string": 2, "pitch": {"step": "B", "alter": 0, "octave": 3}},
    {"string": 1, "pitch": {"step": "E", "alter": 0, "octave": 4}},
]


def normalize_part_input(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ScoreAuthoringInputError("part input must be an object")
    allowed = {"id", "name", "role", "instrument", "guitar", "events"}
    unknown = set(value) - allowed
    if unknown:
        raise ScoreAuthoringInputError(
            f"part input has unsupported fields: {sorted(unknown)}"
        )

    part = dict(value)
    events = part.get("events", [])
    if events != []:
        raise ScoreAuthoringInputError(
            "part input events must be empty; add notes through score notes"
        )
    part["events"] = []

    if "guitar" in part:
        guitar = part["guitar"]
        if not isinstance(guitar, dict) or set(guitar) != {"tuning"}:
            raise ScoreAuthoringInputError(
                "part input guitar must contain only tuning"
            )
        tuning = guitar["tuning"]
        if tuning == "standard":
            part["guitar"] = {
                "tuning": [
                    {
                        "string": item["string"],
                        "pitch": dict(item["pitch"]),
                    }
                    for item in _STANDARD_GUITAR_TUNING
                ]
            }
        elif isinstance(tuning, list):
            part["guitar"] = {"tuning": tuning}
        else:
            raise ScoreAuthoringInputError(
                "part input guitar.tuning must be 'standard' or a tuning list"
            )
    return part

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
    inputs: JsonDocumentStore | None = None

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


    def replace_notes(
        self,
        source: str,
        *,
        part_id: str,
        input_path: str,
        output: str,
    ) -> dict[str, Any]:
        if self.inputs is None:
            raise ScoreAuthoringInputError("score note authoring input store is not configured")
        input_document = self.inputs.read(input_path)
        if set(input_document) != {"notes"}:
            raise ScoreAuthoringInputError("note input document must contain only notes")
        notes = input_document.get("notes")
        if not isinstance(notes, list):
            raise ScoreAuthoringInputError("note input notes must be a list")

        document = dict(self.documents.read(source))
        result = score_authoring.replace_part_notes(
            document,
            part_id=part_id,
            notes=notes,
        )
        self.documents.write(output, result)
        return result


    def apply_voicing(
        self,
        source: str,
        *,
        part_id: str,
        input_path: str,
        output: str,
    ) -> dict[str, Any]:
        if self.inputs is None:
            raise ScoreAuthoringInputError("score voicing input store is not configured")
        input_document = self.inputs.read(input_path)
        if set(input_document) != {"positions"}:
            raise ScoreAuthoringInputError("voicing input document must contain only positions")
        positions = input_document.get("positions")
        if not isinstance(positions, list):
            raise ScoreAuthoringInputError("voicing input positions must be a list")

        document = dict(self.documents.read(source))
        result = score_authoring.apply_note_positions(
            document,
            part_id=part_id,
            positions=positions,
        )
        self.documents.write(output, result)
        return result


    def apply_rhythm(
        self,
        source: str,
        *,
        part_id: str,
        input_path: str,
        output: str,
    ) -> dict[str, Any]:
        if self.inputs is None:
            raise ScoreAuthoringInputError("score rhythm input store is not configured")
        input_document = self.inputs.read(input_path)
        if set(input_document) != {"rhythm"}:
            raise ScoreAuthoringInputError("rhythm input document must contain only rhythm")
        patches = input_document.get("rhythm")
        if not isinstance(patches, list):
            raise ScoreAuthoringInputError("rhythm input rhythm must be a list")

        document = dict(self.documents.read(source))
        result = score_authoring.apply_note_rhythm(
            document,
            part_id=part_id,
            patches=patches,
        )
        self.documents.write(output, result)
        return result

    def apply_technique(
        self,
        source: str,
        *,
        part_id: str,
        input_path: str,
        output: str,
    ) -> dict[str, Any]:
        if self.inputs is None:
            raise ScoreAuthoringInputError("score technique input store is not configured")
        input_document = self.inputs.read(input_path)
        if set(input_document) != {"technique"}:
            raise ScoreAuthoringInputError(
                "technique input document must contain only technique"
            )
        patches = input_document.get("technique")
        if not isinstance(patches, list):
            raise ScoreAuthoringInputError("technique input technique must be a list")

        document = dict(self.documents.read(source))
        result = score_authoring.apply_note_technique(
            document,
            part_id=part_id,
            patches=patches,
        )
        self.documents.write(output, result)
        return result


    def add_part(
        self,
        source: str,
        *,
        input_path: str,
        output: str,
    ) -> dict[str, Any]:
        if self.inputs is None:
            raise ScoreAuthoringInputError("score part input store is not configured")
        input_document = self.inputs.read(input_path)
        if set(input_document) != {"part"}:
            raise ScoreAuthoringInputError(
                "part input document must contain only part"
            )
        part = normalize_part_input(input_document["part"])
        document = dict(self.documents.read(source))
        result = score_authoring.add_part(document, part=part)
        self.documents.write(output, result)
        return result
