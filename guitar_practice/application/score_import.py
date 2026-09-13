"""Application orchestration for importing external score formats."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath

from guitar_practice.application.ports import JsonDocumentStore, ScoreConverter
from guitar_practice.domain.musicxml import parse_musicxml
from guitar_practice.domain.song import Song, song_to_dict

SUPPORTED_SCORE_SUFFIXES = frozenset(
    {".gp", ".gp3", ".gp4", ".gp5", ".gpx", ".musicxml", ".xml"}
)


class UnsupportedScoreFormat(ValueError):
    """The source extension is not accepted by the score import boundary."""


def _path(source_path: str) -> PurePosixPath:
    return PurePosixPath(source_path.replace("\\", "/"))


def source_id_for(source_path: str) -> str:
    stem = _path(source_path).stem
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip(".-_")
    return safe or "score"


def validate_source_format(source_path: str) -> None:
    suffix = _path(source_path).suffix.casefold()
    if suffix not in SUPPORTED_SCORE_SUFFIXES:
        supported = ", ".join(sorted(SUPPORTED_SCORE_SUFFIXES))
        raise UnsupportedScoreFormat(
            f"unsupported score format {suffix or '<none>'}; expected one of: {supported}"
        )


@dataclass(frozen=True)
class ImportScore:
    converter: ScoreConverter
    documents: JsonDocumentStore

    def execute(self, source_path: str, output_path: str) -> Song:
        validate_source_format(source_path)
        converted = self.converter.convert(source_path)
        song = parse_musicxml(converted.musicxml, source_id=source_id_for(source_path))
        self.documents.write(
            output_path,
            {
                "schema_version": 1,
                "song": song_to_dict(song),
                "import": {
                    "source": source_path,
                    "converter": converted.converter,
                    "converter_version": converted.converter_version,
                },
            },
        )
        return song
