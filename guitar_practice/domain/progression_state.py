"""Canonical progression-state vocabulary shared by assessment and scheduling."""

from __future__ import annotations

STATES = frozenset(
    {
        "discovered",
        "developing",
        "reliable-isolation",
        "reliable-context",
        "maintained",
        "paused",
        "retired",
    }
)

DEVELOPMENT_STATES = frozenset(
    {
        "discovered",
        "developing",
        "reliable-isolation",
        "reliable-context",
    }
)

ACTIVE_RANK = {
    "discovered": 0,
    "developing": 1,
    "reliable-isolation": 2,
    "reliable-context": 3,
    "maintained": 4,
}

TRANSITIONS = {
    "discovered": frozenset({"developing", "paused", "retired"}),
    "developing": frozenset({"reliable-isolation", "paused", "retired"}),
    "reliable-isolation": frozenset(
        {"developing", "reliable-context", "paused", "retired"}
    ),
    "reliable-context": frozenset(
        {"developing", "reliable-isolation", "maintained", "paused", "retired"}
    ),
    "maintained": frozenset(
        {"developing", "reliable-isolation", "reliable-context", "paused", "retired"}
    ),
    "paused": frozenset(
        {"developing", "reliable-isolation", "reliable-context", "maintained", "retired"}
    ),
    "retired": frozenset({"discovered"}),
}
