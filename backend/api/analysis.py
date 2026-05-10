"""
EVIDRA — Analysis, TOD, Hypothesis & Anomalies API.

Serves all forensic intelligence results to the frontend.
"""
from fastapi import APIRouter, Depends
import json
from core.database import db
from api.auth import get_current_user

router = APIRouter(prefix="/cases/{case_id}/analysis", tags=["Analysis"])


@router.get("")
async def get_analysis_summary(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get the Bayesian hypothesis probabilities and bias flags."""
    run = await db.fetchrow("SELECT pipeline_run_id FROM pipeline_runs WHERE case_id=$1 ORDER BY created_at DESC LIMIT 1", case_id)
    if not run:
        return {"hypotheses": [], "bias_flags": []}

    run_id = run["pipeline_run_id"]

    hypotheses = await db.fetch(
        "SELECT hypothesis_key, probability, evidence_summary FROM hypothesis_history WHERE pipeline_run_id=$1 ORDER BY probability DESC",
        run_id
    )

    reports = await db.fetchrow(
        "SELECT bias_flags, overall_score FROM uncertainty_reports WHERE pipeline_run_id=$1",
        run_id
    )

    return {
        "pipeline_run_id": str(run_id),
        "hypotheses": [dict(h) for h in hypotheses],
        "bias": dict(reports) if reports else {"bias_flags": [], "overall_score": 0}
    }


@router.get("/tod")
async def get_tod_result(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get the Time of Death estimation result."""
    run = await db.fetchrow("SELECT pipeline_run_id FROM pipeline_runs WHERE case_id=$1 ORDER BY created_at DESC LIMIT 1", case_id)
    if not run:
        return {"error": "No pipeline run found"}

    result = await db.fetchrow(
        "SELECT result_data FROM agent_results WHERE case_id=$1 AND agent_id='tod_agent' ORDER BY created_at DESC LIMIT 1",
        case_id
    )
    if not result or not result["result_data"]:
        return {"error": "No TOD result available"}

    data = result["result_data"]
    if isinstance(data, str):
        data = json.loads(data)
    return data


@router.get("/hypothesis")
async def get_hypothesis(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get hypothesis posterior probabilities and evidence signals."""
    run = await db.fetchrow("SELECT pipeline_run_id FROM pipeline_runs WHERE case_id=$1 ORDER BY created_at DESC LIMIT 1", case_id)
    if not run:
        return {"posteriors": {}, "signals": [], "topHypothesis": "UNDETERMINED", "topConfidence": 0}

    run_id = run["pipeline_run_id"]

    hypotheses = await db.fetch(
        "SELECT hypothesis_key, probability, evidence_summary FROM hypothesis_history WHERE pipeline_run_id=$1 ORDER BY probability DESC",
        run_id
    )

    posteriors = {}
    for h in hypotheses:
        posteriors[h["hypothesis_key"]] = float(h["probability"])

    top = hypotheses[0] if hypotheses else None

    # Get the hypothesis manager's full result for signals
    agent_result = await db.fetchrow(
        "SELECT result_data FROM agent_results WHERE case_id=$1 AND agent_id='hypothesis_manager' ORDER BY created_at DESC LIMIT 1",
        case_id
    )

    signals = []
    if agent_result and agent_result["result_data"]:
        data = agent_result["result_data"]
        if isinstance(data, str):
            data = json.loads(data)
        signals = data.get("signals", [])

    return {
        "posteriors": posteriors,
        "topHypothesis": top["hypothesis_key"] if top else "UNDETERMINED",
        "topConfidence": float(top["probability"]) if top else 0,
        "signals": signals
    }


@router.get("/anomalies")
async def get_anomalies(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get anomaly detection results from the timeline anomaly agent."""
    rows = await db.fetch(
        "SELECT * FROM anomaly_windows WHERE case_id=$1 ORDER BY severity_score DESC",
        case_id
    )

    anomalies = []
    for r in rows:
        anomalies.append({
            "id": str(r["anomaly_id"]),
            "score": float(r["severity_score"]) if r["severity_score"] else 0,
            "severity": r["severity"] if "severity" in r.keys() else ("CRITICAL" if float(r.get("severity_score", 0)) > 0.8 else "HIGH" if float(r.get("severity_score", 0)) > 0.5 else "MEDIUM"),
            "title": r.get("label", "Anomaly Detected"),
            "detail": r.get("description", ""),
            "sources": r.get("sources", []),
            "rule": r.get("rule", ""),
            "inTodWindow": r.get("in_tod_window", False),
            "time_start": str(r["time_start"]) if "time_start" in r.keys() else None,
            "time_end": str(r["time_end"]) if "time_end" in r.keys() else None,
        })

    return anomalies
