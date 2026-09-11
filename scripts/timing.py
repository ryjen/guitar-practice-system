#!/usr/bin/env python3
"""Compatibility module for deterministic timing rules."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    # Compatibility only: script-module imports predate the installable package.
    sys.path.insert(0, str(ROOT))

from guitar_practice.domain import timing as _domain  # noqa: E402

BEAT_UNITS = _domain.BEAT_UNITS
CLICK_MODES = _domain.CLICK_MODES
STRATEGIES = _domain.STRATEGIES
SOURCES = _domain.SOURCES
TimingError = _domain.TimingError
_positive_number = _domain._positive_number
_meter = _domain._meter
validate_timing = _domain.validate_timing
effective_event_rate = _domain.effective_event_rate
