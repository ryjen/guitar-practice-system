from __future__ import annotations

import copy
import json
import struct
import unittest
from pathlib import Path

from guitar_practice.domain import backing, midi

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "backing-tracks" / "call-response-gap" / "manifest.json"
GROOVE_CATALOG = json.loads(
    (ROOT / "catalogs" / "grooves" / "catalog.json").read_text(encoding="utf-8")
)


def _note_on_ticks(data: bytes) -> dict[str, list[int]]:
    offset = 14
    result: dict[str, list[int]] = {}
    while offset < len(data):
        if data[offset : offset + 4] != b"MTrk":
            raise AssertionError("missing track chunk")
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


class BackingTrackEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_resolves_named_groove_preset(self) -> None:
        drum = self.manifest["tracks"][0]
        resolved = backing.resolve_track(
            drum,
            self.manifest["meter"],
            GROOVE_CATALOG,
        )
        self.assertNotIn("groove_preset", resolved)
        self.assertIn("groove", resolved)
        self.assertEqual(16, resolved["groove"]["subdivision"])
        self.assertIn("kick", resolved["groove"]["instruments"])

    def test_rejects_unknown_or_wrong_meter_preset(self) -> None:
        unknown = copy.deepcopy(self.manifest)
        unknown["tracks"][0]["groove_preset"] = "does-not-exist"
        with self.assertRaises(midi.ManifestError):
            backing.validate_manifest(unknown, GROOVE_CATALOG)

        wrong_meter = copy.deepcopy(self.manifest)
        wrong_meter["tracks"][0]["groove_preset"] = "odd-7-8"
        with self.assertRaises(midi.ManifestError):
            backing.validate_manifest(wrong_meter, GROOVE_CATALOG)

    def test_rejects_inline_and_preset_groove_together(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["tracks"][0]["groove"] = {
            "subdivision": 8,
            "instruments": {"kick": {"steps": [0]}},
        }
        with self.assertRaises(midi.ManifestError):
            backing.validate_manifest(manifest, GROOVE_CATALOG)

    def test_arrangement_cycle_starts_after_count_in(self) -> None:
        self.assertEqual({3, 4, 7, 8}, backing.arrangement_muted_bars(self.manifest))

    def test_full_band_gap_mutes_drums_and_bass(self) -> None:
        data = backing.render(self.manifest, GROOVE_CATALOG)
        report = midi.validate_rendered(self.manifest, data)
        note_ticks = _note_on_ticks(data)

        self.assertEqual(["Conductor", "Drums", "Bass"], report["track_names"])
        bar_ticks = midi.TPQN * 4
        for track_name in ("Drums", "Bass"):
            hits = note_ticks[track_name]
            for bar in (3, 4, 7, 8):
                self.assertFalse(
                    any(bar * bar_ticks <= tick < (bar + 1) * bar_ticks for tick in hits),
                    f"{track_name} emitted notes in muted bar {bar}",
                )
            for bar in (1, 2, 5, 6):
                self.assertTrue(
                    any(bar * bar_ticks <= tick < (bar + 1) * bar_ticks for tick in hits),
                    f"{track_name} emitted no notes in active bar {bar}",
                )


if __name__ == "__main__":
    unittest.main()
