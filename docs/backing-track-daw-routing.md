# Backing-Track DAW Assignment and Routing

This document defines the intended DAW-side interpretation of the portable backing-track MIDI. It is a routing target, not a claim that a particular DAW import has already been verified.

The manifest and generated Type-1 MIDI remain canonical. GarageBand and REAPER projects are optional realizations.

## Common track mapping

| MIDI track | DAW assignment | Routing intent | Guitar-space rule |
|---|---|---|---|
| `Conductor` | No instrument | Preserve tempo, meter, key, count-in, and section markers where the DAW supports them | Never render as an audible instrument |
| `Drums` | Restrained acoustic/rock/country kit as appropriate | Stereo drum instrument to a simple rhythm bus | Avoid fills or cymbal density that obscure attack, muting, or wah timing |
| `Bass` | Clean electric bass | Mono/stereo instrument to a low-frequency rhythm bus | Keep fills sparse and stay below the guitar's principal register |
| `Keys` | Electric piano or plain piano | Stereo keys bus with conservative ambience | Prefer simple voicings; reduce or mute if it competes with guitar phrasing |
| `Pad` | Soft sustained pad | Stereo ambience bus | Roll back upper-mid density so sustained E-Bow lines remain distinct |

General MIDI program numbers in the manifest are hints only. Do not choose a DAW instrument merely to match a General MIDI patch if another stock instrument better serves the practice goal.

## Baseline routing

Use a deliberately simple practice mix before any production treatment:

```text
Drums -----> Rhythm bus ----\
Bass ------> Rhythm bus -----+--> Main output
Keys/Pad --> Support bus ----/
Guitar ----> Guitar input --------> Main output
```

Recommended constraints:

- keep each MIDI track independently routable and muteable;
- keep the guitar on its own live/recorded input path;
- avoid master-bus compression while diagnosing technique;
- avoid side-chain or tempo-synced effects until marker/loop alignment is verified;
- preserve a dry/minimally processed version of each practice scaffold;
- use conservative monitoring levels and leave headroom for the live guitar.

## Track-specific assignments

### `slide-slow-blues-a-60`

- **Drums:** dry restrained blues/rock kit.
- **Bass:** round electric bass.
- **Keys:** soft electric piano.
- **Guitar space:** avoid upper-register keyboard fills; the slide should carry sustained melody and response phrases.
- **Primary loop:** `PRACTICE-A` through `END`; optionally loop one 12-bar section while diagnosing intonation/muting.

### `ebow-ambient-bed-d-56`

- **Drums:** very restrained kit; mute entirely for activation/sustain diagnostics if useful.
- **Bass:** round electric bass with minimal articulation.
- **Pad:** slow soft pad with modest high-frequency content.
- **Guitar space:** reserve the upper-mid register and long decay windows for E-Bow melody, drones, and counter-lines.
- **Primary loop:** `DRONE` through `END`; `DRONE` alone is useful for activation and string-change work.

### `wah-rhythmic-groove-em-96`

- **Drums:** tight dry funk/rock kit with an obvious pulse.
- **Bass:** short supportive electric bass.
- **Keys:** light electric piano; mute it for the most exposed timing checks.
- **Guitar space:** rhythm guitar owns the subdivision layer; supporting instruments should not add busy sixteenth-note figures.
- **Primary loop:** `GROOVE-A` through `END`; isolate `GROOVE-A` for repeatable pedal-motion comparisons.

### `country-i-iv-v-g-100`

- **Drums:** restrained country/roots kit.
- **Bass:** clean electric bass emphasizing root/fifth support.
- **Keys:** minimal piano.
- **Guitar space:** leave upper strings clear for hybrid-picked fills, double-stops, and pedal-steel bends.
- **Primary loop:** `I-IV-V` through `END`; isolate the first section for clean diagnostic work.

### `country-rock-form-a-108`

- **Drums:** firmer country-rock backbeat.
- **Bass:** simple root/fifth support.
- **Keys:** sparse piano.
- **Guitar space:** the guitar should alternate deliberately between accompaniment and fill roles rather than play continuously.
- **Primary loop:** `RHYTHM-A` through `END`; section markers explicitly identify `RHYTHM-A`, `FILL-B`, `RHYTHM-C`, and `TURNAROUND`.

## GarageBand verification target

When the files are tested in GarageBand, record whether:

- conductor tempo and meter are imported correctly;
- named instrument tracks remain separate;
- section markers are retained, transformed, or lost;
- the count-in bar remains aligned;
- channel/program hints cause unwanted instrument assignment;
- loop boundaries land exactly on bar lines;
- any octave or drum-map adjustments are required.

Do not silently edit the manifest merely to accommodate a GarageBand-specific quirk. Document the import behavior first.

## REAPER verification target

When the same files are tested in REAPER, record whether:

- tracks import separately rather than as one merged item;
- tempo and meter populate the project correctly;
- MIDI marker events require conversion to REAPER project markers;
- track names survive import;
- channel/program hints need to be ignored or remapped;
- loop boundaries and count-in align to the grid;
- the same source file remains portable after instrument assignment.

Prefer a small reusable REAPER routing template over track-specific opaque project state.

## Verification status

The routing model above is documented, but hands-on DAW interoperability remains intentionally separate.

| DAW | Import verified | Track names | Tempo/meter | Markers | Loop boundaries | Routing notes |
|---|---|---|---|---|---|---|
| GarageBand | No | Pending | Pending | Pending | Pending | Target mapping documented above |
| REAPER | No | Pending | Pending | Pending | Pending | Target mapping documented above |

Update this table only after importing the generated files into the actual DAW.
