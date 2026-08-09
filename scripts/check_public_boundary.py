#!/usr/bin/env python3
"""Fail when strong private/AI boundary markers appear outside governance files."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".py", ".json", ".yaml", ".yml", ".toml", ".mmd", ".txt"}
EXCLUDED_DIRS = {".git", "generated", "__pycache__"}
ALLOWLIST = {
    ".github/pull_request_template.md",
    "docs/decisions/ADR-0002-public-core-product-boundary.md",
    "docs/decisions/ADR-0003-private-ai-ownership.md",
    "docs/governance/ip-boundary.md",
    "scripts/check_public_boundary.py",
}
MARKERS = (
    ("guitar-practice-platform", re.compile(r"guitar-practice-platform", re.IGNORECASE)),
    ("AI-assisted", re.compile(r"\bAI-assisted\b", re.IGNORECASE)),
    ("AI-generated", re.compile(r"\bAI-generated\b", re.IGNORECASE)),
    ("AI coaching", re.compile(r"\bAI\s+coaching\b", re.IGNORECASE)),
    ("AI-related", re.compile(r"\bAI-related\b", re.IGNORECASE)),
    ("OpenAI", re.compile(r"\bOpenAI\b", re.IGNORECASE)),
    ("LLM", re.compile(r"\bLLM\b", re.IGNORECASE)),
    ("prompt injection", re.compile(r"\bprompt\s+injection\b", re.IGNORECASE)),
    ("prompt template", re.compile(r"\bprompt\s+templates?\b", re.IGNORECASE)),
    ("prompts/", re.compile(r"prompts/", re.IGNORECASE)),
    ("model provider", re.compile(r"\bmodel\s+providers?\b", re.IGNORECASE)),
    ("model/provider", re.compile(r"\bmodel/provider\b", re.IGNORECASE)),
    ("provider-specific", re.compile(r"\bprovider-specific\b", re.IGNORECASE)),
    ("local language model", re.compile(r"\blocal\s+language\s+models?\b", re.IGNORECASE)),
    ("embeddings", re.compile(r"\bembeddings?\b", re.IGNORECASE)),
)


def candidates() -> list[Path]:
    result: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        if relative.as_posix() in ALLOWLIST:
            continue
        result.append(path)
    return sorted(result)


def violations() -> list[str]:
    findings: list[str] = []
    for path in candidates():
        relative = path.relative_to(ROOT).as_posix()
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(lines, start=1):
            for marker, pattern in MARKERS:
                if pattern.search(line):
                    findings.append(f"{relative}:{line_number}: contains boundary marker {marker!r}")
    return findings


def main() -> int:
    findings = violations()
    if findings:
        print("Public boundary check failed:", file=sys.stderr)
        for finding in findings:
            print(f"- {finding}", file=sys.stderr)
        return 1
    print("Public boundary check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
