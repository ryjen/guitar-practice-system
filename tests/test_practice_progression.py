from __future__ import annotations

import json
import struct
import tempfile
import unittest
from pathlib import Path

from guitar_practice.adapters.binary_files import BinaryFileStore
from guitar_practice.adapters.json_files import JsonFileStore
from guitar_practice.application.generation import GeneratePracticeProgression
from guitar_practice.domain import backing, midi, practice_progression

ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / "examples" / "backing-tracks" / "funk-wah-request.json"
GROOVE_CATALOG = json.loads(
    (ROOT / "catalogs" / "grooves" / "catalog.json").read_text(encoding="utf-8")
)
PROGRESSION_CATALOG = json.loads(
    (ROOT / "catalogs" / "progressions" / "catalog.json").read_text(encoding="utf-8")
)


def resolve(request: dict) -> dict:
    return practice_progression.resolve_progression(
        request,
        GROOVE_CATALOG,
        PROGRESSION_CATALOG,
    )


def _note_on_ticks(data: bytes) -> dict[str, list[int]]:
    offset = 14
    result: dict[str, list[int]] = {}
    while offset < len(data):
        length = struct.unpack(">I", data[offset + 4 : offset + 8])[0]
        track = data[offset + 8 : offset + 8 + length]
        cursor = 0
        absolute = 0
        running_status: int | None = None
        name = ""
        hits: list[int] = []
        while cursor < len(track):
            delta, cursor = midi.read_vlq(track, cursor)
            absolute += delta
            status = track[cursor]
            if status < 0x80:
                if running_status is None:
                    raise AssertionError("invalid running status")
                status = running_status
            else:
                cursor += 1
                if status < 0xF0:
                    running_status = status
            if status == 0xFF:
                kind = track[cursor]
                cursor += 1
                size, cursor = midi.read_vlq(track, cursor)
                payload = track[cursor : cursor + size]
                cursor += size
                if kind == 0x03:
                    name = payload.decode(errors="replace")
                continue
            if status in {0xF0, 0xF7}:
                size, cursor = midi.read_vlq(track, cursor)
                cursor += size
                continue
            message = status & 0xF0
            size = 1 if message in {0xC0, 0xD0} else 2
            payload = track[cursor : cursor + size]
            cursor += size
            if message == 0x90 and len(payload) == 2 and payload[1] > 0:
                hits.append(absolute)
        if name:
            result[name] = hits
        offset += 8 + length
    return result


class PracticeProgressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.request = json.loads(REQUEST.read_text(encoding="utf-8"))

    def test_funk_progression_has_expected_tempos_ids_and_gaps(self) -> None:
        progression = resolve(self.request)
        self.assertEqual("tempo-space-v1", progression["profile"])
        self.assertEqual(["slow", "medium", "fast"], [s["name"] for s in progression["stages"]])
        self.assertEqual([75, 82, 96], [s["tempo_bpm"] for s in progression["stages"]])

        specs = [stage["spec"] for stage in progression["stages"]]
        self.assertEqual(
            [
                "funk-wah-pocket-em-96-slow",
                "funk-wah-pocket-em-96-medium",
                "funk-wah-pocket-em-96-fast",
            ],
            [spec["id"] for spec in specs],
        )
        self.assertNotIn("bar_cycle", specs[0]["tracks"][0]["groove"])
        self.assertEqual(
            {"length": 4, "mute_bars": [3]},
            specs[1]["tracks"][0]["groove"]["bar_cycle"],
        )
        self.assertEqual(
            {"length": 4, "mute_bars": [2, 3]},
            specs[2]["tracks"][0]["groove"]["bar_cycle"],
        )
        for spec in specs:
            self.assertEqual(self.request["arrangement"], spec["arrangement"])
            backing.validate_manifest(spec, GROOVE_CATALOG)

    def test_composes_existing_and_added_drum_cycles(self) -> None:
        combined = practice_progression.compose_bar_cycles(
            {"length": 3, "mute_bars": [1]},
            {"length": 4, "mute_bars": [3]},
        )
        assert combined is not None
        self.assertEqual(12, combined["length"])
        self.assertEqual([1, 3, 4, 7, 10, 11], combined["mute_bars"])

    def test_resolution_is_deterministic(self) -> None:
        self.assertEqual(resolve(self.request), resolve(self.request))

    def test_fast_stage_reduces_drums_before_whole_band_gap(self) -> None:
        progression = resolve(self.request)
        fast = progression["stages"][2]["spec"]
        data = backing.render(fast, GROOVE_CATALOG)
        midi.validate_rendered(fast, data)
        ticks = _note_on_ticks(data)

        bar_ticks = midi.TPQN * 4
        drum_gap_bar = 3
        whole_band_gap_bar = 4
        self.assertFalse(
            any(
                drum_gap_bar * bar_ticks <= tick < (drum_gap_bar + 1) * bar_ticks
                for tick in ticks["Drums"]
            )
        )
        self.assertTrue(
            any(
                drum_gap_bar * bar_ticks <= tick < (drum_gap_bar + 1) * bar_ticks
                for tick in ticks["Bass"]
            )
        )
        for name in ("Drums", "Bass"):
            self.assertFalse(
                any(
                    whole_band_gap_bar * bar_ticks
                    <= tick
                    < (whole_band_gap_bar + 1) * bar_ticks
                    for tick in ticks[name]
                )
            )

    def test_application_writes_all_stage_artifacts(self) -> None:
        service = GeneratePracticeProgression(
            documents=JsonFileStore(ROOT),
            artifacts=BinaryFileStore(ROOT),
        )
        progression = service.execute(
            "examples/backing-tracks/funk-wah-request.json"
        )
        with tempfile.TemporaryDirectory() as directory:
            output_dir = str(Path(directory) / "progression")
            service.write(progression, output_dir, render_midi=True)
            root = Path(output_dir)
            self.assertTrue((root / "progression.json").exists())
            for stage in progression["stages"]:
                spec = stage["spec"]
                self.assertTrue((root / "manifests" / f"{spec['id']}.json").exists())
                self.assertTrue((root / spec["outputs"]["midi"]).exists())


if __name__ == "__main__":
    unittest.main()
