"""CLI handlers for deterministic backing-track request resolution."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence

from guitar_practice.adapters.json_files import JsonDocumentError, JsonFileStore
from guitar_practice.application.backing import ResolveBackingRequest
from guitar_practice.domain.midi import ManifestError
from guitar_practice.interfaces.cli import exit_codes
from guitar_practice.interfaces.cli.runtime import CliContext

NativeHandler = Callable[[Sequence[str], CliContext], int]


def backing_resolve(argv: Sequence[str], context: CliContext) -> int:
    parser = argparse.ArgumentParser(prog="guitarctl backing resolve")
    parser.add_argument("request", help="BackingTrackRequest JSON")
    parser.add_argument("--output", help="Optional BackingTrackSpec output JSON")
    try:
        args = parser.parse_args(list(argv))
        service = ResolveBackingRequest(JsonFileStore(context.workspace))
        if args.output is not None:
            service.execute_to(args.request, args.output)
            return exit_codes.OK
        result = service.execute(args.request)
    except (ManifestError, JsonDocumentError, OSError) as exc:
        print(f"guitarctl: {exc}", file=context.stderr)
        return exit_codes.DATA_ERROR

    json.dump(result, context.stdout, indent=2, sort_keys=True)
    context.stdout.write("\n")
    return exit_codes.OK


BACKING_HANDLERS: dict[str, NativeHandler] = {
    "backing-resolve": backing_resolve,
}
