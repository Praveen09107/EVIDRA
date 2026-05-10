// ================================================================
// AIVENTRA — WebSocket Client with Auto-Reconnect
// Endpoint: /ws/cases/{case_id}?token=... (per CANONICAL_03 CTR-03)
// ================================================================

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 16000, 30000];

export class TelemetryClient {
  constructor() {
    this.ws = null;
    this.reconnectAttempt = 0;
    this.reconnectTimer = null;
    this.heartbeatTimer = null;
    this.listeners = new Map();
    this.connected = false;
    this.caseId = null;
  }

  connect(caseId) {
    if (typeof window === 'undefined') return;
    this.caseId = caseId;
    const token = localStorage.getItem('aiventra_token') || '';
    const url = `${WS_BASE}/ws/cases/${caseId}?token=${token}`;

    try {
      this.ws = new WebSocket(url);
    } catch {
      console.warn('[WS] Connection failed, running in mock mode');
      return;
    }

    this.ws.onopen = () => {
      this.connected = true;
      this.reconnectAttempt = 0;
      this._emit('connection', { connected: true });
      this._startHeartbeat();
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        this._emit(msg.event || msg.event_type || 'message', msg.payload || msg.data || msg);
      } catch (e) {
        console.warn('[WS] Parse error:', e);
      }
    };

    this.ws.onclose = (event) => {
      this.connected = false;
      this._stopHeartbeat();
      this._emit('connection', { connected: false });
      if (!event.wasClean) this._scheduleReconnect();
    };

    this.ws.onerror = () => { this.ws?.close(); };
  }

  disconnect() {
    this._stopHeartbeat();
    clearTimeout(this.reconnectTimer);
    if (this.ws) { this.ws.close(1000); this.ws = null; }
    this.connected = false;
  }

  on(event, callback) {
    if (!this.listeners.has(event)) this.listeners.set(event, new Set());
    this.listeners.get(event).add(callback);
    return () => this.listeners.get(event)?.delete(callback);
  }

  _emit(event, data) {
    this.listeners.get(event)?.forEach(cb => {
      try { cb(data); } catch (e) { console.error('[WS] Listener error:', e); }
    });
  }

  _scheduleReconnect() {
    const delay = RECONNECT_DELAYS[Math.min(this.reconnectAttempt, RECONNECT_DELAYS.length - 1)];
    this.reconnectAttempt++;
    this._emit('reconnecting', { attempt: this.reconnectAttempt, delay });
    this.reconnectTimer = setTimeout(() => this.connect(this.caseId), delay);
  }

  _startHeartbeat() {
    this.heartbeatTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) this.ws.send('ping');
    }, 25000);
  }

  _stopHeartbeat() { clearInterval(this.heartbeatTimer); }
}

// Singleton instance
let _instance = null;
export function getTelemetryClient() {
  if (!_instance) _instance = new TelemetryClient();
  return _instance;
}
