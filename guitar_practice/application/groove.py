"""Application use cases for deterministic groove catalogs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from guitar_practice.application.ports import JsonDocumentStore
from guitar_practice.domain import groove

DEFAULT_CATALOG = "catalogs/grooves/catalog.json"


@dataclass(frozen=True)
class GrooveCatalog:
    documents: JsonDocumentStore
    catalog_path: str = DEFAULT_CATALOG

    def _catalog(self) -> dict[str, Any]:
        catalog = dict(self.documents.read(self.catalog_path))
        groove.validate_catalog(catalog)
        return catalog

    def validate(self) -> dict[str, Any]:
        catalog = self._catalog()
        return {
            "version": catalog["version"],
            "presets": len(catalog["presets"]),
            "ids": [preset["id"] for preset in catalog["presets"]],
        }

    def list(self) -> list[dict[str, Any]]:
        return [
            {
                "id": preset["id"],
                "title": preset["title"],
                "meter": preset["meter"],
                "default_tempo_bpm": preset["default_tempo_bpm"],
                "tags": preset["tags"],
            }
            for preset in self._catalog()["presets"]
        ]

    def show(self, preset_id: str) -> dict[str, Any]:
        return groove.get_preset(self._catalog(), preset_id)

    def resolved(self, preset_id: str) -> dict[str, Any]:
        return groove.resolved_groove(self._catalog(), preset_id)
