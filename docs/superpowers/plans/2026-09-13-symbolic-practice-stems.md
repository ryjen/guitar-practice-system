# Symbolic Practice Stems Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend imported Song IR with note events, derive non-mutating tempo realizations, select conservative backing/drum stems, and render deterministic Type-1 MIDI artifacts through native `guitarctl` commands.

**Architecture:** MusicXML remains an import adapter into a tool-neutral Song domain. Pure domain functions own note-event validation, tempo-map scaling, stem selection, and MIDI byte rendering using existing `guitar_practice.domain.midi` primitives. Application services own JSON loading and artifact persistence; CLI handlers only parse arguments, call services, and render stable output/errors.

**Tech Stack:** Python 3.12+, stdlib `xml.etree.ElementTree`, existing package MIDI primitives, `unittest`, `guitarctl` command registry.

**Spec:** `docs/superpowers/specs/2026-09-13-guitar-pro-rc3-import-design.md`

## Global Constraints

- `guitarctl` remains the only executable surface; do not add score-specific scripts or executables.
- Practice tempo is derived symbolic state and must never mutate canonical imported tempo.
- Unknown/ambiguous tracks remain included in backing output unless explicitly excluded.
- Guitar/BOSS/MuseScore details do not enter canonical Song IR.
- MIDI rendering remains pure and receives no filesystem/process authority.
- Stdout is result/data output; diagnostics go to stderr; retain stable exit-code conventions from #94/#100.
- Reuse the existing MIDI encoder instead of introducing a second MIDI implementation.

---
### Task 1: Canonical note events and MusicXML import

**Files:**
- Modify: `guitar_practice/domain/song.py`
- Modify: `guitar_practice/domain/musicxml.py`
- Modify: `tests/fixtures/musicxml/multitrack.musicxml`
- Modify: `tests/test_song_domain.py`
- Modify: `tests/test_musicxml_import.py`

**Interfaces:**
- Produces: `NoteEvent(position: float, duration: float, midi_note: int, velocity: int = 80)` and `SongTrack.notes: tuple[NoteEvent, ...]`.
- MusicXML parsing maps pitched notes and percussion `midi-unpitched` identities to deterministic MIDI note events in quarter-note units.

- [ ] **Step 1: Write failing domain/parser tests** proving note validation, JSON round-trip, chord onset sharing, rests, and percussion-note import.
- [ ] **Step 2: Run targeted tests** and verify failures are caused by missing `NoteEvent`/note parsing.
- [ ] **Step 3: Implement the minimal note record and MusicXML cursor parsing**, handling `divisions`, `note/chord`, `rest`, duration, pitch, and percussion identity without adding notation-authoring concerns.
- [ ] **Step 4: Run song, MusicXML, and layering tests** and keep them green.
- [ ] **Step 5: Commit** as `feat: preserve imported note events`.

### Task 2: Pure tempo realization and stem selection

**Files:**
- Create: `guitar_practice/domain/song_stems.py`
- Create: `tests/test_song_stems.py`

**Interfaces:**
- Produces: `scale_tempo(song: Song, factor: float) -> Song`.
- Produces: `select_backing_tracks(song: Song, *, include_track_ids=(), exclude_track_ids=()) -> tuple[SongTrack, ...]`.
- Produces: `select_drum_tracks(song: Song, *, include_track_ids=(), exclude_track_ids=()) -> tuple[SongTrack, ...]`.

- [ ] **Step 1: Write failing tests** for multi-tempo proportional scaling, canonical immutability, invalid factors, default guitar exclusion, unknown-track retention, drum-only selection, and explicit track-id override precedence.
- [ ] **Step 2: Run targeted tests** and confirm the transform/selection APIs are absent.
- [ ] **Step 3: Implement pure transforms** using immutable dataclass replacement/copy semantics; reject unknown explicit track ids rather than silently ignoring them.
- [ ] **Step 4: Run stem, song, and layering tests** and confirm canonical Song data is unchanged after realization.
- [ ] **Step 5: Commit** as `feat: add symbolic tempo and stem transforms`.

### Task 3: Deterministic imported-song MIDI renderer

**Files:**
- Modify: `guitar_practice/domain/midi.py` only if a small reusable primitive is genuinely missing.
- Create: `guitar_practice/domain/song_midi.py`
- Create: `tests/test_song_midi.py`

**Interfaces:**
- Consumes: `Song`, selected `SongTrack` values, `TempoPoint`, `MeterPoint`, and existing `midi.TimedEvent`, `midi.note_events`, `midi.track_bytes`, `midi.meta`, `midi.midi_chunk`.
- Produces: `render_song_midi(song: Song, tracks: Sequence[SongTrack]) -> bytes`.

- [ ] **Step 1: Write failing tests** proving Type-1 header/track count, proportional tempo metadata, meter metadata, melodic program/channel events, drum channel semantics, deterministic bytes, and no excluded-guitar note events.
- [ ] **Step 2: Run tests** and verify failure because `song_midi` does not exist.
- [ ] **Step 3: Implement the minimal pure conductor/track renderer** by composing existing MIDI primitives; do not add filesystem or subprocess behavior.
- [ ] **Step 4: Validate generated bytes structurally in tests** and run existing MIDI/generation/layering suites.
- [ ] **Step 5: Commit** as `feat: render imported song stems to midi`.

### Task 4: Application services and native CLI surface

**Files:**
- Create: `guitar_practice/application/song_stems.py`
- Modify: `guitar_practice/interfaces/cli/score_handlers.py` only for shared song-document loading helpers if useful.
- Create: `guitar_practice/interfaces/cli/stem_handlers.py`
- Modify: `guitar_practice/interfaces/cli/commands.py`
- Modify: `guitar_practice/interfaces/cli/handler_registry.py`
- Create: `tests/test_song_stem_application.py`
- Create: `tests/test_native_stem_cli.py`
- Modify: `docs/cli.md`

**Interfaces:**
- Produces: package-native `guitarctl backing render SONG --tempo PERCENT --output PATH [--include-track ID] [--exclude-track ID]` for MIDI output in this slice.
- Keeps `guitarctl drums export` reserved for slice 4 where `--target boss-rc3` has real WAV/profile semantics; do not create a misleading partial hardware-export command.
- Application output metadata records source id, selected/excluded track ids, and tempo factor next to the MIDI artifact.
- [ ] **Step 1: Write failing application/CLI tests** for workspace-relative input/output, `75%` tempo parsing, no-guitar default selection, explicit track include/exclude, native registry entries, quiet file-output stdout, and structured metadata persistence.
- [ ] **Step 2: Run tests** and confirm failure because the application service/handler are absent.
- [ ] **Step 3: Implement the application orchestration and thin native handlers**, reusing `JsonFileStore`/`BinaryFileStore`; keep path containment checks at the interface/adapter boundary.
- [ ] **Step 4: Update CLI docs** to distinguish symbolic `backing render` from future audio/RC-3 export and to cross-reference #95 authoring rather than creating duplicate song-building commands.
- [ ] **Step 5: Run targeted tests, public-boundary validation, and the complete unit suite** from a clean worktree.
- [ ] **Step 6: Commit and push**, then review exact-head CI before taking PR #109 out of draft.

## Self-review

- Spec coverage: this plan covers delivery slice 2 only—note events, tempo scaling, stem selection, backing/drum symbolic MIDI foundations. Audio rendering and RC-3 WAV export remain later slices by design.
- CLI coordination: `score import|tracks` stays import/inspection; #95 retains authoring under `song`; #94 remains the common registry/runtime; #97/#100 remain independent migration issues.
- No partial `drums export` is exposed before it can honor the hardware-profile contract.
- Type consistency: all renderers consume immutable `Song`/`SongTrack`; tempo positions and note positions use quarter-note units established by the importer.
