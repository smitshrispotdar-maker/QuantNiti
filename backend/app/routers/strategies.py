from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Strategy, Conversation
from ..schemas import StrategyIn, StrategySpec, ChatIn
from ..services import nlp
router = APIRouter(prefix="/api/strategies", tags=["strategies"])
@router.get("")
def list_(db: Session = Depends(get_db)):
    return [{"id": s.id, "name": s.name, "version": s.version, "spec": s.spec} for s in db.query(Strategy).order_by(Strategy.id.desc())]
@router.post("")
def save(body: StrategyIn, db: Session = Depends(get_db)):
    """Create a strategy, or a new VERSION when a strategy with the same name exists."""
    prev = db.query(Strategy).filter(Strategy.name == body.spec.name).order_by(Strategy.version.desc()).first()
    s = Strategy(user_id=1, name=body.spec.name, version=(prev.version + 1 if prev else 1), spec=body.spec.model_dump())
    db.add(s); db.commit(); db.refresh(s)
    return {"id": s.id, "version": s.version, "spec": s.spec}
@router.get("/{sid}")
def get(sid: int, db: Session = Depends(get_db)):
    s = db.get(Strategy, sid)
    if not s: raise HTTPException(404, "Strategy not found")
    return {"id": s.id, "version": s.version, "spec": s.spec}
@router.get("/chat/{cid}")
def history(cid: int, db: Session = Depends(get_db)):
    c = db.get(Conversation, cid)
    if not c: raise HTTPException(404, "Conversation not found")
    return {"id": c.id, "messages": c.messages, "draft_spec": c.draft_spec}
@router.post("/chat")
def chat(body: ChatIn, db: Session = Depends(get_db)):
    c = db.get(Conversation, body.conversation_id) if body.conversation_id else None
    if not c: c = Conversation(user_id=1, messages=[]); db.add(c)
    base = StrategySpec(**c.draft_spec) if c.draft_spec else None
    spec, ask = nlp.parse(body.message, base)
    reply = "Updated the draft strategy." + ("" if not ask else " I need a few details:")
    c.messages = c.messages + [{"role": "user", "text": body.message}, {"role": "assistant", "text": reply, "clarifications": ask}]
    c.draft_spec = spec.model_dump(); db.commit(); db.refresh(c)
    return {"conversation_id": c.id, "messages": c.messages, "draft_spec": c.draft_spec, "clarifications": ask}
