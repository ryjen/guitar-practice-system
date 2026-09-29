"""In-memory interactive score editing over existing deterministic application APIs."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping

from guitar_practice.application.ports import JsonDocumentStore
from guitar_practice.application.score_authoring import ScoreAuthoring
from guitar_practice.domain import score


class ScoreEditError(ValueError):
    """Interactive score editing cannot proceed safely."""


class ScoreEditConflictError(ScoreEditError):
    """The source score changed after the edit session started."""


class _MemoryDocuments:
    def __init__(self, values: Mapping[str, Mapping[str, Any]]) -> None:
        self.values = {
            key: copy.deepcopy(dict(value))
            for key, value in values.items()
        }

    def read(self, path: str) -> Mapping[str, Any]:
        if path not in self.values:
            raise ScoreEditError(f"missing in-memory document: {path}")
        return copy.deepcopy(self.values[path])

    def write(self, path: str, document: Mapping[str, Any]) -> None:
        value = copy.deepcopy(dict(document))
        score.validate(value)
        self.values[path] = value


@dataclass
class ScoreEditSession:
    """Canonical Score IR working copy with explicit conflict-checked save."""

    source_path: str
    source_documents: JsonDocumentStore

    def __post_init__(self) -> None:
        original = dict(self.source_documents.read(self.source_path))
        score.validate(original)
        self._original = copy.deepcopy(original)
        self._memory = _MemoryDocuments({"working": original})
        self._authoring = ScoreAuthoring(self._memory, inputs=self._memory)

    def snapshot(self) -> dict[str, Any]:
        value = dict(self._memory.read("working"))
        score.validate(value)
        return value

    def context(self) -> dict[str, Any]:
        value = self.snapshot()
        return {
            "id": value["id"],
            "title": value["metadata"]["title"],
            "bars": len(value["bars"]),
            "sections": [
                {
                    "id": item["id"],
                    "label": item["label"],
                    "start_bar": item["start_bar"],
                    "end_bar": item["end_bar"],
                }
                for item in value.get("sections", [])
            ],
            "parts": [
                {
                    "id": part["id"],
                    "name": part["name"],
                    "role": part["role"],
                    "notes": sum(
                        1 for event in part["events"] if event["kind"] == "note"
                    ),
                }
                for part in value["parts"]
            ],
            "valid": True,
        }

    def replace_form(self, spec: str) -> dict[str, Any]:
        return self._authoring.replace_form("working", spec, "working")

    def replace_chords(
        self,
        spec: str,
        *,
        section: str | None = None,
    ) -> dict[str, Any]:
        return self._authoring.replace_chords(
            "working",
            spec,
            "working",
            section=section,
        )

    def apply_structured(
        self,
        action: str,
        *,
        part_id: str,
        input_document: Mapping[str, Any],
    ) -> dict[str, Any]:
        self._memory.write("input", input_document)
        if action == "notes":
            return self._authoring.replace_notes(
                "working",
                part_id=part_id,
                input_path="input",
                output="working",
            )
        if action == "voicing":
            return self._authoring.apply_voicing(
                "working",
                part_id=part_id,
                input_path="input",
                output="working",
            )
        if action == "rhythm":
            return self._authoring.apply_rhythm(
                "working",
                part_id=part_id,
                input_path="input",
                output="working",
            )
        if action == "technique":
            return self._authoring.apply_technique(
                "working",
                part_id=part_id,
                input_path="input",
                output="working",
            )
        raise ScoreEditError(f"unsupported edit action: {action}")

    def validate(self) -> dict[str, Any]:
        value = self.snapshot()
        return {
            "id": value["id"],
            "schema": value["schema"],
            "version": value["version"],
            "valid": True,
        }

    def save(self) -> dict[str, Any]:
        working = self.snapshot()
        current = dict(self.source_documents.read(self.source_path))
        score.validate(current)
        if current != self._original:
            raise ScoreEditConflictError(
                "source score changed during edit session; refusing to overwrite"
            )
        self.source_documents.write(self.source_path, working)
        self._original = copy.deepcopy(working)
        return working
