"""Control-plane render CLI tests; use a stub executable, not duplicated DSP."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

from guitar_practice.interfaces.cli.commands import MigrationState, find_command
from guitar_practice.interfaces.cli.main import main


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "contracts" / "dsp" / "fixtures" / "jazz-blues-preset-v1.json"
)


class DspRenderCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.workspace = Path(self.temporary.name)
        (self.workspace / "input.wav").write_bytes(b"RIFF" + b"\x00" * 40)
        (self.workspace / "preset.json").write_text(
            json.dumps(json.loads(FIXTURE.read_text(encoding="utf-8")), indent=2),
            encoding="utf-8",
        )
        self.engine = self.workspace / "stub-dsp"
        self.engine.write_text(
            "#!" + sys.executable + "\n"
            "import pathlib, sys\n"
            "args = sys.argv[1:]\n"
            "assert args[0] == 'render'\n"
            "assert pathlib.Path(args[1]).is_file()\n"
            "if '--preset' in args:\n"
            "    content = pathlib.Path(args[args.index('--preset') + 1]).read_text()\n"
            "    assert content.startswith('{\"schema\":\"guitar-dsp.preset\",\"version\":1,')\n"
            "    assert '\\n' not in content\n"
            "pathlib.Path(args[args.index('--output') + 1]).write_bytes(b'RIFFstub')\n",
            encoding="utf-8",
        )
        self.engine.chmod(0o700)

    def cli(self, *arguments: str) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(["--workspace", str(self.workspace), *arguments])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_both_command_paths_are_native(self) -> None:
        for tokens in (["render"], ["dsp", "render"]):
            with self.subTest(tokens=tokens):
                command, consumed = find_command(tokens)
                self.assertIsNotNone(command)
                assert command is not None
                self.assertEqual(len(tokens), consumed)
                self.assertEqual(MigrationState.NATIVE, command.migration)
                self.assertEqual("dsp-audio-render", command.native_handler)

    def test_renders_with_canonical_v1_preset_and_ordered_effects(self) -> None:
        code, out, error = self.cli(
            "render", "input.wav", "--preset", "preset.json",
            "--output", "output.wav", "--effects", "tremolo,delay",
            "--tremolo-rate", "3.0", "--engine", str(self.engine),
        )
        self.assertEqual(0, code, error)
        self.assertEqual("", error)
        self.assertEqual(
            {"status": "rendered", "output": "output.wav", "effects": "tremolo,delay"},
            json.loads(out),
        )
        self.assertEqual(b"RIFFstub", (self.workspace / "output.wav").read_bytes())
        self.assertIn("\n", (self.workspace / "preset.json").read_text())

    def test_existing_output_is_not_modified(self) -> None:
        (self.workspace / "output.wav").write_bytes(b"original")
        code, out, error = self.cli(
            "dsp", "render", "input.wav", "--output", "output.wav",
            "--engine", str(self.engine),
        )
        self.assertEqual(65, code)
        self.assertEqual("", out)
        self.assertIn("already exists", error)
        self.assertEqual(b"original", (self.workspace / "output.wav").read_bytes())

    def test_invalid_preset_fails_before_engine_invocation(self) -> None:
        document = json.loads((self.workspace / "preset.json").read_text())
        document["parameters"]["delay.feedback_milli"] = 999
        (self.workspace / "preset.json").write_text(json.dumps(document))
        code, out, error = self.cli(
            "render", "input.wav", "--output", "output.wav",
            "--preset", "preset.json", "--engine", str(self.engine),
        )
        self.assertEqual(65, code)
        self.assertEqual("", out)
        self.assertIn("delay.feedback_milli", error)
        self.assertFalse((self.workspace / "output.wav").exists())

    def test_parent_traversal_and_symlink_escape_fail_closed(self) -> None:
        for path in ("../input.wav", "/tmp/input.wav"):
            code, out, error = self.cli(
                "render", path, "--output", "output.wav",
                "--engine", str(self.engine),
            )
            self.assertEqual(65, code, error)
            self.assertEqual("", out)
        outside = self.workspace.parent / ("outside-" + self.workspace.name + ".wav")
        try:
            outside.write_bytes(b"RIFF")
            (self.workspace / "linked.wav").symlink_to(outside)
            code, out, error = self.cli(
                "render", "linked.wav", "--output", "output.wav",
                "--engine", str(self.engine),
            )
            self.assertEqual(65, code)
            self.assertEqual("", out)
            self.assertIn("escapes workspace", error)
        finally:
            outside.unlink(missing_ok=True)

    def test_missing_engine_is_explicit_unavailable(self) -> None:
        code, out, error = self.cli(
            "render", "input.wav", "--output", "output.wav",
            "--engine", str(self.workspace / "not-installed"),
        )
        self.assertEqual(69, code)
        self.assertEqual("", out)
        self.assertIn("DSP engine unavailable", error)

    def test_engine_failure_produces_no_success_message(self) -> None:
        self.engine.write_text(
            "#!" + sys.executable + "\nimport sys\nprint('bad DSP', file=sys.stderr)\nsys.exit(9)\n",
            encoding="utf-8",
        )
        code, out, error = self.cli(
            "render", "input.wav", "--output", "output.wav",
            "--engine", str(self.engine),
        )
        self.assertEqual(65, code)
        self.assertEqual("", out)
        self.assertIn("bad DSP", error)


if __name__ == "__main__":
    unittest.main()
