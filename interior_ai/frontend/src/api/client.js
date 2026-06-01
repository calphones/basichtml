import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 300_000,  // 5 min (renders can be slow)
});

// ── Upload ────────────────────────────────────────────────────────────────

export async function uploadFloorPlan(file, sessionId = '') {
  const form = new FormData();
  form.append('file', file);
  form.append('session_id', sessionId);
  const { data } = await api.post('/upload/floor-plan', form);
  return data;
}

export async function uploadInspiration(file, sessionId = '') {
  const form = new FormData();
  form.append('file', file);
  form.append('session_id', sessionId);
  const { data } = await api.post('/upload/inspiration', form);
  return data;
}

// ── Design ────────────────────────────────────────────────────────────────

export async function parseFloorPlan(sessionId, filePath) {
  const { data } = await api.post('/design/parse-floor-plan', null, {
    params: { session_id: sessionId, file_path: filePath },
  });
  return data;
}

export async function generateDesign(sessionId, { style, prompt, familyFriendly, extraStorage }) {
  const { data } = await api.post('/design/generate', {
    session_id: sessionId,
    style,
    prompt,
    family_friendly: familyFriendly,
    extra_storage: extraStorage,
  });
  return data;
}

export async function listStyles() {
  const { data } = await api.get('/design/styles');
  return data.styles;
}

export async function getSession(sessionId) {
  const { data } = await api.get(`/design/session/${sessionId}`);
  return data;
}

// ── Render ────────────────────────────────────────────────────────────────

export async function submitRender(sessionId, { mode = 'preview', width = 1920, height = 1080, cameraPreset }) {
  const { data } = await api.post('/render/submit', {
    session_id: sessionId,
    mode,
    resolution_w: width,
    resolution_h: height,
    camera_preset: cameraPreset || null,
  });
  return data;
}

export async function runRender(jobId) {
  const { data } = await api.post(`/render/run/${jobId}`);
  return data;
}

export async function getRenderStatus(jobId) {
  const { data } = await api.get(`/render/status/${jobId}`);
  return data;
}

export function getRenderImageUrl(jobId) {
  return `${BASE_URL}/render/result/${jobId}`;
}

// ── Edit ──────────────────────────────────────────────────────────────────

export async function applyCommand(sessionId, command) {
  const { data } = await api.post('/edit/command', {
    session_id: sessionId,
    command,
  });
  return data;
}

export async function previewIntent(command) {
  const { data } = await api.post('/edit/preview', null, { params: { command } });
  return data;
}

export async function undoCommand(sessionId) {
  const { data } = await api.post(`/edit/undo/${sessionId}`);
  return data;
}

// ── Assets ────────────────────────────────────────────────────────────────

export async function listFurniture(category = '', style = '') {
  const { data } = await api.get('/assets/furniture', { params: { category, style } });
  return data;
}

export async function getHealth() {
  const { data } = await api.get('/health');
  return data;
}
