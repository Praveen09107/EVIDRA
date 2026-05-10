"""
EVIDRA — Agents Registry API.

Provides the full agent registry for the Pipeline Explorer UI,
individual agent details, and per-case agent results.
"""
from fastapi import APIRouter, Depends, HTTPException
from core.database import db
from api.auth import get_current_user

router = APIRouter(tags=["Agents"])

# ═══════════════════════════════════════════════════════════
# Static Agent Registry (mirrors the CANONICAL_01 spec)
# ═══════════════════════════════════════════════════════════

AGENT_REGISTRY = [
    {"id": "evidence_parser", "name": "Evidence Parser", "tier": 0, "category": "INGEST", "model": "Rule-based", "port": 8010},
    {"id": "ocr", "name": "OCR Engine", "tier": 0, "category": "INGEST", "model": "Tesseract 5", "port": 8011},
    {"id": "format_normalizer", "name": "Format Normalizer", "tier": 1, "category": "INGEST", "model": "Rule-based", "port": 8012},
    {"id": "autopsy_agent", "name": "Autopsy Agent", "tier": 2, "category": "NLP", "model": "Gemini 2.0 Flash", "port": 8020},
    {"id": "cdr_analyzer", "name": "CDR Analyzer", "tier": 2, "category": "TABULAR", "model": "Rule + Anomaly", "port": 8021},
    {"id": "financial_analyzer", "name": "Financial Analyzer", "tier": 2, "category": "TABULAR", "model": "Rule + Anomaly", "port": 8022},
    {"id": "image_agent", "name": "Image Agent", "tier": 2, "category": "VISION", "model": "YOLOv8n", "port": 8023},
    {"id": "tod_agent", "name": "TOD Agent", "tier": 3, "category": "HYBRID", "model": "Henssge + RF", "port": 8030},
    {"id": "timeline_anomaly", "name": "Timeline & Anomaly", "tier": 3, "category": "ML", "model": "IF + AE", "port": 8031},
    {"id": "collision_agent", "name": "Collision Agent", "tier": 3, "category": "TABULAR", "model": "Spatio-temporal", "port": 8032},
    {"id": "hotspot_engine", "name": "Hotspot Engine", "tier": 4, "category": "FUSION", "model": "KDE + DBSCAN", "port": 8040},
    {"id": "claim_extractor", "name": "Claim Extractor", "tier": 4, "category": "NLP", "model": "Gemini 2.0 Flash", "port": 8041},
    {"id": "evidence_claim_mapper", "name": "Evidence-Claim Mapper", "tier": 5, "category": "NLP", "model": "NLI Pipeline", "port": 8050},
    {"id": "hypothesis_manager", "name": "Hypothesis Manager", "tier": 5, "category": "REASONING", "model": "Bayesian Engine", "port": 8051},
    {"id": "bias_uncertainty", "name": "Bias & Uncertainty", "tier": 5, "category": "XAI", "model": "SHAP + Monitor", "port": 8052},
    {"id": "nbe_agent", "name": "Next-Best-Evidence", "tier": 6, "category": "GUIDANCE", "model": "Gemini 2.0 Flash", "port": 8060},
    {"id": "reasoning_replay", "name": "Reasoning Replay", "tier": 7, "category": "AUDIT", "model": "Chain Builder", "port": 8061},
]


@router.get("/agents")
async def get_agents():
    """Return the full 17-agent registry for the Pipeline Explorer UI."""
    return AGENT_REGISTRY


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Return details for a specific agent."""
    agent = next((a for a in AGENT_REGISTRY if a["id"] == agent_id), None)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("/agents/{agent_id}/test-run")
async def test_agent(agent_id: str, current_user: dict = Depends(get_current_user)):
    """Mock test-run for an agent (demo purposes)."""
    agent = next((a for a in AGENT_REGISTRY if a["id"] == agent_id), None)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"output_summary": f"Test run for {agent['name']} completed", "status": "DONE", "duration_ms": 1500}


# ═══════════════════════════════════════════════════════════
# Per-case agent results
# ═══════════════════════════════════════════════════════════

@router.get("/cases/{case_id}/agents/results")
async def get_agent_results(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get raw JSON results from every completed agent for this case."""
    rows = await db.fetch(
        "SELECT agent_id, result_data, confidence, warnings, created_at FROM agent_results WHERE case_id=$1 ORDER BY created_at DESC",
        case_id
    )
    return {"results": [dict(r) for r in rows]}
