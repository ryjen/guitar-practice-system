# Guitar DSP preset v1 contract

guitarctl owns authoring, strict validation, and canonical emission of the
minimal guitar-to-DSP preset contract. The independent consumer contract is
tracked by **ryjen/dsp#7**. The DSP repository validates and applies supported
realtime controls; neither repository imports the other's source tree.

This contract is intentionally an external control document. It is **not**
Score IR, a practice plan, a progression, a key/mode model, a hardware
description, or a transport packet.

## Envelope

Version 1 has exactly five top-level fields:

~~~json
{
  "schema": "guitar-dsp.preset",
  "version": 1,
  "preset": "jazz-blues",
  "tempo_bpm": 92,
  "parameters": {
    "delay.feedback_milli": 320,
    "delay.free_ms": 375,
    "delay.mix_milli": 500,
    "delay.subdivision": "dotted-eighth"
  }
}
~~~

Unknown or missing top-level fields and parameter IDs fail closed. Version 1 is
a complete delay-control snapshot rather than a partial patch, so all four
parameter IDs are required.

The portable JSON Schema is at
**contracts/dsp/guitar-dsp-preset-v1.schema.json**.

The canonical interoperability fixture is at
**contracts/dsp/fixtures/jazz-blues-preset-v1.json**.

## Parameter semantics

| Field | v1 domain | Meaning |
|---|---:|---|
| preset | lowercase slug, max 64 chars | Stable preset identity only |
| tempo_bpm | integer 20..300 | Normalized tempo supplied to tempo-aware delay |
| delay.feedback_milli | integer 0..950 | Feedback scaled by 1000; 320 means 0.320 |
| delay.free_ms | integer 1..2000 | Free-running delay time in milliseconds |
| delay.mix_milli | integer 0..1000 | Wet/dry mix scaled by 1000; 500 means 0.500 |
| delay.subdivision | fixed enum | Selects free or tempo-synchronized delay mode |

The subdivision enum is:

~~~text
free
quarter
dotted-eighth
eighth
eighth-triplet
sixteenth
~~~

**delay.subdivision** is the delay-time mode selector. When it is **free**,
**delay.free_ms** is the active delay time. For the musical subdivision values,
the consumer resolves delay time from **tempo_bpm** and the selected
subdivision. **delay.free_ms** remains explicit state so switching back to free
mode does not depend on an ambient/default value.

Scaled integers are deliberate. The wire contract does not use binary floating
point for feedback or mix, which keeps canonical JSON byte-stable across
languages.

## Canonical JSON

Canonical serialization is UTF-8 JSON with:

- lexicographically sorted object keys;
- no insignificant whitespace;
- one trailing newline;
- duplicate object keys rejected while decoding;
- non-finite numeric tokens rejected;
- exact schema/version validation before emission.

The canonical jazz-blues fixture is therefore exactly:

~~~json
{"parameters":{"delay.feedback_milli":320,"delay.free_ms":375,"delay.mix_milli":500,"delay.subdivision":"dotted-eighth"},"preset":"jazz-blues","schema":"guitar-dsp.preset","tempo_bpm":92,"version":1}
~~~

## guitarctl

Validate without rewriting the document:

~~~bash
guitarctl dsp preset validate contracts/dsp/fixtures/jazz-blues-preset-v1.json
~~~

Emit canonical bytes:

~~~bash
guitarctl dsp preset canonicalize contracts/dsp/fixtures/jazz-blues-preset-v1.json
~~~

Both commands require an explicit workspace-relative input. Stdout is data;
validation diagnostics go to stderr. Invalid contract data returns the stable
data-error exit code 65.

## Boundary and non-goals

Version 1 deliberately contains no:

- device path, serial port, MIDI/SysEx packet, USB detail, or hardware ID;
- shell command, arbitrary file path, executable payload, or callback;
- Score IR state, song form, progression, key, mode, practice-session state, or
  assessment/evidence state;
- implicit rule for deriving effects from musical/practice data;
- device-send/apply command.

A later transport adapter may carry the canonical document, but transport and
realtime application remain outside this slice and outside the practice domain.
