from __future__ import annotations

import json
import unittest
from pathlib import Path

from guitar_practice.domain import bass, groove, midi

ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads(
    (ROOT / "catalogs" / "grooves" / "catalog.json").read_text(encoding="utf-8")
)


class BassEngineTests(unittest.TestCase):
    def _groove(self, preset_id: str) -> groove.GrooveSpec:
        preset = groove.get_preset(CATALOG, preset_id)
        return groove.parse_groove(preset["groove"], meter=preset["meter"])

    def test_kick_root_octave_uses_kick_timing_and_alternates_notes(self) -> None:
        groove_spec = self._groove("funk-wah-16")
        spec = bass.parse_bass({"style": "kick-root-octave"})
        bar_ticks = midi.TPQN * 4
        beat_ticks = midi.TPQN

        bass_hits = bass.render_bar(
            spec,
            chord="Em7",
            bar_index=0,
            meter=[4, 4],
            bar_ticks=bar_ticks,
            beat_ticks=beat_ticks,
            tempo_bpm=96,
            base_velocity=80,
            groove_spec=groove_spec,
        )
        drum_hits = groove.render_bar(
            groove_spec,
            bar_index=0,
            meter=[4, 4],
            bar_ticks=bar_ticks,
            tempo_bpm=96,
        )
        kick_ticks = [
            hit.tick
            for hit in drum_hits
            if hit.note == groove.GENERAL_MIDI_DRUMS["kick"]
        ]

        root = midi.chord_notes("Em7")[0] - 12
        self.assertEqual(kick_ticks, [hit.tick for hit in bass_hits])
        self.assertEqual(
            [root if index % 2 == 0 else root + 12 for index in range(len(bass_hits))],
            [hit.note for hit in bass_hits],
        )

    def test_drum_only_gap_cycle_does_not_mute_kick_reference_bass(self) -> None:
        groove_spec = self._groove("call-response-2x2")
        spec = bass.parse_bass({"style": "kick-root"})
        bar_ticks = midi.TPQN * 4

        self.assertEqual(
            [],
            groove.render_bar(
                groove_spec,
                bar_index=2,
                meter=[4, 4],
                bar_ticks=bar_ticks,
                tempo_bpm=92,
            ),
        )
        bass_hits = bass.render_bar(
            spec,
            chord="Em",
            bar_index=2,
            meter=[4, 4],
            bar_ticks=bar_ticks,
            beat_ticks=midi.TPQN,
            tempo_bpm=92,
            base_velocity=80,
            groove_spec=groove_spec,
        )
        self.assertTrue(bass_hits)

    def test_walking_bass_needs_no_groove_reference(self) -> None:
        spec = bass.parse_bass({"style": "walking", "gate_percent": 80})
        hits = bass.render_bar(
            spec,
            chord="Dm7",
            bar_index=0,
            meter=[4, 4],
            bar_ticks=midi.TPQN * 4,
            beat_ticks=midi.TPQN,
            tempo_bpm=120,
            base_velocity=74,
            groove_spec=None,
        )
        self.assertEqual([0, 480, 960, 1440], [hit.tick for hit in hits])
        self.assertEqual(4, len(hits))

    def test_bass_spec_rejects_unsupported_fields_and_invalid_walking_follow(self) -> None:
        with self.assertRaisesRegex(midi.ManifestError, "unsupported fields"):
            bass.parse_bass({"style": "kick-root", "free": True})

        with self.assertRaisesRegex(midi.ManifestError, "cannot follow kick velocity"):
            bass.parse_bass({"style": "walking", "follow_kick_velocity": True})

    def test_kick_locked_rendering_is_deterministic(self) -> None:
        groove_spec = self._groove("alt-rock")
        spec = bass.parse_bass(
            {
                "style": "kick-root-fifth",
                "gate_percent": 68,
                "follow_kick_velocity": True,
            }
        )
        kwargs = {
            "chord": "Em",
            "bar_index": 3,
            "meter": [4, 4],
            "bar_ticks": midi.TPQN * 4,
            "beat_ticks": midi.TPQN,
            "tempo_bpm": 108,
            "base_velocity": 80,
            "groove_spec": groove_spec,
        }
        self.assertEqual(bass.render_bar(spec, **kwargs), bass.render_bar(spec, **kwargs))


if __name__ == "__main__":
    unittest.main()
