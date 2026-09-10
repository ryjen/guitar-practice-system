from __future__ import annotations

import unittest

from guitar_practice.application.ai import ProposalStatus, may_mutate_canonical_state
from guitar_practice.interfaces.cli.commands import command_paths
from guitar_practice.interfaces.cli.main import main


class CommandRegistryTests(unittest.TestCase):
    def test_command_paths_are_unique(self) -> None:
        paths = tuple(command_paths())
        self.assertEqual(len(paths), len(set(paths)))

    def test_expected_capability_roots_exist(self) -> None:
        roots = {path[0] for path in command_paths()}
        self.assertTrue(
            {"session", "schedule", "assess", "discover", "progression", "backing", "midi", "export", "validate"}
            <= roots
        )

    def test_missing_command_is_usage_error(self) -> None:
        self.assertEqual(main([]), 2)


class AiBoundaryTests(unittest.TestCase):
    def test_only_approved_proposals_can_mutate_canonical_state(self) -> None:
        self.assertFalse(may_mutate_canonical_state(ProposalStatus.PROPOSED))
        self.assertFalse(may_mutate_canonical_state(ProposalStatus.VALIDATED))
        self.assertFalse(may_mutate_canonical_state(ProposalStatus.REJECTED))
        self.assertTrue(may_mutate_canonical_state(ProposalStatus.APPROVED))


if __name__ == "__main__":
    unittest.main()
