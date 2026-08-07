const REPOSITORY_URL = 'https://github.com/ryjen/guitar-practice-system';
const durationAllocations = {
  15: [4, 7, 4],
  30: [8, 14, 8],
  45: [12, 21, 12],
};

const sessions = [
  {
    technique: 'Slide',
    key: 'A minor',
    meter: '4/4',
    title: 'Intonation before vocabulary',
    intent: 'Make pitch arrival, muting, and release credible before adding speed or density.',
    useCaseTitle: 'Slow-blues response phrases',
    useCaseCopy: 'Two-bar answers over a sparse 12-bar scaffold.',
    gearTitle: 'Clear attack, long decay',
    gearCopy: 'Low-gain compression, restrained drive, short delay, clean headroom.',
    space: 'Leave beat four empty after every answer.',
    tempo: { slow: 52, medium: 64, fast: 72, pulse: 'quarter-note', beatsPerBar: 4 },
    stages: [
      ['Arrival drill', 'Match target pitch, then remove visual correction.'],
      ['Two-note answers', 'Use one stable tone and one expressive arrival.'],
      ['Record evidence', 'Capture three passes and identify the largest defect.'],
    ],
    sourceLabel: 'Open slow-blues backing-track source',
    sourceHref: `${REPOSITORY_URL}/blob/main/backing-tracks/slide-slow-blues/manifest.json`,
  },
  {
    technique: 'Wah',
    key: 'E minor',
    meter: '4/4',
    title: 'Rhythm before sweep range',
    intent: 'Treat the pedal as a timing and articulation device rather than a continuous effect.',
    useCaseTitle: 'Muted sixteenth-note hook',
    useCaseCopy: 'One-bar call-and-response over a restrained rock groove.',
    gearTitle: 'Controlled midrange motion',
    gearCopy: 'Compressor before wah, modest drive, noise gate only as needed.',
    space: 'Mute the final eighth note of every second bar.',
    tempo: { slow: 72, medium: 84, fast: 96, pulse: 'quarter-note', beatsPerBar: 4 },
    stages: [
      ['Quarter-note centres', 'Land the pedal consistently on the beat.'],
      ['Syncopated accents', 'Move only on selected sixteenth-note attacks.'],
      ['Record evidence', 'Check whether pedal motion strengthens or obscures the groove.'],
    ],
    sourceLabel: 'Open wah technique setup source',
    sourceHref: `${REPOSITORY_URL}/blob/main/docs/gear/technique-setups.md`,
  },
  {
    technique: 'E-Bow',
    key: 'D major',
    meter: '6/8',
    title: 'Activation without the swell becoming the phrase',
    intent: 'Control entry timing, string changes, and decay so the sustained line serves the arrangement.',
    useCaseTitle: 'Drone and counterline',
    useCaseCopy: 'A sparse upper-register response over a D–G movement.',
    gearTitle: 'Stable sustain, low noise',
    gearCopy: 'Clean guitar, restrained compression, long but quiet delay return.',
    space: 'Wait one full dotted quarter before answering.',
    tempo: { slow: 48, medium: 56, fast: 64, pulse: 'dotted-quarter', beatsPerBar: 2 },
    stages: [
      ['Activation point', 'Produce repeatable entries at three dynamic levels.'],
      ['String transition', 'Cross strings without an uncontrolled volume spike.'],
      ['Record evidence', 'Review entry timing, pitch centre, and arrangement space.'],
    ],
    sourceLabel: 'Open E-Bow and sustain source',
    sourceHref: `${REPOSITORY_URL}/blob/main/docs/ebow-and-sustain.md`,
  },
  {
    technique: 'Hybrid picking',
    key: 'A major',
    meter: '4/4',
    title: 'Country articulation as a colour layer',
    intent: 'Add snap, separation, and chord-tone targeting without turning the session into a separate curriculum.',
    useCaseTitle: 'Eighties-rock turnaround',
    useCaseCopy: 'Apply selective double-stops and open-string pull-offs to a familiar rock cadence.',
    gearTitle: 'Fast clean response',
    gearCopy: 'Strat or PRS split-coil sound, light compression, minimal ambience.',
    space: 'Cap each phrase at six notes and leave the next beat empty.',
    tempo: { slow: 76, medium: 92, fast: 104, pulse: 'quarter-note', beatsPerBar: 4 },
    stages: [
      ['String-pair control', 'Alternate pick and fingers without volume imbalance.'],
      ['Chord-tone target', 'Resolve each lick to the next chord, not the scale box.'],
      ['Record evidence', 'Decide whether the country layer supports or distracts from the core sound.'],
    ],
    sourceLabel: 'Open country-over-eighties-rock session source',
    sourceHref: `${REPOSITORY_URL}/blob/main/examples/musical-dimensions/country-over-eighties-rock-session.md`,
  },
];

const techniques = [
  { name: 'Slide', copy: 'Pitch, vibrato, muting, arrival, and release.', items: ['Intonation gates', 'Position-independent phrasing', 'Brass / glass / ring slide'] },
  { name: 'Wah', copy: 'Rhythmic control, vowel shape, accents, and range.', items: ['Beat-centred motion', 'Syncopated articulation', 'Noise-aware gain staging'] },
  { name: 'E-Bow', copy: 'Activation, sustain, drones, counterlines, and texture.', items: ['Dynamic entries', 'String transitions', 'Arrangement role'] },
  { name: 'Country branch', copy: 'Hybrid picking, snap, voice leading, and vocabulary.', items: ['Selective layering', 'Double-stops', 'Chord-tone resolution'] },
];

const layers = {
  technique: {
    title: 'Technique owns learning progress',
    copy: 'Every session begins with an audible problem and ends with evidence against a quality gate. A technique may use many songs, gear setups, and backing tracks without losing its identity.',
    flow: ['audible defect', 'exercise', 'quality gate', 'recording evidence', 'next target'],
  },
  song: {
    title: 'Songs validate integration',
    copy: 'A song section is a use case for one or more techniques. It tests transitions, endurance, recovery, arrangement awareness, and whether the skill survives real musical context.',
    flow: ['song section', 'technique mapping', 'arrangement cue', 'full take', 'integration review'],
  },
  gear: {
    title: 'Gear makes intent repeatable',
    copy: 'The signal chain captures purpose, order, sensitive ranges, gain staging, and noise behaviour. It supports a technique but never owns progress.',
    flow: ['sound intent', 'instrument', 'signal order', 'sensitive controls', 'noise check'],
  },
  backing: {
    title: 'Backing tracks create portable context',
    copy: 'Source specs define key, tempo, meter, feel, form, parts, and explicit space. MIDI and DAW exports are generated outputs that can be replaced.',
    flow: ['source spec', 'arrangement scaffold', 'named MIDI tracks', 'DAW import', 'promoted artifact'],
  },
};

let currentSessionIndex = 0;
let selectedDuration = 30;
let selectedTempoLevel = 'slow';
let currentBpm = sessions[0].tempo.slow;
let audioContext;
let schedulerTimer;
let nextClickTime = 0;
let currentBeat = 0;
let metronomeRunning = false;

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

function setPressed(buttons, activeButton) {
  buttons.forEach((button) => {
    const active = button === activeButton;
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', String(active));
  });
}

function renderStages(session) {
  const allocations = durationAllocations[selectedDuration];
  const stageElements = session.stages.map(([title, copy], index) => {
    const item = document.createElement('li');
    const content = document.createElement('div');
    const heading = document.createElement('strong');
    const description = document.createElement('small');
    const time = document.createElement('span');

    heading.textContent = title;
    description.textContent = copy;
    time.className = 'stage-time';
    time.textContent = `${allocations[index]} min`;
    content.append(heading, description);
    item.append(content, time);
    return item;
  });
  $('#session-stages').replaceChildren(...stageElements);
}

function updateMetronomeDisplay(session, resetTempo = false) {
  if (resetTempo) {
    selectedTempoLevel = 'slow';
    currentBpm = session.tempo.slow;
  }

  ['slow', 'medium', 'fast'].forEach((level) => {
    $(`#tempo-${level}`).textContent = session.tempo[level];
  });
  $('#tempo-input').value = currentBpm;

  const tempoButtons = $$('[data-tempo-level]');
  const activeButton = tempoButtons.find((button) => button.dataset.tempoLevel === selectedTempoLevel);
  setPressed(tempoButtons, activeButton);
  updateMetronomeStatus();
}

function renderSession(index, { resetTempo = true } = {}) {
  const session = sessions[index];
  $('#session-technique').textContent = session.technique;
  $('#session-meta').textContent = `${session.key} · target ${session.tempo.fast} BPM · ${session.meter}`;
  $('#session-title').textContent = session.title;
  $('#session-intent').textContent = session.intent;
  $('#use-case-title').textContent = session.useCaseTitle;
  $('#use-case-copy').textContent = session.useCaseCopy;
  $('#gear-title').textContent = session.gearTitle;
  $('#gear-copy').textContent = session.gearCopy;
  $('#space-rule').textContent = session.space;
  $('#session-source').textContent = session.sourceLabel;
  $('#session-source').href = session.sourceHref;
  renderStages(session);
  updateMetronomeDisplay(session, resetTempo);
}

function renderTechniques() {
  const cards = techniques.map((technique, index) => {
    const article = document.createElement('article');
    article.className = 'technique-card card';

    const number = document.createElement('span');
    number.className = 'number';
    number.textContent = String(index + 1).padStart(2, '0');

    const heading = document.createElement('h3');
    heading.textContent = technique.name;

    const copy = document.createElement('p');
    copy.textContent = technique.copy;

    const list = document.createElement('ul');
    technique.items.forEach((item) => {
      const listItem = document.createElement('li');
      listItem.textContent = item;
      list.append(listItem);
    });

    article.append(number, heading, copy, list);
    return article;
  });
  $('#technique-grid').replaceChildren(...cards);
}

function renderLayer(key) {
  const layer = layers[key];
  const label = document.createElement('p');
  label.className = 'label';
  label.textContent = 'Selected layer';

  const heading = document.createElement('h3');
  heading.textContent = layer.title;

  const copy = document.createElement('p');
  copy.textContent = layer.copy;

  const flow = document.createElement('div');
  flow.className = 'flow';
  layer.flow.forEach((item) => {
    const step = document.createElement('span');
    step.textContent = item;
    flow.append(step);
  });

  $('#layer-detail').replaceChildren(label, heading, copy, flow);
}

function stopMetronome() {
  if (schedulerTimer) {
    window.clearInterval(schedulerTimer);
    schedulerTimer = undefined;
  }
  metronomeRunning = false;
  currentBeat = 0;
  $('#metronome-toggle').textContent = 'Start click';
  $('#metronome-toggle').setAttribute('aria-pressed', 'false');
  updateMetronomeStatus();
}

function scheduleClick(time, accented) {
  const oscillator = audioContext.createOscillator();
  const gain = audioContext.createGain();
  oscillator.frequency.value = accented ? 1200 : 800;
  gain.gain.setValueAtTime(0.0001, time);
  gain.gain.exponentialRampToValueAtTime(0.25, time + 0.002);
  gain.gain.exponentialRampToValueAtTime(0.0001, time + 0.04);
  oscillator.connect(gain);
  gain.connect(audioContext.destination);
  oscillator.start(time);
  oscillator.stop(time + 0.05);
}

function runScheduler() {
  const session = sessions[currentSessionIndex];
  while (nextClickTime < audioContext.currentTime + 0.1) {
    scheduleClick(nextClickTime, currentBeat === 0);
    nextClickTime += 60 / currentBpm;
    currentBeat = (currentBeat + 1) % session.tempo.beatsPerBar;
  }
}

async function startMetronome() {
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) {
    $('#metronome-status').textContent = 'This browser does not support the Web Audio metronome.';
    return;
  }

  audioContext ||= new AudioContextClass();
  await audioContext.resume();
  nextClickTime = audioContext.currentTime + 0.05;
  currentBeat = 0;
  metronomeRunning = true;
  runScheduler();
  schedulerTimer = window.setInterval(runScheduler, 25);
  $('#metronome-toggle').textContent = 'Stop click';
  $('#metronome-toggle').setAttribute('aria-pressed', 'true');
  updateMetronomeStatus();
}

function updateMetronomeStatus() {
  const session = sessions[currentSessionIndex];
  const state = metronomeRunning ? `Playing ${currentBpm} BPM` : 'Stopped';
  $('#metronome-status').textContent = `${state} · ${session.tempo.pulse} pulse · ${session.tempo.beatsPerBar} beats per bar.`;
}

$('#shuffle-session').addEventListener('click', () => {
  stopMetronome();
  let nextIndex = currentSessionIndex;
  while (nextIndex === currentSessionIndex) {
    nextIndex = Math.floor(Math.random() * sessions.length);
  }
  currentSessionIndex = nextIndex;
  renderSession(currentSessionIndex);
  $('#today').scrollIntoView({ behavior: prefersReducedMotion.matches ? 'auto' : 'smooth', block: 'start' });
});

$$('[data-duration]').forEach((button) => button.addEventListener('click', () => {
  selectedDuration = Number(button.dataset.duration);
  setPressed($$('[data-duration]'), button);
  renderStages(sessions[currentSessionIndex]);
}));

$$('[data-layer]').forEach((button) => button.addEventListener('click', () => {
  setPressed($$('[data-layer]'), button);
  renderLayer(button.dataset.layer);
}));

$$('[data-tempo-level]').forEach((button) => button.addEventListener('click', () => {
  const session = sessions[currentSessionIndex];
  selectedTempoLevel = button.dataset.tempoLevel;
  currentBpm = session.tempo[selectedTempoLevel];
  setPressed($$('[data-tempo-level]'), button);
  $('#tempo-input').value = currentBpm;
  updateMetronomeStatus();
}));

$('#tempo-input').addEventListener('change', (event) => {
  const parsed = Number(event.target.value);
  currentBpm = Math.min(240, Math.max(30, Number.isFinite(parsed) ? parsed : 60));
  event.target.value = currentBpm;
  selectedTempoLevel = 'custom';
  setPressed($$('[data-tempo-level]'), undefined);
  updateMetronomeStatus();
});

$('#metronome-toggle').addEventListener('click', () => {
  if (metronomeRunning) {
    stopMetronome();
  } else {
    startMetronome().catch(() => {
      stopMetronome();
      $('#metronome-status').textContent = 'The browser could not start audio. Check site audio permissions.';
    });
  }
});

$('#review-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const session = sessions[currentSessionIndex];
  const note = [
    '# Practice review',
    '',
    `- Technique: ${session.technique}`,
    `- Session duration: ${selectedDuration} minutes`,
    `- Metronome: ${currentBpm} BPM (${session.tempo.pulse} pulse)`,
    `- Largest audible defect: ${$('#defect').value}`,
    `- Observation: ${$('#observation').value.trim() || 'Not recorded'}`,
    `- Next action: ${$('#next-action').value.trim() || 'Not recorded'}`,
  ].join('\n');

  $('#review-output').value = note;
  $('#review-output-wrap').hidden = false;

  try {
    await navigator.clipboard.writeText(note);
    $('#form-status').textContent = 'Review note created and copied to the clipboard.';
  } catch {
    $('#review-output').focus();
    $('#review-output').select();
    $('#form-status').textContent = 'Review note created. Clipboard access was unavailable, so the note is selected for manual copying.';
  }
});

window.addEventListener('pagehide', stopMetronome);
document.addEventListener('visibilitychange', () => {
  if (document.hidden) stopMetronome();
});
renderSession(currentSessionIndex);
renderTechniques();
renderLayer('technique');
