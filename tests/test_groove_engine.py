from __future__ import annotations

import json
import unittest
from pathlib import Path

from guitar_practice.domain import groove, midi

ROOT = Path(__file__).resolve().parents[1]


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
        groove.validate_manifest(self.manifest)
        spec = groove.parse_groove(
            self.drum_track["groove"],
            meter=self.manifest["meter"],
            default_velocity=self.drum_track["velocity"],
        )

        self.assertEqual(16, spec.subdivision)
        self.assertEqual("click", spec.count_in)
        self.assertEqual(16, groove.steps_per_bar(self.manifest["meter"], 16))
        self.assertGreaterEqual(len(spec.instruments), 3)

    def test_rendering_is_deterministic_for_seed_and_bar(self) -> None:
        spec = groove.parse_groove(
            self.drum_track["groove"],
            meter=self.manifest["meter"],
            default_velocity=self.drum_track["velocity"],
        )
        kwargs = {
            "bar_index": 2,
            "meter": self.manifest["meter"],
            "bar_ticks": midi.TPQN * 4,
            "tempo_bpm": self.manifest["tempo_bpm"],
        }

        self.assertEqual(groove.render_bar(spec, **kwargs), groove.render_bar(spec, **kwargs))

    def test_variation_is_applied_on_configured_bar(self) -> None:
        spec = groove.parse_groove(
            self.drum_track["groove"],
            meter=self.manifest["meter"],
            default_velocity=self.drum_track["velocity"],
        )
        kwargs = {
            "meter": self.manifest["meter"],
            "bar_ticks": midi.TPQN * 4,
            "tempo_bpm": self.manifest["tempo_bpm"],
        }
        bar_three = groove.render_bar(spec, bar_index=2, **kwargs)
        bar_four = groove.render_bar(spec, bar_index=3, **kwargs)

        open_hat = groove.GENERAL_MIDI_DRUMS["open_hat"]
        self.assertFalse(any(hit.note == open_hat for hit in bar_three))
        self.assertTrue(any(hit.note == open_hat for hit in bar_four))

    def test_rejects_step_outside_meter(self) -> None:
        raw = json.loads(json.dumps(self.drum_track["groove"]))
        raw["instruments"]["kick"]["steps"] = [16]
        with self.assertRaises(midi.ManifestError):
            groove.parse_groove(
                raw,
                meter=self.manifest["meter"],
                default_velocity=self.drum_track["velocity"],
            )

    def test_renders_type_one_midi_compatible_with_midi_domain(self) -> None:
        first = groove.render(self.manifest)
        second = groove.render(json.loads(json.dumps(self.manifest)))
        self.assertEqual(first, second)
        report = midi.validate_rendered(self.manifest, first)

        self.assertEqual(1, report["format"])
        self.assertEqual(["Conductor", "Drums", "Bass"], report["track_names"])
        self.assertEqual(
            ["COUNT-IN", "RIFF-A", "LIFT-B", "RIFF-C", "END"],
            report["markers"],
        )


if __name__ == "__main__":
    unittest.main()
