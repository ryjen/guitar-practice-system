# M3 Slide Real Session

Status: pre-session plan only. Leave every observation/result field blank until after playing.

## Fixed realization

- Primary target: slide intonation and two-hand muting
- Technique ID: slide-foundations
- Backing track: slide-slow-blues-a-60
- Backing section: PRACTICE-A
- Key / harmony: A dominant twelve-bar blues
- Tempo: 60 BPM
- Meter: 4/4
- Tuning: standard
- Guitar: choose PRS or Strat and keep it unchanged for baseline and verification
- Slide: choose one material/finger and keep it unchanged
- Diagnostic tone: clean or edge-of-breakup; minimal delay/reverb
- Target duration: about 30 minutes
- Stop condition: pain, unusual hand/shoulder tension, or deteriorating pitch control after simplification

## Space constraint

Use a two-bar call followed by a two-bar response window. During the call, prefer no more than four intentional notes per bar. Let sustained notes decay instead of filling the response window.

## Prepare — about 5 minutes

- Match sustained fretted/reference pitches with the slide on at least three strings.
- Check minimum slide pressure directly over the fret.
- Check fretting-hand muting behind the slide.
- Check picking-hand muting on unused strings.
- Play one delayed-vibrato note that starts centred and ends centred.

Preparation success cue: pitch and muting are stable enough to record a representative baseline without repeated restarts.

## Baseline — 30 to 60 seconds

Record one uninterrupted take containing:

- sustained reference-note matches
- at least one fret-to-fret movement
- one adjacent-string transition
- one short phrase with intentional space

Do not restart to manufacture a best take.

- Recording reference:
- What remained credible:
- Largest audible defect observed:
- Physical tension / fatigue before isolation:

## Isolate the largest defect

Choose one branch only after hearing the baseline.

| Observed defect | Isolation |
| --- | --- |
| Sharp/flat arrival | One string, two target frets, sustained reference pitch, no vibrato |
| Adjacent-string noise | Alternate two strings slowly; separate fretting-hand and picking-hand muting checks |
| Uncontrolled vibrato | Hold centred pitch first; add vibrato only after two beats; stop on centre |
| Timing / late arrival | Use a bounded click at the current 60 BPM realization; simplify movement before changing tempo |
| Attack/release noise | Quarter-note attacks/releases on one string with effects minimized |

- Defect selected:
- Variables held constant:
- Simplification used:
- Clean-repetition criterion:
- What happened:

## Reintegration

Return to slide-slow-blues-a-60 at 60 BPM.

Record one complete PRACTICE-A chorus. Keep the same guitar, slide, tuning, and diagnostic tone used for the baseline.

- Did isolated control survive the changing harmony? yes / no / unknown
- Did the backing density help or obscure intonation/muting?
- Did the two-bar response windows remain genuinely open?
- Largest defect in musical context:

## Verification take

Record a second bounded take comparable with the baseline.

- Recording reference:
- Comparable to baseline: yes / no
- Intentional changed variable, if any:
- What improved:
- What did not transfer:
- Largest remaining audible defect:
- Physical tension / fatigue after the session:

## Evidence

Fill only from the actual takes.

- Date:
- Attempted realization: slide-slow-blues-a-60 / 60 BPM / standard tuning
- Timing observation:
- Pitch / intonation observation:
- Articulation / muting observation:
- Dynamics observation:
- Phrase identity observation:
- Space observation:
- Recovery observation:
- Plan deviations:
- Next action: maintain / change / simplify / increase constraint / discard

## Optional #87 end-to-end handoff

Prefer this slide session for the first complete lifecycle because existing slide evidence, assessment, and scheduling examples already exercise the same target.

After recording the real observations:

1. Capture a new evidence record using templates/evidence.json. Do not reuse the populated example observations.
2. If multiple records are summarized, place the real records under the existing records input shape and run guitarctl evidence feedback.
3. Translate only observed/approved facts into the assessment context and run guitarctl assess evaluate with the existing gate set.
4. Explicitly approve or reject any proposed progression-state change.
5. Put only the approved state into the scheduling snapshot and run guitarctl schedule propose.

A failed or unknown gate is a valid result. The objective is to test the handoffs, not force a promotion.
