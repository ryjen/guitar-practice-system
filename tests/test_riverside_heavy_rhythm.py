"""An original, dynamic heavy-blues rhythm-section alternative."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from guitar_practice.domain import backing, groove, midi, performance
from tests.test_backing_track_engine import _note_on_ticks

ROOT = Path(__file__).resolve().parents[1]
ALTERNATE = json.loads(
    (ROOT / "backing-tracks/riverside-heavy-rhythm/manifest.json").read_text(
        encoding="utf-8"
    )
)
BASE = json.loads(
    (ROOT / "backing-tracks/riverside-blues-video/manifest.json").read_text(
        encoding="utf-8"
    )
)
CATALOG = json.loads(
    (ROOT / "catalogs/grooves/catalog.json").read_text(encoding="utf-8")
)


class HeavyRhythmTests(unittest.TestCase):
    def test_distinct_variant_retains_video_form_and_tempo(self) -> None:
        self.assertNotEqual(ALTERNATE["id"], BASE["id"])
        self.assertNotEqual(ALTERNATE["outputs"]["midi"], BASE["outputs"]["midi"])
        self.assertEqual(92, ALTERNATE["tempo_bpm"])
        self.assertEqual(2, ALTERNATE["count_in_bars"])
        self.assertEqual(
            [(s["name"], s["bars"], s["chords"]) for s in BASE["sections"]],
            [(s["name"], s["bars"], s["chords"]) for s in ALTERNATE["sections"]],
        )
        self.assertEqual("original", ALTERNATE["provenance"]["type"])

    def test_drums_keep_heavy_backbeat_and_space_for_guitar(self) -> None:
        config = ALTERNATE["tracks"][0]["groove"]
        instruments = config["instruments"]
        self.assertEqual([0, 4], instruments["kick"]["steps"])
        self.assertEqual([2, 6], instruments["snare"]["steps"])
        self.assertAlmostEqual(1 / 3, config["swing"])
        self.assertLess(instruments["closed_hat"]["velocity"], 50)
        self.assertEqual("click", config["count_in"])

        spec = groove.parse_groove(config, meter=ALTERNATE["meter"])
        overrides = performance.parse(
            ALTERNATE, groove_spec=spec, has_bass=True
        )
        self.assertEqual(
            32, sum(len(section["drum_fills"]) for section in ALTERNATE["sections"])
        )
        self.assertEqual(32, len(overrides.drum_fills))

        ghost_snare = groove.GENERAL_MIDI_DRUMS["snare"]
        tom_notes = {
            groove.GENERAL_MIDI_DRUMS[name]
            for name in ("low_tom", "mid_tom", "high_tom")
        }
        self.assertGreaterEqual(
            sum(
                hit.note == ghost_snare and hit.velocity <= 64
                for f in overrides.drum_fills.values() for hit in f.hits
            ),
            12,
        )
        self.assertGreaterEqual(
            sum(
                hit.note in tom_notes and hit.tick % 480 != 0
                for f in overrides.drum_fills.values() for hit in f.hits
            ),
            18,
        )

    def test_exact_triplet_hand_foot_fills_are_on_the_three_part_grid(self) -> None:
        spec = groove.parse_groove(
            ALTERNATE["tracks"][0]["groove"], meter=ALTERNATE["meter"]
        )
        values = performance.parse(ALTERNATE, groove_spec=spec, has_bass=True)
        hands = [groove.GENERAL_MIDI_DRUMS["mid_tom"],
                 groove.GENERAL_MIDI_DRUMS["low_tom"],
                 groove.GENERAL_MIDI_DRUMS["kick"]]
        triplet_fills = [
            fill for fill in values.drum_fills.values()
            if [(hit.tick, hit.note) for hit in fill.hits]
            == [(1440, hands[0]), (1600, hands[1]), (1760, hands[2])]
        ]
        self.assertEqual(7, len(triplet_fills))
        self.assertTrue(all(hit.tick < 1920 for f in triplet_fills for hit in f.hits))

        # The ordinary swung eighth step is not the same as 1/3 of a beat.
        self.assertEqual(
            1600,
            next(h.tick for h in triplet_fills[0].hits if h.note == hands[1]),
        )
        self.assertEqual(320, round(240 + 240 * spec.swing))

    def test_triplet_contract_fails_closed_for_malformed_or_colliding_slots(self) -> None:
        source = copy.deepcopy(ALTERNATE)
        for hit in (
            {"instrument": "kick", "step": 1, "triplet_step": 1, "velocity": 85},
            {"instrument": "kick", "velocity": 85},
            {"instrument": "kick", "triplet_step": 12, "velocity": 85},
            {"instrument": "kick", "triplet_step": True, "velocity": 85},
        ):
            modified = copy.deepcopy(source)
            modified["sections"][0]["drum_fills"][0]["hits"] = [hit]
            with self.assertRaises(midi.ManifestError):
                backing.validate_manifest(modified, CATALOG)

        modified = copy.deepcopy(source)
        modified["sections"][0]["drum_fills"][0]["hits"] = [
            {"instrument": "kick", "step": 0, "velocity": 85},
            {"instrument": "kick", "triplet_step": 0, "velocity": 85},
        ]
        with self.assertRaisesRegex(midi.ManifestError, "duplicate drum hit"):
            backing.validate_manifest(modified, CATALOG)

        schema = json.loads(
            (ROOT / "contracts/backing-tracks/backing-track-spec.schema.json")
            .read_text(encoding="utf-8")
        )
        hits = schema["$defs"]["section"]["properties"]["drum_fills"]["items"]["properties"]["hits"]["items"]
        self.assertEqual(["instrument", "velocity"], hits["required"])
        self.assertEqual(2, len(hits["oneOf"]))
        self.assertIn("triplet_step", hits["properties"])

    def test_melodic_bass_answers_approach_changes_and_avoid_excess(self) -> None:
        spec = groove.parse_groove(
            ALTERNATE["tracks"][0]["groove"], meter=ALTERNATE["meter"]
        )
        values = performance.parse(ALTERNATE, groove_spec=spec, has_bass=True)
        self.assertEqual(44, len(values.bass_riffs))
        self.assertLessEqual(max(map(len, values.bass_riffs.values())), 4)
        self.assertGreater(
            sum(n.step % 2 != 0 for notes in values.bass_riffs.values() for n in notes),
            30,
        )
        approached = 0
        for section in ALTERNATE["sections"]:
            riffs = {r["bar"]: r["notes"] for r in section["bass_riffs"]}
            for bar, notes in riffs.items():
                if bar >= section["bars"]:
                    continue
                current = section["chords"][bar - 1]
                nxt = section["chords"][bar]
                if current == nxt or not any(n["step"] == 7 for n in notes):
                    continue
                last = next(n for n in notes if n["step"] == 7)
                note = midi.chord_notes(current)[0] - 12 + last["offset"]
                target = midi.chord_notes(nxt)[0] - 12
                self.assertEqual(1, abs(note - target))
                approached += 1
        self.assertGreaterEqual(approached, 5)

    def test_render_is_deterministic_and_distinct_from_sparser_backing(self) -> None:
        first = backing.render(ALTERNATE, CATALOG)
        self.assertEqual(first, backing.render(copy.deepcopy(ALTERNATE), CATALOG))
        self.assertNotEqual(first, backing.render(BASE, CATALOG))
        report = midi.validate_rendered(ALTERNATE, first)
        self.assertEqual(["Conductor", "Drums", "Bass"], report["track_names"])
        self.assertEqual(
            ["COUNT-IN", *[s["name"] for s in ALTERNATE["sections"]], "END"],
            report["markers"],
        )
        notes = _note_on_ticks(first)
        self.assertGreater(len(notes["Bass"]), 180)
        self.assertGreater(len(notes["Drums"]), 500)


if __name__ == "__main__":
    unittest.main()
