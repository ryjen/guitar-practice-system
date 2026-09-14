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
        self.assertEqual(8.0, song.duration_quarters)

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

    def test_imports_note_events_and_percussion_identity(self) -> None:
        song = parse_musicxml(FIXTURE.read_bytes(), source_id="fixture")
        guitar, bass, drums, keys = song.tracks

        self.assertEqual(
            [(0.0, 4.0, 64), (4.0, 4.0, 67)],
            [(note.position, note.duration, note.midi_note) for note in guitar.notes],
        )
        self.assertEqual((), bass.notes)
        self.assertEqual([(0.0, 1.0, 35)], [
            (note.position, note.duration, note.midi_note) for note in drums.notes
        ])
        self.assertEqual((), keys.notes)

    def test_divisions_chords_rests_and_offsets_use_quarter_note_units(self) -> None:
        data = b"""<score-partwise><part-list>
        <score-part id='P1'><part-name>Guitar</part-name></score-part>
        </part-list><part id='P1'><measure number='1'>
        <attributes><divisions>2</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
        <direction><offset>2</offset><sound tempo='90'/></direction>
        <note><pitch><step>C</step><octave>4</octave></pitch><duration>2</duration></note>
        <note><chord/><pitch><step>E</step><octave>4</octave></pitch><duration>2</duration></note>
        <note><rest/><duration>2</duration></note>
        <note><pitch><step>G</step><octave>4</octave></pitch><duration>2</duration></note>
        </measure></part></score-partwise>"""
        song = parse_musicxml(data, source_id="fixture")

        self.assertEqual([1.0], [point.position for point in song.tempo_map])
        self.assertEqual(
            [(0.0, 1.0, 60), (0.0, 1.0, 64), (2.0, 1.0, 67)],
            [(note.position, note.duration, note.midi_note) for note in song.tracks[0].notes],
        )

    def test_structural_duration_uses_actual_span_for_implicit_pickup_measure(self) -> None:
        data = b"""<score-partwise><part-list>
        <score-part id='P1'><part-name>Guitar</part-name></score-part>
        </part-list><part id='P1'>
        <measure number='0' implicit='yes'>
          <attributes><divisions>1</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
          <note><rest/><duration>1</duration></note>
        </measure>
        <measure number='1'><note><rest/><duration>4</duration></note></measure>
        </part></score-partwise>"""
        song = parse_musicxml(data, source_id="pickup")
        self.assertEqual(5.0, song.duration_quarters)

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
