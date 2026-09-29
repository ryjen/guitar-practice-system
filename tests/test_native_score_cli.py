from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from guitar_practice.adapters.midi_playback import MidiPlaybackError
from guitar_practice.application.ports import PlaybackResult
from guitar_practice.domain import midi, score
from guitar_practice.interfaces.cli.commands import MigrationState, find_command
from guitar_practice.interfaces.cli.main import main
from tests.test_score_ir import timeline_score
from tests.test_score_realization import realization_score

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "musicxml" / "multitrack.musicxml"


class NativeScoreCliTests(unittest.TestCase):
    def test_score_commands_are_native(self) -> None:
        for tokens in (
            ["score", "init", "--title", "Blue Thing"],
            ["score", "import", "song.musicxml"],
            ["score", "form", "song.score.json", "verse:12"],
            ["score", "chords", "song.score.json", "C | F | G | C"],
            ["score", "notes", "song.score.json", "guitar-1"],
            ["score", "voicing", "song.score.json", "guitar-1"],
            ["score", "rhythm", "song.score.json", "guitar-1"],
            ["score", "technique", "song.score.json", "guitar-1"],
            ["score", "render", "song.score.json", "--format", "musicxml"],
            ["score", "play", "song.score.json"],
            ["score", "show", "song.score.json"],
            ["score", "tracks", "song.score.json"],
            ["score", "validate", "song.score.json"],
        ):
            with self.subTest(tokens=tokens):
                command, _ = find_command(tokens)
                self.assertIsNotNone(command)
                assert command is not None
                self.assertEqual(MigrationState.NATIVE, command.migration)


    def test_init_emits_canonical_score_without_ambient_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "score",
                        "init",
                        "--title",
                        "Blue Thing",
                    ]
                )

            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            document = score.loads(stdout.getvalue())
            self.assertEqual("blue-thing", document["id"])
            self.assertEqual("Blue Thing", document["metadata"]["title"])
            self.assertEqual([{"number": 1}], document["bars"])
            self.assertEqual(
                [{"bar": 1, "beats": 4, "beat_unit": 4}],
                document["meter_map"],
            )
            self.assertEqual([], document["tempo_map"])
            self.assertEqual([], document["parts"])
            self.assertEqual([], list(workspace.iterdir()))

    def test_init_explicit_output_show_and_validate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "score",
                        "init",
                        "--title",
                        "Blue Thing",
                        "--output",
                        "scores/blue.score.json",
                    ]
                )
            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            self.assertEqual(
                {"id": "blue-thing", "output": "scores/blue.score.json", "title": "Blue Thing"},
                json.loads(stdout.getvalue()),
            )

            path = workspace / "scores" / "blue.score.json"
            expected = score.loads(path.read_text(encoding="utf-8"))

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(["--workspace", str(workspace), "score", "show", "scores/blue.score.json"])
            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            self.assertEqual(expected, score.loads(stdout.getvalue()))

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(["--workspace", str(workspace), "score", "validate", "scores/blue.score.json"])
            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            self.assertEqual(
                {"id": "blue-thing", "schema": score.SCHEMA_ID, "valid": True, "version": score.SCHEMA_VERSION},
                json.loads(stdout.getvalue()),
            )

    def test_validate_rejects_invalid_score_and_never_infers_current_score(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "current.score.json").write_text("{}\n", encoding="utf-8")

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                missing_target = main(["--workspace", str(workspace), "score", "validate"])
            self.assertEqual(2, missing_target)
            self.assertEqual("", stdout.getvalue())

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                invalid = main(
                    ["--workspace", str(workspace), "score", "validate", "current.score.json"]
                )
            self.assertEqual(65, invalid)
            self.assertEqual("", stdout.getvalue())
            self.assertIn("missing required fields", stderr.getvalue())

    def test_song_namespace_is_not_registered(self) -> None:
        command, consumed = find_command(["song", "show", "song.score.json"])
        self.assertIsNone(command)
        self.assertEqual(0, consumed)

    def test_form_and_chords_are_explicit_immutable_transforms(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "score",
                        "init",
                        "--title",
                        "Blue Thing",
                        "--output",
                        "draft.score.json",
                    ]
                )
            self.assertEqual(0, result)

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "score",
                        "form",
                        "draft.score.json",
                        "intro:1 verse:2 outro:1",
                        "--output",
                        "formed.score.json",
                    ]
                )
            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            self.assertEqual(
                {"bars": 4, "id": "blue-thing", "output": "formed.score.json", "sections": 3},
                json.loads(stdout.getvalue()),
            )

            formed = score.loads((workspace / "formed.score.json").read_text(encoding="utf-8"))
            self.assertEqual(1, len(score.loads((workspace / "draft.score.json").read_text(encoding="utf-8"))["bars"]))
            self.assertNotIn("harmony", formed)

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "score",
                        "chords",
                        "formed.score.json",
                        "Cmaj7 | Dm7 G7",
                        "--section",
                        "Verse",
                        "--output",
                        "harmonized.score.json",
                    ]
                )
            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            self.assertEqual(
                {"harmony_events": 3, "id": "blue-thing", "output": "harmonized.score.json"},
                json.loads(stdout.getvalue()),
            )

            harmonized = score.loads(
                (workspace / "harmonized.score.json").read_text(encoding="utf-8")
            )
            self.assertEqual([2, 3, 3], [item["location"]["bar"] for item in harmonized["harmony"]])
            self.assertNotIn("harmony", formed)

    def test_notes_command_uses_explicit_input_part_and_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            source = timeline_score()
            (workspace / "source.score.json").write_text(
                score.dumps(source),
                encoding="utf-8",
            )
            (workspace / "notes.json").write_text(
                json.dumps(
                    {
                        "notes": [
                            {
                                "location": {"bar": 1, "beat": [1, 1]},
                                "duration": [1, 8],
                                "voice": 1,
                                "pitch": {"step": "E", "alter": 0, "octave": 4},
                            },
                            {
                                "location": {"bar": 2, "beat": [2, 1]},
                                "duration": [1, 8],
                                "voice": 1,
                                "pitch": {"step": "A", "alter": 0, "octave": 4},
                            },
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "score",
                        "notes",
                        "source.score.json",
                        "guitar-1",
                        "--input",
                        "notes.json",
                        "--output",
                        "written.score.json",
                    ]
                )

            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            self.assertEqual(
                {
                    "id": source["id"],
                    "note_events": 2,
                    "output": "written.score.json",
                    "part": "guitar-1",
                },
                json.loads(stdout.getvalue()),
            )
            written = score.loads(
                (workspace / "written.score.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                ["note", "rest", "note"],
                [event["kind"] for event in written["parts"][0]["events"]],
            )
            self.assertEqual(source, score.loads((workspace / "source.score.json").read_text()))
            self.assertFalse((workspace / "current.score.json").exists())

    def test_voicing_command_uses_exact_selector_and_explicit_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            source = timeline_score()
            (workspace / "source.score.json").write_text(
                score.dumps(source),
                encoding="utf-8",
            )
            (workspace / "voicing.json").write_text(
                json.dumps(
                    {
                        "positions": [
                            {
                                "selector": {
                                    "location": {"bar": 1, "beat": [1, 1]},
                                    "voice": 1,
                                    "pitch": {"step": "E", "alter": 0, "octave": 4},
                                },
                                "position": {"string": 2, "fret": 5},
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "score",
                        "voicing",
                        "source.score.json",
                        "guitar-1",
                        "--input",
                        "voicing.json",
                        "--output",
                        "voiced.score.json",
                    ]
                )

            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            self.assertEqual(
                {
                    "id": source["id"],
                    "output": "voiced.score.json",
                    "part": "guitar-1",
                    "positioned_notes": 2,
                },
                json.loads(stdout.getvalue()),
            )
            voiced = score.loads(
                (workspace / "voiced.score.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                {"string": 2, "fret": 5},
                voiced["parts"][0]["events"][0]["position"],
            )
            self.assertEqual(source, score.loads((workspace / "source.score.json").read_text()))

    def test_rhythm_command_uses_explicit_selector_input_and_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            source = timeline_score()
            source["parts"][0]["events"][2].pop("tuplet")
            score.validate(source)
            (workspace / "source.score.json").write_text(
                score.dumps(source),
                encoding="utf-8",
            )
            (workspace / "rhythm.json").write_text(
                json.dumps(
                    {
                        "rhythm": [
                            {
                                "selector": {
                                    "location": {"bar": 2, "beat": [1, 1]},
                                    "voice": 2,
                                    "pitch": {"step": "G", "alter": 0, "octave": 4},
                                },
                                "location": {"bar": 2, "beat": [2, 1]},
                                "duration": [1, 8],
                                "voice": 1,
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "score",
                        "rhythm",
                        "source.score.json",
                        "guitar-1",
                        "--input",
                        "rhythm.json",
                        "--output",
                        "rhythmic.score.json",
                    ]
                )

            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            written = score.loads(
                (workspace / "rhythmic.score.json").read_text(encoding="utf-8")
            )
            moved = [
                event
                for event in written["parts"][0]["events"]
                if event.get("pitch") == {"step": "G", "alter": 0, "octave": 4}
            ][0]
            self.assertEqual({"bar": 2, "beat": [2, 1]}, moved["location"])
            self.assertEqual([1, 8], moved["duration"])
            self.assertEqual(source, score.loads((workspace / "source.score.json").read_text()))

    def test_technique_command_uses_explicit_selector_input_and_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            source = timeline_score()
            (workspace / "source.score.json").write_text(
                score.dumps(source),
                encoding="utf-8",
            )
            (workspace / "technique.json").write_text(
                json.dumps(
                    {
                        "technique": [
                            {
                                "selector": {
                                    "location": {"bar": 1, "beat": [1, 1]},
                                    "voice": 1,
                                    "pitch": {"step": "E", "alter": 0, "octave": 4},
                                },
                                "articulations": ["accent", "tenuto"],
                                "techniques": [{"name": "vibrato"}],
                                "dynamics": "ff",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "score",
                        "technique",
                        "source.score.json",
                        "guitar-1",
                        "--input",
                        "technique.json",
                        "--output",
                        "expressive.score.json",
                    ]
                )

            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            self.assertEqual(
                {
                    "expressive_notes": 1,
                    "id": source["id"],
                    "output": "expressive.score.json",
                    "part": "guitar-1",
                },
                json.loads(stdout.getvalue()),
            )
            written = score.loads(
                (workspace / "expressive.score.json").read_text(encoding="utf-8")
            )
            note = written["parts"][0]["events"][0]
            self.assertEqual(["accent", "tenuto"], note["articulations"])
            self.assertEqual([{"name": "vibrato"}], note["techniques"])
            self.assertEqual("ff", note["dynamics"])
            self.assertEqual(
                source,
                score.loads((workspace / "source.score.json").read_text(encoding="utf-8")),
            )

    def test_render_musicxml_to_stdout_or_explicit_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            source = timeline_score()
            (workspace / "source.score.json").write_text(
                score.dumps(source),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "score",
                        "render",
                        "source.score.json",
                        "--format",
                        "musicxml",
                    ]
                )

            self.assertEqual(0, result)
            self.assertTrue(stdout.getvalue().startswith('<?xml version="1.0" encoding="UTF-8"?>'))
            self.assertIn("generic-technique", stderr.getvalue())
            self.assertFalse((workspace / "source.musicxml").exists())

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "score",
                        "render",
                        "source.score.json",
                        "--format",
                        "musicxml",
                        "--output",
                        "generated/source.musicxml",
                    ]
                )

            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            summary = json.loads(stdout.getvalue())
            self.assertEqual("musicxml", summary["format"])
            self.assertEqual("generated/source.musicxml", summary["output"])
            self.assertEqual("generic-technique", summary["diagnostics"][0]["code"])
            exported = (workspace / "generated" / "source.musicxml").read_text(encoding="utf-8")
            self.assertTrue(exported.startswith('<?xml version="1.0" encoding="UTF-8"?>'))
            self.assertEqual(source, score.loads((workspace / "source.score.json").read_text()))

    def test_render_midi_supports_section_tempo_and_sidecar_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            source = realization_score()
            (workspace / "source.score.json").write_text(score.dumps(source), encoding="utf-8")

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace", str(workspace),
                        "score", "render", "source.score.json",
                        "--format", "midi",
                        "--section", "Chorus",
                        "--tempo", "75%",
                        "--output", "generated/chorus.mid",
                    ]
                )

            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            metadata = json.loads(stdout.getvalue())
            self.assertEqual("score-midi-v1", metadata["render_path"])
            self.assertEqual([3, 4], metadata["bar_range"])
            self.assertEqual("Chorus", metadata["section"])
            self.assertEqual(0.75, metadata["tempo_factor"])
            report = midi.inspect((workspace / "generated" / "chorus.mid").read_bytes())
            self.assertGreaterEqual(report["tracks"], 1)
            sidecar = json.loads((workspace / "generated" / "chorus.mid.json").read_text())
            self.assertEqual(metadata, sidecar)
            self.assertEqual(source, score.loads((workspace / "source.score.json").read_text()))

    def test_render_midi_requires_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "source.score.json").write_text(
                score.dumps(realization_score()), encoding="utf-8"
            )
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace", str(workspace),
                        "score", "render", "source.score.json",
                        "--format", "midi",
                    ]
                )
            self.assertEqual(65, result)
            self.assertIn("requires --output", stderr.getvalue())

    def test_play_uses_generated_artifact_and_player_provenance(self) -> None:
        class FakePlayer:
            def __init__(self, *args, **kwargs) -> None:
                pass

            def play(self, data: bytes) -> PlaybackResult:
                self.data = data
                return PlaybackResult("fake-player", "1.0", "fixture.sf2")

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "source.score.json").write_text(
                score.dumps(realization_score()), encoding="utf-8"
            )
            soundfont = workspace / "fixture.sf2"
            soundfont.write_bytes(b"sf2")
            stdout = io.StringIO()
            stderr = io.StringIO()
            with mock.patch(
                "guitar_practice.interfaces.cli.score_handlers.FluidSynthMidiPlayer",
                FakePlayer,
            ), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace", str(workspace),
                        "score", "play", "source.score.json",
                        "--section", "Chorus",
                        "--soundfont", "fixture.sf2",
                    ]
                )

            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            payload = json.loads(stdout.getvalue())
            self.assertEqual("fake-player", payload["playback"]["player"])
            artifact = workspace / payload["artifact"]
            self.assertTrue(artifact.is_file())
            self.assertTrue(Path(str(artifact) + ".json").is_file())
            self.assertEqual([3, 4], payload["bar_range"])

    def test_play_without_soundfont_still_retains_generated_midi(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "source.score.json").write_text(
                score.dumps(realization_score()), encoding="utf-8"
            )
            stdout = io.StringIO()
            stderr = io.StringIO()
            with mock.patch.dict("os.environ", {}, clear=True), \
                 contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace", str(workspace),
                        "score", "play", "source.score.json",
                        "--output", "generated/no-soundfont.mid",
                    ]
                )

            self.assertEqual(69, result)
            self.assertIn("SoundFont is required", stderr.getvalue())
            self.assertIn("MIDI artifact retained", stderr.getvalue())
            self.assertTrue((workspace / "generated" / "no-soundfont.mid").is_file())
            self.assertTrue((workspace / "generated" / "no-soundfont.mid.json").is_file())

    def test_playback_failure_retains_generated_midi(self) -> None:
        class FailingPlayer:
            def __init__(self, *args, **kwargs) -> None:
                pass

            def play(self, data: bytes) -> PlaybackResult:
                raise MidiPlaybackError("audio device unavailable")

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "source.score.json").write_text(
                score.dumps(realization_score()), encoding="utf-8"
            )
            (workspace / "fixture.sf2").write_bytes(b"sf2")
            stdout = io.StringIO()
            stderr = io.StringIO()
            with mock.patch(
                "guitar_practice.interfaces.cli.score_handlers.FluidSynthMidiPlayer",
                FailingPlayer,
            ), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace", str(workspace),
                        "score", "play", "source.score.json",
                        "--output", "generated/audition.mid",
                        "--soundfont", "fixture.sf2",
                    ]
                )

            self.assertEqual(69, result)
            self.assertIn("audio device unavailable", stderr.getvalue())
            self.assertTrue((workspace / "generated" / "audition.mid").is_file())
            self.assertTrue((workspace / "generated" / "audition.mid.json").is_file())

    def test_render_requires_explicit_score_and_rejects_output_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            source = timeline_score()
            (workspace / "source.score.json").write_text(score.dumps(source), encoding="utf-8")

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                missing_score = main(["--workspace", str(workspace), "score", "render"])
            self.assertEqual(2, missing_score)

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                escaped = main(
                    [
                        "--workspace",
                        str(workspace),
                        "score",
                        "render",
                        "source.score.json",
                        "--format",
                        "musicxml",
                        "--output",
                        "../escaped.musicxml",
                    ]
                )
            self.assertEqual(65, escaped)
            self.assertIn("workspace-relative", stderr.getvalue())

    def test_authoring_commands_require_explicit_output_and_form_rejects_nonempty_score(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            draft = {
                "schema": score.SCHEMA_ID,
                "version": score.SCHEMA_VERSION,
                "id": "draft",
                "metadata": {"title": "Draft"},
                "bars": [{"number": 1}],
                "meter_map": [{"bar": 1, "beats": 4, "beat_unit": 4}],
                "tempo_map": [],
                "parts": [],
                "harmony": [
                    {"location": {"bar": 1, "beat": [1, 1]}, "symbol": "C"}
                ],
            }
            (workspace / "draft.score.json").write_text(score.dumps(draft), encoding="utf-8")

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                missing_output = main(
                    [
                        "--workspace",
                        str(workspace),
                        "score",
                        "chords",
                        "draft.score.json",
                        "C",
                    ]
                )
            self.assertEqual(2, missing_output)

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                unsafe_form = main(
                    [
                        "--workspace",
                        str(workspace),
                        "score",
                        "form",
                        "draft.score.json",
                        "verse:4",
                        "--output",
                        "changed.score.json",
                    ]
                )
            self.assertEqual(65, unsafe_form)
            self.assertIn("empty draft", stderr.getvalue())
            self.assertFalse((workspace / "changed.score.json").exists())

    def test_import_writes_canonical_score_ir_and_tracks_reads_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            shutil.copyfile(FIXTURE, workspace / "song.musicxml")

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "score",
                        "import",
                        "song.musicxml",
                        "--output",
                        "generated/song.score.json",
                    ]
                )

            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            summary = json.loads(stdout.getvalue())
            self.assertEqual("song", summary["id"])
            self.assertEqual(4, summary["parts"])

            output = workspace / "generated" / "song.score.json"
            document = score.loads(output.read_text(encoding="utf-8"))
            self.assertEqual("guitar-practice.score", document["schema"])
            self.assertNotIn("song", document)

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "score",
                        "tracks",
                        "generated/song.score.json",
                    ]
                )

            self.assertEqual(0, result)
            self.assertEqual("", stderr.getvalue())
            tracks = json.loads(stdout.getvalue())
            self.assertEqual("song", tracks["id"])
            self.assertEqual(
                ["guitar", "bass", "drums", "keys"],
                [track["role"] for track in tracks["tracks"]],
            )
            self.assertEqual(
                {"program": 29, "channel": 1},
                tracks["tracks"][0]["midi"],
            )
            self.assertEqual(
                {"channel": 10, "percussion": True},
                tracks["tracks"][2]["midi"],
            )
            self.assertFalse((workspace / "scripts").exists())

    def test_import_rejects_workspace_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(
                    [
                        "--workspace",
                        str(workspace),
                        "score",
                        "import",
                        "../song.musicxml",
                        "--output",
                        "song.score.json",
                    ]
                )

            self.assertEqual(65, result)
            self.assertIn("workspace-relative", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
