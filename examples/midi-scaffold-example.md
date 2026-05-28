# MIDI Scaffold Example

## Title

Post-punk E minor bass scaffold

## Musical intent

Create a minimal MIDI backing scaffold for practicing clipped guitar accents and wah punctuation over a driving bassline.

## Global settings

- BPM: 142
- Time signature: 4/4
- Key / mode: E minor
- Bars: 24
- Feel: straight eighths

## Tracks

| Track | Instrument | Role |
|---|---|---|
| Drums | basic rock kit | pulse and section cues |
| Bass | electric bass | eighth-note motor |
| Chords | muted synth/guitar pad | section harmony guide |
| Cue | simple bell / click | guitar entry markers |

## Section map

| Section | Bars | Notes |
|---|---:|---|
| Intro | 1-4 | bass establishes pulse |
| A | 5-12 | guitar accent cue on bar 5 |
| B | 13-20 | higher hook cue on bar 13 |
| Break | 21-24 | tom cue, bass simplified |

## JSON-like sketch

```json
{
  "title": "post-punk-e-minor-bass-scaffold",
  "bpm": 142,
  "time_signature": "4/4",
  "key": "E minor",
  "bars": 24,
  "tracks": [
    {
      "name": "bass",
      "pattern": "E E G E | D E B E",
      "subdivision": "eighth"
    },
    {
      "name": "drum_cues",
      "kick": "1 and 3",
      "snare": "2 and 4",
      "break": "bars 21-24 tom pulse"
    },
    {
      "name": "guitar_cues",
      "events": [
        { "bar": 5, "label": "clipped accents enter" },
        { "bar": 13, "label": "higher hook enters" },
        { "bar": 21, "label": "wah response phrase" }
      ]
    }
  ]
}
```

## Export notes

Render to `generated/post-punk-e-minor-bass-scaffold.mid` when a generator exists. Do not commit the generated output unless it becomes curated practice material.
