// ================================================================
// ForensIQ — Test Backend (DIFFERENT data to prove dynamic rendering)
// This simulates Dev A's FastAPI backend with COMPLETELY DIFFERENT values
// to verify the frontend renders whatever the backend sends.
// ================================================================

const http = require('http');

const PORT = 8000;

// ── COMPLETELY DIFFERENT test data ──
const TEST_CASES = [
  {
    case_id: 'c-test-001', case_number: 'AIV-2026-9999',
    title: 'Ravi Verma Suspicious Fire Case',
    description: 'Arson suspected at a warehouse in Noida sector 62.',
    location: 'Noida, Uttar Pradesh', status: 'OPEN', risk_level: 'CRITICAL', priority: 'URGENT',
    created_at: '2026-05-10T10:00:00Z', updated_at: '2026-05-10T12:00:00Z',
    assigned_to: 'Dr. Meera Patel', victim_name: '[REDACTED]', victim_age: 45,
    hypothesis: [
      { key: 'HOMICIDE', probability: 0.45, trend: 'UP' },
      { key: 'ACCIDENT', probability: 0.35, trend: 'DOWN' },
      { key: 'SUICIDE', probability: 0.15, trend: 'STABLE' },
      { key: 'NATURAL', probability: 0.05, trend: 'STABLE' },
    ],
    evidence_count: 12, pipeline_status: 'IN_PROGRESS',
    agents_completed: 9, agents_total: 17,
  },
  {
    case_id: 'c-test-002', case_number: 'AIV-2026-8888',
    title: 'Sneha Iyer Missing Person → Found Deceased',
    description: 'Body found in Kodaikanal forest area, 3 days after disappearance.',
    location: 'Kodaikanal, Tamil Nadu', status: 'IN_ANALYSIS', risk_level: 'HIGH',
    created_at: '2026-05-09T08:00:00Z', updated_at: '2026-05-10T06:00:00Z',
    assigned_to: 'DCP Ramesh Kumar', evidence_count: 4, pipeline_status: 'COMPLETE',
    hypothesis: [
      { key: 'SUICIDE', probability: 0.52, trend: 'UP' },
      { key: 'HOMICIDE', probability: 0.28, trend: 'DOWN' },
      { key: 'ACCIDENT', probability: 0.18, trend: 'STABLE' },
      { key: 'NATURAL', probability: 0.02, trend: 'STABLE' },
    ],
    agents_completed: 17, agents_total: 17,
  },
];

const TEST_TOD = {
  mode: 'MULTI_MODEL',
  pointEstimate: '2026-05-09T23:45:00Z',
  window95: { start: '2026-05-09T20:00:00Z', end: '2026-05-10T04:00:00Z' },
  pmiMeanHours: 6.25,
  componentContributions: [
    { component: 'henssge_core', weight: 0.40, description: 'Nomogram from rectal temperature' },
    { component: 'heuristic_signs', weight: 0.30, description: 'Rigor and livor staging assessment' },
    { component: 'prior_timeline', weight: 0.20, description: 'Last known alive from CCTV footage' },
    { component: 'ml_surrogate', weight: 0.10, description: 'XGBoost ensemble model' },
  ],
  consistency: { rigor: 'CONSISTENT', livor: 'INCONSISTENT', algor: 'CONSISTENT', decomposition: 'CONSISTENT' },
  henssgeInputs: { rectalTemp: 28.5, ambientTemp: 22.0, bodyWeight: 55, clothingInsulation: 'LIGHT', sceneType: 'OUTDOOR', bodySurface: 'GROUND', measurementTime: '2026-05-10T06:00:00Z' },
};

const TEST_HYPOTHESIS = {
  posteriors: { HOMICIDE: 0.45, ACCIDENT: 0.35, SUICIDE: 0.15, NATURAL: 0.05 },
  topHypothesis: 'HOMICIDE', topConfidence: 0.45,
  signals: [
    { signal: 'accelerant_detected', source: 'Cat A', value: 'GASOLINE', lr: 8.5, direction: 'HOMICIDE', confidence: 0.88 },
    { signal: 'multiple_ignition_points', source: 'Cat A', value: 'TRUE', lr: 6.1, direction: 'HOMICIDE', confidence: 0.82 },
    { signal: 'insurance_policy_recent', source: 'Cat C', value: 'TRUE', lr: 3.4, direction: 'HOMICIDE', confidence: 0.75 },
    { signal: 'no_suicide_note', source: 'Cat D', value: 'ABSENT', lr: 1.2, direction: 'NEUTRAL', confidence: 0.60 },
    { signal: 'electrical_fault_possible', source: 'Cat B', value: 'MINOR', lr: 0.6, direction: 'ACCIDENT', confidence: 0.55 },
  ],
};

const TEST_ANOMALIES = [
  { id: 'ta-1', score: 0.97, severity: 'CRITICAL', title: 'Multiple accelerant traces found at scene', detail: 'Chemical analysis detected gasoline residue at 3 separate ignition points.', sources: ['FORENSIC_LAB'], rule: 'Rule 1: Multi-point ignition', inTodWindow: true },
  { id: 'ta-2', score: 0.85, severity: 'HIGH', title: 'Insurance policy purchased 2 weeks ago', detail: '₹50 lakh fire insurance policy acquired on 2026-04-26.', sources: ['FINANCIAL'], rule: 'Rule 4: Recent financial motive', inTodWindow: false },
  { id: 'ta-3', score: 0.72, severity: 'MEDIUM', title: 'CCTV footage gap of 90 minutes', detail: 'Security camera in loading bay offline from 22:30 to 00:00.', sources: ['CCTV'], rule: 'Rule 8: Surveillance anomaly', inTodWindow: true },
];

const TEST_TIMELINE = [
  { id: 'te01', timestamp: '2026-05-09T22:30:00Z', source: 'CCTV', type: 'CAMERA_OFFLINE', description: 'Loading bay camera goes offline', anomalyScore: 0.85 },
  { id: 'te02', timestamp: '2026-05-09T23:15:00Z', source: 'PHONE', type: 'OUTGOING_CALL', description: 'Call to unknown number — 3min', anomalyScore: 0.72 },
  { id: 'te03', timestamp: '2026-05-09T23:45:00Z', source: 'FIRE', type: 'FIRE_START', description: '★ Estimated fire ignition time', anomalyScore: null },
  { id: 'te04', timestamp: '2026-05-10T00:05:00Z', source: 'OTHER', type: 'FIRE_REPORTED', description: 'Fire reported by security guard', anomalyScore: null },
  { id: 'te05', timestamp: '2026-05-10T00:22:00Z', source: 'OTHER', type: 'FIRE_BRIGADE', description: 'Fire brigade arrival', anomalyScore: null },
];

const TEST_AGENTS = [
  { id: 'evidence_parser', name: 'Evidence Parser', tier: 0, category: 'INGEST', model: 'Rule-based', port: 8010 },
  { id: 'ocr', name: 'OCR Engine', tier: 0, category: 'INGEST', model: 'Tesseract 5', port: 8011 },
  { id: 'format_normalizer', name: 'Format Normalizer', tier: 1, category: 'INGEST', model: 'Rule-based', port: 8012 },
  { id: 'fire_scene_agent', name: 'Fire Scene Analyzer', tier: 2, category: 'VISION', model: 'YOLOv8 + ViT', port: 8020 },
  { id: 'chemical_analyzer', name: 'Chemical Analyzer', tier: 2, category: 'NLP', model: 'Gemini 2.0', port: 8021 },
];

const TEST_REPORT = {
  executiveSummary: 'Analysis of the Ravi Verma warehouse fire indicates ARSON (classified as HOMICIDE) as the most probable cause with 45% posterior probability. Multiple accelerant traces and a recently purchased insurance policy are key signals. TOD estimate places the fire at approximately 11:45 PM on May 9, 2026.',
  sections: ['Scene Reconstruction', 'Chemical Analysis', 'Fire Origin & Spread', 'Financial Motive', 'Digital Timeline', 'Hypothesis Assessment', 'Uncertainty Report'],
  chainValid: true,
  generatedAt: '2026-05-10T08:00:00Z',
};

const TEST_AUDIT = [
  { id: 'tal-1', timestamp: '2026-05-10T06:00:00Z', user: 'Dr. Meera Patel', role: 'FORENSIC_PATHOLOGIST', action: 'EVIDENCE_UPLOAD', resource: 'Fire_Scene_Report.pdf', result: 'SUCCESS', ip: '10.0.1.15' },
  { id: 'tal-2', timestamp: '2026-05-10T06:01:00Z', user: 'SYSTEM', role: '-', action: 'AGENT_RUN_START', resource: 'fire_scene_agent', result: 'SUCCESS', ip: 'internal' },
  { id: 'tal-3', timestamp: '2026-05-10T06:05:00Z', user: 'DCP Ramesh Kumar', role: 'INVESTIGATOR', action: 'CASE_ACCESS', resource: 'AIV-2026-9999', result: 'SUCCESS', ip: '10.0.1.20' },
];

const TEST_REPLAY = [
  { seq: 1, agent_id: 'evidence_parser', trigger: 'PIPELINE_START', input: '12 files uploaded', conclusion: 'Parsed 12 evidence files, identified fire-related documents', confidence: 0.97, duration_ms: 1800 },
  { seq: 2, agent_id: 'fire_scene_agent', trigger: 'PARSER_COMPLETE', input: 'Scene photographs (48)', conclusion: 'Identified 3 separate ignition points, V-patterns consistent with arson', confidence: 0.89, duration_ms: 6200 },
  { seq: 3, agent_id: 'chemical_analyzer', trigger: 'SCENE_COMPLETE', input: 'Lab report + residue samples', conclusion: 'Gasoline detected at ignition points 1 and 3', confidence: 0.94, duration_ms: 3100 },
];

const TEST_EVIDENCE = [
  { file_id: 'tf-1', original_name: 'Fire_Scene_Report.pdf', doc_type: 'SCENE_REPORT', size_bytes: 3200000, status: 'PROCESSED', uploaded_at: '2026-05-10T06:00:00Z', checksum: 'x1y2z3...a4b5' },
  { file_id: 'tf-2', original_name: 'Chemical_Analysis.pdf', doc_type: 'LAB_REPORT', size_bytes: 1500000, status: 'PROCESSED', uploaded_at: '2026-05-10T06:02:00Z', checksum: 'p9q8r7...s6t5' },
  { file_id: 'tf-3', original_name: 'Insurance_Policy.pdf', doc_type: 'FINANCIAL_RECORDS', size_bytes: 420000, status: 'PROCESSED', uploaded_at: '2026-05-10T06:04:00Z', checksum: 'm3n4o5...k6j7' },
];

const TEST_HOTSPOTS = [
  { id: 'ths-1', rank: 1, score: 0.97, label: 'Primary Fire Window', timeWindow: { start: '2026-05-09T23:30:00Z', end: '2026-05-10T00:15:00Z' }, inTodBand: true, anomalyCount: 3, explanation: 'Fire ignition and CCTV gap overlap.' },
];

// ── Route handler ──
function handleRequest(req, res) {
  res.setHeader('Content-Type', 'application/json');
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') { res.writeHead(200); return res.end(); }

  const url = req.url;
  console.log(`[TEST-BACKEND] ${req.method} ${url}`);

  // Auth
  if (url === '/api/v1/auth/login' && req.method === 'POST') {
    return json(res, { access_token: 'test-jwt-live', role: 'FORENSIC_PATHOLOGIST', user_id: 'u-test-001', name: 'Dr. Meera Patel' });
  }

  // Cases
  if (url === '/api/v1/cases/' || url === '/api/v1/cases') {
    return json(res, { data: TEST_CASES });
  }
  if (url.match(/^\/api\/v1\/cases\/[^/]+$/)) {
    return json(res, { data: TEST_CASES[0] });
  }

  // Pipeline
  if (url.match(/\/pipeline\/status/)) {
    return json(res, { data: { pipeline_run_id: 'pr-test-001', status: 'IN_PROGRESS', agents: TEST_AGENTS.map((a, i) => ({ agent_id: a.id, display_name: a.name, tier: a.tier, status: i < 3 ? 'DONE' : 'RUNNING', duration_ms: i < 3 ? 2000 + i * 500 : null })) } });
  }

  // Timeline
  if (url.match(/\/timeline\/summary/)) {
    return json(res, { todWindow: { start: '2026-05-09T20:00:00Z', end: '2026-05-10T04:00:00Z', mode: 'MULTI_MODEL' }, buckets: [] });
  }
  if (url.match(/\/timeline\/events/)) {
    return json(res, { data: TEST_TIMELINE });
  }

  // TOD
  if (url.match(/\/tod$/)) {
    return json(res, TEST_TOD);
  }

  // Hotspots
  if (url.match(/\/hotspots/)) {
    return json(res, { data: TEST_HOTSPOTS });
  }

  // Anomalies
  if (url.match(/\/digital\/anomalies/)) {
    return json(res, { data: TEST_ANOMALIES });
  }

  // Hypothesis
  if (url.match(/\/hypothesis/)) {
    return json(res, TEST_HYPOTHESIS);
  }

  // Graph
  if (url.match(/\/graph/)) {
    return json(res, { nodes: [], edges: [] });
  }

  // Replay
  if (url.match(/\/replay/)) {
    return json(res, { data: TEST_REPLAY });
  }

  // Report
  if (url.match(/\/report/)) {
    return json(res, TEST_REPORT);
  }

  // Audit
  if (url.match(/\/audit/)) {
    return json(res, { data: TEST_AUDIT });
  }

  // Files
  if (url.match(/\/files/)) {
    return json(res, { data: TEST_EVIDENCE });
  }

  // Agents
  if (url === '/api/v1/agents') {
    return json(res, { data: TEST_AGENTS });
  }
  if (url.match(/^\/api\/v1\/agents\//)) {
    return json(res, TEST_AGENTS[0]);
  }

  // System metrics
  if (url.match(/\/system\/metrics/)) {
    return json(res, { active_pipelines: 3, agents_running: 9, llm_tokens_today: 128500, system_health: 'DEGRADED' });
  }

  // 404
  res.writeHead(404);
  res.end(JSON.stringify({ error: 'Not found' }));
}

function json(res, data) {
  res.writeHead(200);
  res.end(JSON.stringify(data));
}

const server = http.createServer(handleRequest);
server.listen(PORT, () => {
  console.log(`\n🧪 ForensIQ Test Backend running on http://localhost:${PORT}`);
  console.log(`   Serving COMPLETELY DIFFERENT data to prove dynamic rendering!\n`);
  console.log(`   Case: "Ravi Verma Suspicious Fire Case" (instead of "Arun Kumar")`);
  console.log(`   Hypothesis: HOMICIDE 45% (instead of 79%)`);
  console.log(`   TOD: 11:45 PM (instead of 09:00 AM)`);
  console.log(`   User: "Dr. Meera Patel" (instead of "Arjun Sharma")`);
  console.log(`   Agents: 5 (instead of 17)`);
  console.log(`   System Health: DEGRADED (instead of HEALTHY)\n`);
});
