from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from guitar_practice.adapters.binary_files import BinaryArtifactError, BinaryFileStore


class BinaryFileStoreTests(unittest.TestCase):
    def test_round_trip_is_workspace_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            store = BinaryFileStore(workspace)

            store.write_bytes("generated/test.bin", b"payload")

            self.assertEqual(b"payload", store.read_bytes("generated/test.bin"))
            self.assertEqual(
                b"payload",
                (workspace / "generated" / "test.bin").read_bytes(),
            )

    def test_absolute_path_inside_workspace_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            store = BinaryFileStore(workspace)
            path = workspace / "generated" / "test.bin"

            store.write_bytes(str(path), b"payload")

            self.assertEqual(b"payload", path.read_bytes())

    def test_workspace_escape_is_rejected_for_read_and_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "workspace"
            workspace.mkdir()
            store = BinaryFileStore(workspace)

            with self.assertRaisesRegex(BinaryArtifactError, "inside workspace"):
                store.write_bytes("../escape.bin", b"payload")
            with self.assertRaisesRegex(BinaryArtifactError, "inside workspace"):
                store.read_bytes("../escape.bin")


if __name__ == "__main__":
    unittest.main()
