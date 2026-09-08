import 'dotenv/config';
import { randomUUID } from 'node:crypto';
import express from 'express';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const app = express();
const port = Number(process.env.PORT || 8787);
const root = path.dirname(fileURLToPath(import.meta.url));
const incidentFile = path.join(root, 'data', 'incidents.json');

app.use(express.json({ limit: '1mb' }));

async function readIncidents() {
  return JSON.parse(await fs.readFile(incidentFile, 'utf8'));
}

async function writeIncidents(incidents) {
  await fs.writeFile(incidentFile, `${JSON.stringify(incidents, null, 2)}\n`);
}

app.get('/api/health', (_request, response) => response.json({ ok: true, service: 'voice-bridge' }));

app.get('/api/incidents', async (request, response) => {
  const incidents = await readIncidents();
  const status = typeof request.query.status === 'string' ? request.query.status : null;
  const limit = Math.min(Number(request.query.limit) || 50, 100);
  const filtered = status ? incidents.filter((incident) => incident.status === status) : incidents;
  response.json(filtered.slice(0, limit));
});

app.get('/api/incidents/:id', async (request, response) => {
  const incidents = await readIncidents();
  const incident = incidents.find((item) => item.id === request.params.id);
  if (!incident) return response.status(404).json({ error: 'Incident not found.' });
  response.json(incident);
});

app.post('/api/incidents', async (request, response) => {
  const { transcript, issue, location, owner, urgency, nextStep, spokenText } = request.body ?? {};
  if (![transcript, issue, location, owner, urgency, nextStep, spokenText].every((value) => typeof value === 'string' && value.trim())) {
    return response.status(400).json({ error: 'transcript, issue, location, owner, urgency, nextStep, and spokenText are required.' });
  }
  if (!['critical', 'high', 'standard'].includes(urgency)) {
    return response.status(400).json({ error: 'urgency must be critical, high, or standard.' });
  }
  const now = new Date().toISOString();
  const incident = { id: randomUUID(), transcript, issue, location, owner, urgency, nextStep, spokenText, status: 'open', createdAt: now, updatedAt: now };
  const incidents = await readIncidents();
  incidents.unshift(incident);
  await writeIncidents(incidents);
  response.status(201).json(incident);
});

app.patch('/api/incidents/:id/status', async (request, response) => {
  const { status } = request.body ?? {};
  if (!['open', 'acknowledged', 'resolved'].includes(status)) return response.status(400).json({ error: 'Invalid incident status.' });
  const incidents = await readIncidents();
  const incident = incidents.find((item) => item.id === request.params.id);
  if (!incident) return response.status(404).json({ error: 'Incident not found.' });
  incident.status = status;
  incident.updatedAt = new Date().toISOString();
  await writeIncidents(incidents);
  response.json(incident);
});

app.post('/api/speak', async (request, response) => {
  const { text } = request.body ?? {};
  if (!text || typeof text !== 'string') {
    return response.status(400).json({ error: 'Text is required.' });
  }
  if (!process.env.RIME_API_KEY) {
    return response.status(503).json({ error: 'Add RIME_API_KEY to .env to enable spoken output.' });
  }

  try {
    const rimeResponse = await fetch('https://users.rime.ai/v1/rime-tts', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${process.env.RIME_API_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        text,
        speaker: process.env.RIME_SPEAKER || 'rex',
        modelId: process.env.RIME_MODEL || 'mist'
      })
    });

    if (!rimeResponse.ok) {
      const detail = await rimeResponse.text();
      return response.status(rimeResponse.status).json({ error: `Rime error: ${detail}` });
    }

    const contentType = rimeResponse.headers.get('content-type') || '';
    if (contentType.includes('audio')) {
      response.set('Content-Type', contentType);
      return response.send(Buffer.from(await rimeResponse.arrayBuffer()));
    }

    const payload = await rimeResponse.json();
    const encoded = payload.audioContent || payload.audio || payload.audio_base64;
    if (!encoded) return response.status(502).json({ error: 'Rime returned no audio.' });
    response.type('audio/wav').send(Buffer.from(encoded, 'base64'));
  } catch (error) {
    console.error(error);
    response.status(502).json({ error: 'Could not reach Rime.' });
  }
});

app.use(express.static(path.join(root, 'dist')));
app.get('*', (_request, response) => response.sendFile(path.join(root, 'dist', 'index.html')));

app.listen(port, () => console.log(`Voice Bridge listening on http://localhost:${port}`));
