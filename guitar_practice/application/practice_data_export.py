"""Application use case for deterministic practice-data export."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from guitar_practice.application.ports import JsonValueReader, WorkspaceTree
from guitar_practice.domain import practice_data

DEFAULT_SOURCE = "catalogs/practice-data.json"
DEFAULT_OUTPUT = "docs/data/practice-data.json"


@dataclass(frozen=True)
class PracticeDataExport:
    values: JsonValueReader
    tree: WorkspaceTree
    source: str = DEFAULT_SOURCE

    def catalog(self) -> dict[str, Any]:
        value = self.values.read(self.source)
        if not isinstance(value, Mapping):
            raise practice_data.CatalogError("practice-data catalog must be an object")
        catalog = dict(value)
        for source_path in practice_data.validate_catalog(catalog):
            if not self.tree.exists(source_path):
                raise practice_data.CatalogError(
                    f"session source path does not exist: {source_path}"
                )
        return catalog

    def export(self, output: str = DEFAULT_OUTPUT) -> str:
        rendered = practice_data.render_catalog(self.catalog())
        self.tree.write_text(output, rendered)
        return output

    def check(self, output: str = DEFAULT_OUTPUT) -> str:
        expected = self.catalog()
        if not self.tree.exists(output):
            raise practice_data.CatalogError(f"generated export is missing: {output}")
        actual = self.values.read(output)
        if not isinstance(actual, Mapping):
            raise practice_data.CatalogError("generated export must be a JSON object")
        practice_data.validate_catalog(dict(actual))
        if dict(actual) != expected:
            raise practice_data.CatalogError(
                "generated export is stale: run guitarctl export practice-data"
            )
        return output
