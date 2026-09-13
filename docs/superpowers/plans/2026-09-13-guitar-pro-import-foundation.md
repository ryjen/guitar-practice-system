# Guitar Pro Import Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first #108 vertical slice: a minimal canonical Song IR, deterministic track-role classification, MusicXML parsing, a bounded MuseScore conversion adapter, and native `guitarctl score import` / `score tracks` inspection.

**Architecture:** Keep musical representation and classification pure in `domain/song.py`. Put filesystem/process authority behind application ports and adapters; MuseScore converts Guitar Pro to MusicXML, while a parser maps MusicXML bytes to Song IR. CLI handlers compose adapters/application services without teaching the domain about files, subprocesses, or MuseScore.

**Tech Stack:** Python 3.12 stdlib (`dataclasses`, `enum`, `xml.etree.ElementTree`, `subprocess`, `pathlib`, `tempfile`, `json`), existing `guitar_practice` domain/application/adapter/interface layers, `unittest`.

**Spec:** `docs/superpowers/specs/2026-09-13-guitar-pro-rc3-import-design.md`

## Global Constraints

- `guitarctl` is the stable interface.
- Guitar Pro and MuseScore details must not appear in canonical Song IR.
- Imported titles/track names are untrusted data and must never become executable shell text or unchecked output paths.
- Heuristic role classification is non-destructive; unknown/ambiguous tracks remain `unknown` until explicitly resolved.
- The initial importer accepts `.gp`, `.gp3`, `.gp4`, `.gp5`, `.gpx`, `.musicxml`, and `.xml` only.
- MuseScore conversion uses argv execution (`shell=False`) and an explicit executable name/path.
- Tests must not require MuseScore to be installed.

---

### Task 1: Canonical Song IR and deterministic role classification

**Files:**
- Create: `guitar_practice/domain/song.py`
- Create: `tests/test_song_domain.py`

**Interfaces:**
- Produces: `TrackRole`, `ClassificationSource`, `TrackClassification`, `SongTrack`, `TempoPoint`, `MeterPoint`, `Song`, `classify_track(...)`, `song_to_dict(song)` and `song_from_dict(document)`.

- [ ] **Step 1: Write failing domain tests**

Cover deterministic precedence and non-destructive fallback:

```python
classification = classify_track(
    name="Lead Guitar",
    instrument_name="Electric Guitar",
    midi_program=29,
    is_percussion=False,
)
self.assertEqual(TrackRole.GUITAR, classification.role)
self.assertEqual(ClassificationSource.INSTRUMENT, classification.source)

unknown = classify_track(
    name="Mystery Layer",
    instrument_name=None,
    midi_program=None,
    is_percussion=False,
)
self.assertEqual(TrackRole.UNKNOWN, unknown.role)
```

Also prove percussion beats name heuristics, explicit overrides beat all inferred sources, duplicate track ids are rejected, BPM/meter values are validated, and dict round-trip is deterministic.

- [ ] **Step 2: Run the tests and confirm RED**

Run: `python -m unittest tests.test_song_domain -v`
Expected: import failure because `guitar_practice.domain.song` does not exist.

- [ ] **Step 3: Implement the minimal pure domain model**

Use frozen dataclasses and string enums. Classification precedence is explicit override → instrument → MIDI program family → percussion → name heuristic → unknown, except percussion identity is treated as authoritative source metadata before weak name heuristics. Validate stable ids with a conservative `[A-Za-z0-9._-]+` rule; display names remain unrestricted data.

- [ ] **Step 4: Run targeted + layering tests**

Run:

```bash
python -m unittest tests.test_song_domain -v
python -m unittest tests.test_layering -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add guitar_practice/domain/song.py tests/test_song_domain.py
git commit -m "feat: add canonical imported song model"
```

---

### Task 2: Parse MusicXML into Song IR

**Files:**
- Create: `guitar_practice/domain/musicxml.py`
- Create: `tests/fixtures/musicxml/multitrack.musicxml`
- Create: `tests/test_musicxml_import.py`

**Interfaces:**
- Consumes: Song IR from Task 1.
- Produces: `parse_musicxml(data: bytes, *, source_id: str) -> Song` and `MusicXmlError`.

- [ ] **Step 1: Add a compact fixture and failing parser tests**

Fixture contains lead guitar, bass, drum-set/percussion and keys parts; includes a 120 BPM start tempo and a later 90 BPM change plus 4/4 meter. Tests assert stable part-derived ids, title preservation, role/provenance classification, percussion detection, tempo points, and meter points.

```python
song = parse_musicxml(FIXTURE.read_bytes(), source_id="fixture")
self.assertEqual("Fixture Song", song.title)
self.assertEqual(["guitar", "bass", "drums", "keys"], [t.classification.role.value for t in song.tracks])
self.assertEqual([120.0, 90.0], [point.bpm for point in song.tempo_map])
```

Malformed XML and a document without `score-partwise` must raise `MusicXmlError` rather than leaking parser exceptions.

- [ ] **Step 2: Run and confirm RED**

Run: `python -m unittest tests.test_musicxml_import -v`
Expected: import failure because parser does not exist.

- [ ] **Step 3: Implement parser with stdlib XML only**

Parse part-list metadata, MIDI program/channel/unpitched information, first/changed tempo markers, and time signatures required by this slice. Preserve display strings as data. Unsupported notation is ignored only when it is irrelevant to the import-foundation contract; malformed required structure raises `MusicXmlError`.

- [ ] **Step 4: Run parser/domain/layering tests**

```bash
python -m unittest tests.test_musicxml_import tests.test_song_domain tests.test_layering -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add guitar_practice/domain/musicxml.py tests/fixtures/musicxml/multitrack.musicxml tests/test_musicxml_import.py
git commit -m "feat: parse MusicXML into song model"
```

---

### Task 3: Application import service and bounded converter port

**Files:**
- Modify: `guitar_practice/application/ports.py`
- Create: `guitar_practice/application/score_import.py`
- Create: `tests/test_score_import_application.py`

**Interfaces:**
- Produces port `ScoreConverter.convert(source_path: str) -> ConvertedScore`.
- Produces `ConvertedScore(musicxml: bytes, converter: str, converter_version: str | None)`.
- Produces service `ImportScore(converter, documents).execute(source_path, output_path) -> Song`.

- [ ] **Step 1: Write failing application tests using a fake converter**

```python
class FakeConverter:
    def convert(self, source_path: str) -> ConvertedScore:
        self.seen = source_path
        return ConvertedScore(FIXTURE.read_bytes(), "fake", "1")
```

Assert `.musicxml` can bypass external conversion through a direct adapter in the next task, converted provenance is serialized next to canonical Song data, invalid extensions fail closed, and application logic does not import concrete adapters.

- [ ] **Step 2: Run and confirm RED**

Run: `python -m unittest tests.test_score_import_application -v`
Expected: missing application service/port.

- [ ] **Step 3: Implement service and port**

The application service validates source extension from the path supplied by the trusted CLI/workspace boundary, asks the converter for MusicXML, calls `parse_musicxml`, writes deterministic JSON through `JsonDocumentStore`, and returns the Song. Do not perform subprocess or direct filesystem work here.

- [ ] **Step 4: Run targeted + layering tests**

```bash
python -m unittest tests.test_score_import_application tests.test_layering -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add guitar_practice/application/ports.py guitar_practice/application/score_import.py tests/test_score_import_application.py
git commit -m "feat: add score import application boundary"
```

---

### Task 4: MuseScore and direct-MusicXML adapters

**Files:**
- Create: `guitar_practice/adapters/score_conversion.py`
- Create: `tests/test_score_conversion_adapter.py`

**Interfaces:**
- Consumes: `ScoreConverter` / `ConvertedScore` from Task 3.
- Produces: `MuseScoreConverter(workspace, executable="MuseScore4")` and `DirectMusicXmlConverter(workspace)`.

- [ ] **Step 1: Write failing adapter tests**

Patch `subprocess.run` and assert the exact argv shape:

```python
["MuseScore4", "-o", str(output_path), str(source_path)]
```

No string command and no `shell=True` are permitted. Assert source and temporary output resolve under the configured workspace, converter failure produces `ScoreConversionError`, and direct `.musicxml` reads bytes without subprocess execution.

- [ ] **Step 2: Run and confirm RED**

Run: `python -m unittest tests.test_score_conversion_adapter -v`
Expected: missing adapter.

- [ ] **Step 3: Implement bounded adapters**

Use `Path.resolve()` containment checks, `tempfile.TemporaryDirectory(dir=workspace)` for conversion output, `subprocess.run(argv, check=False, capture_output=True, shell=False)`, and an explicit version probe isolated from score metadata. Never derive output filenames from score title/track names.

- [ ] **Step 4: Run adapter/application/layering tests**

```bash
python -m unittest tests.test_score_conversion_adapter tests.test_score_import_application tests.test_layering -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add guitar_practice/adapters/score_conversion.py tests/test_score_conversion_adapter.py
git commit -m "feat: add bounded MuseScore conversion adapter"
```

---

### Task 5: Native `guitarctl score import` and `score tracks`

**Files:**
- Modify: `guitar_practice/interfaces/cli/commands.py`
- Create: `guitar_practice/interfaces/cli/score_handlers.py`
- Modify: `guitar_practice/interfaces/cli/handler_registry.py`
- Create: `tests/test_native_score_cli.py`
- Modify: `docs/cli.md`

**Interfaces:**
- Produces native handlers `score-import` and `score-tracks`.

- [ ] **Step 1: Write failing CLI tests**

Assert both command specs are `MigrationState.NATIVE`. Use a `.musicxml` fixture copied into a temporary workspace so CI needs no MuseScore installation:

```bash
guitarctl --workspace TMP score import fixture.musicxml --output songs/fixture.json
guitarctl --workspace TMP score tracks songs/fixture.json
```

`score tracks` emits deterministic JSON containing stable id, display name, role, classification source, and instrument/percussion metadata. It must not emit filesystem paths outside the workspace.

- [ ] **Step 2: Run and confirm RED**

Run: `python -m unittest tests.test_native_score_cli -v`
Expected: unregistered score commands.

- [ ] **Step 3: Implement handlers and registration**

`score import` chooses `DirectMusicXmlConverter` for `.xml/.musicxml`; Guitar Pro extensions use `MuseScoreConverter`, configurable via `--musescore` with default `mscore`. `score tracks` reads canonical JSON through `JsonFileStore` and deserializes with `song_from_dict` before emitting normalized inspection output.

- [ ] **Step 4: Run targeted and full repository validation**

```bash
python -m unittest tests.test_native_score_cli tests.test_song_domain tests.test_musicxml_import tests.test_score_import_application tests.test_score_conversion_adapter -v
python scripts/check_public_boundary.py
python -m unittest discover -s tests -v
```

Expected: all PASS.

- [ ] **Step 5: Update CLI docs and commit**

Document the stable commands and note that Guitar Pro import requires a configured MuseScore executable while MusicXML inspection does not.

```bash
git add guitar_practice/interfaces/cli/commands.py guitar_practice/interfaces/cli/score_handlers.py guitar_practice/interfaces/cli/handler_registry.py tests/test_native_score_cli.py docs/cli.md
git commit -m "feat: add native score import and inspection CLI"
```

---

## Slice review gate

Before starting symbolic stem/tempo work:

- [ ] all repository workflows are green on the exact PR head;
- [ ] layering tests prove domain/application boundaries remain inward-only;
- [ ] CLI tests prove MusicXML import runs in CI without MuseScore;
- [ ] adapter tests prove Guitar Pro conversion uses bounded argv execution with no shell interpolation;
- [ ] review confirms no Song IR field contains MuseScore/RC-3-specific state;
- [ ] update #108 with slice status and any discovered constraints.
