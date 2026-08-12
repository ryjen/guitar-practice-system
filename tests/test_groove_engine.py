from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIDI_MODULE_PATH = ROOT / "scripts" / "midi_workflow.py"
MIDI_SPEC = importlib.util.spec_from_file_location("midi_workflow", MIDI_MODULE_PATH)
assert MIDI_SPEC is not None and MIDI_SPEC.loader is not None
midi_workflow = importlib.util.module_from_spec(MIDI_SPEC)
sys.modules[MIDI_SPEC.name] = midi_workflow
MIDI_SPEC.loader.exec_module(midi_workflow)

GROOVE_MODULE_PATH = ROOT / "scripts" / "groove_engine.py"
GROOVE_SPEC = importlib.util.spec_from_file_location("groove_engine", GROOVE_MODULE_PATH)
assert GROOVE_SPEC is not None and GROOVE_SPEC.loader is not None
groove_engine = importlib.util.module_from_spec(GROOVE_SPEC)
sys.modules[GROOVE_SPEC.name] = groove_engine
GROOVE_SPEC.loader.exec_module(groove_engine)


class GrooveEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest_path = (
            ROOT / "backing-tracks" / "hard-rock-riff-bed" / "manifest.json"
        )
        self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        self.drum_track = next(
            track for track in self.manifest["tracks"] if track["role"] == "drums"
        )

    def test_hard_rock_manifest_exposes_valid_explicit_groove(self) -> None:
        groove_engine.validate_manifest(self.manifest)
        spec = groove_engine.parse_groove(
            self.drum_track["groove"],
            meter=self.manifest["meter"],
            default_velocity=self.drum_track["velocity"],
        )

        self.assertEqual(16, spec.subdivision)
        self.assertEqual("click", spec.count_in)
        self.assertEqual(16, groove_engine.steps_per_bar(self.manifest["meter"], 16))
        self.assertGreaterEqual(len(spec.instruments), 3)

    def test_rendering_is_deterministic_for_seed_and_bar(self) -> None:
        spec = groove_engine.parse_groove(
            self.drum_track["groove"],
            meter=self.manifest["meter"],
            default_velocity=self.drum_track["velocity"],
        )
        kwargs = {
            "bar_index": 2,
            "meter": self.manifest["meter"],
            "bar_ticks": midi_workflow.TPQN * 4,
            "tempo_bpm": self.manifest["tempo_bpm"],
        }

        self.assertEqual(
            groove_engine.render_bar(spec, **kwargs),
            groove_engine.render_bar(spec, **kwargs),
        )

    def test_variation_is_applied_on_configured_bar(self) -> None:
        spec = groove_engine.parse_groove(
            self.drum_track["groove"],
            meter=self.manifest["meter"],
            default_velocity=self.drum_track["velocity"],
        )
        kwargs = {
            "meter": self.manifest["meter"],
            "bar_ticks": midi_workflow.TPQN * 4,
            "tempo_bpm": self.manifest["tempo_bpm"],
        }
        bar_three = groove_engine.render_bar(spec, bar_index=2, **kwargs)
        bar_four = groove_engine.render_bar(spec, bar_index=3, **kwargs)

        open_hat = groove_engine.GENERAL_MIDI_DRUMS["open_hat"]
        self.assertFalse(any(hit.note == open_hat for hit in bar_three))
        self.assertTrue(any(hit.note == open_hat for hit in bar_four))

    def test_rejects_step_outside_meter(self) -> None:
        raw = json.loads(json.dumps(self.drum_track["groove"]))
        raw["instruments"]["kick"]["steps"] = [16]
        with self.assertRaises(midi_workflow.ManifestError):
            groove_engine.parse_groove(
                raw,
                meter=self.manifest["meter"],
                default_velocity=self.drum_track["velocity"],
            )

    def test_generates_type_one_midi_compatible_with_existing_validator(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "hard-rock.mid"
            groove_engine.generate(self.manifest_path, output)
            report = midi_workflow.validate_output(self.manifest_path, output)

        self.assertEqual(1, report["format"])
        self.assertEqual(["Conductor", "Drums", "Bass"], report["track_names"])
        self.assertEqual(
            ["COUNT-IN", "RIFF-A", "LIFT-B", "RIFF-C", "END"],
            report["markers"],
        )


if __name__ == "__main__":
    unittest.main()
