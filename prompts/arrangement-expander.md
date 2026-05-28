# Arrangement Expander Prompt

```text
Expand a small guitar fragment into a practice arrangement.

Input:
- Fragment description: {{fragment}}
- Style lane: {{style_lane}}
- Tempo / key: {{tempo_key}}
- Current backing idea: {{backing_idea}}
- Target length: {{target_length}}
- Constraint: {{constraint}}

Output:
1. What the fragment does musically
2. Section map
3. How the fragment changes per section
4. Bassline changes
5. Drum energy changes
6. Texture / effect changes
7. Transition cue between sections
8. One stripped-down version
9. One expanded version

Rules:
- Preserve the identity of the fragment
- Expand by changing density, register, rhythm, or texture
- Do not add complexity unless it improves the practice goal
- Keep full-song writing optional
```
