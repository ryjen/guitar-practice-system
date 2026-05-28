# MIDI Scaffold Generator Prompt

```text
Generate a source-first MIDI scaffold spec for guitar practice.

Input:
- Style lane: {{style_lane}}
- Tempo: {{tempo}}
- Time signature: {{time_signature}}
- Key / mode: {{key_mode}}
- Length: {{bars}}
- Tracks needed: {{tracks}}
- Practice purpose: {{practice_purpose}}

Output:
1. Title
2. Musical intent
3. Tempo / meter / key
4. Track list
5. Section map
6. Bassline rhythm and pitch outline
7. Drum cue pattern, not full drum programming unless requested
8. Chord vamp or drone notes
9. Guitar entry cues
10. JSON-like MIDI sketch suitable for later scripting

Rules:
- Keep the scaffold minimal
- Prefer repeatable loops
- Avoid dense note data unless necessary
- Explain assumptions clearly
- Generated MIDI should be considered disposable unless curated
```
