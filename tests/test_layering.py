from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "guitar_practice"


def imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def violations(layer: str, forbidden: set[str]) -> list[str]:
    findings: list[str] = []
    for path in (PACKAGE / layer).glob("*.py"):
        for name in imported_modules(path):
            if any(name == item or name.startswith(f"{item}.") for item in forbidden):
                findings.append(f"{path.relative_to(ROOT)} imports {name}")
    return findings


class LayeringTests(unittest.TestCase):
    def test_domain_points_only_inward(self) -> None:
        self.assertEqual(
            [],
            violations(
                "domain",
                {
                    "argparse",
                    "subprocess",
                    "guitar_practice.application",
                    "guitar_practice.adapters",
                    "guitar_practice.interfaces",
                },
            ),
        )

    def test_application_does_not_depend_on_adapters_or_interfaces(self) -> None:
        self.assertEqual(
            [],
            violations(
                "application",
                {
                    "argparse",
                    "subprocess",
                    "guitar_practice.adapters",
                    "guitar_practice.interfaces",
                },
            ),
        )

    def test_adapters_do_not_depend_on_interfaces(self) -> None:
        self.assertEqual(
            [],
            violations("adapters", {"guitar_practice.interfaces"}),
        )


if __name__ == "__main__":
    unittest.main()
