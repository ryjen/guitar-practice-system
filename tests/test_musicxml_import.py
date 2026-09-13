from __future__ import annotations

import unittest
from pathlib import Path

from guitar_practice.domain.musicxml import MusicXmlError, parse_musicxml
from guitar_practice.domain.song import ClassificationSource, TrackRole

FIXTURE = Path(__file__).parent / "fixtures" / "musicxml" / "multitrack.musicxml"


class MusicXmlImportTests(unittest.TestCase):
    def test_parses_multitrack_metadata_tempo_and_meter(self) -> None:
        song = parse_musicxml(FIXTURE.read_bytes(), source_id="fixture")

        self.assertEqual("Fixture Song", song.title)
        self.assertEqual(
            [TrackRole.GUITAR, TrackRole.BASS, TrackRole.DRUMS, TrackRole.KEYS],
            [track.classification.role for track in song.tracks],
        )
        self.assertEqual([120.0, 90.0], [point.bpm for point in song.tempo_map])
        self.assertEqual([(4, 4)], [(point.numerator, point.denominator) for point in song.meter_map])

    def test_preserves_part_identity_and_midi_metadata(self) -> None:
        song = parse_musicxml(FIXTURE.read_bytes(), source_id="fixture")

        self.assertEqual(["P1", "P2", "P3", "P4"], [track.id for track in song.tracks])
        guitar, bass, drums, keys = song.tracks
        self.assertEqual(29, guitar.midi_program)
        self.assertEqual(33, bass.midi_program)
        self.assertEqual(1, guitar.midi_channel)
        self.assertTrue(drums.is_percussion)
        self.assertEqual(10, drums.midi_channel)
        self.assertEqual(ClassificationSource.INSTRUMENT, keys.classification.source)

    def test_rejects_malformed_xml(self) -> None:
        with self.assertRaises(MusicXmlError):
            parse_musicxml(b"<score-partwise>", source_id="fixture")

    def test_rejects_non_partwise_document(self) -> None:
        with self.assertRaises(MusicXmlError):
            parse_musicxml(b"<score-timewise version='4.0'/>", source_id="fixture")

    def test_rejects_duplicate_part_ids(self) -> None:
        data = b"""<score-partwise><part-list>
        <score-part id='P1'><part-name>One</part-name></score-part>
        <score-part id='P1'><part-name>Two</part-name></score-part>
        </part-list></score-partwise>"""
        with self.assertRaises(MusicXmlError):
            parse_musicxml(data, source_id="fixture")


if __name__ == "__main__":
    unittest.main()
