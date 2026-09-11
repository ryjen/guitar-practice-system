"""Discovery use cases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from guitar_practice.application.ports import JsonDocumentStore
from guitar_practice.domain.discovery import search_catalog


@dataclass(frozen=True)
class SearchCatalog:
    """Load explicit inputs and execute deterministic catalog discovery."""

    documents: JsonDocumentStore

    def execute(self, request_path: str, catalog_path: str) -> Mapping[str, Any]:
        request = dict(self.documents.read(request_path))
        try:
            catalog = dict(self.documents.read(catalog_path))
        except FileNotFoundError:
            catalog = None
        return search_catalog(request, catalog)
