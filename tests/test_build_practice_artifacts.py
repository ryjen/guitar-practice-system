from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_practice_artifacts  # noqa: E402


class PracticeBundleTests(unittest.TestCase):
    def test_bundle_is_reproducible_and_self_describing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "first"
            second = root / "second"
            source_sha = "0123456789abcdef0123456789abcdef01234567"

            build_practice_artifacts.build_bundle(first, source_sha)
            build_practice_artifacts.build_bundle(second, source_sha)

            first_files = {
                str(path.relative_to(first)): path.read_bytes()
                for path in build_practice_artifacts.iter_files(first)
            }
            second_files = {
                str(path.relative_to(second)): path.read_bytes()
                for path in build_practice_artifacts.iter_files(second)
            }
            self.assertEqual(first_files, second_files)

            provenance = json.loads((first / "provenance.json").read_text())
            self.assertEqual(provenance["sourceGitSha"], source_sha)
            self.assertIn("scripts/backing_track_engine.py", provenance["generatorInputs"])
            self.assertIn("scripts/generate_backing_tracks.py", provenance["generatorInputs"])
            self.assertIn(
                "generated/backing-tracks/slide-slow-blues-a-60.mid",
                provenance["artifacts"],
            )
            self.assertIn(
                "generated/backing-tracks/call-response-gap-em-92.mid",
                provenance["artifacts"],
            )
            self.assertTrue((first / "exports/practice-data.json").exists())
            self.assertTrue((first / "SHA256SUMS").exists())

    def test_source_sha_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                build_practice_artifacts.build_bundle(Path(tmp) / "bundle", "   ")


if __name__ == "__main__":
    unittest.main()
