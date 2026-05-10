// ================================================================
// AIVENTRA — Zustand Global State Stores
// Stores: auth, case, pipeline (per Layer 4 spec)
// ================================================================

import { create } from 'zustand';

// --- Auth Store ---
export const useAuthStore = create((set) => ({
  token: typeof window !== 'undefined' ? localStorage.getItem('aiventra_token') : null,
  user: null,
  role: null,
  isAuthenticated: typeof window !== 'undefined' ? !!localStorage.getItem('aiventra_token') : false,

  login: (token, user, role) => {
    if (typeof window !== 'undefined') localStorage.setItem('aiventra_token', token);
    set({ token, user, role, isAuthenticated: true });
  },
  logout: () => {
    if (typeof window !== 'undefined') localStorage.removeItem('aiventra_token');
    set({ token: null, user: null, role: null, isAuthenticated: false });
  },
}));

// --- Case Store ---
export const useCaseStore = create((set) => ({
  activeCaseId: null,
  activeCase: null,
  activeTab: 'overview',
  cases: [],
  loading: false,

  setActiveCaseId: (id) => set({ activeCaseId: id }),
  setActiveCase: (c) => set({ activeCase: c }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setCases: (cases) => set({ cases }),
  setLoading: (loading) => set({ loading }),
}));

// --- Pipeline Store ---
export const usePipelineStore = create((set) => ({
  pipelineRunId: null,
  status: 'IDLE',       // IDLE | QUEUED | RUNNING | DONE | FAILED
  agentStatuses: {},     // { [agentId]: 'PENDING' | 'RUNNING' | 'DONE' | 'FAILED' }
  agentDurations: {},    // { [agentId]: ms }
  totalTokens: 0,
  totalDurationMs: 0,
  progress: 0,

  setStatus: (status) => set({ status }),
  setPipelineRun: (id) => set({ pipelineRunId: id }),
  setAgentStatus: (agentId, status) => set((s) => ({
    agentStatuses: { ...s.agentStatuses, [agentId]: status },
  })),
  setAgentDuration: (agentId, ms) => set((s) => ({
    agentDurations: { ...s.agentDurations, [agentId]: ms },
  })),
  updateProgress: () => set((s) => {
    const total = Object.keys(s.agentStatuses).length || 1;
    const done = Object.values(s.agentStatuses).filter(v => v === 'DONE').length;
    return { progress: Math.round((done / total) * 100) };
  }),
  reset: () => set({
    pipelineRunId: null, status: 'IDLE', agentStatuses: {},
    agentDurations: {}, totalTokens: 0, totalDurationMs: 0, progress: 0,
  }),
}));
