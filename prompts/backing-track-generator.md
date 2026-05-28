# Backing Track Generator Prompt

```text
Generate a backing-track spec for guitar practice.

Input:
- Style lane: {{style_lane}}
- Tempo range: {{tempo_range}}
- Key / mode: {{key_mode}}
- Duration / section count: {{duration_or_sections}}
- Guitar role: {{guitar_role}}
- Bass role: {{bass_role}}
- Drum feel: {{drum_feel}}
- DAW target: {{daw_target}}

Output a DAW-neutral spec with:
1. Title
2. Tempo and time signature
3. Key / mode
4. Section map with bar counts
5. Chord or drone plan
6. Bassline behavior by section
7. Drum behavior by section
8. Cue points for guitar entries
9. Energy curve
10. Export notes for GarageBand or another DAW

Rules:
- Keep it playable and loopable
- Use simple harmonic material unless complexity is requested
- Make the bass and drums strong enough to practice against
- Do not over-arrange the first version
```
