import './style.css';
import type { Incident, ScenarioPreset, IncidentStatus } from './types';

type SpeechRecognitionResultEventLike = Event & { results: SpeechRecognitionResultList };
type SpeechRecognitionErrorEventLike = Event & { error?: string };
type SpeechRecognitionInstance = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start(): void;
  stop(): void;
  onresult: ((event: SpeechRecognitionResultEventLike) => void) | null;
  onstart: (() => void) | null;
  onend: (() => void) | null;
  onerror: ((event: SpeechRecognitionErrorEventLike) => void) | null;
};
type SpeechRecognitionConstructor = new () => SpeechRecognitionInstance;

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }
}

const PRESET_SCENARIOS: ScenarioPreset[] = [
  {
    id: 'cold-storage',
    badge: 'COLD CHAIN',
    title: 'Cold Room Temperature Spike',
    description: 'Refrigeration unit failure in storage dock',
    transcript: 'The cold room at North Dock is reading 12 degrees. Product is still inside, and Maya from facilities is on site. Please get the temperature back under control before the morning shift. This is urgent.'
  },
  {
    id: 'substation',
    badge: 'HIGH VOLTAGE',
    title: 'Transformer Thermal Runaway',
    description: 'Overheating auxiliary transformer unit',
    transcript: 'Transformer 3B in South Substation is showing thermal runaway at 94 degrees Celsius. Dave from high-voltage is on site isolated from the feed. Need emergency cooling fan replacement immediately.'
  },
  {
    id: 'chemical-reactor',
    badge: 'SAFETY / HAZARD',
    title: 'Reactor Pressure Anomaly',
    description: 'Exceeding safe relief valve thresholds',
    transcript: 'Reactor tank 4 in Sector B is exhibiting rapid pressure spikes above 85 PSI. Marcus from process engineering is monitoring the relief valves. Need manual depressurization protocol initiated asap.'
  },
  {
    id: 'san-storage',
    badge: 'IT / INFRA',
    title: 'SAN Storage Array Degradation',
    description: 'Double drive fault in storage cluster',
    transcript: 'SAN Storage Cluster Delta in Rack 18 had double drive failure with degraded RAID array. Elena from DevOps is on site preparing hot spares. Rebuild must start before midnight to avoid SLA breach.'
  }
];

const MAX_CAPTURE_MS = 45_000;
let currentTranscript = '';
let isListening = false;
let audioUrl: string | null = null;
let recognition: SpeechRecognitionInstance | null = null;
let captureTimer: number | null = null;
let activeIncidents: Incident[] = [];
let currentFilter: 'all' | IncidentStatus = 'all';
let currentIncident: Incident | null = null;

// Audio visualizer state
let audioCtx: AudioContext | null = null;
let analyserNode: AnalyserNode | null = null;
let micStream: MediaStream | null = null;
let visualizerAnimationFrame: number | null = null;

const app = document.querySelector<HTMLDivElement>('#app')!;
app.innerHTML = `
  <div class="app-shell">
    <!-- Top Console Navigation & Telemetry -->
    <header class="console-header">
      <div class="brand-section">
        <div class="brand-badge">VB</div>
        <div class="brand-title-group">
          <span class="brand-title">Voice Bridge // Dispatch Console</span>
          <span class="brand-subtitle">AI Incident Intake & Voice Handoff</span>
        </div>
      </div>
      <div class="telemetry-strip">
        <div class="telemetry-item">
          <span id="health-pulse" class="pulse-dot"></span>
          <span id="health-status">System: <strong>Connecting...</strong></span>
        </div>
        <div class="telemetry-item">
          <span class="pulse-dot amber"></span>
          <span id="speech-engine-status">Engine: <strong>Web Speech Ready</strong></span>
        </div>
        <div class="telemetry-item">
          <span>Active Incidents:</span>
          <strong id="incident-counter">0</strong>
        </div>
      </div>
    </header>

    <!-- Hero Header -->
    <section class="hero-banner">
      <div class="hero-content">
        <h1>Voice-Native <span class="gradient-text">Incident Dispatch</span></h1>
        <p>Capture noisy field reports, extract mission-critical parameters in real time, and synthesize crystal-clear audio handoffs for operational continuity.</p>
      </div>
      <div class="action-mode-pills">
        <div class="mode-badge"><span>⚡</span> Latency: &lt; 250ms</div>
        <div class="mode-badge"><span>🎙️</span> Rime TTS + Web Audio</div>
      </div>
    </section>

    <!-- 2-Column Mission Grid -->
    <section class="mission-grid">
      <!-- Left Column: Input & Capture -->
      <div class="glass-panel capture-panel">
        <div class="panel-head">
          <div class="panel-tag">
            <span class="tag-num">01</span>
            <span>Live Audio Capture</span>
          </div>
          <div class="panel-actions">
            <span id="capture-indicator" class="scenario-badge">IDLE</span>
          </div>
        </div>

        <!-- Real-Time Visualizer Canvas -->
        <div class="canvas-wrapper">
          <canvas id="visualizer-canvas"></canvas>
          <div id="visualizer-status" class="canvas-overlay-status">Audio Stream: Inactive</div>
        </div>

        <!-- Record Button -->
        <div class="capture-controls">
          <div class="record-btn-wrapper">
            <button id="record-button" class="record-action-btn" aria-label="Start recording speech">
              <svg class="record-btn-icon" viewBox="0 0 24 24">
                <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
                <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
              </svg>
              <span id="record-btn-label" class="record-btn-text">Record</span>
            </button>
            <div class="record-rings"></div>
          </div>
          <p id="capture-status-desc" class="capture-status-desc">Click Record to start microphone capture, or load an operational scenario preset below.</p>
        </div>

        <!-- Scenario Presets -->
        <div class="scenarios-container">
          <div class="scenarios-header">
            <span class="section-label">Field Scenario Presets</span>
            <span class="section-label">One-Click Simulation</span>
          </div>
          <div class="scenario-chips-grid">
            ${PRESET_SCENARIOS.map(
              (scenario, idx) => `
              <button class="scenario-card-btn" data-scenario-id="${scenario.id}" id="scenario-btn-${idx}">
                <div class="scenario-top">
                  <span class="scenario-badge ${idx === 0 ? 'amber' : idx === 1 ? 'crimson' : idx === 2 ? 'rose' : 'emerald'}">${scenario.badge}</span>
                  <span style="font-family: var(--font-mono); font-size: 10px; color: var(--text-muted)">#0${idx + 1}</span>
                </div>
                <div class="scenario-title">${scenario.title}</div>
                <div class="scenario-desc">${scenario.description}</div>
              </button>
            `
            ).join('')}
          </div>
        </div>

        <!-- Transcript Console Box -->
        <div class="transcript-card">
          <div class="transcript-header">
            <span class="section-label">Real-time Transcript Feed</span>
            <div class="transcript-meta">
              <span id="word-count" style="font-family: var(--font-mono); font-size: 10px;">0 words</span>
              <button id="clear-transcript-btn" class="status-btn" style="padding: 2px 6px;">Clear</button>
            </div>
          </div>
          <div id="transcript-body" class="transcript-body empty">Microphone transcript or scenario text will appear here...</div>
        </div>
      </div>

      <!-- Right Column: Extracted Spoken Handoff Brief -->
      <div class="glass-panel brief-panel">
        <div class="panel-head">
          <div class="panel-tag">
            <span class="tag-num">02</span>
            <span>Actionable Handoff Brief</span>
          </div>
          <div class="panel-actions">
            <span id="dispatch-sync-badge" class="scenario-badge emerald">STANDBY</span>
          </div>
        </div>

        <!-- Empty State -->
        <div id="brief-empty" class="brief-empty-state">
          <div class="brief-empty-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
              <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>
            </svg>
          </div>
          <div>
            <h3 style="font-family: var(--font-display); font-size: 16px; color: var(--text-primary); margin-bottom: 6px;">No Active Incident Loaded</h3>
            <p style="font-size: 13px; max-width: 320px;">Speak an incident report or select a scenario preset on the left to generate structured parameters.</p>
          </div>
        </div>

        <!-- Populated Brief Card -->
        <div id="brief-populated" class="brief-container hidden">
          <div class="brief-urgency-bar">
            <span id="brief-urgency-badge" class="urgency-badge critical">CRITICAL PRIORITY</span>
            <span id="brief-timestamp" style="font-family: var(--font-mono); font-size: 11px; color: var(--text-muted)">--:--</span>
          </div>

          <div class="brief-title-area">
            <h2 id="brief-title" class="brief-headline">Incident Title</h2>
          </div>

          <!-- Structured & Editable Dispatch Form -->
          <div class="dispatch-data-grid">
            <div class="data-cell">
              <label class="data-label" for="edit-location">Location / Zone</label>
              <input type="text" id="edit-location" class="data-input" placeholder="e.g. North Dock" />
            </div>
            <div class="data-cell">
              <label class="data-label" for="edit-owner">Owner On Site</label>
              <input type="text" id="edit-owner" class="data-input" placeholder="e.g. Maya Facilities" />
            </div>
            <div class="data-cell">
              <label class="data-label" for="edit-urgency">Priority Level</label>
              <select id="edit-urgency" class="data-input" style="cursor: pointer;">
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="standard">Standard</option>
              </select>
            </div>
            <div class="data-cell">
              <label class="data-label" for="edit-issue">Incident Category</label>
              <input type="text" id="edit-issue" class="data-input" placeholder="Issue description" />
            </div>
            <div class="data-cell full-width">
              <label class="data-label" for="edit-next-step">Actionable Next Step</label>
              <input type="text" id="edit-next-step" class="data-input" placeholder="Immediate resolution command" />
            </div>
          </div>

          <!-- Highlight Action Banner -->
          <div class="action-box">
            <div class="action-label">Directive Summary</div>
            <div id="brief-action-preview" class="action-text">--</div>
          </div>

          <!-- Spoken Audio Controls -->
          <div class="audio-action-bar">
            <div class="audio-buttons-row">
              <button id="play-spoken-btn" class="btn-primary-audio">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                  <polygon points="5 3 19 12 5 21 5 3"></polygon>
                </svg>
                <span id="play-btn-text">Synthesize & Play Spoken Brief</span>
              </button>
              <button id="save-dispatch-btn" class="btn-secondary-action">
                <span>💾</span> Re-Save
              </button>
            </div>
            <div class="audio-status-feedback">
              <span id="audio-status-dot" class="pulse-dot"></span>
              <span id="audio-status-text">Ready for speech synthesis</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Incident History & Dispatch Log Feed -->
    <section class="incident-feed-section">
      <div class="feed-header-bar">
        <div class="feed-title-group">
          <h2 class="feed-title">Dispatch Log & Incident Stream</h2>
          <span id="feed-count" class="feed-count-badge">0 incidents</span>
        </div>
        <div class="feed-filter-tabs">
          <button class="filter-tab-btn active" data-filter="all" id="filter-all">All</button>
          <button class="filter-tab-btn" data-filter="open" id="filter-open">Open</button>
          <button class="filter-tab-btn" data-filter="acknowledged" id="filter-acknowledged">Acknowledged</button>
          <button class="filter-tab-btn" data-filter="resolved" id="filter-resolved">Resolved</button>
        </div>
      </div>

      <div id="incidents-container" class="incident-cards-container">
        <!-- Rendered dynamically -->
      </div>
    </section>

    <!-- Footer -->
    <footer class="console-footer">
      <div>
        <strong>Voice Bridge Console v2.0</strong> &bull; Incident handoff system with Rime TTS & Gemini AI.
      </div>
      <div class="footer-tech-stack">
        <span>Audio: <span class="tag">Rime AI / WebAudio</span></span>
        <span>Transport: <span class="tag">Express :8787</span></span>
        <span>Speech: <span class="tag">WebSpeech API</span></span>
      </div>
    </footer>
  </div>
`;

// Element References
const recordButton = document.querySelector<HTMLButtonElement>('#record-button')!;
const recordBtnLabel = document.querySelector<HTMLSpanElement>('#record-btn-label')!;
const captureStatusDesc = document.querySelector<HTMLParagraphElement>('#capture-status-desc')!;
const captureIndicator = document.querySelector<HTMLSpanElement>('#capture-indicator')!;
const transcriptBody = document.querySelector<HTMLDivElement>('#transcript-body')!;
const wordCountElement = document.querySelector<HTMLSpanElement>('#word-count')!;
const clearTranscriptBtn = document.querySelector<HTMLButtonElement>('#clear-transcript-btn')!;

const briefEmpty = document.querySelector<HTMLDivElement>('#brief-empty')!;
const briefPopulated = document.querySelector<HTMLDivElement>('#brief-populated')!;
const briefUrgencyBadge = document.querySelector<HTMLSpanElement>('#brief-urgency-badge')!;
const briefTimestamp = document.querySelector<HTMLSpanElement>('#brief-timestamp')!;
const briefTitle = document.querySelector<HTMLHeadingElement>('#brief-title')!;
const briefActionPreview = document.querySelector<HTMLDivElement>('#brief-action-preview')!;

const editLocation = document.querySelector<HTMLInputElement>('#edit-location')!;
const editOwner = document.querySelector<HTMLInputElement>('#edit-owner')!;
const editUrgency = document.querySelector<HTMLSelectElement>('#edit-urgency')!;
const editIssue = document.querySelector<HTMLInputElement>('#edit-issue')!;
const editNextStep = document.querySelector<HTMLInputElement>('#edit-next-step')!;

const playSpokenBtn = document.querySelector<HTMLButtonElement>('#play-spoken-btn')!;
const playBtnText = document.querySelector<HTMLSpanElement>('#play-btn-text')!;
const saveDispatchBtn = document.querySelector<HTMLButtonElement>('#save-dispatch-btn')!;
const audioStatusText = document.querySelector<HTMLSpanElement>('#audio-status-text')!;
const audioStatusDot = document.querySelector<HTMLSpanElement>('#audio-status-dot')!;

const incidentsContainer = document.querySelector<HTMLDivElement>('#incidents-container')!;
const feedCount = document.querySelector<HTMLSpanElement>('#feed-count')!;
const incidentCounter = document.querySelector<HTMLSpanElement>('#incident-counter')!;
const healthStatus = document.querySelector<HTMLSpanElement>('#health-status')!;
const visualizerStatus = document.querySelector<HTMLDivElement>('#visualizer-status')!;
const visualizerCanvas = document.querySelector<HTMLCanvasElement>('#visualizer-canvas')!;

// -------------------------------------------------------------
// Real-Time Canvas Audio Visualizer
// -------------------------------------------------------------
function initVisualizer(): void {
  const canvas = visualizerCanvas;
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const resize = () => {
    canvas.width = canvas.parentElement?.clientWidth || 400;
    canvas.height = canvas.parentElement?.clientHeight || 110;
  };
  resize();
  window.addEventListener('resize', resize);

  let phase = 0;
  const draw = () => {
    visualizerAnimationFrame = requestAnimationFrame(draw);
    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);

    if (analyserNode && isListening) {
      // Live microphone frequency visualizer
      const bufferLength = analyserNode.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);
      analyserNode.getByteFrequencyData(dataArray);

      const barWidth = (width / bufferLength) * 2.5;
      let x = 0;

      for (let i = 0; i < bufferLength; i++) {
        const barHeight = (dataArray[i] / 255) * height * 0.85;
        const gradient = ctx.createLinearGradient(0, height, 0, height - barHeight);
        gradient.addColorStop(0, '#00f2fe');
        gradient.addColorStop(0.6, '#38bdf8');
        gradient.addColorStop(1, '#f43f5e');

        ctx.fillStyle = gradient;
        ctx.fillRect(x, height - barHeight, barWidth - 1, barHeight);
        x += barWidth + 1;
        if (x > width) break;
      }
    } else {
      // Idle ambient multi-layer sine waves
      phase += 0.03;
      const centerY = height / 2;

      // Draw grid line
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.1)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, centerY);
      ctx.lineTo(width, centerY);
      ctx.stroke();

      // Wave 1 - Cyan
      ctx.beginPath();
      ctx.strokeStyle = 'rgba(0, 242, 254, 0.45)';
      ctx.lineWidth = 2;
      for (let x = 0; x < width; x += 2) {
        const y = centerY + Math.sin(x * 0.015 + phase) * 14 * Math.sin(phase * 0.5);
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      // Wave 2 - Purple harmonic
      ctx.beginPath();
      ctx.strokeStyle = 'rgba(129, 140, 248, 0.35)';
      ctx.lineWidth = 1.5;
      for (let x = 0; x < width; x += 3) {
        const y = centerY + Math.cos(x * 0.02 - phase * 0.8) * 10 * Math.sin(phase * 0.3);
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    }
  };
  draw();
}

async function setupAudioContext(): Promise<void> {
  try {
    if (!audioCtx) {
      audioCtx = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
    }
    if (audioCtx.state === 'suspended') {
      await audioCtx.resume();
    }
    if (!micStream) {
      micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    }
    analyserNode = audioCtx.createAnalyser();
    analyserNode.fftSize = 128;
    const source = audioCtx.createMediaStreamSource(micStream);
    source.connect(analyserNode);
    visualizerStatus.textContent = 'Audio Stream: Live Mic Connected';
    visualizerStatus.style.color = '#38bdf8';
  } catch (err) {
    console.warn('Microphone audio stream for visualizer not granted:', err);
    visualizerStatus.textContent = 'Audio Stream: Simulation Active';
  }
}

function tearDownAudioContext(): void {
  if (micStream) {
    micStream.getTracks().forEach((track) => track.stop());
    micStream = null;
  }
  analyserNode = null;
  visualizerStatus.textContent = 'Audio Stream: Idle';
  visualizerStatus.style.color = 'var(--text-muted)';
}

// -------------------------------------------------------------
// NLP Extraction Heuristics
// -------------------------------------------------------------
function parseIncident(text: string): Incident {
  const lower = text.toLowerCase();

  // Location extraction
  const locationMatch = text.match(/(?:at|in|near|inside|around)\s+([A-Z0-9][\w\s-]{2,28}?)(?=\s+(?:is|reads|has|was|showing|had|,|\.|$))/i);
  let location = locationMatch?.[1]?.trim();
  if (!location) {
    if (lower.includes('north dock')) location = 'North Dock';
    else if (lower.includes('substation')) location = 'South Substation';
    else if (lower.includes('sector b')) location = 'Sector B';
    else if (lower.includes('rack 18')) location = 'Rack 18 (Data Center)';
    else location = 'Field Operational Zone';
  }

  // Owner / Engineer extraction
  let owner = 'No owner named';
  const ownerPattern1 = text.match(/([A-Z][a-z]+)\s+(?:from|with|in|at)\s+([a-z\s-]+?)(?=\s+(?:is\s+on\s+site|is\s+monitoring|is\s+preparing|is\s+isolated|,|\.|$))/i);
  const ownerPattern2 = text.match(/(?:with|from|by|operator|engineer)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)/);
  const ownerPattern3 = text.match(/([A-Z][a-z]+)\s+is\s+on\s+site/i);

  if (ownerPattern1) {
    owner = `${ownerPattern1[1]} (${ownerPattern1[2].trim()})`;
  } else if (ownerPattern3) {
    owner = ownerPattern3[1];
  } else if (ownerPattern2) {
    owner = ownerPattern2[1];
  }

  // Urgency
  let urgency: 'critical' | 'high' | 'standard' = 'standard';
  if (/critical|immediately|asap|urgent|runaway|out of control|blow|danger|failure/i.test(lower)) {
    urgency = 'critical';
  } else if (/soon|priority|warning|degraded|breach|alert/i.test(lower)) {
    urgency = 'high';
  }

  // Issue & Next Step categorization
  let issue = 'Operational irregularity detected';
  let nextStep = 'Notify field shift supervisor and dispatch maintenance crew.';

  if (lower.includes('temperature') || lower.includes('degrees') || lower.includes('cold room')) {
    issue = 'Cold chain thermal excursion / cooling malfunction';
    nextStep = 'Stabilize cooling compressor and verify temperature drops below 4°C before morning shift.';
  } else if (lower.includes('transformer') || lower.includes('voltage') || lower.includes('substation')) {
    issue = 'Transformer thermal runaway / electrical hazard';
    nextStep = 'Engage auxiliary cooling fans and prepare emergency breaker trip sequence.';
  } else if (lower.includes('reactor') || lower.includes('pressure') || lower.includes('psi') || lower.includes('tank')) {
    issue = 'Vessel over-pressurization anomaly';
    nextStep = 'Initiate manual depressurization protocol and clear personnel from Sector B perimeter.';
  } else if (lower.includes('san') || lower.includes('raid') || lower.includes('drive') || lower.includes('storage') || lower.includes('disk')) {
    issue = 'Storage cluster array degradation / drive fault';
    nextStep = 'Insert verified hot spare drives and trigger background RAID parity reconstruction.';
  }

  return {
    transcript: text,
    location,
    issue,
    urgency,
    owner,
    nextStep,
    status: 'open'
  };
}

function spokenTextFor(incident: Incident): string {
  return `${incident.urgency} priority incident. ${incident.issue} at ${incident.location}. Responsible personnel: ${incident.owner}. Immediate directive: ${incident.nextStep}`;
}

// -------------------------------------------------------------
// Render Brief & Dispatch Form
// -------------------------------------------------------------
function renderBrief(incident: Incident): void {
  currentIncident = incident;
  briefEmpty.classList.add('hidden');
  briefPopulated.classList.remove('hidden');

  briefUrgencyBadge.className = `urgency-badge ${incident.urgency}`;
  briefUrgencyBadge.textContent = `${incident.urgency.toUpperCase()} PRIORITY`;
  briefTitle.textContent = incident.issue;
  briefTimestamp.textContent = incident.createdAt
    ? new Date(incident.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

  editLocation.value = incident.location;
  editOwner.value = incident.owner;
  editUrgency.value = incident.urgency;
  editIssue.value = incident.issue;
  editNextStep.value = incident.nextStep;

  briefActionPreview.textContent = spokenTextFor(incident);
  audioStatusText.textContent = 'Brief generated. Ready for voice synthesis.';
  audioStatusDot.className = 'pulse-dot';
}

function updateBriefFromForm(): Incident {
  if (!currentIncident) {
    currentIncident = parseIncident(currentTranscript || 'Field incident report');
  }
  currentIncident.location = editLocation.value.trim() || 'Unspecified';
  currentIncident.owner = editOwner.value.trim() || 'No owner named';
  currentIncident.urgency = editUrgency.value as 'critical' | 'high' | 'standard';
  currentIncident.issue = editIssue.value.trim() || 'Operational issue';
  currentIncident.nextStep = editNextStep.value.trim() || 'Inspect site immediately';
  currentIncident.spokenText = spokenTextFor(currentIncident);

  briefUrgencyBadge.className = `urgency-badge ${currentIncident.urgency}`;
  briefUrgencyBadge.textContent = `${currentIncident.urgency.toUpperCase()} PRIORITY`;
  briefTitle.textContent = currentIncident.issue;
  briefActionPreview.textContent = currentIncident.spokenText;

  return currentIncident;
}

// -------------------------------------------------------------
// Speech Synthesis (Rime TTS + Browser Speech Fallback)
// -------------------------------------------------------------
async function synthesizeAndPlaySpokenBrief(): Promise<void> {
  const incident = updateBriefFromForm();
  const text = incident.spokenText || spokenTextFor(incident);

  playSpokenBtn.disabled = true;
  playBtnText.textContent = 'Generating Audio...';
  audioStatusText.textContent = 'Synthesizing voice stream...';
  audioStatusDot.className = 'pulse-dot amber';

  try {
    const response = await fetch('/api/speak', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });

    if (!response.ok) {
      const errJson = await response.json().catch(() => ({}));
      throw new Error(errJson.error || `Voice server returned HTTP ${response.status}`);
    }

    const blob = await response.blob();
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    audioUrl = URL.createObjectURL(blob);

    const audio = new Audio(audioUrl);
    audio.onended = () => {
      audioStatusText.textContent = 'Playback completed (Rime AI Rex)';
      audioStatusDot.className = 'pulse-dot';
      playSpokenBtn.disabled = false;
      playBtnText.textContent = 'Replay Spoken Brief';
    };
    audio.play();

    audioStatusText.textContent = 'Playing spoken brief via Rime TTS...';
    audioStatusDot.className = 'pulse-dot';
  } catch (error) {
    console.warn('Rime TTS unavailable, falling back to Browser Web Speech API:', error);

    // Browser SpeechSynthesis Fallback
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.05;
      utterance.pitch = 0.95;
      utterance.onend = () => {
        audioStatusText.textContent = 'Playback completed (Browser Voice Fallback)';
        audioStatusDot.className = 'pulse-dot';
        playSpokenBtn.disabled = false;
        playBtnText.textContent = 'Replay Spoken Brief';
      };
      window.speechSynthesis.speak(utterance);
      audioStatusText.textContent = 'Playing spoken brief (Web Speech Fallback)...';
      audioStatusDot.className = 'pulse-dot';
    } else {
      audioStatusText.textContent = error instanceof Error ? error.message : 'Speech synthesis unavailable.';
      audioStatusDot.className = 'pulse-dot rose';
      playSpokenBtn.disabled = false;
      playBtnText.textContent = 'Synthesize & Play Spoken Brief';
    }
  }
}

// -------------------------------------------------------------
// Backend API Persistence & Fetching
// -------------------------------------------------------------
async function persistIncident(incident: Incident): Promise<Incident | null> {
  const dispatchSyncBadge = document.querySelector<HTMLSpanElement>('#dispatch-sync-badge');
  if (dispatchSyncBadge) {
    dispatchSyncBadge.textContent = 'SAVING...';
    dispatchSyncBadge.className = 'scenario-badge amber';
  }

  try {
    const payload = {
      ...incident,
      spokenText: incident.spokenText || spokenTextFor(incident)
    };
    const res = await fetch('/api/incidents', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('Failed to persist incident');
    const created: Incident = await res.json();

    if (dispatchSyncBadge) {
      dispatchSyncBadge.textContent = 'DISPATCHED';
      dispatchSyncBadge.className = 'scenario-badge emerald';
    }
    await loadIncidents();
    return created;
  } catch (err) {
    console.error('Error saving incident:', err);
    if (dispatchSyncBadge) {
      dispatchSyncBadge.textContent = 'OFFLINE SAVE';
      dispatchSyncBadge.className = 'scenario-badge crimson';
    }
    return null;
  }
}

async function loadIncidents(): Promise<void> {
  try {
    const res = await fetch('/api/incidents');
    if (!res.ok) throw new Error('Failed to load incidents');
    activeIncidents = await res.json();
    renderIncidentCards();
  } catch (err) {
    console.warn('Could not load incidents feed:', err);
  }
}

async function updateIncidentStatus(id: string, status: IncidentStatus): Promise<void> {
  try {
    const res = await fetch(`/api/incidents/${id}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    });
    if (!res.ok) throw new Error('Failed to update incident status');
    await loadIncidents();
  } catch (err) {
    console.error('Error updating status:', err);
  }
}

function renderIncidentCards(): void {
  const filtered = currentFilter === 'all'
    ? activeIncidents
    : activeIncidents.filter((inc) => inc.status === currentFilter);

  feedCount.textContent = `${activeIncidents.length} total (${filtered.length} shown)`;
  incidentCounter.textContent = activeIncidents.filter((i) => i.status !== 'resolved').length.toString();

  if (filtered.length === 0) {
    incidentsContainer.innerHTML = `
      <div style="grid-column: 1 / -1; padding: 36px; text-align: center; color: var(--text-muted); background: rgba(0,0,0,0.25); border-radius: var(--radius-md); border: 1px dashed var(--border-subtle);">
        No incidents matching status "${currentFilter}". Dispatch a new report above.
      </div>
    `;
    return;
  }

  incidentsContainer.innerHTML = filtered
    .map((inc) => {
      const timeStr = inc.createdAt ? new Date(inc.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Recent';
      const statusClass = inc.status || 'open';

      return `
      <div class="incident-card" data-id="${inc.id}">
        <div class="incident-card-top">
          <span class="urgency-badge ${inc.urgency}" style="font-size: 9px; padding: 2px 6px;">${inc.urgency}</span>
          <span class="incident-card-time">${timeStr}</span>
        </div>
        <div class="incident-card-title">${escapeHtml(inc.issue)}</div>
        <div class="incident-meta-row">
          <span>📍 <strong>${escapeHtml(inc.location)}</strong></span>
          <span>👤 <strong>${escapeHtml(inc.owner)}</strong></span>
        </div>
        <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.4; border-left: 2px solid var(--border-active); padding-left: 8px;">
          ${escapeHtml(inc.nextStep)}
        </div>
        <div class="incident-card-footer">
          <span class="status-pill ${statusClass}">${statusClass}</span>
          <div class="status-actions-group">
            <button class="status-btn inspect-btn" data-id="${inc.id}">View</button>
            ${
              inc.status !== 'acknowledged' && inc.status !== 'resolved'
                ? `<button class="status-btn ack-btn" data-id="${inc.id}">Ack</button>`
                : ''
            }
            ${
              inc.status !== 'resolved'
                ? `<button class="status-btn resolve-btn" data-id="${inc.id}">Resolve</button>`
                : ''
            }
          </div>
        </div>
      </div>
    `;
    })
    .join('');

  // Attach card event listeners
  incidentsContainer.querySelectorAll('.inspect-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      const id = (e.currentTarget as HTMLElement).getAttribute('data-id');
      const inc = activeIncidents.find((i) => i.id === id);
      if (inc) {
        currentTranscript = inc.transcript;
        transcriptBody.textContent = inc.transcript;
        transcriptBody.classList.remove('empty');
        updateWordCount(inc.transcript);
        renderBrief(inc);
      }
    });
  });

  incidentsContainer.querySelectorAll('.ack-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      const id = (e.currentTarget as HTMLElement).getAttribute('data-id');
      if (id) void updateIncidentStatus(id, 'acknowledged');
    });
  });

  incidentsContainer.querySelectorAll('.resolve-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      const id = (e.currentTarget as HTMLElement).getAttribute('data-id');
      if (id) void updateIncidentStatus(id, 'resolved');
    });
  });
}

function escapeHtml(text: string): string {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function updateWordCount(text: string): void {
  const count = text.trim() ? text.trim().split(/\s+/).length : 0;
  wordCountElement.textContent = `${count} words`;
}

// -------------------------------------------------------------
// Live Speech Recognition Capture Flow
// -------------------------------------------------------------
function finishCapture(emptyStatus = 'No speech detected. Try again.'): void {
  if (!isListening) return;
  isListening = false;
  tearDownAudioContext();

  if (captureTimer !== null) {
    window.clearTimeout(captureTimer);
    captureTimer = null;
  }

  recordButton.classList.remove('recording');
  recordBtnLabel.textContent = 'Record';
  captureIndicator.textContent = 'IDLE';
  captureIndicator.className = 'scenario-badge';

  if (!currentTranscript.trim()) {
    captureStatusDesc.textContent = emptyStatus;
    transcriptBody.textContent = 'Nothing captured yet.';
    transcriptBody.classList.add('empty');
    updateWordCount('');
    return;
  }

  captureStatusDesc.textContent = 'Speech capture completed. Brief generated.';
  transcriptBody.textContent = currentTranscript;
  transcriptBody.classList.remove('empty');
  updateWordCount(currentTranscript);

  const incident = parseIncident(currentTranscript);
  renderBrief(incident);
  void persistIncident(incident);
  void synthesizeAndPlaySpokenBrief();
}

async function startCapture(): Promise<void> {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    captureStatusDesc.textContent = 'Web Speech Recognition is not supported in this browser. Loading sample scenario.';
    loadScenarioPreset(PRESET_SCENARIOS[0]);
    return;
  }

  await setupAudioContext();

  recognition = new SpeechRecognition();
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.lang = 'en-US';

  recognition.onresult = (event) => {
    currentTranscript = Array.from(event.results).map((result) => result[0].transcript).join(' ');
    transcriptBody.textContent = currentTranscript;
    transcriptBody.classList.remove('empty');
    updateWordCount(currentTranscript);
  };

  recognition.onstart = () => {
    captureStatusDesc.textContent = 'Microphone listening live. Speak clearly into your input device.';
    recordBtnLabel.textContent = 'Finish';
    captureIndicator.textContent = 'RECORDING';
    captureIndicator.className = 'scenario-badge crimson';
  };

  recognition.onend = () => {
    if (!isListening) return;
    window.setTimeout(() => {
      if (!isListening) return;
      try {
        recognition?.start();
      } catch {
        captureStatusDesc.textContent = 'Reconnecting microphone...';
      }
    }, 100);
  };

  recognition.onerror = (event) => {
    if (event.error === 'not-allowed') {
      finishCapture('Microphone permission blocked. Enable microphone access in browser settings.');
      return;
    }
    if (event.error === 'audio-capture') {
      finishCapture('No microphone input device detected.');
      return;
    }
    console.warn('Speech recognition warning:', event.error);
  };

  currentTranscript = '';
  transcriptBody.textContent = 'Listening for speech input...';
  transcriptBody.classList.remove('empty');
  updateWordCount('');
  isListening = true;

  recordButton.classList.add('recording');
  recordBtnLabel.textContent = 'Starting...';
  captureStatusDesc.textContent = 'Opening microphone input stream...';

  captureTimer = window.setTimeout(() => {
    if (isListening) {
      recognition?.stop();
      finishCapture();
    }
  }, MAX_CAPTURE_MS);

  try {
    recognition.start();
  } catch (err) {
    console.error('Recognition start failed:', err);
    finishCapture('Could not initiate speech recognition.');
  }
}

function loadScenarioPreset(scenario: ScenarioPreset): void {
  currentTranscript = scenario.transcript;
  transcriptBody.textContent = scenario.transcript;
  transcriptBody.classList.remove('empty');
  updateWordCount(scenario.transcript);
  captureStatusDesc.textContent = `Preset loaded: ${scenario.title}`;

  const incident = parseIncident(scenario.transcript);
  renderBrief(incident);
  void persistIncident(incident);
  void synthesizeAndPlaySpokenBrief();
}

// -------------------------------------------------------------
// System Health Check
// -------------------------------------------------------------
async function checkSystemHealth(): Promise<void> {
  const healthPulse = document.querySelector<HTMLSpanElement>('#health-pulse');
  try {
    const res = await fetch('/api/health');
    if (res.ok) {
      healthStatus.innerHTML = 'System: <strong>Online (API :8787)</strong>';
      if (healthPulse) healthPulse.className = 'pulse-dot';
    } else {
      throw new Error();
    }
  } catch {
    healthStatus.innerHTML = 'System: <strong style="color: #f43f5e">Offline</strong>';
    if (healthPulse) healthPulse.className = 'pulse-dot rose';
  }
}

// -------------------------------------------------------------
// Event Listeners Initialization
// -------------------------------------------------------------
function setupEventListeners(): void {
  // Record toggle
  recordButton.addEventListener('click', () => {
    if (!isListening) {
      void startCapture();
    } else {
      recognition?.stop();
      finishCapture();
    }
  });

  // Preset Scenario Buttons
  document.querySelectorAll('.scenario-card-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      const scenarioId = (e.currentTarget as HTMLElement).getAttribute('data-scenario-id');
      const scenario = PRESET_SCENARIOS.find((s) => s.id === scenarioId);
      if (scenario) {
        loadScenarioPreset(scenario);
      }
    });
  });

  // Clear Transcript Button
  clearTranscriptBtn.addEventListener('click', () => {
    currentTranscript = '';
    transcriptBody.textContent = 'Microphone transcript or scenario text will appear here...';
    transcriptBody.classList.add('empty');
    updateWordCount('');
  });

  // Form Inputs live sync
  [editLocation, editOwner, editUrgency, editIssue, editNextStep].forEach((input) => {
    input.addEventListener('input', () => {
      updateBriefFromForm();
    });
  });

  // Play Spoken Audio button
  playSpokenBtn.addEventListener('click', () => {
    void synthesizeAndPlaySpokenBrief();
  });

  // Re-save dispatch button
  saveDispatchBtn.addEventListener('click', () => {
    const incident = updateBriefFromForm();
    void persistIncident(incident);
  });

  // Filter tabs
  document.querySelectorAll('.filter-tab-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('.filter-tab-btn').forEach((b) => b.classList.remove('active'));
      const target = e.currentTarget as HTMLElement;
      target.classList.add('active');
      currentFilter = target.getAttribute('data-filter') as 'all' | IncidentStatus;
      renderIncidentCards();
    });
  });
}

// -------------------------------------------------------------
// App Bootstrap
// -------------------------------------------------------------
function bootstrap(): void {
  initVisualizer();
  setupEventListeners();
  void checkSystemHealth();
  void loadIncidents();
  setInterval(() => void checkSystemHealth(), 15_000);
}

bootstrap();
