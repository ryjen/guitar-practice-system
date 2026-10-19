from __future__ import annotations

import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from guitar_practice.domain import backing, midi
from guitar_practice.interfaces.cli.commands import MigrationState, find_command
from guitar_practice.interfaces.cli.main import main

ROOT = Path(__file__).resolve().parents[1]


class NativeMidiCliTests(unittest.TestCase):
    def test_midi_commands_are_native(self) -> None:
        for tokens in (
            ["midi", "generate"],
            ["midi", "validate"],
            ["midi", "generate-exercises"],
        ):
            command, consumed = find_command(tokens)
            self.assertIsNotNone(command)
            assert command is not None
            self.assertEqual(len(tokens), consumed)
            self.assertEqual(MigrationState.NATIVE, command.migration)
            self.assertIsNotNone(command.native_handler)
            self.assertIsNone(command.legacy)

    def test_generate_and_validate_run_without_repository_scripts(self) -> None:
        manifest = json.loads(
            (
                ROOT
                / "backing-tracks"
                / "slide-slow-blues"
                / "manifest.json"
            ).read_text(encoding="utf-8")
        )
        expected_bytes = midi.render(manifest)
        expected_report = midi.validate_rendered(manifest, expected_bytes)

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "manifest.json").write_text(
                json.dumps(manifest),
                encoding="utf-8",
            )

            generate_stdout = io.StringIO()
            generate_stderr = io.StringIO()
            with contextlib.redirect_stdout(generate_stdout), contextlib.redirect_stderr(
                generate_stderr
            ):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "midi",
                        "generate",
                        "manifest.json",
                        "output.mid",
                    ]
                )

            self.assertEqual(0, result)
            self.assertEqual(expected_report, json.loads(generate_stdout.getvalue()))
            self.assertEqual("", generate_stderr.getvalue())
            self.assertEqual(expected_bytes, (workspace / "output.mid").read_bytes())
            self.assertFalse((workspace / "scripts").exists())

            validate_stdout = io.StringIO()
            validate_stderr = io.StringIO()
            with contextlib.redirect_stdout(validate_stdout), contextlib.redirect_stderr(
                validate_stderr
            ):
                validate_result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "midi",
                        "validate",
                        "manifest.json",
                        "output.mid",
                    ]
                )

            self.assertEqual(0, validate_result)
            self.assertEqual(expected_report, json.loads(validate_stdout.getvalue()))
            self.assertEqual("", validate_stderr.getvalue())
            self.assertEqual(
                hashlib.sha256(expected_bytes).hexdigest(),
                hashlib.sha256((workspace / "output.mid").read_bytes()).hexdigest(),
            )

    def test_authored_backing_round_trip_preserves_drums_and_sparse_bass(self) -> None:
        manifest = json.loads(
            (ROOT / "backing-tracks/riverside-blues-video/manifest.json")
            .read_text(encoding="utf-8")
        )
        catalog = json.loads(
            (ROOT / "catalogs/grooves/catalog.json").read_text(encoding="utf-8")
        )
        reference = backing.render(manifest, catalog)
        generic = midi.render(manifest)
        self.assertNotEqual(generic, reference, "generic renderer must not erase authored parts")

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            catalog_path = workspace / "catalogs" / "grooves" / "catalog.json"
            catalog_path.parent.mkdir(parents=True)
            catalog_path.write_text(json.dumps(catalog), encoding="utf-8")

            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                status = main([
                    "--workspace", str(workspace), "midi", "generate",
                    "manifest.json", "riverside.mid",
                ])
            self.assertEqual(0, status)
            self.assertEqual(reference, (workspace / "riverside.mid").read_bytes())

            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(0, main([
                    "--workspace", str(workspace), "midi", "validate",
                    "manifest.json", "riverside.mid",
                ]))

            # Legacy rendering passes structural inspection but not authored
            # musical-content inspection. It must be rejected by the CLI.
            midi.validate_rendered(manifest, generic)
            (workspace / "stripped.mid").write_bytes(generic)
            diagnostics = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(diagnostics):
                status = main([
                    "--workspace", str(workspace), "midi", "validate",
                    "manifest.json", "stripped.mid",
                ])
            self.assertEqual(65, status)
            self.assertIn("MIDI note content differs", diagnostics.getvalue())

            # Missing groove metadata must fail before creating any MIDI file.
            catalog_path.unlink()
            diagnostics = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(diagnostics):
                status = main([
                    "--workspace", str(workspace), "midi", "generate",
                    "manifest.json", "missing-catalog.mid",
                ])
            self.assertEqual(65, status)
            self.assertFalse((workspace / "missing-catalog.mid").exists())

    def test_malformed_section_override_cannot_fall_back_to_generic_renderer(self) -> None:
        manifest = json.loads(
            (ROOT / "backing-tracks/slide-slow-blues/manifest.json")
            .read_text(encoding="utf-8")
        )
        manifest["sections"][0]["drum_fills"] = [
            {"bar": 1, "hits": [{"instrument": "invalid", "step": 0, "velocity": 96}]}
        ]
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            catalog_path = workspace / "catalogs" / "grooves" / "catalog.json"
            catalog_path.parent.mkdir(parents=True)
            catalog_path.write_text(
                (ROOT / "catalogs/grooves/catalog.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            errors = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(errors):
                status = main([
                    "--workspace", str(workspace), "midi", "generate",
                    "manifest.json", "invalid.mid",
                ])
            self.assertEqual(65, status)
            self.assertFalse((workspace / "invalid.mid").exists())
            self.assertIn("drum_fills", errors.getvalue())



if __name__ == "__main__":
    unittest.main()
