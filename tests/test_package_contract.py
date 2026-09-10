from __future__ import annotations

import importlib
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PackageContractTests(unittest.TestCase):
    def test_cli_module_is_importable(self) -> None:
        module = importlib.import_module("guitar_practice.interfaces.cli.main")
        self.assertTrue(callable(module.main))

    def test_pyproject_publishes_guitarctl_entrypoint(self) -> None:
        config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(
            "guitar_practice.interfaces.cli.main:main",
            config["project"]["scripts"]["guitarctl"],
        )


if __name__ == "__main__":
    unittest.main()
