"""Stable command registry for `guitarctl`.

The registry is the anti-corruption boundary between stable command identities and
legacy implementation files. New behavior should use native handlers; legacy
targets exist only during strangler migration.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Sequence


class MigrationState(StrEnum):
    NATIVE = "native"
    LEGACY = "legacy"
    DEPRECATED = "deprecated"


@dataclass(frozen=True)
class LegacyTarget:
    script: str
    prefix: tuple[str, ...] = ()
    global_options: tuple[str, ...] = ()


@dataclass(frozen=True)
class CommandSpec:
    path: tuple[str, ...]
    help: str
    migration: MigrationState
    native_handler: str | None = None
    legacy: LegacyTarget | None = None

    def __post_init__(self) -> None:
        if bool(self.native_handler) == bool(self.legacy):
            raise ValueError("command must define exactly one implementation")


COMMANDS: tuple[CommandSpec, ...] = (
    CommandSpec(
        ("discover", "search"),
        "Search deterministic repository catalogs",
        MigrationState.NATIVE,
        native_handler="discover-search",
    ),
    CommandSpec(
        ("schedule", "propose"),
        "Propose a deterministic v2 practice schedule",
        MigrationState.NATIVE,
        native_handler="schedule-propose",
    ),
    CommandSpec(
        ("schedule", "check-approval"),
        "Check whether a v2 schedule proposal can still be approved",
        MigrationState.NATIVE,
        native_handler="schedule-check-approval",
    ),
    CommandSpec(
        ("schedule", "legacy", "propose"),
        "Compatibility access to the v1 scheduling proposal",
        MigrationState.DEPRECATED,
        legacy=LegacyTarget("scripts/scheduling.py", ("propose",)),
    ),
    CommandSpec(
        ("schedule", "legacy", "check-approval"),
        "Compatibility access to v1 schedule approval checks",
        MigrationState.DEPRECATED,
        legacy=LegacyTarget("scripts/scheduling.py", ("check-approval",)),
    ),
    CommandSpec(
        ("assess", "evaluate"),
        "Evaluate evidence against deterministic assessment gates",
        MigrationState.NATIVE,
        native_handler="assess-evaluate",
    ),
    CommandSpec(
        ("session", "adapt"),
        "Build a deterministic adaptive-session recommendation",
        MigrationState.LEGACY,
        legacy=LegacyTarget("scripts/adaptive_session.py"),
    ),
    CommandSpec(
        ("evidence", "feedback"),
        "Derive deterministic feedback from evidence records",
        MigrationState.LEGACY,
        legacy=LegacyTarget("scripts/evidence_feedback.py"),
    ),
    CommandSpec(
        ("groove", "validate"),
        "Validate the groove catalog",
        MigrationState.NATIVE,
        native_handler="groove-validate",
    ),
    CommandSpec(
        ("groove", "list"),
        "List groove presets",
        MigrationState.NATIVE,
        native_handler="groove-list",
    ),
    CommandSpec(
        ("groove", "show"),
        "Show one groove preset",
        MigrationState.NATIVE,
        native_handler="groove-show",
    ),
    CommandSpec(
        ("progression", "validate"),
        "Validate the progression catalog",
        MigrationState.NATIVE,
        native_handler="progression-validate",
    ),
    CommandSpec(
        ("progression", "list"),
        "List progression presets",
        MigrationState.NATIVE,
        native_handler="progression-list",
    ),
    CommandSpec(
        ("progression", "show"),
        "Show one progression preset",
        MigrationState.NATIVE,
        native_handler="progression-show",
    ),
    CommandSpec(
        ("progression", "resolve"),
        "Resolve a progression preset in a key",
        MigrationState.NATIVE,
        native_handler="progression-resolve",
    ),
    CommandSpec(
        ("progression", "fourths"),
        "Resolve a progression through the circle of fourths",
        MigrationState.NATIVE,
        native_handler="progression-fourths",
    ),
    CommandSpec(
        ("progression", "generate"),
        "Generate a practice progression from an explicit request",
        MigrationState.LEGACY,
        legacy=LegacyTarget("scripts/generate_practice_progression.py"),
    ),
    CommandSpec(
        ("backing", "resolve"),
        "Resolve a backing-track request into a deterministic spec",
        MigrationState.NATIVE,
        native_handler="backing-resolve",
    ),
    CommandSpec(
        ("backing", "generate"),
        "Generate and validate committed backing-track manifests",
        MigrationState.LEGACY,
        legacy=LegacyTarget("scripts/generate_backing_tracks.py"),
    ),
    CommandSpec(
        ("midi", "generate"),
        "Generate MIDI from a manifest",
        MigrationState.NATIVE,
        native_handler="midi-generate",
    ),
    CommandSpec(
        ("midi", "validate"),
        "Validate generated MIDI against a manifest",
        MigrationState.NATIVE,
        native_handler="midi-validate",
    ),
    CommandSpec(
        ("midi", "generate-exercises"),
        "Generate starter MIDI practice exercises",
        MigrationState.LEGACY,
        legacy=LegacyTarget("tools/generate_midi.py"),
    ),
    CommandSpec(
        ("artifact", "build"),
        "Build deterministic practice artifacts",
        MigrationState.LEGACY,
        legacy=LegacyTarget("scripts/build_practice_artifacts.py"),
    ),
    CommandSpec(
        ("export", "practice-data"),
        "Export portable practice data",
        MigrationState.LEGACY,
        legacy=LegacyTarget("scripts/export_practice_data.py"),
    ),
    CommandSpec(
        ("validate", "repo"),
        "Run repository validation",
        MigrationState.LEGACY,
        legacy=LegacyTarget("scripts/validate_repo.py"),
    ),
    CommandSpec(
        ("validate", "public-boundary"),
        "Validate the public/private repository boundary",
        MigrationState.LEGACY,
        legacy=LegacyTarget("scripts/check_public_boundary.py"),
    ),
)

# These files are implementation libraries, not process entrypoints.
INTERNAL_LIBRARY_SCRIPTS = frozenset()

# Old entrypoints/modules retained only for backwards compatibility after extraction.
COMPATIBILITY_SHIMS = frozenset(
    {
        "scripts/discovery_catalog.py",
        "scripts/scheduling_v2.py",
        "scripts/assessment_core.py",
        "scripts/progression_catalog.py",
        "scripts/timing.py",
        "scripts/midi_workflow.py",
        "scripts/groove_catalog.py",
        "scripts/groove_engine.py",
        "scripts/bass_engine.py",
        "scripts/backing_track_engine.py",
        "scripts/resolve_backing_track_request.py",
    }
)


def command_paths() -> Sequence[tuple[str, ...]]:
    return tuple(command.path for command in COMMANDS)


def registered_legacy_scripts() -> frozenset[str]:
    return frozenset(command.legacy.script for command in COMMANDS if command.legacy)


def find_command(tokens: Sequence[str]) -> tuple[CommandSpec | None, int]:
    """Resolve the longest registered command prefix."""

    best: CommandSpec | None = None
    best_length = 0
    for command in COMMANDS:
        length = len(command.path)
        if length <= len(tokens) and tuple(tokens[:length]) == command.path and length > best_length:
            best = command
            best_length = length
    return best, best_length


def commands_below(prefix: Sequence[str]) -> tuple[CommandSpec, ...]:
    normalized = tuple(prefix)
    return tuple(command for command in COMMANDS if command.path[: len(normalized)] == normalized)
