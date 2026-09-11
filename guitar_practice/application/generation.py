"""Application orchestration for deterministic generated practice artifacts."""

from __future__ import annotations

import posixpath
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

from guitar_practice.application.ports import (
    BinaryArtifactStore,
    DocumentLocator,
    JsonDocumentStore,
)
from guitar_practice.domain import backing, midi, midi_exercises, practice_progression

DEFAULT_GROOVE_CATALOG = "catalogs/grooves/catalog.json"
DEFAULT_PROGRESSION_CATALOG = "catalogs/progressions/catalog.json"
DEFAULT_EXERCISE_MANIFEST = "midi/exercises.json"
DEFAULT_EXERCISE_OUTPUT_DIR = "generated/midi"


def manifest_output_path(manifest: dict[str, Any]) -> str:
    outputs = manifest.get("outputs")
    if not isinstance(outputs, dict) or not isinstance(outputs.get("midi"), str):
        raise midi.ManifestError("manifest outputs.midi must be a path string")

    relative = PurePosixPath(outputs["midi"])
    if relative.is_absolute() or ".." in relative.parts:
        raise midi.ManifestError("outputs.midi must remain inside the repository")
    if relative.suffix.lower() != ".mid":
        raise midi.ManifestError("outputs.midi must end in .mid")
    if relative.parts[:2] != ("generated", "backing-tracks"):
        raise midi.ManifestError("outputs.midi must be under generated/backing-tracks")
    if relative.name != f"{manifest.get('id')}.mid":
        raise midi.ManifestError("outputs.midi filename must match manifest id")
    return relative.as_posix()


@dataclass(frozen=True)
class GenerateBackingCatalog:
    documents: JsonDocumentStore
    locator: DocumentLocator
    artifacts: BinaryArtifactStore
    groove_catalog_path: str = DEFAULT_GROOVE_CATALOG

    def execute(self) -> list[dict[str, Any]]:
        manifest_paths = tuple(self.locator.glob("backing-tracks/*/manifest.json"))
        if not manifest_paths:
            raise midi.ManifestError("no backing-track manifests found")
        groove_catalog = dict(self.documents.read(self.groove_catalog_path))

        results: list[dict[str, Any]] = []
        for manifest_path in manifest_paths:
            manifest = dict(self.documents.read(manifest_path))
            output = manifest_output_path(manifest)
            data = backing.render(manifest, groove_catalog)
            report = midi.validate_rendered(manifest, data)
            self.artifacts.write_bytes(output, data)
            results.append(
                {
                    "id": manifest["id"],
                    "manifest": manifest_path,
                    "output": output,
                    "tracks": report["tracks"],
                    "markers": report["markers"],
                }
            )
        return results


@dataclass(frozen=True)
class GeneratePracticeProgression:
    documents: JsonDocumentStore
    artifacts: BinaryArtifactStore
    groove_catalog_path: str = DEFAULT_GROOVE_CATALOG
    progression_catalog_path: str = DEFAULT_PROGRESSION_CATALOG

    def execute(
        self,
        request_path: str,
        *,
        profile: str = practice_progression.PROFILE,
    ) -> dict[str, Any]:
        request = dict(self.documents.read(request_path))
        groove_catalog = dict(self.documents.read(self.groove_catalog_path))
        progression_catalog = dict(self.documents.read(self.progression_catalog_path))
        return practice_progression.resolve_progression(
            request,
            groove_catalog,
            progression_catalog,
            profile=profile,
        )

    def write(
        self,
        progression: dict[str, Any],
        output_dir: str,
        *,
        render_midi: bool,
    ) -> None:
        groove_catalog = dict(self.documents.read(self.groove_catalog_path))
        for stage in progression["stages"]:
            spec = stage["spec"]
            manifest_path = posixpath.join(
                output_dir,
                "manifests",
                f"{spec['id']}.json",
            )
            self.documents.write(manifest_path, spec)
            if render_midi:
                data = backing.render(spec, groove_catalog)
                midi.validate_rendered(spec, data)
                midi_path = posixpath.join(output_dir, spec["outputs"]["midi"])
                self.artifacts.write_bytes(midi_path, data)

        self.documents.write(posixpath.join(output_dir, "progression.json"), progression)


@dataclass(frozen=True)
class GenerateMidiExercises:
    documents: JsonDocumentStore
    artifacts: BinaryArtifactStore
    manifest_path: str = DEFAULT_EXERCISE_MANIFEST
    output_dir: str = DEFAULT_EXERCISE_OUTPUT_DIR

    def execute(self) -> tuple[str, ...]:
        manifest = dict(self.documents.read(self.manifest_path))
        exercises = manifest.get("exercises")
        if not isinstance(exercises, list) or not exercises:
            raise ValueError("midi exercise manifest must contain exercises")

        outputs: list[str] = []
        for raw in exercises:
            if not isinstance(raw, dict):
                raise ValueError("each MIDI exercise must be an object")
            exercise = dict(raw)
            exercise_id = exercise.get("id")
            if not isinstance(exercise_id, str) or not exercise_id:
                raise ValueError("exercise.id must be a non-empty string")
            data = midi_exercises.generate_exercise(exercise)
            output = posixpath.join(self.output_dir, f"{exercise_id}.mid")
            self.artifacts.write_bytes(output, data)
            outputs.append(output)
        return tuple(outputs)
