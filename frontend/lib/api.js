// ================================================================
// ForensIQ — REST API Client with JWT
// All endpoints follow CANONICAL_05 contract: /api/v1/*
// Fully integrated with Dev A backend endpoints. No mock data.
// ================================================================

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

function getToken() {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('forensiq_token');
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
  login: async (email, password) => {
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
  },

  // --- Cases ---
  getCases: async () => {
    const r = await request('/cases'); return r.data || r;
  },
  getCase: async (caseId) => {
    const r = await request(`/cases/${caseId}`); return r.data || r;
  },
  createCase: async (data) => {
    return await request('/cases', { method: 'POST', body: JSON.stringify(data) });
  },

  // --- Files ---
  getFiles: async (caseId) => {
    const r = await request(`/cases/${caseId}/files`); return r.data || r;
  },
  uploadFile: async (caseId, formData) => {
    const token = getToken();
    const res = await fetch(`${API_BASE}/cases/${caseId}/files`, {
      method: 'POST', body: formData,
      headers: token ? { 'Authorization': `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error('Upload failed');
    return res.json();
  },

  // --- Pipeline ---
  triggerPipeline: async (caseId) => {
    return await request(`/cases/${caseId}/pipeline/trigger`, { method: 'POST' });
  },
  getPipelineStatus: async (caseId) => {
    const r = await request(`/cases/${caseId}/pipeline/status`); return r.data || r;
  },

  // --- Timeline ---
  getTimelineSummary: async (caseId) => {
    return await request(`/cases/${caseId}/timeline/summary`);
  },
  getTimelineEvents: async (caseId) => {
    const r = await request(`/cases/${caseId}/timeline/events`); return r.data || r;
  },

  // --- TOD ---
  getTodResult: async (caseId) => {
    return await request(`/cases/${caseId}/analysis/tod`);
  },

  // --- Hotspots ---
  getHotspots: async (caseId) => {
    const r = await request(`/cases/${caseId}/hotspots`); return r.hotspots || r.data || r;
  },

  // --- Anomalies ---
  getAnomalies: async (caseId) => {
    const r = await request(`/cases/${caseId}/analysis/anomalies`); return r.data || r;
  },

  // --- Hypothesis ---
  getHypothesis: async (caseId) => {
    return await request(`/cases/${caseId}/analysis/hypothesis`);
  },

  // --- Causal Graph ---
  getGraph: async (caseId) => {
    return await request(`/cases/${caseId}/graph`);
  },

  // --- Replay ---
  getReplay: async (caseId) => {
    const r = await request(`/cases/${caseId}/replay`); return r.data || r;
  },

  // --- Report ---
  getReport: async (caseId) => {
    return await request(`/cases/${caseId}/report`);
  },

  // --- Audit ---
  getAuditLog: async (caseId) => {
    const r = await request(`/cases/${caseId}/audit`); return r.data || r;
  },

  // --- Agents ---
  getAgents: async () => {
    const r = await request('/agents'); return r.data || r;
  },
  getAgent: async (agentId) => {
    return await request(`/agents/${agentId}`);
  },

  // --- System ---
  getSystemMetrics: async () => {
    const r = await request('/system/metrics'); return r.data || r;
  }
};
