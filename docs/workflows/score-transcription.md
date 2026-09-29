# Guided score transcription workflow

This workflow uses canonical Score IR as the only editable state and reaches a MuseScore-importable MusicXML artifact without introducing a wizard-specific song model.

## 1. Start from a score with an explicit guitar part

For the current end-to-end workflow, import an existing MusicXML or Guitar Pro skeleton so the canonical Score IR already contains the guitar part/instrument identity that later note and TAB authoring targets:

```bash
guitarctl score import inputs/blue-thing.musicxml \
  --output scores/blue-thing.score.json

guitarctl score edit scores/blue-thing.score.json
```

A Guitar Pro source can be used instead; the bounded MuseScore conversion adapter still produces the same canonical Score IR.

`score init` intentionally creates a minimal score with no parts. From-scratch part/instrument creation is a separate deterministic authoring capability and is not implied by this workflow.

Inside the editor, changes remain in memory until `save`.

## 2. Establish form and harmony

```text
score-edit> form intro:2 verse:4 solo:4 outro:2
score-edit> chords Cmaj7 | A7 | Dm7 G7 | Cmaj7 | Fmaj7 | Em7 A7 | Dm7 G7 | Cmaj7 | Fmaj7 | G7 | Cmaj7 | Cmaj7
score-edit> context
score-edit> validate
```

For section-scoped harmony, use a quoted section label when needed:

```text
score-edit> chords --section "Verse" Cmaj7 | A7 | Dm7 G7 | Cmaj7
```

## 3. Add notes

Structured note input uses the same JSON envelope as the non-interactive `score notes` command:

```json
{
  "notes": [
    {
      "location": {"bar": 1, "beat": [1, 1]},
      "duration": [1, 4],
      "voice": 1,
      "pitch": {"step": "E", "alter": 0, "octave": 4}
    }
  ]
}
```

```text
score-edit> notes guitar-1 inputs/notes.json
```

## 4. Add guitar position, rhythm, and technique

Voicing, rhythm, and technique reuse the exact-selector contracts from the deterministic commands:

```text
score-edit> voicing guitar-1 inputs/voicing.json
score-edit> rhythm guitar-1 inputs/rhythm.json
score-edit> technique guitar-1 inputs/technique.json
score-edit> validate
```

Each operation produces another validated in-memory Score IR working copy. Invalid or ambiguous edits are rejected without modifying the source file.

## 5. Audition before saving

```text
score-edit> play --section "Verse"
score-edit> play --bars 3:6 --output generated/blue-thing-verse.mid
```

Playback uses the #113 Score IR MIDI realization/application boundary. MIDI and provenance are persisted before FluidSynth is invoked. A player, SoundFont, or audio-device failure therefore does not lose the preview artifact and does not modify the score.

## 6. Export a MuseScore preview

```text
score-edit> export generated/blue-thing.musicxml
```

The export uses the #112 deterministic MusicXML exporter directly against the unsaved working Score IR. Standard notation and guitar TAB/string/fret information are included where represented. The repository's flake-backed CI verifies that generated guitar MusicXML imports in MuseScore.

The canonical score is still unchanged at this point. Use `cancel` to discard the working copy.

## 7. Commit the edit

```text
score-edit> save
```

Before replacement, the editor validates the working Score IR and re-reads the source. If the source changed after the session started, save fails closed instead of overwriting concurrent changes. Successful persistence uses the atomic `ScoreFileStore` path.

## Future inference proposals

AI or deterministic helpers can present a transient proposal without becoming canonical state:

```json
{
  "action": "chords",
  "value": "G7#9",
  "confidence": 0.71,
  "alternatives": ["G7", "G7b9"],
  "source": "chord-specialist"
}
```

Proposal metadata remains outside Score IR. Once a user or policy accepts a proposal, it must enter the score through the same deterministic authoring operation as a manually entered value.
