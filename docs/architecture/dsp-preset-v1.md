# guitar-dsp preset v1 producer boundary

Related: ryjen/dsp#7, ryjen/guitar-practice-system#152.

`guitar-practice-system` is the control-plane producer of the frozen
`guitar-dsp.preset` v1 document. It validates human-authored JSON and emits
canonical protocol bytes; it does not import DSP implementation or hardware
state.

Canonical fixture:

```json
{"schema":"guitar-dsp.preset","version":1,"preset":"jazz-blues","tempo_bpm":92,"parameters":{"delay.feedback_milli":320,"delay.free_ms":375,"delay.mix_milli":500,"delay.subdivision":"dotted-eighth"}}
```

The authoritative cross-repo semantics are tracked in `ryjen/dsp#7`.
This repository independently implements the same frozen v1 values and
canonical bytes. No source-tree dependency is permitted in either direction.

Initial CLI surface:

```text
guitarctl dsp preset validate <document>
guitarctl dsp preset canonicalize <document>
```

No device transport, implicit Score IR mapping, or practice-state mutation is
part of v1.
