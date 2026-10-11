from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
ANY_ACTION = re.compile(r"uses:\s+[^@\s]+@([^\s#]+)")
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


class ReleaseWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = WORKFLOW.read_text(encoding="utf-8")

    def test_release_triggers_only_for_version_tags(self) -> None:
        self.assertIn('tags:\n      - "v*"', self.text)
        self.assertNotIn("workflow_dispatch:", self.text)
        self.assertNotIn("branches:", self.text)

    def test_third_party_actions_are_pinned_by_full_sha(self) -> None:
        refs = ANY_ACTION.findall(self.text)
        self.assertTrue(refs)
        self.assertTrue(all(FULL_SHA.fullmatch(ref) for ref in refs))

    def test_validation_is_read_only_and_only_publisher_can_write(self) -> None:
        self.assertIn("permissions:\n  contents: read", self.text)
        self.assertEqual(1, self.text.count("contents: write"))
        validate = self.text.split("  validate-release:", 1)[1].split(
            "  publish-release:", 1
        )[0]
        publish = self.text.split("  publish-release:", 1)[1]
        self.assertNotIn("contents: write", validate)
        self.assertIn("permissions:\n      contents: write", publish)
        self.assertIn("needs: validate-release", publish)

    def test_no_workflow_uses_actions_artifact_storage(self) -> None:
        for path in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertNotIn("actions/upload-artifact", text)
                self.assertNotIn("actions/download-artifact", text)

    def test_release_verifies_identity_validation_replay_and_checksums(self) -> None:
        for required in (
            'test "${GITHUB_REF_TYPE}" = "tag"',
            'test "$(git rev-parse HEAD)" = "${GITHUB_SHA}"',
            'test "$(git rev-list -n 1 "${GITHUB_REF_NAME}")" = "${GITHUB_SHA}"',
            "guitarctl validate repo",
            "guitarctl release prepare",
            "guitarctl release verify",
            "diff -qr generated/release generated/release-replay",
            "sha256sum -c",
            "gh release create",
            "--verify-tag",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.text)

    def test_material_change_scope_covers_public_release_inputs(self) -> None:
        for path in (
            "backing-tracks",
            "catalogs/grooves",
            "catalogs/progressions",
            "catalogs/practice-data.json",
            "contracts/backing-tracks",
            "contracts/progressions",
            "contracts/dsp",
        ):
            with self.subTest(path=path):
                self.assertIn(path, self.text)


if __name__ == "__main__":
    unittest.main()
