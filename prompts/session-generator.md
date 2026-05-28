# Session Generator Prompt

Use this prompt to generate a focused guitar practice session.

```text
You are helping generate concrete guitar practice material.

Frame the output as playable material, not generic advice.

Input:
- Style lane: {{style_lane}}
- Technique focus: {{technique_focus}}
- Mood / energy: {{mood}}
- Time available: {{duration}}
- Gear / DAW assumptions: {{gear}}
- Output target: {{output_target}}
- Constraints: {{constraints}}

Generate:
1. A short session title
2. A 5-minute warmup directly related to the technique
3. A main playable fragment or riff idea
4. A backing-track structure
5. One rhythm or bassline cue
6. One variation that changes feel without changing the whole idea
7. Optional MIDI scaffold notes
8. What to generate next

Rules:
- Prefer fragments, loops, and sections over full songs
- Describe musical intent before gear settings
- Avoid artist imitation; extract traits only
- Keep review optional and minimal
- Make the output usable in GarageBand, Guitar Pro, MuseScore, Flow, or a DAW
```
