from pathlib import Path
import unittest


class FlakeContractTests(unittest.TestCase):
    def _flake_text(self) -> str:
        flake = Path("flake.nix")
        self.assertTrue(flake.is_file(), "flake.nix must exist")
        return flake.read_text()

    def test_full_guitar_toolchain_is_declared(self) -> None:
        text = self._flake_text()
        for package in (
            "python312",
            "ruff",
            "musescore",
            "fluidsynth",
            "ffmpeg",
            "soundfont-fluid",
        ):
            self.assertIn(package, text)

    def test_soundfont_environment_is_declared(self) -> None:
        text = self._flake_text()
        self.assertIn("GUITAR_SOUNDFONT", text)
        self.assertIn("FluidR3_GM2-2.sf2", text)


class FlakePythonEnvironmentTests(unittest.TestCase):
    def test_python_environment_includes_ruff_module(self) -> None:
        text = Path("flake.nix").read_text()
        self.assertIn("ps.ruff", text)


if __name__ == "__main__":
    unittest.main()
