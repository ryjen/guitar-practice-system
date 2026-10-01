# Guitar Pro to practice backing and BOSS RC-3

This workflow imports Guitar Pro or MusicXML into canonical Score IR, derives slowed practice realizations without mutating the score, renders a no-guitar backing MIDI artifact, and exports the drum realization as a BOSS RC-3-compatible WAV.

## Enter the pinned toolchain

Use the repository flake so MuseScore, FluidSynth, ffmpeg, Python, `guitarctl`, and the default SoundFont are provided by the repository rather than the runner or host:

```bash
nix develop
```

The shell sets `GUITAR_SOUNDFONT` to the pinned FluidR3 GM2 SoundFont.

## Import the score

For Guitar Pro input, `guitarctl` invokes the bounded MuseScore conversion adapter and then imports the resulting MusicXML into canonical Score IR:

```bash
guitarctl score import songs/example.gp5 \
  --output generated/example.score.json
```

MusicXML can be imported directly:

```bash
guitarctl score import songs/example.musicxml \
  --output generated/example.score.json
```

The source file remains an input artifact. The JSON output is canonical Score IR. Simple forward/backward repeats and ordinary first/second endings remain written-form bar metadata in Score IR rather than being flattened during import. D.C./D.S./coda navigation is still unsupported and fails closed.

Inspect imported parts and their role/provenance before generating practice artifacts:

```bash
guitarctl score tracks generated/example.score.json
guitarctl score validate generated/example.score.json
```

Heuristic guitar classifications are not silently removed. Authoritative guitar roles are excluded from backing by default; ambiguous parts remain unless explicitly excluded.

## Render a slowed no-guitar backing track

Render a 75% practice realization as deterministic Type-1 MIDI:

```bash
guitarctl backing render generated/example.score.json \
  --tempo 75% \
  --output generated/practice/example-backing-75.mid
```

The canonical score is not modified. For a full-song render, bounded canonical repeat/ending notation is first expanded into a generated linear playback realization; tempo, meter, events, and other bar-local content are remapped deterministically before MIDI rendering. A sidecar at
`generated/practice/example-backing-75.mid.json` records the source score, generated realization, selected/excluded part IDs, tempo factor, and optional structural selection.

Explicit overrides remain available:

```bash
guitarctl backing render generated/example.score.json \
  --tempo 75% \
  --exclude-part rhythm-guitar \
  --include-part mystery-part \
  --output generated/practice/example-backing-75.mid
```

Focused practice can use either an exact bar range or a named section:

```bash
guitarctl backing render generated/example.score.json \
  --tempo 60% \
  --bars 42:58 \
  --output generated/practice/example-bars42-58-60.mid

guitarctl backing render generated/example.score.json \
  --tempo 70% \
  --section Chorus \
  --output generated/practice/example-chorus-70.mid
```

Structural `--bars` / `--section` slicing continues to fail closed when canonical repeat/ending notation inside the requested range would make the slice ambiguous. Full-song rendering performs the bounded playback expansion automatically; focused slicing never guesses across unresolved form boundaries.

## Export drums for the BOSS RC-3

The default RC-3 export uses the full score and selects drum parts only:

```bash
guitarctl drums export generated/example.score.json \
  --tempo 75% \
  --target boss-rc3
```

The deterministic default output is written under `generated/rc3/`. The export also preserves the source MIDI and writes a provenance sidecar.

An explicit output path is supported:

```bash
guitarctl drums export generated/example.score.json \
  --tempo 75% \
  --target boss-rc3 \
  --output generated/rc3/example-drums-75pct.wav
```

Focused loop exports use musical structure, never silence trimming:

```bash
guitarctl drums export generated/example.score.json \
  --tempo 70% \
  --target boss-rc3 \
  --section Chorus

guitarctl drums export generated/example.score.json \
  --tempo 60% \
  --target boss-rc3 \
  --bars 42:58
```

The RC-3 profile enforces:

- 44.1 kHz;
- stereo;
- 16-bit linear PCM WAV;
- exact score-derived duration;
- deterministic filenames.

FluidSynth is an adapter, not canonical state. Renderer version, SoundFont identity, PCM profile, source score/realization, selected parts, tempo factor, and structural range are written to the sidecar metadata.

## Failure boundaries

Import, symbolic realization, MIDI rendering, audio rendering, and hardware-profile validation fail independently.

If FluidSynth fails, the deterministic drum MIDI has already been written and remains available for inspection or rendering elsewhere. External process calls use explicit argv with `shell=False` and bounded timeouts.

This workflow produces portable WAV/MIDI artifacts only. It does not inspect, overwrite, or synchronize BOSS RC-3 phrase memory.
