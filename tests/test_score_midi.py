from __future__ import annotations

import copy
import unittest

from guitar_practice.domain import midi, score
from guitar_practice.domain.score_midi import ScoreMidiError, render_score_midi
from guitar_practice.domain.score_realization import (
    scale_tempo,
    select_backing_parts,
)


def midi_score() -> dict:
    document = {
        "schema": score.SCHEMA_ID,
        "version": score.SCHEMA_VERSION,
        "id": "midi-score",
        "metadata": {"title": "MIDI Score"},
        "bars": [{"number": 1}, {"number": 2}],
        "meter_map": [
            {"bar": 1, "beats": 4, "beat_unit": 4},
            {"bar": 2, "beats": 3, "beat_unit": 4},
        ],
        "tempo_map": [
            {
                "location": {"bar": 1, "beat": [1, 1]},
                "bpm": 120,
                "beat_unit": [1, 4],
            },
            {
                "location": {"bar": 2, "beat": [1, 1]},
                "bpm": 60,
                "beat_unit": [1, 8],
            },
        ],
        "key_map": [
            {"bar": 1, "fifths": 0, "mode": "major"},
            {"bar": 2, "fifths": 1, "mode": "major"},
        ],
        "sections": [
            {"id": "verse", "label": "Verse", "start_bar": 1, "end_bar": 1},
            {"id": "chorus", "label": "Chorus", "start_bar": 2, "end_bar": 2},
        ],
        "rehearsal_marks": [
            {"location": {"bar": 1, "beat": [1, 1]}, "label": "Verse"},
            {"location": {"bar": 2, "beat": [1, 1]}, "label": "Chorus"},
        ],
        "parts": [
            {
                "id": "guitar",
                "name": "Guitar",
                "role": "guitar",
                "instrument": {
                    "name": "Electric Guitar",
                    "family": "guitar",
                    "midi": {"program": 29, "channel": 1},
                },
                "events": [
                    {
                        "kind": "note",
                        "location": {"bar": 1, "beat": [1, 1]},
                        "duration": [1, 4],
                        "voice": 1,
                        "pitch": {"step": "E", "alter": 0, "octave": 4},
                    }
                ],
            },
            {
                "id": "bass",
                "name": "Bass",
                "role": "bass",
                "instrument": {
                    "name": "Electric Bass",
                    "family": "bass",
                    "midi": {"program": 33, "channel": 2},
                },
                "events": [
                    {
                        "kind": "note",
                        "location": {"bar": 1, "beat": [1, 1]},
                        "duration": [1, 2],
                        "voice": 1,
                        "pitch": {"step": "C", "alter": 0, "octave": 3},
                    }
                ],
            },
            {
                "id": "drums",
                "name": "Drums",
                "role": "drums",
                "instrument": {
                    "name": "Drum Kit",
                    "family": "drums",
                    "midi": {"channel": 10, "percussion": True},
                },
                "events": [
                    {
                        "kind": "note",
                        "location": {"bar": 2, "beat": [1, 1]},
                        "duration": [1, 4],
                        "voice": 1,
                        "pitch": {"step": "C", "alter": 0, "octave": 5},
                    }
                ],
            },
        ],
    }
    score.validate(document)
    return document


class ScoreMidiTests(unittest.TestCase):
    def test_renders_type_one_midi_with_score_conductor_metadata(self) -> None:
        data = render_score_midi(midi_score())

        report = midi.inspect(data)

        self.assertEqual(1, report["format"])
        self.assertEqual(midi.TPQN, report["division"])
        self.assertEqual(4, report["tracks"])
        self.assertEqual(
            ["Conductor", "Guitar", "Bass", "Drums"],
            report["track_names"],
        )
        self.assertEqual(["Verse", "Chorus", "END"], report["markers"])
        self.assertEqual(2, report["tempo_events"])
        self.assertEqual(2, report["meter_events"])
        self.assertEqual(2, report["key_events"])

    def test_backing_realization_renders_without_song_or_manifest_model(self) -> None:
        realized = select_backing_parts(midi_score())

        data = render_score_midi(realized)
        report = midi.inspect(data)

        self.assertEqual(["Conductor", "Bass", "Drums"], report["track_names"])
        self.assertEqual(3, report["tracks"])

    def test_scaled_tempo_changes_midi_without_mutating_source(self) -> None:
        original = midi_score()
        snapshot = copy.deepcopy(original)

        normal = render_score_midi(original)
        slower = render_score_midi(scale_tempo(original, 0.5))

        self.assertNotEqual(normal, slower)
        self.assertEqual(snapshot, original)

    def test_tempo_beat_unit_is_converted_to_quarter_note_tempo(self) -> None:
        eighth = midi_score()
        eighth["tempo_map"] = [
            {
                "location": {"bar": 1, "beat": [1, 1]},
                "bpm": 60,
                "beat_unit": [1, 8],
            }
        ]
        quarter = copy.deepcopy(eighth)
        quarter["tempo_map"][0]["bpm"] = 30
        quarter["tempo_map"][0]["beat_unit"] = [1, 4]
        score.validate(eighth)
        score.validate(quarter)

        self.assertEqual(render_score_midi(eighth), render_score_midi(quarter))

    def test_tie_segments_render_like_one_sustained_note(self) -> None:
        tied = midi_score()
        tied["parts"] = [copy.deepcopy(tied["parts"][0])]
        tied["parts"][0]["events"] = [
            {
                "kind": "note",
                "location": {"bar": 1, "beat": [1, 1]},
                "duration": [1, 4],
                "voice": 1,
                "pitch": {"step": "E", "alter": 0, "octave": 4},
                "tie": "start",
            },
            {
                "kind": "note",
                "location": {"bar": 1, "beat": [2, 1]},
                "duration": [1, 4],
                "voice": 1,
                "pitch": {"step": "E", "alter": 0, "octave": 4},
                "tie": "stop",
            },
        ]
        sustained = copy.deepcopy(tied)
        sustained["parts"][0]["events"] = [
            {
                "kind": "note",
                "location": {"bar": 1, "beat": [1, 1]},
                "duration": [1, 2],
                "voice": 1,
                "pitch": {"step": "E", "alter": 0, "octave": 4},
            }
        ]
        score.validate(tied)
        score.validate(sustained)

        self.assertEqual(render_score_midi(tied), render_score_midi(sustained))

    def test_unterminated_tie_fails_closed(self) -> None:
        document = midi_score()
        document["parts"] = [copy.deepcopy(document["parts"][0])]
        document["parts"][0]["events"][0]["tie"] = "start"
        score.validate(document)

        with self.assertRaisesRegex(ScoreMidiError, "unterminated tie"):
            render_score_midi(document)

    def test_unrepresentable_tick_fraction_fails_closed(self) -> None:
        document = midi_score()
        document["parts"] = [copy.deepcopy(document["parts"][0])]
        document["parts"][0]["events"][0]["duration"] = [1, 7]
        score.validate(document)

        with self.assertRaisesRegex(ScoreMidiError, "cannot be represented exactly"):
            render_score_midi(document)


if __name__ == "__main__":
    unittest.main()
