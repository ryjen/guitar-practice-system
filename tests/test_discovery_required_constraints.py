from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "discovery_catalog.py"
SPEC = importlib.util.spec_from_file_location("discovery_catalog_required", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
discovery = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = discovery
SPEC.loader.exec_module(discovery)


class RequiredConstraintTests(unittest.TestCase):
    def test_required_list_constraint_needs_a_value(self) -> None:
        request = {
            "target_type": "song",
            "goal": "Find a song",
            "required_constraints": ["genres"],
            "constraints": {},
        }

        with self.assertRaises(discovery.DiscoveryError):
            discovery.validate_request(request)

    def test_required_scalar_constraint_needs_a_nonempty_value(self) -> None:
        request = {
            "target_type": "backing-track",
            "goal": "Find a backing track",
            "required_constraints": ["meter"],
            "constraints": {"meter": ""},
        }

        with self.assertRaises(discovery.DiscoveryError):
            discovery.validate_request(request)

    def test_required_tempo_constraint_needs_a_range(self) -> None:
        request = {
            "target_type": "backing-track",
            "goal": "Find a backing track",
            "required_constraints": ["tempo_bpm"],
            "constraints": {},
        }

        with self.assertRaises(discovery.DiscoveryError):
            discovery.validate_request(request)

    def test_boolean_numeric_values_are_rejected(self) -> None:
        request = {
            "target_type": "backing-track",
            "goal": "Find a backing track",
            "limit": True,
            "constraints": {},
        }

        with self.assertRaises(discovery.DiscoveryError):
            discovery.validate_request(request)


if __name__ == "__main__":
    unittest.main()
