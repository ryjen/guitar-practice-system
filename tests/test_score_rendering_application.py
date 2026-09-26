from __future__ import annotations

import unittest

from guitar_practice.application.score_rendering import RenderScoreMidi
from guitar_practice.domain import midi, score


class MemoryArtifacts:
    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}

    def read_bytes(self, path: str) -> bytes:
        return self.values[path]

    def write_bytes(self, path: str, data: bytes) -> None:
        self.values[path] = data


def render_score() -> dict:
    document = {
        "schema": score.SCHEMA_ID,
        "version": score.SCHEMA_VERSION,
        "id": "render-score",
        "metadata": {"title": "Render Score"},
        "bars": [{"number": 1}, {"number": 2}],
        "meter_map": [{"bar": 1, "beats": 4, "beat_unit": 4}],
        "tempo_map": [
            {
                "location": {"bar": 1, "beat": [1, 1]},
                "bpm": 120,
                "beat_unit": [1, 4],
            }
        ],
        "sections": [
            {"id": "intro", "label": "Intro", "start_bar": 1, "end_bar": 1},
            {"id": "chorus", "label": "Chorus", "start_bar": 2, "end_bar": 2},
        ],
        "rehearsal_marks": [
            {"location": {"bar": 1, "beat": [1, 1]}, "label": "Intro"},
            {"location": {"bar": 2, "beat": [1, 1]}, "label": "Chorus"},
        ],
        "parts": [
            {
                "id": "guitar",
                "name": "Guitar",
                "role": "guitar",
                "instrument": {"name": "Electric Guitar", "family": "guitar"},
                "events": [
                    {
                        "kind": "note",
                        "location": {"bar": 1, "beat": [1, 1]},
                        "duration": [1, 4],
                        "voice": 1,
                        "pitch": {"step": "E", "alter": 0, "octave": 4},
                    }
                ],
                "provenance": {
                    "kind": "imported",
                    "source": "track-role:instrument",
                },
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
                        "location": {"bar": 2, "beat": [1, 1]},
                        "duration": [1, 4],
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


class ScoreRenderingApplicationTests(unittest.TestCase):
    def test_backing_render_composes_realization_and_midi(self) -> None:
        artifacts = MemoryArtifacts()
        result = RenderScoreMidi(artifacts).execute(
            render_score(),
            "generated/backing.mid",
            kind="backing",
            tempo_factor=0.75,
        )

        self.assertEqual("generated/backing.mid", result.output_path)
        self.assertEqual(("bass", "drums"), result.part_ids)
        self.assertGreater(result.byte_count, 0)
        report = midi.inspect(artifacts.values[result.output_path])
        self.assertEqual(["Conductor", "Bass", "Drums"], report["track_names"])

    def test_drum_render_can_slice_named_section(self) -> None:
        artifacts = MemoryArtifacts()
        result = RenderScoreMidi(artifacts).execute(
            render_score(),
            "generated/drums.mid",
            kind="drums",
            section_name="chorus",
        )

        self.assertEqual(("drums",), result.part_ids)
        report = midi.inspect(artifacts.values[result.output_path])
        self.assertEqual(["Conductor", "Drums"], report["track_names"])
        self.assertEqual(["Chorus", "END"], report["markers"])

    def test_explicit_part_override_and_bar_slice_are_composable(self) -> None:
        artifacts = MemoryArtifacts()
        result = RenderScoreMidi(artifacts).execute(
            render_score(),
            "generated/custom.mid",
            kind="backing",
            include_part_ids=("guitar",),
            exclude_part_ids=("drums",),
            bar_range=(1, 1),
        )

        self.assertEqual(("guitar", "bass"), result.part_ids)
        report = midi.inspect(artifacts.values[result.output_path])
        self.assertEqual(["Conductor", "Guitar", "Bass"], report["track_names"])

    def test_empty_selection_and_invalid_kind_fail_closed(self) -> None:
        artifacts = MemoryArtifacts()
        with self.assertRaisesRegex(ValueError, "selected no parts"):
            RenderScoreMidi(artifacts).execute(
                render_score(),
                "generated/none.mid",
                kind="drums",
                exclude_part_ids=("drums",),
            )
        with self.assertRaisesRegex(ValueError, "backing or drums"):
            RenderScoreMidi(artifacts).execute(
                render_score(),
                "generated/nope.mid",
                kind="other",
            )


if __name__ == "__main__":
    unittest.main()
