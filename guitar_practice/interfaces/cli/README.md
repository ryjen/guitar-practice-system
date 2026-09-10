# CLI interface layer

This package owns only process-level concerns: parsing, command selection, rendering, and exit-code mapping. Business rules belong in `domain`; orchestration belongs in `application`; side effects belong in `adapters`.

The current legacy command adapter is temporary migration scaffolding. Do not add new behavior to it.
