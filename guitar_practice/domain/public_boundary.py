"""Pure public/private repository-boundary scanning rules."""

from __future__ import annotations

import re
from collections.abc import Iterable

TEXT_SUFFIXES = frozenset(
    {".md", ".py", ".json", ".yaml", ".yml", ".toml", ".mmd", ".txt"}
)
EXCLUDED_DIRS = frozenset({".git", "generated", "__pycache__"})
ALLOWLIST = frozenset(
    {
        ".github/pull_request_template.md",
        "docs/decisions/ADR-0002-public-core-product-boundary.md",
        "docs/decisions/ADR-0003-private-ai-ownership.md",
        "docs/governance/ip-boundary.md",
        "scripts/check_public_boundary.py",
        "guitar_practice/domain/public_boundary.py",
    }
)
MARKERS = (
    ("guitar-practice-platform", re.compile(r"guitar-practice-platform", re.I)),
    ("AI-assisted", re.compile(r"\bAI-assisted\b", re.I)),
    ("AI-generated", re.compile(r"\bAI-generated\b", re.I)),
    ("AI coaching", re.compile(r"\bAI\s+coaching\b", re.I)),
    ("AI-related", re.compile(r"\bAI-related\b", re.I)),
    ("OpenAI", re.compile(r"\bOpenAI\b", re.I)),
    ("LLM", re.compile(r"\bLLM\b", re.I)),
    ("prompt injection", re.compile(r"\bprompt\s+injection\b", re.I)),
    ("prompt template", re.compile(r"\bprompt\s+templates?\b", re.I)),
    ("prompts/", re.compile(r"prompts/", re.I)),
    ("model provider", re.compile(r"\bmodel\s+providers?\b", re.I)),
    ("model/provider", re.compile(r"\bmodel/provider\b", re.I)),
    ("provider-specific", re.compile(r"\bprovider-specific\b", re.I)),
    (
        "local language model",
        re.compile(r"\blocal\s+language\s+models?\b", re.I),
    ),
    ("embeddings", re.compile(r"\bembeddings?\b", re.I)),
)


def should_scan(path: str) -> bool:
    parts = tuple(part for part in path.split("/") if part)
    if not parts:
        return False
    suffix = "." + parts[-1].rsplit(".", 1)[-1] if "." in parts[-1] else ""
    if suffix.lower() not in TEXT_SUFFIXES:
        return False
    if any(part in EXCLUDED_DIRS for part in parts):
        return False
    return path not in ALLOWLIST


def scan_texts(files: Iterable[tuple[str, str]]) -> list[str]:
    findings: list[str] = []
    for path, content in sorted(files):
        if not should_scan(path):
            continue
        for line_number, line in enumerate(content.splitlines(), start=1):
            for marker, pattern in MARKERS:
                if pattern.search(line):
                    findings.append(
                        f"{path}:{line_number}: contains boundary marker {marker!r}"
                    )
    return findings
