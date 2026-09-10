"""Command registry for the stable `guitarctl` interface.

The first migration step delegates to legacy modules through one explicit adapter.
That keeps command semantics stable while application/domain logic is extracted
incrementally. New commands should target application use cases directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class LegacyCommand:
    path: tuple[str, ...]
    script: str
    help: str


LEGACY_COMMANDS: tuple[LegacyCommand, ...] = (
    LegacyCommand(("discover",), "scripts/discovery_catalog.py", "Search deterministic repository catalogs"),
    LegacyCommand(("schedule",), "scripts/scheduling_v2.py", "Propose deterministic practice schedules"),
    LegacyCommand(("assess",), "scripts/assessment_core.py", "Run deterministic assessment workflows"),
    LegacyCommand(("session", "adapt"), "scripts/adaptive_session.py", "Adapt a practice session from explicit evidence"),
    LegacyCommand(("backing", "generate"), "scripts/generate_backing_tracks.py", "Generate backing-track artifacts"),
    LegacyCommand(("midi", "workflow"), "scripts/midi_workflow.py", "Run the MIDI workflow"),
    LegacyCommand(("midi", "generate"), "tools/generate_midi.py", "Generate MIDI from explicit source data"),
    LegacyCommand(("progression", "generate"), "scripts/generate_practice_progression.py", "Generate a practice progression"),
    LegacyCommand(("export",), "scripts/export_practice_data.py", "Export portable practice data"),
    LegacyCommand(("validate", "public-boundary"), "scripts/check_public_boundary.py", "Validate the public/private boundary"),
)


def command_paths() -> Sequence[tuple[str, ...]]:
    return tuple(command.path for command in LEGACY_COMMANDS)
