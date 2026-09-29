from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from guitar_practice.adapters.binary_files import BinaryFileStore
from guitar_practice.adapters.musicxml_export import MusicXmlExporter
from guitar_practice.adapters.musicxml_import import MusicXmlParser
from guitar_practice.adapters.score_files import ScoreFileStore
from guitar_practice.application.score_editor import ScoreEditSession
from guitar_practice.domain import score
from tests.test_score_ir import minimal_score, standard_tuning, structured_score, timeline_score


def _texts(root: ET.Element, path: str) -> list[str]:
    return [element.text or "" for element in root.findall(path)]


def _guided_editor_musicxml(workspace: Path) -> tuple[bytes, dict]:
    document = minimal_score()
    document["id"] = "guided-musescore"
    document["metadata"]["title"] = "Guided MuseScore"
    document["parts"] = [
        {
            "id": "guitar-1",
            "name": "Guitar",
            "role": "guitar",
            "instrument": {"name": "Electric Guitar", "family": "guitar"},
            "guitar": {"tuning": standard_tuning()},
            "events": [],
        }
    ]
    score.validate(document)

    documents = ScoreFileStore(workspace)
    documents.write("guided.score.json", document)
    session = ScoreEditSession("guided.score.json", documents)
    session.replace_form("intro:2")
    session.replace_chords("C | G")
    session.apply_structured(
        "notes",
        part_id="guitar-1",
        input_document={
            "notes": [
                {
                    "location": {"bar": 1, "beat": [1, 1]},
                    "duration": [1, 4],
                    "voice": 1,
                    "pitch": {"step": "E", "alter": 0, "octave": 4},
                },
                {
                    "location": {"bar": 2, "beat": [1, 1]},
                    "duration": [1, 4],
                    "voice": 1,
                    "pitch": {"step": "G", "alter": 0, "octave": 4},
                },
            ]
        },
    )
    session.apply_structured(
        "voicing",
        part_id="guitar-1",
        input_document={
            "positions": [
                {
                    "selector": {
                        "location": {"bar": 1, "beat": [1, 1]},
                        "voice": 1,
                        "pitch": {"step": "E", "alter": 0, "octave": 4},
                    },
                    "position": {"string": 1, "fret": 0},
                },
                {
                    "selector": {
                        "location": {"bar": 2, "beat": [1, 1]},
                        "voice": 1,
                        "pitch": {"step": "G", "alter": 0, "octave": 4},
                    },
                    "position": {"string": 1, "fret": 3},
                },
            ]
        },
    )
    session.apply_structured(
        "rhythm",
        part_id="guitar-1",
        input_document={
            "rhythm": [
                {
                    "selector": {
                        "location": {"bar": 2, "beat": [1, 1]},
                        "voice": 1,
                        "pitch": {"step": "G", "alter": 0, "octave": 4},
                    },
                    "location": {"bar": 2, "beat": [3, 2]},
                    "duration": [1, 8],
                }
            ]
        },
    )
    session.apply_structured(
        "technique",
        part_id="guitar-1",
        input_document={
            "technique": [
                {
                    "selector": {
                        "location": {"bar": 1, "beat": [1, 1]},
                        "voice": 1,
                        "pitch": {"step": "E", "alter": 0, "octave": 4},
                    },
                    "articulations": ["accent"],
                    "techniques": [{"name": "vibrato"}],
                    "dynamics": "mf",
                }
            ]
        },
    )
    result = session.export_musicxml(
        artifacts=BinaryFileStore(workspace),
        exporter=MusicXmlExporter(),
        output="guided.musicxml",
    )
    return result.data, document


class MusicXmlExporterTests(unittest.TestCase):
    def test_timeline_score_exports_deterministically_with_standard_and_tab_metadata(self) -> None:
        document = timeline_score()
        exporter = MusicXmlExporter()

        first = exporter.export(document)
        second = exporter.export(document)

        self.assertEqual(first.data, second.data)
        self.assertTrue(first.data.startswith(b'<?xml version="1.0" encoding="UTF-8"?>'))
        self.assertTrue(first.data.endswith(b"\n"))

        root = ET.fromstring(first.data)
        self.assertEqual("score-partwise", root.tag)
        self.assertEqual("4.0", root.attrib["version"])
        self.assertEqual("Blue Thing", root.findtext("./work/work-title"))
        self.assertEqual(["Guitar"], _texts(root, "./part-list/score-part/part-name"))

        first_measure = root.find("./part/measure[@number='1']")
        assert first_measure is not None
        self.assertEqual("2", first_measure.findtext("./attributes/staves"))
        self.assertEqual("TAB", first_measure.findtext("./attributes/clef[@number='2']/sign"))
        self.assertEqual(
            "alternate",
            first_measure.findtext("./attributes/staff-details[@number='2']/staff-type"),
        )
        self.assertEqual(
            6,
            len(first_measure.findall("./attributes/staff-details[@number='2']/staff-tuning")),
        )

        first_note = next(
            note
            for note in first_measure.findall("./note")
            if note.findtext("./pitch/step") == "E"
        )
        self.assertEqual("1", first_note.findtext("./notations/technical/string"))
        self.assertEqual("0", first_note.findtext("./notations/technical/fret"))
        self.assertIsNotNone(first_note.find("./notations/articulations/accent"))
        self.assertIsNotNone(first_note.find("./notations/dynamics/mf"))
        self.assertEqual(
            "vibrato",
            first_note.findtext("./notations/technical/other-technical"),
        )
        self.assertEqual("start", first_note.find("./tie").attrib["type"])

        second_measure = root.find("./part/measure[@number='2']")
        assert second_measure is not None
        self.assertEqual("6", second_measure.findtext("./attributes/time/beats"))
        self.assertEqual("8", second_measure.findtext("./attributes/time/beat-type"))
        triplet = second_measure.find("./note/time-modification")
        assert triplet is not None
        self.assertEqual("3", triplet.findtext("actual-notes"))
        self.assertEqual("2", triplet.findtext("normal-notes"))
        self.assertEqual("eighth", triplet.findtext("normal-type"))

        self.assertEqual(
            ["120", "96"],
            _texts(root, "./part/measure[@number='1']/direction/direction-type/metronome/per-minute"),
        )
        self.assertEqual("0", first_measure.findtext("./attributes/key/fifths"))
        self.assertEqual("1", second_measure.findtext("./attributes/key/fifths"))

    def test_form_harmony_repeats_endings_and_rehearsal_marks_are_preserved(self) -> None:
        result = MusicXmlExporter().export(structured_score())
        root = ET.fromstring(result.data)

        self.assertEqual(
            ["G7#9", "Cmaj7"],
            [element.attrib["text"] for element in root.findall("./part[1]/measure/harmony/kind")],
        )
        rehearsal = _texts(root, "./part[1]/measure/direction/direction-type/rehearsal")
        self.assertIn("Verse", rehearsal)
        self.assertIn("A", rehearsal)

        first_measure = root.find("./part[1]/measure[@number='1']")
        second_measure = root.find("./part[1]/measure[@number='2']")
        assert first_measure is not None and second_measure is not None
        self.assertEqual(
            "forward",
            first_measure.find("./barline[@location='left']/repeat").attrib["direction"],
        )
        backward = second_measure.find("./barline[@location='right']/repeat")
        assert backward is not None
        self.assertEqual("backward", backward.attrib["direction"])
        self.assertEqual("2", backward.attrib["times"])

        endings = root.findall("./part[1]/measure/barline/ending")
        self.assertTrue(any(item.attrib == {"number": "1", "type": "start"} for item in endings))
        self.assertTrue(any(item.attrib == {"number": "1", "type": "stop"} for item in endings))
        self.assertTrue(any(item.attrib == {"number": "2", "type": "start"} for item in endings))
        self.assertTrue(any(item.attrib == {"number": "2", "type": "stop"} for item in endings))

    def test_multi_part_output_and_project_import_round_trip(self) -> None:
        document = timeline_score()
        bass = {
            "id": "bass-1",
            "name": "Bass",
            "role": "bass",
            "instrument": {
                "name": "Electric Bass",
                "family": "bass",
                "midi": {"program": 33, "channel": 2, "percussion": False},
            },
            "events": [
                {
                    "kind": "note",
                    "location": {"bar": 1, "beat": [1, 1]},
                    "duration": [1, 2],
                    "voice": 1,
                    "pitch": {"step": "E", "alter": 0, "octave": 2},
                }
            ],
        }
        document["parts"].append(bass)

        result = MusicXmlExporter().export(document)
        root = ET.fromstring(result.data)
        self.assertEqual(2, len(root.findall("./part-list/score-part")))
        self.assertEqual(2, len(root.findall("./part")))
        self.assertEqual("F", root.findtext("./part[2]/measure[1]/attributes/clef/sign"))
        self.assertEqual("34", root.findtext("./part-list/score-part[2]/midi-instrument/midi-program"))

        imported = MusicXmlParser().parse(result.data, source_id="roundtrip")
        self.assertEqual("Blue Thing", imported.title)
        self.assertEqual(["Guitar", "Bass"], [track.name for track in imported.tracks])
        self.assertEqual([2, 1], [len(track.notes) for track in imported.tracks])
        self.assertEqual(
            [(4, 4), (6, 8)],
            [(meter.numerator, meter.denominator) for meter in imported.meter_map],
        )
        self.assertEqual([120.0, 96.0], [tempo.bpm for tempo in imported.tempo_map])

    def test_nonstandard_written_duration_emits_explicit_diagnostic(self) -> None:
        document = timeline_score()
        document["parts"][0]["events"][0].pop("tie")
        document["parts"][0]["events"][0]["duration"] = [1, 5]

        result = MusicXmlExporter().export(document)

        codes = [item.code for item in result.diagnostics]
        self.assertIn("written-duration-type-omitted", codes)
        root = ET.fromstring(result.data)
        note = root.find("./part/measure/note")
        assert note is not None
        self.assertIsNone(note.find("./type"))

    def test_generic_technique_is_emitted_with_explicit_diagnostic(self) -> None:
        document = timeline_score()
        document["parts"][0]["events"][0]["techniques"] = [{"name": "palm-mute"}]

        result = MusicXmlExporter().export(document)
        root = ET.fromstring(result.data)

        self.assertEqual(
            "palm-mute",
            root.findtext("./part/measure/note/notations/technical/other-technical"),
        )
        self.assertEqual(1, len(result.diagnostics))
        diagnostic = result.diagnostics[0]
        self.assertEqual("generic-technique", diagnostic.code)
        self.assertEqual("warning", diagnostic.severity)
        self.assertIn("palm-mute", diagnostic.message)
        self.assertIn("parts[guitar-1]", diagnostic.path)


class GuidedScoreMusicXmlTests(unittest.TestCase):
    def test_unsaved_guided_edit_session_exports_musicxml_without_mutating_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            data, original = _guided_editor_musicxml(workspace)

            self.assertTrue(data.startswith(b'<?xml version="1.0" encoding="UTF-8"?>'))
            self.assertEqual(
                original,
                dict(ScoreFileStore(workspace).read("guided.score.json")),
            )
            root = ET.fromstring(data)
            self.assertEqual("Guided MuseScore", root.findtext("./work/work-title"))
            self.assertEqual(2, len(root.findall("./part/measure")))
            self.assertEqual("1", root.findtext("./part/measure/note/notations/technical/string"))


class MuseScoreMusicXmlIntegrationTests(unittest.TestCase):
    def _assert_musescore_imports(self, data: bytes, *, stem: str) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / f"{stem}.musicxml"
            output = root / f"{stem}.mscz"
            source.write_bytes(data)

            runtime = root / "runtime"
            runtime.mkdir(mode=0o700)
            env = os.environ.copy()
            env.update(
                {
                    "QT_QPA_PLATFORM": "offscreen",
                    "MU_QT_QPA_PLATFORM": "offscreen",
                    "QT_QUICK_BACKEND": "software",
                    "XDG_RUNTIME_DIR": str(runtime),
                }
            )
            result = subprocess.run(
                ["mscore", "-o", str(output), str(source)],
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
                env=env,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 0)

    @unittest.skipUnless(shutil.which("mscore"), "MuseScore CLI is not available")
    def test_musescore_imports_exported_guitar_score(self) -> None:
        self._assert_musescore_imports(
            MusicXmlExporter().export(timeline_score()).data,
            stem="guitar",
        )

    @unittest.skipUnless(shutil.which("mscore"), "MuseScore CLI is not available")
    def test_musescore_imports_guided_editor_working_copy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data, _ = _guided_editor_musicxml(Path(directory))
        self._assert_musescore_imports(data, stem="guided-preview")


if __name__ == "__main__":
    unittest.main()
