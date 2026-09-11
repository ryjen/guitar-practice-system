"""Application use cases for deterministic progression catalogs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from guitar_practice.application.ports import JsonDocumentStore
from guitar_practice.domain import progression

DEFAULT_CATALOG = "catalogs/progressions/catalog.json"


@dataclass(frozen=True)
class ProgressionCatalog:
    documents: JsonDocumentStore
    catalog_path: str = DEFAULT_CATALOG

    def _catalog(self) -> dict[str, Any]:
        catalog = dict(self.documents.read(self.catalog_path))
        progression.validate_catalog(catalog)
        return catalog

    def validate(self) -> int:
        return len(self._catalog()["presets"])

    def list_ids(self) -> list[str]:
        return [preset["id"] for preset in self._catalog()["presets"]]

    def show(self, preset_id: str) -> dict[str, Any]:
        return progression.get_preset(self._catalog(), preset_id)

    def resolve(
        self,
        preset_id: str,
        key_signature: str,
        *,
        tonal_center: str | None = None,
    ) -> list[str]:
        return progression.resolve_progression(
            self._catalog(),
            preset_id,
            key_signature,
            tonal_center=tonal_center,
        )

    def fourths(
        self,
        preset_id: str,
        *,
        start_key: str = "C",
        count: int = 12,
    ) -> list[dict[str, Any]]:
        return progression.resolve_circle_of_fourths(
            self._catalog(),
            preset_id,
            start_key=start_key,
            count=count,
        )
