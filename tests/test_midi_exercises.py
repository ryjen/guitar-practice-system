from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from guitar_practice.adapters.binary_files import BinaryFileStore
from guitar_practice.adapters.json_files import JsonFileStore
from guitar_practice.application.generation import GenerateMidiExercises
from guitar_practice.domain import midi_exercises

ROOT = Path(__file__).resolve().parents[1]


class MidiExerciseTests(unittest.TestCase):
    def test_every_manifest_exercise_has_deterministic_generator(self) -> None:
        manifest = json.loads(
            (ROOT / "midi" / "exercises.json").read_text(encoding="utf-8")
        )
        for exercise in manifest["exercises"]:
            with self.subTest(exercise=exercise["id"]):
                first = midi_exercises.generate_exercise(exercise)
                second = midi_exercises.generate_exercise(json.loads(json.dumps(exercise)))
                self.assertEqual(first, second)
                self.assertTrue(first.startswith(b"MThd"))

    def test_application_writes_all_exercises(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "midi").mkdir()
            (workspace / "midi" / "exercises.json").write_text(
                (ROOT / "midi" / "exercises.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            outputs = GenerateMidiExercises(
                documents=JsonFileStore(workspace),
                artifacts=BinaryFileStore(workspace),
            ).execute()

            self.assertEqual(set(midi_exercises.GENERATORS), {Path(p).stem for p in outputs})
            for output in outputs:
                data = (workspace / output).read_bytes()
                self.assertTrue(data.startswith(b"MThd"))


if __name__ == "__main__":
    unittest.main()
