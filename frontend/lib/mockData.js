// ================================================================
// ForensIQ — Centralized Mock Data (Forensically Realistic)
// Based on PLAN_18 Synthetic Test Case: "Arun Kumar Incident"
// ================================================================

export const MOCK_USER = {
  user_id: 'u-001', email: 'arjun.sharma@cbi.gov.in',
  name: 'Arjun Sharma', role: 'INVESTIGATOR', org: 'Central Bureau of Investigation'
};

export const MOCK_AGENTS = [
  { id: 'evidence_parser', name: 'Evidence Parser', tier: 0, category: 'INGEST', model: 'Rule-based', port: 8010 },
  { id: 'ocr', name: 'OCR Engine', tier: 0, category: 'INGEST', model: 'Tesseract 5', port: 8011 },
  { id: 'format_normalizer', name: 'Format Normalizer', tier: 1, category: 'INGEST', model: 'Rule-based', port: 8012 },
  { id: 'autopsy_agent', name: 'Autopsy Agent', tier: 2, category: 'NLP', model: 'Gemini 2.0 Flash', port: 8020 },
  { id: 'cdr_analyzer', name: 'CDR Analyzer', tier: 2, category: 'TABULAR', model: 'Rule + Anomaly', port: 8021 },
  { id: 'financial_analyzer', name: 'Financial Analyzer', tier: 2, category: 'TABULAR', model: 'Rule + Anomaly', port: 8022 },
  { id: 'image_agent', name: 'Image Agent', tier: 2, category: 'VISION', model: 'YOLOv8n', port: 8023 },
  { id: 'tod_agent', name: 'TOD Agent', tier: 3, category: 'HYBRID', model: 'Henssge + RF', port: 8030 },
  { id: 'timeline_anomaly', name: 'Timeline & Anomaly', tier: 3, category: 'ML', model: 'IF + AE', port: 8031 },
  { id: 'collision_agent', name: 'Collision Agent', tier: 3, category: 'TABULAR', model: 'Spatio-temporal', port: 8032 },
  { id: 'hotspot_engine', name: 'Hotspot Engine', tier: 4, category: 'FUSION', model: 'KDE + DBSCAN', port: 8040 },
  { id: 'claim_extractor', name: 'Claim Extractor', tier: 4, category: 'NLP', model: 'Gemini 2.0 Flash', port: 8041 },
  { id: 'evidence_claim_mapper', name: 'Evidence-Claim Mapper', tier: 5, category: 'NLP', model: 'NLI Pipeline', port: 8050 },
  { id: 'hypothesis_manager', name: 'Hypothesis Manager', tier: 5, category: 'REASONING', model: 'Bayesian Engine', port: 8051 },
  { id: 'bias_uncertainty', name: 'Bias & Uncertainty', tier: 5, category: 'XAI', model: 'SHAP + Monitor', port: 8052 },
  { id: 'nbe_agent', name: 'Next-Best-Evidence', tier: 6, category: 'GUIDANCE', model: 'Gemini 2.0 Flash', port: 8060 },
  { id: 'reasoning_replay', name: 'Reasoning Replay', tier: 7, category: 'AUDIT', model: 'Chain Builder', port: 8061 },
];

export const MOCK_CASES = [
  {
    case_id: 'c-550e8400', case_number: 'AIV-2026-0047', title: 'Arun Kumar Death Investigation',
    description: 'Suspicious death of 32-year-old male found in residential apartment, Pitampura, Delhi.',
    location: 'Pitampura, New Delhi', status: 'IN_ANALYSIS', risk_level: 'HIGH', priority: 'URGENT',
    created_at: '2026-05-07T14:30:00Z', updated_at: '2026-05-09T02:14:00Z',
    assigned_to: MOCK_USER.name, victim_name: '[REDACTED]', victim_age: 32,
    hypothesis: [
      { key: 'HOMICIDE', probability: 0.79, trend: 'UP' },
      { key: 'ACCIDENT', probability: 0.12, trend: 'DOWN' },
      { key: 'SUICIDE', probability: 0.06, trend: 'DOWN' },
      { key: 'NATURAL', probability: 0.03, trend: 'STABLE' },
    ],
    evidence_count: 6, pipeline_status: 'COMPLETE',
    agents_completed: 14, agents_total: 17,
  },
  {
    case_id: 'c-7a1b2c3d', case_number: 'AIV-2026-0048', title: 'Priya Menon Drowning Case',
    description: 'Body recovered from Yamuna near Boat Club, possible drowning.',
    location: 'Boat Club, New Delhi', status: 'OPEN', risk_level: 'MEDIUM', priority: 'NORMAL',
    created_at: '2026-05-08T09:15:00Z', updated_at: '2026-05-08T09:15:00Z',
    assigned_to: 'Priya Menon', evidence_count: 2, pipeline_status: 'PENDING',
    hypothesis: [
      { key: 'ACCIDENT', probability: 0.45, trend: 'STABLE' },
      { key: 'SUICIDE', probability: 0.30, trend: 'UP' },
      { key: 'HOMICIDE', probability: 0.20, trend: 'DOWN' },
      { key: 'NATURAL', probability: 0.05, trend: 'STABLE' },
    ],
    agents_completed: 0, agents_total: 17,
  },
  {
    case_id: 'c-9e8f7g6h', case_number: 'AIV-2026-0045', title: 'Vikram Das Poisoning Inquiry',
    description: 'Suspected poisoning found during routine autopsy.',
    location: 'Saket, New Delhi', status: 'REVIEW', risk_level: 'CRITICAL', priority: 'URGENT',
    created_at: '2026-05-05T16:00:00Z', updated_at: '2026-05-09T01:40:00Z',
    assigned_to: 'Vikram Das', evidence_count: 8, pipeline_status: 'COMPLETE',
    hypothesis: [
      { key: 'HOMICIDE', probability: 0.88, trend: 'STABLE' },
      { key: 'SUICIDE', probability: 0.08, trend: 'DOWN' },
      { key: 'ACCIDENT', probability: 0.03, trend: 'DOWN' },
      { key: 'NATURAL', probability: 0.01, trend: 'STABLE' },
    ],
    agents_completed: 17, agents_total: 17,
  },
];

export const MOCK_PIPELINE_STATUS = {
  pipeline_run_id: 'pr-001', status: 'COMPLETE',
  agents: MOCK_AGENTS.map((a, i) => ({
    agent_id: a.id, display_name: a.name, tier: a.tier,
    status: i < 14 ? 'DONE' : 'PENDING',
    duration_ms: i < 14 ? Math.floor(Math.random() * 5000) + 1000 : null,
  })),
};

export const MOCK_TIMELINE_EVENTS = [
  { id: 'e01', timestamp: '2026-05-06T23:47:00Z', source: 'FINANCIAL', type: 'ATM_WITHDRAWAL', description: 'ATM withdrawal ₹10,000 at Pitampura', anomalyScore: 0.62 },
  { id: 'e02', timestamp: '2026-05-07T01:00:00Z', source: 'PHONE', type: 'INCOMING_CALL', description: 'Incoming call from [CONTACT_1] — 45s', anomalyScore: 0.3 },
  { id: 'e03', timestamp: '2026-05-07T02:15:00Z', source: 'PHONE', type: 'OUTGOING_CALL', description: 'Last outgoing call to [CONTACT_2] — 127s', anomalyScore: 0.94 },
  { id: 'e04', timestamp: '2026-05-07T02:17:00Z', source: 'DEVICE', type: 'WHATSAPP_SENT', description: 'WhatsApp message: "yeah can we talk tomorrow"', anomalyScore: 0.4 },
  { id: 'e05', timestamp: '2026-05-07T02:19:00Z', source: 'DEVICE', type: 'WHATSAPP_SENT', description: 'WhatsApp DISTRESSED: "not really. later"', anomalyScore: 0.89 },
  { id: 'e06', timestamp: '2026-05-07T02:20:00Z', source: 'DEVICE', type: 'WHATSAPP_SENT', description: 'Last outgoing WhatsApp message', anomalyScore: 0.91 },
  { id: 'e07', timestamp: '2026-05-07T03:30:00Z', source: 'TOD', type: 'TOD_ESTIMATE', description: '★ TOD Point Estimate (Henssge)', anomalyScore: null },
  { id: 'e08', timestamp: '2026-05-07T14:00:00Z', source: 'OTHER', type: 'BODY_DISCOVERED', description: 'Body discovered by neighbor', anomalyScore: null },
  { id: 'e09', timestamp: '2026-05-07T14:22:00Z', source: 'OTHER', type: 'FIRST_RESPONDER', description: 'First responder arrival', anomalyScore: null },
  { id: 'e10', timestamp: '2026-05-07T15:00:00Z', source: 'OTHER', type: 'SCENE_SEALED', description: 'Scene sealed by forensic team', anomalyScore: null },
];

export const MOCK_TIMELINE_SUMMARY = {
  buckets: Array.from({ length: 24 }, (_, i) => ({
    start: `2026-05-07T${String(i).padStart(2,'0')}:00:00Z`,
    end: `2026-05-07T${String(i+1).padStart(2,'0')}:00:00Z`,
    eventCounts: { phone: i < 3 ? Math.floor(Math.random()*5) : 0, financial: i === 0 ? 1 : 0, device: i < 3 ? Math.floor(Math.random()*3) : 0, other: i >= 14 && i < 16 ? 1 : 0 },
    anomalyScoreAvg: i >= 2 && i < 3 ? 0.88 : i < 3 ? 0.3 : 0.05,
  })),
  todWindow: { start: '2026-05-06T23:30:00Z', end: '2026-05-07T07:00:00Z', mode: 'PHYSICS_ONLY' },
};

export const MOCK_TOD_RESULT = {
  mode: 'PHYSICS_ONLY', pointEstimate: '2026-05-07T03:30:00Z',
  window95: { start: '2026-05-06T23:30:00Z', end: '2026-05-07T07:00:00Z' },
  pmiMeanHours: 10.5,
  componentContributions: [
    { component: 'henssge_core', weight: 0.52, description: 'Nomogram-based core temperature extrapolation' },
    { component: 'heuristic_signs', weight: 0.22, description: 'Rigor, livor, decomposition staging' },
    { component: 'prior_timeline', weight: 0.18, description: 'Last-seen-alive digital evidence' },
    { component: 'ml_surrogate', weight: 0.08, description: 'Random forest regression model' },
  ],
  consistency: { rigor: 'CONSISTENT', livor: 'CONSISTENT', algor: 'CONSISTENT', decomposition: 'CONSISTENT' },
  henssgeInputs: { rectalTemp: 30.0, ambientTemp: 18.0, bodyWeight: 70, clothingInsulation: 'MEDIUM', sceneType: 'INDOOR', bodySurface: 'BED', measurementTime: '2026-05-07T14:00:00Z' },
};

export const MOCK_HOTSPOTS = [
  { id: 'hs-1', rank: 1, score: 0.94, label: 'Primary Hotspot', timeWindow: { start: '2026-05-07T02:15:00Z', end: '2026-05-07T02:20:00Z' }, inTodBand: true, anomalyCount: 4, explanation: 'Cluster of last communication events immediately before silence window.' },
  { id: 'hs-2', rank: 2, score: 0.72, label: 'Secondary Hotspot', timeWindow: { start: '2026-05-06T23:47:00Z', end: '2026-05-07T00:10:00Z' }, inTodBand: true, anomalyCount: 2, explanation: 'Late-night ATM withdrawal coinciding with TOD window boundary.' },
  { id: 'hs-3', rank: 3, score: 0.45, label: 'Tertiary Hotspot', timeWindow: { start: '2026-05-07T14:00:00Z', end: '2026-05-07T15:00:00Z' }, inTodBand: false, anomalyCount: 1, explanation: 'Discovery and scene processing window.' },
];

export const MOCK_ANOMALIES = [
  { id: 'a-1', score: 0.94, severity: 'CRITICAL', title: 'Last outgoing communication before 11h silence', detail: 'Last CDR event: MOC call at 02:17 to [CONTACT_2] (127s). Followed by silence until 14:00 discovery.', sources: ['CDR', 'WhatsApp'], rule: 'Rule 5: Last communication before silence', inTodWindow: true },
  { id: 'a-2', score: 0.91, severity: 'CRITICAL', title: 'Last WhatsApp message before communication cessation', detail: 'Final outgoing WhatsApp at 02:20. No further digital activity for 11h 40min.', sources: ['WhatsApp'], rule: 'Rule 5: Communication cessation', inTodWindow: true },
  { id: 'a-3', score: 0.89, severity: 'HIGH', title: 'Distressed message content at 02:19', detail: 'Content sentiment: DISTRESSED — "not really. later"', sources: ['WhatsApp'], rule: 'Rule 6: Sentiment anomaly', inTodWindow: true },
  { id: 'a-4', score: 0.62, severity: 'MEDIUM', title: 'Late-night ATM withdrawal', detail: 'ATM withdrawal of ₹10,000 at 23:47 — unusual timing pattern.', sources: ['Financial'], rule: 'Rule 3: Night financial activity', inTodWindow: false },
  { id: 'a-5', score: 0.41, severity: 'LOW', title: 'GPS location near crime scene during TOD', detail: '38 of 47 GPS fixes within 200m of scene during TOD window.', sources: ['Location'], rule: 'Rule 7: Scene presence', inTodWindow: true },
];

export const MOCK_HYPOTHESIS = {
  posteriors: { HOMICIDE: 0.79, ACCIDENT: 0.12, SUICIDE: 0.06, NATURAL: 0.03 },
  topHypothesis: 'HOMICIDE', topConfidence: 0.79,
  signals: [
    { signal: 'manner_of_death', source: 'Cat A', value: 'HOMICIDE', lr: 15.0, direction: 'HOMICIDE', confidence: 0.91 },
    { signal: 'defensive_wounds', source: 'Cat A', value: 'TRUE', lr: 3.2, direction: 'HOMICIDE', confidence: 0.87 },
    { signal: 'signs_of_struggle', source: 'Cat F', value: 'TRUE', lr: 2.8, direction: 'HOMICIDE', confidence: 0.93 },
    { signal: 'last_contact_30min', source: 'Cat B', value: 'TRUE', lr: 2.1, direction: 'HOMICIDE', confidence: 0.82 },
    { signal: 'comm_cessation_tod', source: 'Cat B', value: 'MATCHES', lr: 1.4, direction: 'NEUTRAL', confidence: 0.75 },
    { signal: 'distressed_content', source: 'Cat E', value: '0.14 score', lr: 0.8, direction: 'SUICIDE', confidence: 0.71 },
  ],
};

export const MOCK_CAUSAL_GRAPH = {
  nodes: [
    { id: 'n-h1', kind: 'HYPOTHESIS', label: 'HOMICIDE', probability: 0.79 },
    { id: 'n-h2', kind: 'HYPOTHESIS', label: 'SUICIDE', probability: 0.06 },
    { id: 'n-c1', kind: 'CLAIM', label: 'Manner of death indicates homicide' },
    { id: 'n-c2', kind: 'CLAIM', label: 'Defensive wounds present' },
    { id: 'n-c3', kind: 'CLAIM', label: 'Distressed communication before death' },
    { id: 'n-c4', kind: 'CLAIM', label: 'Communication cessation matches TOD' },
    { id: 'n-e1', kind: 'EVIDENCE', label: 'PME_Kumar.pdf' },
    { id: 'n-e2', kind: 'EVIDENCE', label: 'CDR_Victim.csv' },
    { id: 'n-e3', kind: 'EVIDENCE', label: 'WhatsApp_Export.txt' },
    { id: 'n-e4', kind: 'EVIDENCE', label: 'Scene_Report.pdf' },
  ],
  edges: [
    { source: 'n-e1', target: 'n-c1', relation: 'SUPPORTS', strength: 0.91 },
    { source: 'n-e1', target: 'n-c2', relation: 'SUPPORTS', strength: 0.87 },
    { source: 'n-e3', target: 'n-c3', relation: 'SUPPORTS', strength: 0.71 },
    { source: 'n-e2', target: 'n-c4', relation: 'SUPPORTS', strength: 0.82 },
    { source: 'n-c1', target: 'n-h1', relation: 'SUPPORTS', strength: 0.91 },
    { source: 'n-c2', target: 'n-h1', relation: 'SUPPORTS', strength: 0.87 },
    { source: 'n-c3', target: 'n-h2', relation: 'SUPPORTS', strength: 0.45 },
    { source: 'n-c4', target: 'n-h1', relation: 'SUPPORTS', strength: 0.75 },
  ],
};

export const MOCK_REPLAY_STEPS = [
  { seq: 1, agent_id: 'evidence_parser', trigger: 'PIPELINE_START', input: '6 files uploaded', conclusion: 'Parsed 6 evidence files, identified types', confidence: 0.99, duration_ms: 1200 },
  { seq: 2, agent_id: 'ocr', trigger: 'SCANNED_PDF', input: 'PME_Kumar.pdf (scanned)', conclusion: 'OCR extracted 4,200 characters', confidence: 0.95, duration_ms: 3400 },
  { seq: 3, agent_id: 'format_normalizer', trigger: 'PARSER_COMPLETE', input: '6 parsed files', conclusion: 'Normalized to canonical schemas', confidence: 0.98, duration_ms: 800 },
  { seq: 4, agent_id: 'autopsy_agent', trigger: 'NORMALIZED', input: 'canonical_autopsy_json', conclusion: 'COD: stab wound; Manner: HOMICIDE (0.91)', confidence: 0.91, duration_ms: 4500 },
  { seq: 5, agent_id: 'cdr_analyzer', trigger: 'NORMALIZED', input: 'CDR 234 records', conclusion: 'Last call 02:17, 11h silence gap detected', confidence: 0.88, duration_ms: 2100 },
  { seq: 6, agent_id: 'tod_agent', trigger: 'AUTOPSY_COMPLETE', input: 'Henssge inputs', conclusion: 'TOD estimate: 03:30 AM (95% CI: 23:30-07:00)', confidence: 0.85, duration_ms: 3200 },
  { seq: 7, agent_id: 'timeline_anomaly', trigger: 'CDR_COMPLETE', input: '234 CDR + 847 WhatsApp events', conclusion: '12 anomalies detected, 3 CRITICAL', confidence: 0.82, duration_ms: 2800 },
  { seq: 8, agent_id: 'hotspot_engine', trigger: 'TIER3_COMPLETE', input: 'TOD + anomalies + collision', conclusion: '3 hotspot windows identified', confidence: 0.78, duration_ms: 1900 },
  { seq: 9, agent_id: 'hypothesis_manager', trigger: 'TIER4_COMPLETE', input: 'All signals + hotspots', conclusion: 'HOMICIDE 79%, ACCIDENT 12%', confidence: 0.79, duration_ms: 3600 },
  { seq: 10, agent_id: 'bias_uncertainty', trigger: 'HYPOTHESIS_READY', input: 'All agent outputs', conclusion: 'No significant bias detected, evidence coverage 87%', confidence: 0.92, duration_ms: 1400 },
  { seq: 11, agent_id: 'nbe_agent', trigger: 'BIAS_COMPLETE', input: 'Hypothesis + gaps', conclusion: 'Suggest: CCTV footage, witness statements', confidence: 0.75, duration_ms: 1100 },
  { seq: 12, agent_id: 'reasoning_replay', trigger: 'ALL_COMPLETE', input: '47 replay steps', conclusion: 'Chain built, 47 steps verified, integrity ✓', confidence: 0.99, duration_ms: 600 },
];

export const MOCK_AUDIT_LOG = [
  { id: 'al-1', timestamp: '2026-05-09T02:14:00Z', user: 'Arjun Sharma', role: 'INVESTIGATOR', action: 'EVIDENCE_UPLOAD', resource: 'PME_Kumar.pdf', result: 'SUCCESS', ip: '10.0.0.4' },
  { id: 'al-2', timestamp: '2026-05-09T02:14:05Z', user: 'SYSTEM', role: '-', action: 'AGENT_RUN_START', resource: 'evidence_parser', result: 'SUCCESS', ip: 'internal' },
  { id: 'al-3', timestamp: '2026-05-09T02:14:12Z', user: 'SYSTEM', role: '-', action: 'AGENT_RUN_COMPLETE', resource: 'evidence_parser', result: 'SUCCESS', ip: 'internal' },
  { id: 'al-4', timestamp: '2026-05-09T02:14:15Z', user: 'SYSTEM', role: '-', action: 'AGENT_RUN_START', resource: 'autopsy_agent', result: 'SUCCESS', ip: 'internal' },
  { id: 'al-5', timestamp: '2026-05-09T02:14:44Z', user: 'SYSTEM', role: '-', action: 'AGENT_RUN_COMPLETE', resource: 'autopsy_agent', result: 'SUCCESS', ip: 'internal' },
  { id: 'al-6', timestamp: '2026-05-09T02:15:00Z', user: 'Arjun Sharma', role: 'INVESTIGATOR', action: 'EVIDENCE_ACCESS', resource: 'CDR_Victim.csv', result: 'SUCCESS', ip: '10.0.0.4' },
  { id: 'al-7', timestamp: '2026-05-09T02:16:00Z', user: 'SYSTEM', role: '-', action: 'PIPELINE_COMPLETE', resource: 'Pipeline pr-001', result: 'SUCCESS', ip: 'internal' },
  { id: 'al-8', timestamp: '2026-05-09T02:18:00Z', user: 'Arjun Sharma', role: 'INVESTIGATOR', action: 'REPORT_DOWNLOAD', resource: 'Report AIV-2026-0047', result: 'SUCCESS', ip: '10.0.0.4' },
];

export const MOCK_EVIDENCE_FILES = [
  { file_id: 'f-1', original_name: 'PME_Kumar.pdf', doc_type: 'AUTOPSY_REPORT', size_bytes: 2457600, status: 'PROCESSED', uploaded_at: '2026-05-09T02:14:00Z', checksum: 'a3f8c2...d41e' },
  { file_id: 'f-2', original_name: 'CDR_Victim.csv', doc_type: 'CDR', size_bytes: 184320, status: 'PROCESSED', uploaded_at: '2026-05-09T02:14:02Z', checksum: 'b7d9e1...f2a3' },
  { file_id: 'f-3', original_name: 'HDFC_Statement.csv', doc_type: 'FINANCIAL_RECORDS', size_bytes: 92160, status: 'PROCESSED', uploaded_at: '2026-05-09T02:14:04Z', checksum: 'c4e6f8...a1b2' },
  { file_id: 'f-4', original_name: 'WhatsApp_Export.txt', doc_type: 'DEVICE_DATA', size_bytes: 340000, status: 'PROCESSED', uploaded_at: '2026-05-09T02:14:06Z', checksum: 'd1a2b3...c4d5' },
  { file_id: 'f-5', original_name: 'Scene_Report.pdf', doc_type: 'WITNESS_STATEMENT', size_bytes: 512000, status: 'PROCESSED', uploaded_at: '2026-05-09T02:14:08Z', checksum: 'e5f6a7...b8c9' },
  { file_id: 'f-6', original_name: 'Google_Timeline.json', doc_type: 'DEVICE_DATA', size_bytes: 1024000, status: 'PROCESSED', uploaded_at: '2026-05-09T02:14:10Z', checksum: 'f9a0b1...d2e3' },
];

export const MOCK_REPORT = {
  executiveSummary: 'Analysis of the Arun Kumar death investigation indicates HOMICIDE as the most probable manner of death with 79% posterior probability. The Henssge-based Time of Death estimate places the event at approximately 03:30 AM on May 7, 2026 (95% CI: 23:30 May 6 – 07:00 May 7). Key signals include: defensive wounds, signs of struggle at the scene, and communication cessation aligned with the TOD window.',
  sections: ['Case Overview', 'Autopsy & Toxicology', 'Time of Death', 'Digital Timeline', 'Hotspot Analysis', 'Hypothesis Assessment', 'Reasoning Transparency', 'Evidence Integrity', 'Warnings & Limitations'],
  chainValid: true,
  generatedAt: '2026-05-09T02:30:00Z',
};
