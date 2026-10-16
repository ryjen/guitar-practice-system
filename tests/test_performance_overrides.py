from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from guitar_practice.domain import backing, groove, midi, performance

ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads((ROOT / "catalogs/grooves/catalog.json").read_text(encoding="utf-8"))
MANIFEST = json.loads((ROOT / "backing-tracks/riverside-blues-video/manifest.json").read_text(encoding="utf-8"))


def _parsed(manifest: dict = MANIFEST) -> tuple[groove.GrooveSpec, performance.Performance]:
    preset = groove.get_preset(CATALOG, "blues-shuffle")
    drum = groove.parse_groove(preset["groove"], meter=manifest["meter"])
    return drum, performance.parse(manifest, groove_spec=drum, has_bass=True)


class PerformanceOverrideTests(unittest.TestCase):
    def test_section_indices_are_musical_bars_and_not_count_in(self) -> None:
        _, value = _parsed()
        self.assertEqual({0, 7, 8, 19, 20, 27, 28, 39, 40, 47, 48, 59, 60, 67}, set(value.drum_fills))
        self.assertEqual({0, 2, 4, 6, 19, 20, 22, 24, 26, 39, 40, 42, 44, 46, 59, 60, 62, 64, 66}, set(value.bass_riffs))

    def test_riff_vamps_and_blues_verses_are_distinct_sections(self) -> None:
        lengths = [section["bars"] for section in MANIFEST["sections"]]
        self.assertEqual([8, 12, 8, 12, 8, 12, 8], lengths)
        self.assertEqual(68, sum(lengths))
        self.assertTrue(
            all(chord == "G7" for chord in MANIFEST["sections"][0]["chords"])
        )
        verse = MANIFEST["sections"][1]["chords"]
        self.assertEqual(["G7", "C7", "D7"], [verse[0], verse[4], verse[8]])
        self.assertIn("not an independently verified transcription", MANIFEST["provenance"]["notes"])

    def test_fill_replaces_hats_but_preserves_kick_and_snare(self) -> None:
        spec, value = _parsed()
        hits = groove.render_bar(
            spec, bar_index=11, meter=[4, 4], bar_ticks=1920, tempo_bpm=108
        )
        replaced = performance.apply_drum_fill(hits, value.drum_fills[7])
        names = groove.GENERAL_MIDI_DRUMS
        self.assertTrue(any(hit.note == names["kick"] for hit in replaced))
        self.assertTrue(any(hit.note == names["snare"] for hit in replaced))
        self.assertFalse(any(hit.note == names["closed_hat"] for hit in replaced))
        self.assertEqual(4, sum(hit.note in {names["mid_tom"], names["low_tom"]} for hit in replaced))

    def test_riff_is_chord_relative_and_has_ordered_non_overlapping_notes(self) -> None:
        spec, value = _parsed()
        kwargs = {
            "groove_spec": spec, "meter": [4, 4], "bar_ticks": 1920,
            "base_velocity": 90,
        }
        in_d = performance.render_bass_riff(value.bass_riffs[19], chord="D7", **kwargs)
        in_g = performance.render_bass_riff(value.bass_riffs[19], chord="G7", **kwargs)
        self.assertEqual([hit.tick for hit in in_d], [hit.tick for hit in in_g])
        self.assertEqual(8, len(in_d))
        self.assertEqual(midi.chord_notes("D7")[0] - 12, in_d[0].note)
        self.assertEqual(midi.chord_notes("G7")[0] - 12, in_g[0].note)
        for earlier, later in zip(in_d, in_d[1:]):
            self.assertLess(earlier.tick + earlier.duration, later.tick)

    def test_original_backing_is_deterministic_valid_midi(self) -> None:
        first = backing.render(MANIFEST, CATALOG)
        second = backing.render(copy.deepcopy(MANIFEST), CATALOG)
        self.assertEqual(first, second)
        report = midi.validate_rendered(MANIFEST, first)
        self.assertEqual(["Conductor", "Drums", "Bass"], report["track_names"])
        self.assertEqual(["COUNT-IN", "INTRO-RIFF", "VERSE-1", "RIFF-REFRAIN-1", "VERSE-2", "RIFF-REFRAIN-2", "SOLO-BLUES", "OUTRO-RIFF", "END"], report["markers"])

    def test_rejects_duplicate_bars_and_invalid_events(self) -> None:
        duplicate = copy.deepcopy(MANIFEST)
        duplicate["sections"][0]["drum_fills"].append(
            copy.deepcopy(duplicate["sections"][0]["drum_fills"][0])
        )
        with self.assertRaisesRegex(midi.ManifestError, "duplicate drum_fills"):
            backing.validate_manifest(duplicate, CATALOG)

        invalid = copy.deepcopy(MANIFEST)
        invalid["sections"][0]["bass_riffs"][0]["notes"][0]["offset"] = 500
        with self.assertRaisesRegex(midi.ManifestError, "bass_riffs.notes.offset"):
            backing.validate_manifest(invalid, CATALOG)

        invalid = copy.deepcopy(MANIFEST)
        invalid["sections"][0]["drum_fills"][0]["hits"][0]["step"] = -1
        with self.assertRaisesRegex(midi.ManifestError, "drum_fills.hits.step"):
            backing.validate_manifest(invalid, CATALOG)

    def test_rejects_missing_groove_and_bass_roles(self) -> None:
        missing_groove = copy.deepcopy(MANIFEST)
        missing_groove["tracks"][0].pop("groove_preset")
        with self.assertRaisesRegex(midi.ManifestError, "requires exactly one groove-aware"):
            backing.validate_manifest(missing_groove, CATALOG)

        missing_bass = copy.deepcopy(MANIFEST)
        missing_bass["tracks"].pop()
        with self.assertRaisesRegex(midi.ManifestError, "requires a generated bass track"):
            backing.validate_manifest(missing_bass, CATALOG)


if __name__ == "__main__":
    unittest.main()
