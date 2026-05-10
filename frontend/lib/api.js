// ================================================================
// AIVENTRA — REST API Client with JWT + Mock Fallback
// All endpoints follow CANONICAL_05 contract: /api/v1/*
// ================================================================

import {
  MOCK_CASES, MOCK_PIPELINE_STATUS, MOCK_TIMELINE_EVENTS,
  MOCK_TIMELINE_SUMMARY, MOCK_TOD_RESULT, MOCK_HOTSPOTS,
  MOCK_ANOMALIES, MOCK_HYPOTHESIS, MOCK_CAUSAL_GRAPH,
  MOCK_REPLAY_STEPS, MOCK_AUDIT_LOG, MOCK_AGENTS,
  MOCK_EVIDENCE_FILES, MOCK_REPORT
} from './mockData';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

function getToken() {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('aiventra_token');
}

async function request(path, options = {}) {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: { message: res.statusText } }));
    throw new Error(err.error?.message || `API Error ${res.status}`);
  }
  return res.json();
}

export const api = {
  // --- Auth ---
  login: async (email, password) => {
    try { return await request('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }); }
    catch { return { access_token: 'mock-jwt-token', role: 'INVESTIGATOR', user_id: 'u-001', name: 'Arjun Sharma' }; }
  },

  // --- Cases ---
  getCases: async () => {
    try { const r = await request('/cases/'); return r.data || r; }
    catch { return MOCK_CASES; }
  },
  getCase: async (caseId) => {
    try { const r = await request(`/cases/${caseId}`); return r.data || r; }
    catch { return MOCK_CASES.find(c => c.case_id === caseId) || MOCK_CASES[0]; }
  },
  createCase: async (data) => {
    try { return await request('/cases/', { method: 'POST', body: JSON.stringify(data) }); }
    catch { return { case_id: 'c-new-' + Date.now() }; }
  },

  // --- Files ---
  getFiles: async (caseId) => {
    try { const r = await request(`/cases/${caseId}/files`); return r.data || r; }
    catch { return MOCK_EVIDENCE_FILES; }
  },
  uploadFile: async (caseId, formData) => {
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE}/cases/${caseId}/files`, {
        method: 'POST', body: formData,
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      });
      return res.json();
    } catch { return { file_id: 'f-new-' + Date.now(), status: 'PROCESSING' }; }
  },

  // --- Pipeline ---
  triggerPipeline: async (caseId) => {
    try { return await request(`/cases/${caseId}/pipeline/trigger`, { method: 'POST' }); }
    catch { return { pipeline_run_id: 'pr-' + Date.now() }; }
  },
  getPipelineStatus: async (caseId) => {
    try { const r = await request(`/cases/${caseId}/pipeline/status`); return r.data || r; }
    catch { return MOCK_PIPELINE_STATUS; }
  },

  // --- Timeline ---
  getTimelineSummary: async (caseId) => {
    try { return await request(`/cases/${caseId}/timeline/summary`); }
    catch { return MOCK_TIMELINE_SUMMARY; }
  },
  getTimelineEvents: async (caseId) => {
    try { const r = await request(`/cases/${caseId}/timeline/events`); return r.data || r; }
    catch { return MOCK_TIMELINE_EVENTS; }
  },

  // --- TOD ---
  getTodResult: async (caseId) => {
    try { return await request(`/cases/${caseId}/tod`); }
    catch { return MOCK_TOD_RESULT; }
  },

  // --- Hotspots ---
  getHotspots: async (caseId) => {
    try { const r = await request(`/cases/${caseId}/hotspots`); return r.data || r; }
    catch { return MOCK_HOTSPOTS; }
  },

  // --- Anomalies ---
  getAnomalies: async (caseId) => {
    try { const r = await request(`/cases/${caseId}/digital/anomalies`); return r.data || r; }
    catch { return MOCK_ANOMALIES; }
  },

  // --- Hypothesis ---
  getHypothesis: async (caseId) => {
    try { return await request(`/cases/${caseId}/hypothesis`); }
    catch { return MOCK_HYPOTHESIS; }
  },

  // --- Causal Graph ---
  getGraph: async (caseId) => {
    try { return await request(`/cases/${caseId}/graph`); }
    catch { return MOCK_CAUSAL_GRAPH; }
  },

  // --- Replay ---
  getReplay: async (caseId) => {
    try { const r = await request(`/cases/${caseId}/replay`); return r.data || r; }
    catch { return MOCK_REPLAY_STEPS; }
  },

  // --- Report ---
  getReport: async (caseId) => {
    try { return await request(`/cases/${caseId}/report`); }
    catch { return MOCK_REPORT; }
  },

  // --- Audit ---
  getAuditLog: async (caseId) => {
    try { const r = await request(`/cases/${caseId}/audit`); return r.data || r; }
    catch { return MOCK_AUDIT_LOG; }
  },

  // --- Agents ---
  getAgents: async () => {
    try { const r = await request('/agents'); return r.data || r; }
    catch { return MOCK_AGENTS; }
  },
  getAgent: async (agentId) => {
    try { return await request(`/agents/${agentId}`); }
    catch { return MOCK_AGENTS.find(a => a.id === agentId) || MOCK_AGENTS[0]; }
  },
  testAgent: async (agentId, input) => {
    try { return await request(`/agents/${agentId}/test-run`, { method: 'POST', body: JSON.stringify(input) }); }
    catch { return { output_summary: 'Mock test result', status: 'DONE', duration_ms: 1500 }; }
  },

  // --- System ---
  getSystemMetrics: async () => {
    try { return await request('/system/metrics'); }
    catch { return { active_pipelines: 1, agents_running: 3, llm_tokens_today: 42350, system_health: 'HEALTHY' }; }
  },
};
