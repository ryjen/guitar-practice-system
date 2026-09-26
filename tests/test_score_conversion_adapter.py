from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from guitar_practice.adapters.score_conversion import (
    DirectMusicXmlConverter,
    MuseScoreConverter,
    ScoreConversionError,
)


class ScoreConversionAdapterTests(unittest.TestCase):
    def test_direct_musicxml_converter_is_workspace_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            source = workspace / "score.musicxml"
            source.write_text("<score-partwise/>", encoding="utf-8")

            converted = DirectMusicXmlConverter(workspace).convert("score.musicxml")

            self.assertEqual(b"<score-partwise/>", converted.musicxml)
            self.assertEqual("direct-musicxml", converted.converter)

            with self.assertRaisesRegex(ScoreConversionError, "inside workspace"):
                DirectMusicXmlConverter(workspace).convert("../score.musicxml")

    def test_musescore_version_timeout_is_nonfatal_provenance_loss(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            converter = MuseScoreConverter(Path(directory), version_timeout_seconds=1)
            with patch(
                "guitar_practice.adapters.score_conversion.subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd=["mscore", "--version"], timeout=1),
            ) as run:
                self.assertIsNone(converter._version())

            self.assertEqual(1, run.call_count)
            self.assertEqual(1, run.call_args.kwargs["timeout"])
            self.assertFalse(run.call_args.kwargs["shell"])

    def test_musescore_conversion_timeout_fails_boundedly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "song.gp5").write_bytes(b"fixture")
            converter = MuseScoreConverter(
                workspace,
                version_timeout_seconds=2,
                conversion_timeout_seconds=3,
            )
            calls = [
                subprocess.CompletedProcess(
                    args=["mscore", "--version"],
                    returncode=0,
                    stdout="MuseScore 4\n",
                    stderr="",
                ),
                subprocess.TimeoutExpired(cmd=["mscore"], timeout=3),
            ]
            with patch(
                "guitar_practice.adapters.score_conversion.subprocess.run",
                side_effect=calls,
            ) as run:
                with self.assertRaisesRegex(ScoreConversionError, "timed out|Timeout"):
                    converter.convert("song.gp5")

            self.assertEqual(2, run.call_count)
            self.assertEqual(2, run.call_args_list[0].kwargs["timeout"])
            self.assertEqual(3, run.call_args_list[1].kwargs["timeout"])
            self.assertFalse(run.call_args_list[1].kwargs["shell"])


if __name__ == "__main__":
    unittest.main()
