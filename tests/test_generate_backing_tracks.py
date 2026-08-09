from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

MODULE_PATH = SCRIPTS / "generate_backing_tracks.py"
SPEC = importlib.util.spec_from_file_location("generate_backing_tracks", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
generate_backing_tracks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generate_backing_tracks)


class GenerateBackingTracksTests(unittest.TestCase):
    def test_generate_all_uses_manifest_output_paths_and_validates_outputs(self) -> None:
        manifests = generate_backing_tracks.discover_manifests()
        self.assertGreaterEqual(len(manifests), 5)

        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            results = generate_backing_tracks.generate_all(repo_root=repo_root)

            self.assertEqual(len(manifests), len(results))
            for result in results:
                output = repo_root / result["output"]
                self.assertTrue(output.is_file())
                self.assertEqual(".mid", output.suffix)
                self.assertGreaterEqual(result["tracks"], 2)
                self.assertEqual("COUNT-IN", result["markers"][0])
                self.assertEqual("END", result["markers"][-1])

    def test_manifest_output_path_rejects_repository_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_dir = root / "backing-tracks" / "bad"
            manifest_dir.mkdir(parents=True)
            manifest = manifest_dir / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "id": "bad",
                        "outputs": {"midi": "../outside.mid"},
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(generate_backing_tracks.midi_workflow.ManifestError):
                generate_backing_tracks.manifest_output_path(manifest, root)

    def test_manifest_output_filename_must_match_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_dir = root / "backing-tracks" / "bad-name"
            manifest_dir.mkdir(parents=True)
            manifest = manifest_dir / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "id": "expected-name",
                        "outputs": {
                            "midi": "generated/backing-tracks/wrong-name.mid"
                        },
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(generate_backing_tracks.midi_workflow.ManifestError):
                generate_backing_tracks.manifest_output_path(manifest, root)


if __name__ == "__main__":
    unittest.main()
