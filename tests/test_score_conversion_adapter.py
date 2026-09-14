from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from guitar_practice.adapters.score_conversion import (
    DirectMusicXmlConverter,
    MuseScoreConverter,
    ScoreConversionError,
)

FIXTURE = Path(__file__).parent / "fixtures" / "musicxml" / "multitrack.musicxml"


class ScoreConversionAdapterTests(unittest.TestCase):
    def test_direct_musicxml_reads_only_inside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            source = workspace / "input.musicxml"
            source.write_bytes(FIXTURE.read_bytes())

            converted = DirectMusicXmlConverter(workspace).convert("input.musicxml")

            self.assertEqual(FIXTURE.read_bytes(), converted.musicxml)
            self.assertEqual("direct-musicxml", converted.converter)
            self.assertIsNone(converted.converter_version)

    def test_direct_musicxml_rejects_workspace_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            workspace = Path(directory)
            external = Path(outside) / "outside.musicxml"
            external.write_bytes(FIXTURE.read_bytes())
            with self.assertRaises(ScoreConversionError):
                DirectMusicXmlConverter(workspace).convert(str(external))

    def test_musescore_uses_argv_without_shell_and_bounded_temp_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            source = workspace / "song.gp5"
            source.write_bytes(b"guitar-pro-fixture")
            calls: list[tuple[list[str], dict[str, object]]] = []

            def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                calls.append((argv, kwargs))
                if argv[-1] == "--version":
                    return subprocess.CompletedProcess(argv, 0, stdout="MuseScore Studio 4.5.2\n", stderr="")
                output = Path(argv[2])
                self.assertTrue(output.is_relative_to(workspace))
                output.write_bytes(FIXTURE.read_bytes())
                return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

            with mock.patch("guitar_practice.adapters.score_conversion.subprocess.run", side_effect=fake_run):
                converted = MuseScoreConverter(workspace, executable="MuseScore4").convert("song.gp5")

            conversion_argv, conversion_kwargs = calls[-1]
            self.assertEqual("MuseScore4", conversion_argv[0])
            self.assertEqual("-o", conversion_argv[1])
            self.assertEqual(str(source.resolve()), conversion_argv[3])
            self.assertFalse(conversion_kwargs["shell"])
            self.assertTrue(conversion_kwargs["capture_output"])
            self.assertEqual(FIXTURE.read_bytes(), converted.musicxml)
            self.assertEqual("musescore", converted.converter)
            self.assertIn("4.5.2", converted.converter_version or "")

    def test_musescore_failure_is_distinct_conversion_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "song.gp").write_bytes(b"fixture")

            def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                if argv[-1] == "--version":
                    return subprocess.CompletedProcess(argv, 0, stdout="MuseScore 4", stderr="")
                return subprocess.CompletedProcess(argv, 7, stdout="", stderr="bad score")

            with mock.patch("guitar_practice.adapters.score_conversion.subprocess.run", side_effect=fake_run):
                with self.assertRaises(ScoreConversionError):
                    MuseScoreConverter(workspace).convert("song.gp")

    def test_musescore_rejects_source_escape_before_process_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            workspace = Path(directory)
            source = Path(outside) / "song.gp"
            source.write_bytes(b"fixture")
            with mock.patch("guitar_practice.adapters.score_conversion.subprocess.run") as run:
                with self.assertRaises(ScoreConversionError):
                    MuseScoreConverter(workspace).convert(str(source))
                run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
