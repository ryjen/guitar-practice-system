from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LayeringTests(unittest.TestCase):
    def test_domain_has_no_outward_dependencies(self) -> None:
        forbidden = {
            "argparse",
            "subprocess",
            "requests",
            "urllib",
            "httpx",
            "openai",
            "anthropic",
            "guitar_practice.adapters",
            "guitar_practice.interfaces",
        }
        violations: list[str] = []
        for path in (ROOT / "guitar_practice" / "domain").glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                names: list[str] = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                for name in names:
                    if any(name == item or name.startswith(f"{item}.") for item in forbidden):
                        violations.append(f"{path.relative_to(ROOT)} imports {name}")
        self.assertEqual([], violations)


if __name__ == "__main__":
    unittest.main()
