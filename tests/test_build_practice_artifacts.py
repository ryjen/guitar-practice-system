from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from guitar_practice.adapters.workspace_tree import WorkspaceFileTree
from guitar_practice.application.practice_bundle import PracticeBundleBuilder

ROOT = Path(__file__).resolve().parents[1]


def iter_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file())


class PracticeBundleTests(unittest.TestCase):
    def test_bundle_is_reproducible_and_self_describing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "first"
            second = root / "second"
            source_sha = "0123456789abcdef0123456789abcdef01234567"
            builder = PracticeBundleBuilder(WorkspaceFileTree(ROOT))

            builder.build(str(first), source_sha=source_sha)
            builder.build(str(second), source_sha=source_sha)

            first_files = {
                str(path.relative_to(first)): path.read_bytes()
                for path in iter_files(first)
            }
            second_files = {
                str(path.relative_to(second)): path.read_bytes()
                for path in iter_files(second)
            }
            self.assertEqual(first_files, second_files)

            provenance = json.loads((first / "provenance.json").read_text())
            self.assertEqual(provenance["sourceGitSha"], source_sha)
            self.assertEqual("0.1.0", provenance["projectVersion"])
            self.assertEqual(1, provenance["versionedContracts"]["practice-data"])
            self.assertEqual(1, provenance["versionedContracts"]["guitar-dsp.preset"])
            self.assertIn("pyproject.toml", provenance["generatorInputs"])
            self.assertIn(
                "guitar_practice/application/practice_bundle.py",
                provenance["generatorInputs"],
            )
            self.assertIn(
                "guitar_practice/application/practice_data_export.py",
                provenance["generatorInputs"],
            )
            self.assertIn(
                "guitar_practice/domain/practice_data.py",
                provenance["generatorInputs"],
            )
            self.assertIn(
                "guitar_practice/application/generation.py",
                provenance["generatorInputs"],
            )
            self.assertIn(
                "guitar_practice/domain/backing.py",
                provenance["generatorInputs"],
            )
            self.assertIn(
                "guitar_practice/domain/midi.py",
                provenance["generatorInputs"],
            )
            self.assertIn(
                "catalogs/progressions/catalog.json",
                provenance["artifacts"],
            )
            self.assertIn(
                "contracts/progressions/progression-catalog.schema.json",
                provenance["artifacts"],
            )
            self.assertIn(
                "generated/backing-tracks/slide-slow-blues-a-60.mid",
                provenance["artifacts"],
            )
            self.assertIn(
                "generated/backing-tracks/call-response-gap-em-92.mid",
                provenance["artifacts"],
            )
            self.assertIn(
                "generated/backing-tracks/jazz-blues-12-c-110.mid",
                provenance["artifacts"],
            )
            self.assertTrue((first / "contracts/dsp/guitar-dsp-preset-v1.schema.json").exists())
            self.assertTrue((first / "exports/practice-data.json").exists())
            self.assertTrue((first / "SHA256SUMS").exists())

    def test_source_sha_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                PracticeBundleBuilder(
                    WorkspaceFileTree(ROOT)
                ).build(
                    str(Path(tmp) / "bundle"),
                    source_sha="   ",
                )


if __name__ == "__main__":
    unittest.main()
