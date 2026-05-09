"""
EVIDRA — Analysis & Hypothesis API.
"""
from fastapi import APIRouter, Depends
from core.database import db
from api.auth import get_current_user

router = APIRouter(prefix="/cases/{case_id}/analysis", tags=["Analysis"])

@router.get("")
async def get_analysis_summary(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get the Bayesian hypothesis probabilities and bias flags."""
    # Get latest pipeline run
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
