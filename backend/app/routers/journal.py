from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import JournalEntry, Strategy
from ..schemas import JournalIn, ReviewIn
router = APIRouter(prefix="/api/journal", tags=["journal"])
def _o(j): return {"id": j.id, "strategy_id": j.strategy_id, "strategy_version": j.strategy_version, "recommendation": j.recommendation, "evidence": j.evidence, "outcome_review": j.outcome_review, "created_at": j.created_at.isoformat()}
@router.get("")
def list_(db: Session = Depends(get_db)): return [_o(j) for j in db.query(JournalEntry).order_by(JournalEntry.id.desc())]
@router.post("")
def add(body: JournalIn, db: Session = Depends(get_db)):
    s = db.get(Strategy, body.strategy_id) if body.strategy_id else None
    j = JournalEntry(strategy_id=body.strategy_id, strategy_version=s.version if s else None, recommendation=body.recommendation, evidence=body.evidence); db.add(j); db.commit(); db.refresh(j); return _o(j)
@router.post("/{jid}/review")
def review(jid: int, body: ReviewIn, db: Session = Depends(get_db)):
    j = db.get(JournalEntry, jid)
    if not j: raise HTTPException(404, "Entry not found")
    j.outcome_review = body.outcome_review; db.commit(); return _o(j)
