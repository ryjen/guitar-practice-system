from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

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
        self.assertEqual({0, 2, 4, 6, 11, 15, 17, 19, 20, 22, 24, 26, 31, 35, 37, 39, 40, 42, 44, 46, 51, 55, 57, 59, 60, 62, 64, 66}, set(value.bass_riffs))

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

    def test_blues_verses_have_distinct_bass_responses(self) -> None:
        _, overrides = _parsed()
        self.assertEqual([11, 15, 17, 19], [bar for bar in sorted(overrides.bass_riffs) if 8 <= bar < 20])
        self.assertEqual([31, 35, 37, 39], [bar for bar in sorted(overrides.bass_riffs) if 28 <= bar < 40])
        self.assertEqual([51, 55, 57, 59], [bar for bar in sorted(overrides.bass_riffs) if 48 <= bar < 60])
        self.assertNotEqual(overrides.bass_riffs[11], overrides.bass_riffs[15])
        self.assertNotEqual(overrides.bass_riffs[19], overrides.bass_riffs[11])

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

    def test_groove_count_in_never_gets_section_one_fill(self) -> None:
        manifest = copy.deepcopy(MANIFEST)
        resolved_groove = groove.get_preset(CATALOG, "blues-shuffle")["groove"]
        resolved_groove["count_in"] = "groove"
        drum = manifest["tracks"][0]
        drum.pop("groove_preset")
        drum["groove"] = resolved_groove

        groove_spec = groove.parse_groove(resolved_groove, meter=manifest["meter"])
        expected = performance.parse(
            manifest, groove_spec=groove_spec, has_bass=True
        )
        with patch.object(
            performance, "apply_drum_fill", wraps=performance.apply_drum_fill
        ) as apply_fill:
            backing.render(manifest, CATALOG)
        # For this manifest a bar-1 fill exists and there are two count-in
        # bars. The previous bug called apply_drum_fill twice too often.
        self.assertEqual(len(expected.drum_fills), apply_fill.call_count)

    def test_meter_derived_step_grid_accepts_12_8_step_40(self) -> None:
        meter = [12, 8]
        groove_spec = groove.parse_groove(
            {
                "subdivision": 32,
                "instruments": {
                    "kick": {"steps": [0, 40], "velocity": 90}
                },
            },
            meter=meter,
        )
        manifest = {
            "meter": meter,
            "sections": [
                {
                    "name": "TEST",
                    "bars": 1,
                    "chords": ["G7"],
                    "drum_fills": [
                        {
                            "bar": 1,
                            "hits": [
                                {"instrument": "low_tom", "step": 40, "velocity": 90}
                            ],
                        }
                    ],
                    "bass_riffs": [
                        {"bar": 1, "notes": [{"step": 40, "offset": 0}]}
                    ],
                }
            ],
        }
        parsed = performance.parse(
            manifest, groove_spec=groove_spec, has_bass=True
        )
        self.assertEqual(40 * 60, parsed.drum_fills[0].hits[0].tick)
        self.assertEqual(40, parsed.bass_riffs[0][0].step)

        schema = json.loads(
            (ROOT / "contracts/backing-tracks/backing-track-spec.schema.json").read_text(
                encoding="utf-8"
            )
        )
        section_properties = schema["$defs"]["section"]["properties"]
        drum_step = (
            section_properties["drum_fills"]["items"]["properties"]["hits"]
            ["items"]["properties"]["step"]
        )
        bass_step = (
            section_properties["bass_riffs"]["items"]["properties"]["notes"]
            ["items"]["properties"]["step"]
        )
        self.assertNotIn("maximum", drum_step)
        self.assertNotIn("maximum", bass_step)

    def test_override_bar_129_valid_when_section_is_longer_than_128(self) -> None:
        # Runtime derives the bar bound from each section, not a constant.
        manifest = copy.deepcopy(MANIFEST)
        long_section = manifest["sections"][0]
        long_section["bars"] = 129
        long_section["chords"] = ["G7"] * 129
        long_section["drum_fills"] = [
            {
                "bar": 129,
                "hits": [{"instrument": "low_tom", "step": 7, "velocity": 90}],
            }
        ]
        long_section["bass_riffs"] = [
            {"bar": 129, "notes": [{"step": 0, "offset": 0}]}
        ]
        parsed_groove, values = _parsed(manifest)
        self.assertIsNotNone(parsed_groove)
        self.assertIn(128, values.drum_fills)
        self.assertIn(128, values.bass_riffs)
        backing.validate_manifest(manifest, CATALOG)

        schema = json.loads(
            (ROOT / "contracts/backing-tracks/backing-track-spec.schema.json").read_text(
                encoding="utf-8"
            )
        )
        for role in ("drum_fills", "bass_riffs"):
            bar = schema["$defs"]["section"]["properties"][role]["items"]["properties"]["bar"]
            self.assertEqual(1, bar["minimum"])
            self.assertNotIn("maximum", bar)

        rejected = copy.deepcopy(manifest)
        rejected["sections"][0]["bars"] = 128
        rejected["sections"][0]["chords"] = ["G7"] * 128
        with self.assertRaisesRegex(midi.ManifestError, "section.drum_fills.bar"):
            backing.validate_manifest(rejected, CATALOG)

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
