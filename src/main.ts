import './style.css';
import type { Incident } from './types';

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

const sampleTranscript = 'The cold room at North Dock is reading 12 degrees. Product is still inside, and Maya from facilities is on site. Please get the temperature back under control before the morning shift. This is urgent.';
const MAX_CAPTURE_MS = 30_000;
let transcript = '';
let isListening = false;
let audioUrl: string | null = null;
let recognition: SpeechRecognitionInstance | null = null;
let captureTimer: number | null = null;

const app = document.querySelector<HTMLDivElement>('#app')!;
app.innerHTML = `
  <main class="shell">
    <header class="topbar">
      <div class="brand"><span class="brand-mark">VB</span><span>Voice Bridge</span></div>
      <div class="status"><span class="status-dot"></span><span id="status-label">Ready for a live report</span></div>
    </header>
    <section class="intro">
      <p class="kicker">FIELD NOTE  /  INCIDENT INTAKE</p>
      <h1>Say what happened.<br><em>We will make it actionable.</em></h1>
      <p class="lede">A voice-native handoff for the moment when details are messy, time is short, and the next person needs a clear brief.</p>
    </section>
    <section class="workspace">
      <div class="capture-panel">
        <div class="panel-label"><span>01</span> Live capture</div>
        <button id="record-button" class="record-button" aria-label="Start recording">
          <span class="record-ring"><span class="record-icon"></span></span>
          <span id="record-label">Tap to speak</span>
        </button>
        <p class="hint">Describe the issue naturally. Include where, what is wrong, who is there, and what needs to happen.</p>
        <button id="sample-button" class="text-button">Use a sample report <span>→</span></button>
        <div class="transcript-box">
          <div class="box-label">Your words</div>
          <p id="transcript">Nothing captured yet.</p>
        </div>
      </div>
      <div class="brief-panel">
        <div class="panel-label"><span>02</span> Spoken handoff</div>
        <div id="empty-state" class="empty-state"><div class="waveform"><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div><p>Your brief will appear here after you speak.</p></div>
        <div id="brief" class="brief hidden">
          <div class="urgency-row"><span id="urgency" class="urgency">HIGH PRIORITY</span><span id="timestamp"></span></div>
          <h2 id="issue-title"></h2>
          <div class="fact-grid">
            <div><span>LOCATION</span><strong id="location"></strong></div>
            <div><span>OWNER ON SITE</span><strong id="owner"></strong></div>
          </div>
          <div class="next-step"><span>NEXT MOVE</span><p id="next-step"></p></div>
          <button id="replay-button" class="replay-button"><span>▶</span> Play spoken handoff</button>
          <p id="audio-status" class="audio-status">Rime voice ready when your brief is complete.</p>
        </div>
      </div>
    </section>
    <footer><span>ACCEPTANCE TEST</span><strong>Speak a messy report once. In under 10 seconds, hear a concise, accurate handoff.</strong><span class="rime-mark">RIME / PRIMARY VOICE</span></footer>
  </main>
`;

const recordButton = document.querySelector<HTMLButtonElement>('#record-button')!;
const recordLabel = document.querySelector<HTMLSpanElement>('#record-label')!;
const statusLabel = document.querySelector<HTMLSpanElement>('#status-label')!;
const transcriptElement = document.querySelector<HTMLParagraphElement>('#transcript')!;
const sampleButton = document.querySelector<HTMLButtonElement>('#sample-button')!;
const emptyState = document.querySelector<HTMLDivElement>('#empty-state')!;
const briefElement = document.querySelector<HTMLDivElement>('#brief')!;
const replayButton = document.querySelector<HTMLButtonElement>('#replay-button')!;
const audioStatus = document.querySelector<HTMLParagraphElement>('#audio-status')!;

function parseIncident(text: string): Incident {
  const lower = text.toLowerCase();
  const locationMatch = text.match(/(?:at|in|near) ([^.!,]+?)(?: is| reads| has|,|\.|$)/i);
  const ownerMatch = text.match(/(?:with|from|by) ([A-Z][\w-]*(?:\s+[A-Z][\w-]*)?)/);
  const urgency = /urgent|critical|immediately|asap/.test(lower) ? 'critical' : /soon|priority/.test(lower) ? 'high' : 'standard';
  const issue = lower.includes('temperature') || lower.includes('degrees') ? 'Cold room temperature is out of range' : 'Operational issue needs attention';
  return {
    transcript: text,
    location: locationMatch?.[1]?.trim() || 'Location not captured',
    issue,
    urgency,
    owner: ownerMatch?.[1]?.trim() || 'No owner named',
    nextStep: lower.includes('temperature') ? 'Stabilize the cold room and confirm it is under 4 degrees before the morning shift.' : 'Route this report to the responsible operator and confirm the next action.'
  };
}

function renderBrief(incident: Incident): void {
  emptyState.classList.add('hidden');
  briefElement.classList.remove('hidden');
  document.querySelector('#urgency')!.textContent = `${incident.urgency.toUpperCase()} PRIORITY`;
  document.querySelector('#issue-title')!.textContent = incident.issue;
  document.querySelector('#location')!.textContent = incident.location;
  document.querySelector('#owner')!.textContent = incident.owner;
  document.querySelector('#next-step')!.textContent = incident.nextStep;
  document.querySelector('#timestamp')!.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  document.querySelector('#urgency')!.className = `urgency ${incident.urgency}`;
}

function spokenTextFor(incident: Incident): string {
  return `${incident.urgency} priority. ${incident.issue} at ${incident.location}. ${incident.owner} is on site. Next move: ${incident.nextStep}`;
}

async function persistIncident(incident: Incident): Promise<void> {
  try {
    await fetch('/api/incidents', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...incident, spokenText: spokenTextFor(incident) })
    });
  } catch {
    statusLabel.textContent = 'Brief ready; could not save record';
  }
}

async function speakBrief(): Promise<void> {
  const incident = parseIncident(transcript);
  const spokenText = spokenTextFor(incident);
  audioStatus.textContent = 'Generating Rime voice...';
  replayButton.disabled = true;
  try {
    const response = await fetch('/api/speak', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: spokenText }) });
    if (!response.ok) throw new Error((await response.json()).error || 'Rime voice unavailable');
    const blob = await response.blob();
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    audioUrl = URL.createObjectURL(blob);
    new Audio(audioUrl).play();
    audioStatus.textContent = 'Playing with Rime voice.';
  } catch (error) {
    audioStatus.textContent = error instanceof Error ? error.message : 'Rime voice unavailable.';
  } finally {
    replayButton.disabled = false;
  }
}

function finishCapture(emptyStatus = 'No speech detected. Try again.'): void {
  if (!isListening) return;
  isListening = false;
  if (captureTimer !== null) {
    window.clearTimeout(captureTimer);
    captureTimer = null;
  }
  recordButton.classList.remove('recording');
  recordLabel.textContent = 'Tap to speak';
  if (!transcript.trim()) {
    statusLabel.textContent = emptyStatus;
    transcriptElement.textContent = 'Nothing captured yet.';
    return;
  }
  statusLabel.textContent = 'Report captured';
  transcriptElement.textContent = transcript;
  const incident = parseIncident(transcript);
  renderBrief(incident);
  void persistIncident(incident);
  void speakBrief();
}

function startCapture(): void {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    statusLabel.textContent = 'Speech recognition unavailable';
    transcript = sampleTranscript;
    finishCapture();
    return;
  }
  recognition = new SpeechRecognition();
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.lang = 'en-US';
  recognition.onresult = (event) => {
    transcript = Array.from(event.results).map((result) => result[0].transcript).join(' ');
    transcriptElement.textContent = transcript;
  };
  recognition.onstart = () => {
    statusLabel.textContent = 'Listening live';
    recordLabel.textContent = 'Tap to finish';
  };
  recognition.onend = () => {
    if (!isListening) return;
    window.setTimeout(() => {
      if (!isListening) return;
      try {
        recognition?.start();
      } catch {
        statusLabel.textContent = 'Still starting microphone...';
      }
    }, 100);
  };
  recognition.onerror = (event) => {
    if (event.error === 'not-allowed') {
      statusLabel.textContent = 'Microphone permission is blocked.';
      finishCapture('Microphone permission is blocked.');
      return;
    }
    if (event.error === 'audio-capture') {
      statusLabel.textContent = 'No microphone was found.';
      finishCapture('No microphone was found.');
      return;
    }
    statusLabel.textContent = 'Listening live';
  };
  transcript = '';
  transcriptElement.textContent = 'Listening...';
  isListening = true;
  recordButton.classList.add('recording');
  recordLabel.textContent = 'Starting microphone...';
  statusLabel.textContent = 'Starting microphone';
  captureTimer = window.setTimeout(() => {
    if (isListening) {
      recognition?.stop();
      finishCapture();
    }
  }, MAX_CAPTURE_MS);
  recognition.start();
}

recordButton.addEventListener('click', () => {
  if (!isListening) {
    startCapture();
    return;
  }
  recognition?.stop();
  finishCapture();
});
sampleButton.addEventListener('click', () => {
  transcript = sampleTranscript;
  transcriptElement.textContent = transcript;
  statusLabel.textContent = 'Sample report loaded';
  const incident = parseIncident(transcript);
  renderBrief(incident);
  void persistIncident(incident);
  void speakBrief();
});
replayButton.addEventListener('click', () => void speakBrief());
