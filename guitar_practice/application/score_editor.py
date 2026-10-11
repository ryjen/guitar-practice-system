"""In-memory interactive score editing over existing deterministic application APIs."""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass
from typing import Any, Mapping

from guitar_practice.application.ports import (
    BinaryArtifactStore,
    ExportedScore,
    JsonDocumentStore,
    MidiPlayer,
    ScoreExporter,
)
from guitar_practice.application.score_authoring import ScoreAuthoring
from guitar_practice.application.score_export import ExportScore
from guitar_practice.application.score_playback import PlayScoreMidi, RenderScoreMidi
from guitar_practice.domain import score


class ScoreEditError(ValueError):
    """Interactive score editing cannot proceed safely."""


class ScoreEditConflictError(ScoreEditError):
    """The source score changed after the edit session started."""


_INPUT_KEY = "\\0score-edit-input"


@dataclass(frozen=True)
class EditProposal:
    """Transient deterministic/inferred proposal presented to the editor."""

    action: str
    value: Any
    confidence: float | None = None
    alternatives: tuple[Any, ...] = ()
    source: str = "deterministic"

    def __post_init__(self) -> None:
        if not isinstance(self.action, str) or not self.action.strip():
            raise ScoreEditError("proposal action must be a non-empty string")
        if not isinstance(self.source, str) or not self.source.strip():
            raise ScoreEditError("proposal source must be a non-empty string")
        if self.confidence is not None:
            if (
                isinstance(self.confidence, bool)
                or not isinstance(self.confidence, (int, float))
                or not math.isfinite(float(self.confidence))
                or not 0.0 <= float(self.confidence) <= 1.0
            ):
                raise ScoreEditError("proposal confidence must be in [0, 1]")

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "action": self.action,
            "value": copy.deepcopy(self.value),
            "alternatives": copy.deepcopy(list(self.alternatives)),
            "source": self.source,
        }
        if self.confidence is not None:
            payload["confidence"] = float(self.confidence)
        return payload


class _MemoryDocuments:
    def __init__(
        self,
        values: Mapping[str, Mapping[str, Any]],
        *,
        score_paths: set[str],
    ) -> None:
        self.values = {
            key: copy.deepcopy(dict(value))
            for key, value in values.items()
        }
        self.score_paths = frozenset(score_paths)

    def read(self, path: str) -> Mapping[str, Any]:
        if path not in self.values:
            raise ScoreEditError(f"missing in-memory document: {path}")
        return copy.deepcopy(self.values[path])

    def write(self, path: str, document: Mapping[str, Any]) -> None:
        value = copy.deepcopy(dict(document))
        if path in self.score_paths:
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
        self._memory = _MemoryDocuments(
            {self.source_path: original},
            score_paths={self.source_path},
        )
        self._authoring = ScoreAuthoring(self._memory, inputs=self._memory)

    def snapshot(self) -> dict[str, Any]:
        value = dict(self._memory.read(self.source_path))
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
        return self._authoring.replace_form(
            self.source_path,
            spec,
            self.source_path,
        )

    def replace_chords(
        self,
        spec: str,
        *,
        section: str | None = None,
    ) -> dict[str, Any]:
        return self._authoring.replace_chords(
            self.source_path,
            spec,
            self.source_path,
            section=section,
        )

    def add_part(self, input_document: Mapping[str, Any]) -> dict[str, Any]:
        self._memory.write(_INPUT_KEY, input_document)
        return self._authoring.add_part(
            self.source_path,
            input_path=_INPUT_KEY,
            output=self.source_path,
        )

    def apply_structured(
        self,
        action: str,
        *,
        part_id: str,
        input_document: Mapping[str, Any],
    ) -> dict[str, Any]:
        self._memory.write(_INPUT_KEY, input_document)
        if action == "notes":
            return self._authoring.replace_notes(
                self.source_path,
                part_id=part_id,
                input_path=_INPUT_KEY,
                output=self.source_path,
            )
        if action == "voicing":
            return self._authoring.apply_voicing(
                self.source_path,
                part_id=part_id,
                input_path=_INPUT_KEY,
                output=self.source_path,
            )
        if action == "rhythm":
            return self._authoring.apply_rhythm(
                self.source_path,
                part_id=part_id,
                input_path=_INPUT_KEY,
                output=self.source_path,
            )
        if action == "technique":
            return self._authoring.apply_technique(
                self.source_path,
                part_id=part_id,
                input_path=_INPUT_KEY,
                output=self.source_path,
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

    def export_musicxml(
        self,
        *,
        artifacts: BinaryArtifactStore,
        exporter: ScoreExporter,
        output: str,
    ) -> ExportedScore:
        return ExportScore(
            documents=self._memory,
            artifacts=artifacts,
            exporter=exporter,
        ).render_to(self.source_path, output)

    def play(
        self,
        *,
        artifacts: BinaryArtifactStore,
        metadata: JsonDocumentStore,
        player: MidiPlayer,
        output: str | None = None,
        bar_range: tuple[int, int] | None = None,
        section_name: str | None = None,
    ) -> Mapping[str, Any]:
        renderer = RenderScoreMidi(
            documents=self._memory,
            artifacts=artifacts,
            metadata=metadata,
        )
        return PlayScoreMidi(
            renderer=renderer,
            artifacts=artifacts,
            metadata=metadata,
            player=player,
        ).execute(
            self.source_path,
            output,
            bar_range=bar_range,
            section_name=section_name,
        )

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
