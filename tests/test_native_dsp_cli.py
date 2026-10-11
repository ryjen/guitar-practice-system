from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from guitar_practice.interfaces.cli.commands import find_command
from guitar_practice.interfaces.cli.main import main


FIXTURE = '{"schema":"guitar-dsp.preset","version":1,"preset":"jazz-blues","tempo_bpm":92,"parameters":{"delay.feedback_milli":320,"delay.free_ms":375,"delay.mix_milli":500,"delay.subdivision":"dotted-eighth"}}'


class NativeDspCliTests(unittest.TestCase):
    def test_dsp_preset_commands_are_native_and_registered(self) -> None:
        validate, consumed = find_command(["dsp", "preset", "validate", "preset.json"])
        self.assertIsNotNone(validate)
        self.assertEqual(3, consumed)
        self.assertEqual("dsp-preset-validate", validate.native_handler)

        canonicalize, consumed = find_command(
            ["dsp", "preset", "canonicalize", "preset.json"]
        )
        self.assertIsNotNone(canonicalize)
        self.assertEqual(3, consumed)
        self.assertEqual("dsp-preset-canonicalize", canonicalize.native_handler)

    def test_validate_emits_structured_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            document = json.loads(FIXTURE)
            (workspace / "preset.json").write_text(
                json.dumps(document, indent=2),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "dsp",
                        "preset",
                        "validate",
                        "preset.json",
                    ]
                )

            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            self.assertEqual(
                {
                    "preset": "jazz-blues",
                    "schema": "guitar-dsp.preset",
                    "valid": True,
                    "version": 1,
                },
                json.loads(stdout.getvalue()),
            )

    def test_canonicalize_emits_wire_bytes_plus_cli_newline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            reordered = {
                "parameters": {
                    "delay.subdivision": "dotted-eighth",
                    "delay.mix_milli": 500,
                    "delay.free_ms": 375,
                    "delay.feedback_milli": 320,
                },
                "tempo_bpm": 92,
                "preset": "jazz-blues",
                "version": 1,
                "schema": "guitar-dsp.preset",
            }
            (workspace / "preset.json").write_text(
                json.dumps(reordered, indent=2),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "dsp",
                        "preset",
                        "canonicalize",
                        "preset.json",
                    ]
                )

            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            self.assertEqual(FIXTURE + "\n", stdout.getvalue())

    def test_invalid_or_escaping_input_is_data_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "bad.json").write_text(
                '{"schema":"guitar-dsp.preset","version":2}',
                encoding="utf-8",
            )

            for path in ("bad.json", "../bad.json"):
                stdout = io.StringIO()
                stderr = io.StringIO()
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    result = main(
                        [
                            "--workspace",
                            str(workspace),
                            "dsp",
                            "preset",
                            "validate",
                            path,
                        ]
                    )
                self.assertEqual(65, result)
                self.assertEqual("", stdout.getvalue())
                self.assertIn("guitarctl:", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
