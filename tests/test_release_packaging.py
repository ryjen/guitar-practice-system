from __future__ import annotations

import contextlib
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path

from guitar_practice.adapters.workspace_tree import WorkspaceFileTree
from guitar_practice.application.release import ReleasePackager
from guitar_practice.domain import release
from guitar_practice.interfaces.cli.main import main

ROOT = Path(__file__).resolve().parents[1]
TAG = "v0.1.0"
SOURCE_SHA = "0123456789abcdef0123456789abcdef01234567"


def _files(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class ReleaseDomainTests(unittest.TestCase):
    def test_identity_requires_matching_semver_tag_and_full_sha(self) -> None:
        release.validate_identity(TAG, "0.1.0", SOURCE_SHA)
        for tag, version, sha in (
            ("0.1.0", "0.1.0", SOURCE_SHA),
            ("v0.2.0", "0.1.0", SOURCE_SHA),
            (TAG, "0.1.0", "abc"),
            (TAG, "0.1.0", SOURCE_SHA.upper()),
        ):
            with self.subTest(tag=tag, version=version, sha=sha):
                with self.assertRaises(release.ReleaseError):
                    release.validate_identity(tag, version, sha)

    def test_material_changes_are_bounded_sorted_and_deduplicated(self) -> None:
        result = release.material_changes(
            [
                "contracts/backing-tracks/groove-spec.schema.json",
                "backing-tracks/slide-slow-blues/manifest.json",
                "catalogs/grooves/catalog.json",
                "backing-tracks/slide-slow-blues/manifest.json",
                "catalogs/practice-data.json",
                "docs/ignored.md",
            ]
        )
        self.assertEqual(
            (
                "backing-tracks/slide-slow-blues/manifest.json",
                "catalogs/grooves/catalog.json",
            ),
            result["backing_tracks"],
        )
        self.assertEqual(
            (
                "catalogs/practice-data.json",
                "contracts/backing-tracks/groove-spec.schema.json",
            ),
            result["contracts"],
        )
        with self.assertRaises(release.ReleaseError):
            release.material_changes(["../private.txt"])


class ReleasePackagerTests(unittest.TestCase):
    def test_prepare_is_reproducible_and_self_verifying(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            changes = root / "changes.txt"
            changes.write_text(
                "backing-tracks/slide-slow-blues/manifest.json\n"
                "contracts/dsp/guitar-dsp-preset-v1.schema.json\n",
                encoding="utf-8",
            )
            builder = ReleasePackager(WorkspaceFileTree(ROOT))
            first = root / "first"
            second = root / "second"

            first_result = builder.prepare(
                str(first),
                tag=TAG,
                source_sha=SOURCE_SHA,
                previous_tag="v0.0.9",
                changed_paths_path=str(changes),
            )
            builder.prepare(
                str(second),
                tag=TAG,
                source_sha=SOURCE_SHA,
                previous_tag="v0.0.9",
                changed_paths_path=str(changes),
            )

            self.assertEqual(_files(first), _files(second))
            self.assertEqual("prepared", first_result["status"])
            self.assertEqual(TAG, first_result["tag"])
            self.assertEqual(SOURCE_SHA, first_result["source_sha"])
            verification = builder.verify(
                str(first), tag=TAG, source_sha=SOURCE_SHA
            )
            self.assertEqual("verified", verification["status"])
            self.assertEqual(
                first_result["archive_sha256"], verification["archive_sha256"]
            )

            bundle = first / f"guitar-practice-system-{TAG}"
            provenance = json.loads((bundle / "provenance.json").read_text())
            self.assertEqual(TAG, provenance["sourceGitTag"])
            self.assertEqual(SOURCE_SHA, provenance["sourceGitSha"])
            self.assertEqual("0.1.0", provenance["projectVersion"])
            self.assertEqual(1, provenance["versionedContracts"]["practice-data"])
            self.assertEqual(1, provenance["versionedContracts"]["guitar-dsp.preset"])
            self.assertIn("pyproject.toml", provenance["generatorInputs"])
            self.assertIn(
                "guitar_practice/application/practice_bundle.py",
                provenance["generatorInputs"],
            )

            notes = (first / "RELEASE.md").read_text()
            self.assertIn("v0.0.9", notes)
            self.assertIn("--previous-tag v0.0.9", notes)
            self.assertIn("slide-slow-blues/manifest.json", notes)
            self.assertIn("guitar-dsp-preset-v1.schema.json", notes)
            self.assertIn("guitarctl release prepare", notes)
            self.assertIn("guitarctl release verify", notes)

            archive_path = first / f"guitar-practice-system-{TAG}.tar"
            with tarfile.open(archive_path, mode="r:") as archive:
                members = archive.getmembers()
                self.assertEqual(
                    [member.name for member in members],
                    sorted(member.name for member in members),
                )
                self.assertTrue(members)
                self.assertTrue(all(member.mtime == 0 for member in members))
                self.assertTrue(
                    all(member.uid == 0 and member.gid == 0 for member in members)
                )
                names = {member.name for member in members}
                prefix = f"guitar-practice-system-{TAG}/"
                self.assertIn(prefix + "provenance.json", names)
                self.assertIn(prefix + "SHA256SUMS", names)
                self.assertIn(prefix + "contracts/dsp/guitar-dsp-preset-v1.schema.json", names)
                self.assertIn(
                    prefix + "generated/backing-tracks/slide-slow-blues-a-60.mid",
                    names,
                )

    def test_verify_fails_closed_when_archive_or_bundle_is_tampered(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            builder = ReleasePackager(WorkspaceFileTree(ROOT))
            output = root / "release"
            builder.prepare(str(output), tag=TAG, source_sha=SOURCE_SHA)

            archive = output / f"guitar-practice-system-{TAG}.tar"
            original_archive = archive.read_bytes()
            archive.write_bytes(original_archive + b"tamper")
            with self.assertRaisesRegex(release.ReleaseError, "checksum"):
                builder.verify(str(output), tag=TAG, source_sha=SOURCE_SHA)

            archive.write_bytes(original_archive)
            checksum = output / f"guitar-practice-system-{TAG}.tar.sha256"
            import hashlib

            checksum.write_text(
                f"{hashlib.sha256(original_archive).hexdigest()}  {archive.name}\n",
                encoding="utf-8",
            )
            bundle_file = (
                output
                / f"guitar-practice-system-{TAG}"
                / "exports"
                / "practice-data.json"
            )
            bundle_file.write_text("{}\n", encoding="utf-8")
            with self.assertRaises(release.ReleaseError):
                builder.verify(str(output), tag=TAG, source_sha=SOURCE_SHA)

    def test_cli_prepare_and_verify_and_workspace_boundaries(self) -> None:
        output = "generated/test-versioned-release"
        target = ROOT / output
        try:
            prepare_out = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(prepare_out), contextlib.redirect_stderr(
                stderr
            ):
                result = main(
                    [
                        "--workspace",
                        str(ROOT),
                        "release",
                        "prepare",
                        "--tag",
                        TAG,
                        "--source-sha",
                        SOURCE_SHA,
                        "--output-dir",
                        output,
                    ]
                )
            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            self.assertEqual("prepared", json.loads(prepare_out.getvalue())["status"])

            verify_out = io.StringIO()
            with contextlib.redirect_stdout(verify_out), contextlib.redirect_stderr(
                io.StringIO()
            ):
                result = main(
                    [
                        "--workspace",
                        str(ROOT),
                        "release",
                        "verify",
                        "--tag",
                        TAG,
                        "--source-sha",
                        SOURCE_SHA,
                        "--output-dir",
                        output,
                    ]
                )
            self.assertEqual(0, result)
            self.assertEqual("verified", json.loads(verify_out.getvalue())["status"])
        finally:
            if target.exists():
                import shutil

                shutil.rmtree(target)

        with tempfile.TemporaryDirectory() as directory:
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        directory,
                        "release",
                        "prepare",
                        "--tag",
                        TAG,
                        "--source-sha",
                        SOURCE_SHA,
                        "--output-dir",
                        "../release",
                    ]
                )
            self.assertEqual(65, result)
            self.assertEqual("", stdout.getvalue())
            self.assertIn("workspace-relative", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
