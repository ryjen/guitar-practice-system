from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from guitar_practice.adapters.legacy import (
    LegacyCommandError,
    compose_argv,
    run_script,
)


class LegacyAdapterTests(unittest.TestCase):
    def test_fixed_subcommand_follows_registered_parent_options(self) -> None:
        self.assertEqual(
            ["--catalog", "custom.json", "show", "shuffle"],
            compose_argv(
                ["shuffle", "--catalog", "custom.json"],
                prefix=("show",),
                global_options=("--catalog",),
            ),
        )

    def test_equals_form_parent_option_is_preserved(self) -> None:
        self.assertEqual(
            ["--catalog=custom.json", "list"],
            compose_argv(
                ["--catalog=custom.json"],
                prefix=("list",),
                global_options=("--catalog",),
            ),
        )

    def test_missing_parent_option_value_fails_closed(self) -> None:
        with self.assertRaises(LegacyCommandError):
            compose_argv(
                ["--catalog"],
                prefix=("list",),
                global_options=("--catalog",),
            )

    def test_registered_script_cannot_escape_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(LegacyCommandError):
                run_script(
                    workspace=Path(directory),
                    script="../outside.py",
                    argv=(),
                )


if __name__ == "__main__":
    unittest.main()
