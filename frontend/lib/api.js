// ================================================================
// AIVENTRA — REST API Client with JWT + Mock Fallback
// All endpoints follow CANONICAL_05 contract: /api/v1/*
// Fully integrated with Dev A backend endpoints.
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
    throw new Error(err.error?.message || err.detail || `API Error ${res.status}`);
  }
  return res.json();
}

export const api = {
  // --- Auth ---
  // Backend uses OAuth2PasswordRequestForm (form-data), not JSON body
  login: async (email, password) => {
    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData,
      });
      if (!res.ok) throw new Error('Login failed');
      const data = await res.json();
      return { access_token: data.access_token, role: 'INVESTIGATOR', user_id: 'u-001', name: email.split('@')[0] };
    }
    catch { return { access_token: 'mock-jwt-token', role: 'INVESTIGATOR', user_id: 'u-001', name: 'Arjun Sharma' }; }
  },

  // --- Cases ---
  // Backend: GET /api/v1/cases  → list
  getCases: async () => {
    try { const r = await request('/cases'); return r.data || r; }
    catch { return MOCK_CASES; }
  },
  // Backend: GET /api/v1/cases/{case_id}
  getCase: async (caseId) => {
    try { const r = await request(`/cases/${caseId}`); return r.data || r; }
    catch { return MOCK_CASES.find(c => c.case_id === caseId) || MOCK_CASES[0]; }
  },
  // Backend: POST /api/v1/cases
  createCase: async (data) => {
    try { return await request('/cases', { method: 'POST', body: JSON.stringify(data) }); }
    catch { return { case_id: 'c-new-' + Date.now() }; }
  },

  // --- Files ---
  // Backend: GET /api/v1/cases/{case_id}/files
  getFiles: async (caseId) => {
    try { const r = await request(`/cases/${caseId}/files`); return r.data || r; }
    catch { return MOCK_EVIDENCE_FILES; }
  },
  // Backend: POST /api/v1/cases/{case_id}/files (multipart)
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
  // Backend: POST /api/v1/cases/{case_id}/pipeline/trigger
  triggerPipeline: async (caseId) => {
    try { return await request(`/cases/${caseId}/pipeline/trigger`, { method: 'POST' }); }
    catch { return { pipeline_run_id: 'pr-' + Date.now() }; }
  },
  // Backend: GET /api/v1/cases/{case_id}/pipeline/status
  getPipelineStatus: async (caseId) => {
    try { const r = await request(`/cases/${caseId}/pipeline/status`); return r.data || r; }
    catch { return MOCK_PIPELINE_STATUS; }
  },

  // --- Timeline ---
  // Backend: GET /api/v1/cases/{case_id}/timeline/summary
  getTimelineSummary: async (caseId) => {
    try { return await request(`/cases/${caseId}/timeline/summary`); }
    catch { return MOCK_TIMELINE_SUMMARY; }
  },
  // Backend: GET /api/v1/cases/{case_id}/timeline/events
  getTimelineEvents: async (caseId) => {
    try { const r = await request(`/cases/${caseId}/timeline/events`); return r.data || r; }
    catch { return MOCK_TIMELINE_EVENTS; }
  },

  // --- TOD ---
  // Backend: GET /api/v1/cases/{case_id}/analysis/tod
  getTodResult: async (caseId) => {
    try { return await request(`/cases/${caseId}/analysis/tod`); }
    catch { return MOCK_TOD_RESULT; }
  },

  // --- Hotspots ---
  // Backend: GET /api/v1/cases/{case_id}/hotspots
  getHotspots: async (caseId) => {
    try { const r = await request(`/cases/${caseId}/hotspots`); return r.hotspots || r.data || r; }
    catch { return MOCK_HOTSPOTS; }
  },

  // --- Anomalies ---
  // Backend: GET /api/v1/cases/{case_id}/analysis/anomalies
  getAnomalies: async (caseId) => {
    try { const r = await request(`/cases/${caseId}/analysis/anomalies`); return r.data || r; }
    catch { return MOCK_ANOMALIES; }
  },

  // --- Hypothesis ---
  // Backend: GET /api/v1/cases/{case_id}/analysis/hypothesis
  getHypothesis: async (caseId) => {
    try { return await request(`/cases/${caseId}/analysis/hypothesis`); }
    catch { return MOCK_HYPOTHESIS; }
  },

  // --- Causal Graph ---
  // Backend: GET /api/v1/cases/{case_id}/graph
  getGraph: async (caseId) => {
    try { return await request(`/cases/${caseId}/graph`); }
    catch { return MOCK_CAUSAL_GRAPH; }
  },

  // --- Replay ---
  // Backend: GET /api/v1/cases/{case_id}/replay
  getReplay: async (caseId) => {
    try { const r = await request(`/cases/${caseId}/replay`); return r.data || r; }
    catch { return MOCK_REPLAY_STEPS; }
  },

  // --- Report ---
  // Backend: GET /api/v1/cases/{case_id}/report
  getReport: async (caseId) => {
    try { return await request(`/cases/${caseId}/report`); }
    catch { return MOCK_REPORT; }
  },

  // --- Audit ---
  // Backend: GET /api/v1/cases/{case_id}/audit (or /cases/system/audit)
  getAuditLog: async (caseId) => {
    try { const r = await request(`/cases/${caseId}/audit`); return r.data || r; }
    catch { return MOCK_AUDIT_LOG; }
  },

  // --- Agents ---
  // Backend: GET /api/v1/agents
  getAgents: async () => {
    try { const r = await request('/agents'); return r.data || r; }
    catch { return MOCK_AGENTS; }
  },
  // Backend: GET /api/v1/agents/{agent_id}
  getAgent: async (agentId) => {
    try { return await request(`/agents/${agentId}`); }
    catch { return MOCK_AGENTS.find(a => a.id === agentId) || MOCK_AGENTS[0]; }
  },
  // Backend: POST /api/v1/agents/{agent_id}/test-run
  testAgent: async (agentId, input) => {
    try { return await request(`/agents/${agentId}/test-run`, { method: 'POST', body: JSON.stringify(input) }); }
    catch { return { output_summary: 'Mock test result', status: 'DONE', duration_ms: 1500 }; }
  },

  // --- System ---
  // Backend: GET /api/v1/system/metrics
  getSystemMetrics: async () => {
    try { return await request('/system/metrics'); }
    catch { return { active_pipelines: 1, agents_running: 3, llm_tokens_today: 42350, system_health: 'HEALTHY' }; }
  },
};
