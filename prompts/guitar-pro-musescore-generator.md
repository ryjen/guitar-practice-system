# Guitar Pro / MuseScore Generator Prompt

```text
Generate a notation-oriented starting point for guitar practice.

Input:
- Practice idea: {{practice_idea}}
- Instrument / tuning: {{instrument_tuning}}
- Key / mode: {{key_mode}}
- Tempo: {{tempo}}
- Difficulty: {{difficulty}}
- Output target: Guitar Pro, MuseScore, MusicXML, or Markdown tab

Output:
1. Title
2. Tuning and capo assumptions
3. Tempo / meter / key
4. Section or exercise length
5. Plain-English fingering guidance
6. Simple tab draft if useful
7. MusicXML-oriented notes if useful
8. Import/export notes for MuseScore or Guitar Pro
9. What should remain source-of-truth in Markdown

Rules:
- Keep notation practical, not exhaustive
- Avoid relying on proprietary binary formats as canonical source
- Prefer MusicXML for interchange when notation becomes important
- Include rhythm counts when tab alone is ambiguous
```
