"""
EVIDRA — Causal Graph API.
"""
from fastapi import APIRouter, Depends
from core.database import db
from api.auth import get_current_user

router = APIRouter(prefix="/cases/{case_id}/graph", tags=["Causal Graph"])

@router.get("")
async def get_causal_graph(case_id: str, current_user: dict = Depends(get_current_user)):
    """Return nodes and edges for the Causal Graph UI."""
    claims = await db.fetch("SELECT claim_id as id, text as label, 'CLAIM' as kind, certainty as score FROM claims WHERE case_id=$1", case_id)
    relations = await db.fetch("SELECT from_claim_id as source, to_claim_id as target, relation, confidence FROM claim_relations WHERE case_id=$1", case_id)
    
    return {
        "nodes": [dict(c) for c in claims],
        "edges": [dict(r) for r in relations]
    }
