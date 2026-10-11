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

    def test_repository_validation_uses_canonical_package_command(self) -> None:
        text = Path("flake.nix").read_text()
        self.assertIn("checks.${system}.repository-validation", text)
        self.assertIn("guitarctl validate repo", text)
        self.assertIn("cp -R ${self} source", text)
        self.assertIn('export PYTHONPATH="$PWD"', text)

    def test_existing_nix_workflow_proves_flake_check(self) -> None:
        workflow = Path(".github/workflows/validate-score-musicxml.yml").read_text()
        self.assertIn(
            "nix build --no-write-lock-file --no-link --print-build-logs "
            ".#checks.x86_64-linux.repository-validation",
            workflow,
        )

    def test_dev_shell_exposes_package_native_guitarctl(self) -> None:
        text = Path("flake.nix").read_text()
        self.assertIn("writeShellApplication", text)
        self.assertIn('name = "guitarctl"', text)
        self.assertIn("python -m guitar_practice.interfaces.cli.main", text)


if __name__ == "__main__":
    unittest.main()
