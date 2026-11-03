from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..db import get_db
from ..services import lineage
from ..services.auth import get_current_user_dep
from ..models import User
from typing import Optional

router = APIRouter(prefix="/api/lineage", tags=["lineage"])


@router.get("")
def get_lineage(
    db: Session = Depends(get_db),
    strategy_id: Optional[int] = Query(None),
    conversation_id: Optional[int] = None,
    current_user: User = Depends(get_current_user_dep),
):
    """Get the full lineage timeline for a strategy or conversation."""
    try:
        events = lineage.build_lineage(db, strategy_id=strategy_id, conversation_id=conversation_id, user_id=current_user.id)
        return {"events": events, "count": len(events)}
    except Exception as e:
        raise HTTPException(500, f"Error building lineage: {str(e)}")


@router.get("/entity/{entity_type}/{entity_id}")
def get_entity_lineage(
    entity_type: str,
    entity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dep),
):
    """Get lineage for a specific entity (strategy, conversation, backtest, deployment, journal, research)."""
    valid_types = ["strategy", "conversation", "backtest", "deployment", "journal", "research"]
    if entity_type not in valid_types:
        raise HTTPException(400, f"Invalid entity type. Must be one of: {', '.join(valid_types)}")
    
    try:
        events = lineage.get_entity_lineage(db, entity_type, entity_id, user_id=current_user.id)
        return {"events": events, "count": len(events)}
    except Exception as e:
        raise HTTPException(500, f"Error building lineage: {str(e)}")