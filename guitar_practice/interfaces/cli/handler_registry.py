"""Single native CLI handler registry assembled from cohesive command modules."""

from __future__ import annotations

from collections.abc import Mapping

from guitar_practice.interfaces.cli.backing_handlers import BACKING_HANDLERS
from guitar_practice.interfaces.cli.generation_handlers import GENERATION_HANDLERS
from guitar_practice.interfaces.cli.groove_handlers import GROOVE_HANDLERS
from guitar_practice.interfaces.cli.handlers import NATIVE_HANDLERS as CORE_HANDLERS


def _merge(*registries: Mapping[str, object]) -> dict[str, object]:
    merged: dict[str, object] = {}
    for registry in registries:
        duplicate = set(merged) & set(registry)
        if duplicate:
            raise RuntimeError(f"duplicate native CLI handler ids: {sorted(duplicate)}")
        merged.update(registry)
    return merged


NATIVE_HANDLERS = _merge(
    CORE_HANDLERS,
    GROOVE_HANDLERS,
    BACKING_HANDLERS,
    GENERATION_HANDLERS,
)
