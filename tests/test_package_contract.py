from __future__ import annotations

import importlib
import unittest


class PackageContractTests(unittest.TestCase):
    def test_cli_module_imports_without_optional_providers(self) -> None:
        module = importlib.import_module("guitar_practice.interfaces.cli.main")
        self.assertTrue(callable(module.main))


if __name__ == "__main__":
    unittest.main()
