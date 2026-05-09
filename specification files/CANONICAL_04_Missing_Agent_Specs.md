# CANONICAL SPEC 04 — Missing Agent Specifications
**Status:** FINAL | Covers GAP-05 (Image Agent), IMP-02 (Gap Auditor), IMP-03 (Argument Graph Builder)

---

# AGENT M-07: Image Agent (CCTV / Scene Analysis)

## 1. Purpose
The Image Agent processes visual evidence (CCTV footage, scene photographs, device media) through object detection and tracking pipelines to produce structured entity tracks and key events that feed into the Collision Agent and Timeline.

## 2. Input Contract
```python
class ImageAgentRequest(BaseModel):
    case_id: UUID
    pipeline_run_id: UUID
    files: List[ImageFile]

class ImageFile(BaseModel):
    file_id: UUID
    s3_key: str
    media_type: str  # "VIDEO" | "IMAGE"
    source: str      # "CCTV" | "SCENE_PHOTO" | "DEVICE_MEDIA"
    metadata: Dict   # camera_id, timestamp_start, timestamp_end, location
```

## 3. Output Contract
```python
class ImageAgentResult(BaseModel):
    case_id: UUID
    detections: List[Detection]
    tracks: List[EntityTrack]
    key_events: List[KeyEvent]
    frame_count_processed: int
    processing_time_ms: int

class Detection(BaseModel):
    frame_timestamp: datetime
    class_name: str           # "person", "vehicle", "weapon", "phone"
    confidence: float
    bbox: List[float]         # [x1, y1, x2, y2] normalized
    camera_id: str

class EntityTrack(BaseModel):
    track_id: str
    entity_kind: str          # "PERSON" | "VEHICLE" | "OBJECT"
    entity_label: str         # "Person-A", "Vehicle-1"
    segments: List[TrackSegment]
    first_seen: datetime
    last_seen: datetime
    confidence: float

class TrackSegment(BaseModel):
    start_time: datetime
    end_time: datetime
    camera_id: str
    location: Optional[str]

class KeyEvent(BaseModel):
    id: UUID
    timestamp: datetime
    type: str      # "PERSON_ENTER", "PERSON_EXIT", "CO_PRESENCE", "UNUSUAL_LINGER"
    severity: str  # "INFO" | "INTERESTING" | "CRITICAL"
    description: str
    attributes: Dict
```

## 4. Model Configuration
```yaml
# Primary: YOLOv8n (nano) for hackathon speed
model: yolov8n.pt
confidence_threshold: 0.5
iou_threshold: 0.45
max_detections_per_frame: 50

# Frame sampling
video_fps_sample: 2              # process 2 frames/sec (not every frame)
motion_threshold: 0.02           # skip near-static frames
keyframe_only_for_long_videos: true  # >30min → keyframes only

# Tracking
tracker: ByteTrack
max_track_age: 30                # frames before track is lost
min_track_length: 5              # minimum detections to form track
```

## 5. Docker Service (additions to docker-compose.yml)
```yaml
image_agent:
  image: aiventra/image:latest
  restart: always
  environment:
    <<: *common-env
    AGENT_ID: image_agent
    YOLO_MODEL_PATH: /models/yolov8n.pt
    YOLO_CONFIDENCE: "0.5"
  volumes:
    - ./models:/models:ro
  depends_on: [postgres, redis, minio]
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 4G
```

---

# AGENT: Gap & Logic Auditor

## 1. Purpose
Scans the argument graph for structural weaknesses: hypotheses with no supporting evidence, claims with no evidence links, contradictions between evidence items, and circular reasoning patterns.

## 2. Input
- Complete causal graph (nodes + edges)
- Claim verdicts (from Verdict Aggregation)
- Hypothesis probabilities
- Evidence inventory (what files were uploaded vs what was analyzed)

## 3. Output
```python
class GapAuditResult(BaseModel):
    case_id: UUID
    findings: List[GapFinding]
    coverage_stats: CoverageStats

class GapFinding(BaseModel):
    id: UUID
    type: str  # "MISSING_EVIDENCE" | "UNCHECKED_HYPOTHESIS" | "WEAK_SUPPORT"
               # | "CONTRADICTION_UNRESOLVED" | "CIRCULAR_REASONING" | "ORPHAN_CLAIM"
    description: str
    target: str           # "HYPOTHESIS" | "CLAIM" | "TIME_WINDOW" | "LOCATION" | "ENTITY"
    target_ref_id: UUID
    severity: str         # "INFO" | "WARN" | "CRITICAL"
    recommended_action: str

class CoverageStats(BaseModel):
    total_claims: int
    claims_with_evidence: int
    claims_without_evidence: int
    hypotheses_with_strong_support: int  # ≥2 strong support paths
    hypotheses_with_weak_support: int    # <2 support paths
    contradiction_count: int
    evidence_utilization_pct: float      # % of uploaded files referenced in graph
```

## 4. Logic
```python
async def run_gap_audit(case_id, graph, verdicts, hypotheses, inventory):
    findings = []
    
    # 1. Find orphan claims (no evidence links)
    for claim in graph.claims:
        links = [e for e in graph.edges if e.target == claim.id]
        if not links:
            findings.append(GapFinding(
                type="ORPHAN_CLAIM",
                description=f"Claim '{claim.label[:80]}' has no supporting or refuting evidence",
                severity="WARN"
            ))
    
    # 2. Find weakly supported hypotheses
    for hyp in hypotheses:
        support_paths = count_support_paths(graph, hyp.id)
        if support_paths < 2 and hyp.probability > 0.30:
            findings.append(GapFinding(
                type="WEAK_SUPPORT",
                description=f"Hypothesis '{hyp.key}' at {hyp.probability:.0%} confidence relies on <2 evidence paths",
                severity="CRITICAL"
            ))
    
    # 3. Find unresolved contradictions
    for verdict in verdicts:
        if verdict.verdict == "CONFLICTING":
            findings.append(GapFinding(
                type="CONTRADICTION_UNRESOLVED",
                description=f"Claim '{verdict.claim_text[:80]}' has conflicting evidence",
                severity="HIGH"
            ))
    
    # 4. Find unused evidence
    used_files = extract_referenced_files(graph)
    for file in inventory:
        if file.id not in used_files and file.status == "PROCESSED":
            findings.append(GapFinding(
                type="MISSING_EVIDENCE",
                description=f"File '{file.original_name}' was processed but not referenced in any claim",
                severity="WARN"
            ))
    
    return GapAuditResult(findings=findings, coverage_stats=compute_stats(...))
```

---

# AGENT: Argument Graph Builder

## 1. Purpose
Assembles the causal/argument graph that connects hypotheses → claims → evidence into a navigable structure for the UI and downstream reasoning.

## 2. Input
- Claims (from Claim Extractor)
- Evidence-Claim Links (from Mapper)
- Hypothesis scores (from Hypothesis Manager)
- Hotspots (from Hotspot Engine)

## 3. Output: CausalGraph
```python
class CausalGraph(BaseModel):
    case_id: UUID
    nodes: List[GraphNode]
    edges: List[GraphEdge]

class GraphNode(BaseModel):
    id: UUID
    kind: str         # "HYPOTHESIS" | "CLAIM" | "EVIDENCE"
    label: str
    probability: float | None  # for HYPOTHESIS nodes
    importance: float          # centrality score 0-1
    metadata: Dict

class GraphEdge(BaseModel):
    id: UUID
    source: UUID      # from node
    target: UUID      # to node
    relation: str     # "SUPPORTS" | "CONTRADICTS" | "NEUTRAL"
    strength: float   # 0-1
```

## 4. Graph Construction Algorithm
```python
async def build_graph(claims, ec_links, hypotheses, hotspots):
    graph = CausalGraph(nodes=[], edges=[])
    
    # 1. Create HYPOTHESIS nodes
    for hyp in hypotheses:
        graph.nodes.append(GraphNode(
            kind="HYPOTHESIS", label=hyp.key, probability=hyp.probability
        ))
    
    # 2. Create CLAIM nodes
    for claim in claims:
        graph.nodes.append(GraphNode(
            kind="CLAIM", label=claim.normalized_text[:120]
        ))
    
    # 3. Create EVIDENCE nodes from unique evidence referenced in links
    evidence_ids = {link.evidence_id for link in ec_links}
    for eid in evidence_ids:
        graph.nodes.append(GraphNode(kind="EVIDENCE", label=get_evidence_label(eid)))
    
    # 4. Create EVIDENCE → CLAIM edges from links
    for link in ec_links:
        relation = "SUPPORTS" if link.label in ("SUPPORTS","PARTIAL_SUPPORT") else \
                   "CONTRADICTS" if link.label in ("REFUTES","PARTIAL_REFUTE") else "NEUTRAL"
        graph.edges.append(GraphEdge(
            source=link.evidence_id, target=link.claim_id,
            relation=relation, strength=link.confidence
        ))
    
    # 5. Create CLAIM → HYPOTHESIS edges (via hypothesis manager scoring)
    for hyp_node in [n for n in graph.nodes if n.kind == "HYPOTHESIS"]:
        related_claims = get_claims_for_hypothesis(hyp_node.label, claims, ec_links)
        for claim_id, strength, direction in related_claims:
            graph.edges.append(GraphEdge(
                source=claim_id, target=hyp_node.id,
                relation=direction, strength=strength
            ))
    
    # 6. Compute importance (betweenness centrality)
    for node in graph.nodes:
        node.importance = compute_centrality(graph, node.id)
    
    return graph
```

---

# LLM Gateway Service (GAP-03 Resolution)

## Canonical Configuration
```python
class LLMGateway:
    """All agents call this. Never call LLM APIs directly."""
    
    TASK_MODEL_MAP = {
        "autopsy_extract":      {"model": "gemini-2.0-flash", "temp": 0.1, "max_tokens": 4000},
        "claim_extract":        {"model": "gemini-2.0-flash", "temp": 0.1, "max_tokens": 3000},
        "nli_classify":         {"model": "gemini-2.0-flash", "temp": 0.0, "max_tokens": 500},
        "hypothesis_reason":    {"model": "gemini-2.0-flash", "temp": 0.2, "max_tokens": 2000},
        "narrative_generate":   {"model": "gemini-2.0-flash", "temp": 0.3, "max_tokens": 1500},
        "hotspot_explain":      {"model": "gemini-2.0-flash", "temp": 0.2, "max_tokens": 800},
        "bias_assess":          {"model": "gemini-2.0-flash", "temp": 0.1, "max_tokens": 1000},
        "replay_narrative":     {"model": "gemini-2.0-flash", "temp": 0.3, "max_tokens": 800},
    }
    
    RATE_LIMITS = {
        "max_requests_per_minute": 60,
        "max_tokens_per_pipeline_run": 100_000,
        "max_tokens_per_agent_call": 8_000,
    }
    
    FALLBACK_CHAIN = ["gemini-2.0-flash", "deepseek-chat", "gpt-4o-mini"]

    async def complete(self, task: str, prompt: str, **overrides) -> LLMResponse:
        config = {**self.TASK_MODEL_MAP[task], **overrides}
        for model in self._get_model_chain(config["model"]):
            try:
                return await self._call_provider(model, prompt, config)
            except RateLimitError:
                continue
            except ProviderError:
                continue
        raise AllProvidersFailedError(task)
```

## Environment Variables
```bash
# Primary LLM
GEMINI_API_KEY=<key>
# Fallback LLMs (optional)
DEEPSEEK_API_KEY=<key>
OPENAI_API_KEY=<key>
# Controls
LLM_MAX_TOKENS_PER_RUN=100000
LLM_RATE_LIMIT_RPM=60
```
