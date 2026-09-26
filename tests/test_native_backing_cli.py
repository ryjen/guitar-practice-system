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

ROOT = Path(__file__).resolve().parents[1]


class NativeBackingCliTests(unittest.TestCase):
    def _workspace(self, directory: str) -> Path:
        workspace = Path(directory)
        groove_target = workspace / "catalogs" / "grooves" / "catalog.json"
        progression_target = workspace / "catalogs" / "progressions" / "catalog.json"
        request_target = workspace / "request.json"
        groove_target.parent.mkdir(parents=True)
        progression_target.parent.mkdir(parents=True)
        groove_target.write_text(
            (ROOT / "catalogs" / "grooves" / "catalog.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        progression_target.write_text(
            (ROOT / "catalogs" / "progressions" / "catalog.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        request_target.write_text(
            (ROOT / "examples" / "backing-tracks" / "funk-wah-request.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        return workspace

    def test_backing_commands_are_native(self) -> None:
        for tokens in (
            ["backing", "resolve", "request.json"],
            ["backing", "generate"],
            ["backing", "render", "score.json"],
        ):
            command, _ = find_command(tokens)
            self.assertIsNotNone(command)
            assert command is not None
            self.assertEqual(MigrationState.NATIVE, command.migration)
            self.assertIsNotNone(command.native_handler)
            self.assertIsNone(command.legacy)

    def test_backing_render_uses_score_ir_and_excludes_authoritative_guitar(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            document = {
                "schema": score.SCHEMA_ID,
                "version": score.SCHEMA_VERSION,
                "id": "fixture",
                "metadata": {"title": "Fixture"},
                "bars": [{"number": 1}, {"number": 2}],
                "meter_map": [{"bar": 1, "beats": 4, "beat_unit": 4}],
                "tempo_map": [
                    {
                        "location": {"bar": 1, "beat": [1, 1]},
                        "bpm": 120,
                        "beat_unit": [1, 4],
                    }
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
                                "location": {"bar": 1, "beat": [1, 1]},
                                "duration": [1, 4],
                                "voice": 1,
                                "pitch": {"step": "E", "alter": 0, "octave": 2},
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
                                "location": {"bar": 1, "beat": [1, 1]},
                                "duration": [1, 4],
                                "voice": 1,
                                "pitch": {"step": "C", "alter": 0, "octave": 5},
                            }
                        ],
                    },
                ],
            }
            score.validate(document)
            (workspace / "score.json").write_text(score.dumps(document), encoding="utf-8")

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
            self.assertEqual("", stdout.getvalue())
            self.assertEqual("", stderr.getvalue())
            rendered = workspace / "generated" / "backing.mid"
            report = midi.inspect(rendered.read_bytes())
            self.assertEqual(["Conductor", "Bass", "Drums"], report["track_names"])

            metadata = json.loads(
                (workspace / "generated" / "backing.mid.json").read_text(encoding="utf-8")
            )
            self.assertEqual(0.75, metadata["tempo_factor"])
            self.assertEqual(["bass", "drums"], metadata["selected_part_ids"])
            self.assertEqual(["guitar"], metadata["excluded_part_ids"])
            self.assertFalse((workspace / "scripts").exists())

    def test_backing_resolve_runs_without_repository_scripts(self) -> None:
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
                        "resolve",
                        "request.json",
                    ]
                )

            self.assertEqual(0, result)
            payload = json.loads(stdout.getvalue())
            self.assertEqual("funk-wah-pocket-em-96", payload["id"])
            self.assertEqual("", stderr.getvalue())
            self.assertFalse((workspace / "scripts").exists())

    def test_backing_resolve_output_preserves_quiet_stdout_contract(self) -> None:
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
                        "resolve",
                        "request.json",
                        "--output",
                        "resolved/spec.json",
                    ]
                )

            self.assertEqual(0, result)
            self.assertEqual("", stdout.getvalue())
            self.assertEqual("", stderr.getvalue())
            payload = json.loads((workspace / "resolved" / "spec.json").read_text())
            self.assertEqual("funk-wah-pocket-em-96", payload["id"])


if __name__ == "__main__":
    unittest.main()
