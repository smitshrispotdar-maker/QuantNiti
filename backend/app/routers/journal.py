from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from ..db import get_db
from ..models import JournalEntry, Strategy, Conversation, BacktestRun, PaperDeployment, ResearchRun
from ..schemas import (
    JournalIn, ReviewIn, JournalEntryCreate, JournalEntryUpdate,
    JournalEntryResponse, JournalEntryListResponse
)
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api/journal", tags=["journal"])


def _to_response(j: JournalEntry) -> JournalEntryResponse:
    return JournalEntryResponse(
        id=j.id,
        user_id=j.user_id,
        title=j.title,
        decision_type=j.decision_type,
        status=j.status,
        strategy_id=j.strategy_id,
        strategy_version=j.strategy_version,
        conversation_id=j.conversation_id,
        backtest_run_id=j.backtest_run_id,
        research_run_id=j.research_run_id,
        deployment_id=j.deployment_id,
        hypothesis_rationale=j.hypothesis_rationale,
        evidence_summary=j.evidence_summary,
        risks_assumptions=j.risks_assumptions,
        decision_next_steps=j.decision_next_steps,
        expected_outcome=j.expected_outcome,
        actual_outcome=j.actual_outcome,
        recommendation=j.recommendation,
        evidence=j.evidence,
        outcome_review=j.outcome_review,
        created_at=j.created_at,
        updated_at=j.updated_at,
    )


@router.get("")
def list_entries(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    strategy_id: Optional[int] = None,
    status: Optional[str] = None,
    decision_type: Optional[str] = None,
    conversation_id: Optional[int] = None,
    backtest_run_id: Optional[int] = None,
    research_run_id: Optional[int] = None,
    deployment_id: Optional[int] = None,
    user_id: int = 1,  # TODO: replace with actual auth
):
    """List journal entries with pagination and filtering."""
    query = db.query(JournalEntry).filter(JournalEntry.user_id == user_id)
    
    if strategy_id:
        query = query.filter(JournalEntry.strategy_id == strategy_id)
    if status:
        query = query.filter(JournalEntry.status == status)
    if decision_type:
        query = query.filter(JournalEntry.decision_type == decision_type)
    if conversation_id:
        query = query.filter(JournalEntry.conversation_id == conversation_id)
    if backtest_run_id:
        query = query.filter(JournalEntry.backtest_run_id == backtest_run_id)
    if research_run_id:
        query = query.filter(JournalEntry.research_run_id == research_run_id)
    if deployment_id:
        query = query.filter(JournalEntry.deployment_id == deployment_id)
    
    total = query.count()
    entries = query.order_by(JournalEntry.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    return JournalEntryListResponse(
        items=[_to_response(j) for j in entries],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("")
def create_entry(body: JournalEntryCreate, db: Session = Depends(get_db), user_id: int = 1):
    """Create a new journal entry."""
    # Validate foreign key references
    if body.strategy_id:
        strategy = db.get(Strategy, body.strategy_id)
        if not strategy:
            raise HTTPException(404, "Strategy not found")
        if strategy.user_id != 1:  # TODO: use actual user_id
            raise HTTPException(403, "Not authorized")
    
    if body.conversation_id:
        conv = db.get(Conversation, body.conversation_id)
        if not conv:
            raise HTTPException(404, "Conversation not found")
        if conv.user_id != 1:
            raise HTTPException(403, "Not authorized")
    
    if body.backtest_run_id:
        run = db.get(BacktestRun, body.backtest_run_id)
        if not run:
            raise HTTPException(404, "Backtest run not found")
    
    if body.research_run_id:
        run = db.get(ResearchRun, body.research_run_id)
        if not run:
            raise HTTPException(404, "Research run not found")
    
    if body.deployment_id:
        dep = db.get(PaperDeployment, body.deployment_id)
        if not dep:
            raise HTTPException(404, "Deployment not found")
    
    # Use title as recommendation if recommendation not provided
    recommendation = body.recommendation or body.title
    
    entry = JournalEntry(
        user_id=1,  # TODO: replace with actual auth
        title=body.title,
        decision_type=body.decision_type,
        status=body.status,
        strategy_id=body.strategy_id,
        strategy_version=body.strategy_version,
        conversation_id=body.conversation_id,
        backtest_run_id=body.backtest_run_id,
        research_run_id=body.research_run_id,
        deployment_id=body.deployment_id,
        hypothesis_rationale=body.hypothesis_rationale,
        evidence_summary=body.evidence_summary,
        risks_assumptions=body.risks_assumptions,
        decision_next_steps=body.decision_next_steps,
        expected_outcome=body.expected_outcome,
        actual_outcome=body.actual_outcome,
        recommendation=recommendation,
        evidence=body.evidence or {},
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _to_response(entry)


@router.get("/{jid}")
def get_entry(jid: int, db: Session = Depends(get_db), user_id: int = 1):
    """Get a single journal entry."""
    entry = db.get(JournalEntry, jid)
    if not entry:
        raise HTTPException(404, "Entry not found")
    if entry.user_id != user_id:
        raise HTTPException(403, "Not authorized")
    return _to_response(entry)


@router.patch("/{jid}")
def update_entry(jid: int, body: JournalEntryUpdate, db: Session = Depends(get_db), user_id: int = 1):
    """Update a journal entry."""
    entry = db.get(JournalEntry, jid)
    if not entry:
        raise HTTPException(404, "Entry not found")
    if entry.user_id != user_id:
        raise HTTPException(403, "Not authorized")
    
    # Update only provided fields
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(entry, field, value)
    
    entry.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(entry)
    return _to_response(entry)


@router.delete("/{jid}")
def delete_entry(jid: int, db: Session = Depends(get_db), user_id: int = 1):
    """Delete a journal entry."""
    entry = db.get(JournalEntry, jid)
    if not entry:
        raise HTTPException(404, "Entry not found")
    if entry.user_id != user_id:
        raise HTTPException(403, "Not authorized")
    db.delete(entry)
    db.commit()
    return {"deleted": True, "id": jid}


# Legacy endpoints for backward compatibility
@router.get("/legacy")
def list_legacy(db: Session = Depends(get_db)):
    """Legacy list endpoint - returns all entries without pagination."""
    entries = db.query(JournalEntry).order_by(JournalEntry.id.desc()).all()
    return [_legacy_to_response(j) for j in entries]


@router.post("/legacy")
def add_legacy(body: JournalIn, db: Session = Depends(get_db)):
    """Legacy create endpoint."""
    from ..schemas import JournalEntryCreate
    new_body = JournalEntryCreate(
        title=body.recommendation[:50] + "..." if len(body.recommendation) > 50 else body.recommendation,
        decision_type="general_note",
        status="draft",
        strategy_id=body.strategy_id,
        recommendation=body.recommendation,
        evidence=body.evidence,
    )
    return create_entry(new_body, db)


@router.post("/{jid}/review")
def review(jid: int, body: ReviewIn, db: Session = Depends(get_db), user_id: int = 1):
    """Add or update outcome review for a journal entry."""
    entry = db.get(JournalEntry, jid)
    if not entry:
        raise HTTPException(404, "Entry not found")
    if entry.user_id != user_id:
        raise HTTPException(403, "Not authorized")
    entry.outcome_review = body.outcome_review
    entry.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(entry)
    return _to_response(entry)


def _legacy_to_response(j: JournalEntry) -> dict:
    return {
        "id": j.id,
        "strategy_id": j.strategy_id,
        "strategy_version": j.strategy_version,
        "recommendation": j.recommendation,
        "evidence": j.evidence,
        "outcome_review": j.outcome_review,
        "created_at": j.created_at.isoformat(),
    }