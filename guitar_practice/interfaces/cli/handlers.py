"""Package-native CLI command handlers."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence

from guitar_practice.adapters.json_files import JsonDocumentError, JsonFileStore
from guitar_practice.application.discovery import SearchCatalog
from guitar_practice.domain.discovery import DiscoveryError
from guitar_practice.interfaces.cli import exit_codes
from guitar_practice.interfaces.cli.runtime import CliContext

NativeHandler = Callable[[Sequence[str], CliContext], int]


def discover_search(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl discover search")
    parser.add_argument("request", help="Discovery request JSON")
    parser.add_argument("catalog", help="Repository catalog JSON")
    try:
        args = parser.parse_args(list(argv))
        service = SearchCatalog(JsonFileStore(context.workspace))
        result = service.execute(args.request, args.catalog)
    except (DiscoveryError, JsonDocumentError, OSError) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    json.dump(result, context.stdout, indent=2, sort_keys=True)
    context.stdout.write("\n")
    return exit_codes.OK


NATIVE_HANDLERS: dict[str, NativeHandler] = {
    "discover-search": discover_search,
}
