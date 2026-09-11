"""Application use cases for deterministic backing-track requests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from guitar_practice.application.ports import JsonDocumentStore
from guitar_practice.domain import backing_request

DEFAULT_GROOVE_CATALOG = "catalogs/grooves/catalog.json"
DEFAULT_PROGRESSION_CATALOG = "catalogs/progressions/catalog.json"


@dataclass(frozen=True)
class ResolveBackingRequest:
    documents: JsonDocumentStore
    groove_catalog_path: str = DEFAULT_GROOVE_CATALOG
    progression_catalog_path: str = DEFAULT_PROGRESSION_CATALOG

    def execute(self, request_path: str) -> dict[str, Any]:
        request = dict(self.documents.read(request_path))
        groove_catalog = dict(self.documents.read(self.groove_catalog_path))
        progression_catalog = dict(self.documents.read(self.progression_catalog_path))
        return backing_request.resolve_request(
            request,
            groove_catalog,
            progression_catalog,
        )

    def execute_to(self, request_path: str, output_path: str) -> dict[str, Any]:
        spec = self.execute(request_path)
        self.documents.write(output_path, spec)
        return spec
