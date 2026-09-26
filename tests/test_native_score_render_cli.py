from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from guitar_practice.domain import midi, score
from guitar_practice.interfaces.cli.commands import MigrationState, find_command
from guitar_practice.interfaces.cli.main import main


def cli_score() -> dict:
    document = {
        "schema": score.SCHEMA_ID,
        "version": score.SCHEMA_VERSION,
        "id": "cli-score",
        "metadata": {"title": "CLI Score"},
        "bars": [{"number": 1}, {"number": 2}],
        "meter_map": [{"bar": 1, "beats": 4, "beat_unit": 4}],
        "tempo_map": [
            {
                "location": {"bar": 1, "beat": [1, 1]},
                "bpm": 100,
                "beat_unit": [1, 4],
            }
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
                "instrument": {"name": "Electric Guitar", "family": "guitar"},
                "events": [],
                "provenance": {
                    "kind": "imported",
                    "source": "track-role:instrument",
                },
            },
            {
                "id": "bass",
                "name": "Bass",
                "role": "bass",
                "instrument": {"name": "Bass", "family": "bass"},
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


class NativeScoreRenderCliTests(unittest.TestCase):
    def _workspace(self, directory: str) -> Path:
        workspace = Path(directory)
        (workspace / "score.json").write_text(
            score.dumps(cli_score()),
            encoding="utf-8",
        )
        return workspace

    def test_symbolic_render_commands_are_native(self) -> None:
        for tokens in (
            ["backing", "render", "score.json"],
            ["drums", "render", "score.json"],
        ):
            with self.subTest(tokens=tokens):
                command, _ = find_command(tokens)
                self.assertIsNotNone(command)
                assert command is not None
                self.assertEqual(MigrationState.NATIVE, command.migration)

    def test_backing_render_writes_score_ir_derived_midi(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = self._workspace(directory)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "backing",
                        "render",
                        "score.json",
                        "--tempo",
                        "75%",
                        "--output",
                        "generated/backing.mid",
                    ]
                )

            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            payload = json.loads(stdout.getvalue())
            self.assertEqual("backing", payload["kind"])
            self.assertEqual(["bass", "drums"], payload["parts"])
            self.assertEqual("75%", payload["tempo"])
            output = workspace / payload["output"]
            self.assertTrue(output.is_file())
            self.assertEqual(
                ["Conductor", "Bass", "Drums"],
                midi.inspect(output.read_bytes())["track_names"],
            )

    def test_drums_render_supports_section_and_track_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = self._workspace(directory)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "drums",
                        "render",
                        "score.json",
                        "--section",
                        "chorus",
                        "--include-track",
                        "bass",
                        "--output",
                        "generated/drums.mid",
                    ]
                )

            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            payload = json.loads(stdout.getvalue())
            self.assertEqual(["bass", "drums"], payload["parts"])
            report = midi.inspect((workspace / payload["output"]).read_bytes())
            self.assertEqual(["Conductor", "Bass", "Drums"], report["track_names"])
            self.assertEqual(["Chorus", "END"], report["markers"])

    def test_render_rejects_ambiguous_slice_and_output_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = self._workspace(directory)

            stderr = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "backing",
                        "render",
                        "score.json",
                        "--bars",
                        "1:1",
                        "--section",
                        "verse",
                        "--output",
                        "generated/backing.mid",
                    ]
                )
            self.assertEqual(65, result)
            self.assertIn("either --bars or --section", stderr.getvalue())

            stderr = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "backing",
                        "render",
                        "score.json",
                        "--output",
                        "../escape.mid",
                    ]
                )
            self.assertEqual(65, result)
            self.assertIn("workspace-relative", stderr.getvalue())

    def test_render_rejects_nonfinite_tempo(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = self._workspace(directory)
            stderr = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "backing",
                        "render",
                        "score.json",
                        "--tempo",
                        "inf%",
                        "--output",
                        "generated/backing.mid",
                    ]
                )
            self.assertEqual(65, result)
            self.assertIn("positive and finite", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
