"""Paper engine. NO broker integration exists anywhere; fills are simulated at the latest bar close."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import PaperAccount, PaperOrder, Strategy, BacktestRun
from ..schemas import AccountIn, OrderIn, DeployIn, StrategySpec
from ..services import market, backtest, validation
router = APIRouter(prefix="/api/paper", tags=["paper"])
def _acct(db, aid):
    a = db.get(PaperAccount, aid)
    if not a: raise HTTPException(404, "Account not found")
    return a
def _state(db, a):
    pos = {}
    for o in db.query(PaperOrder).filter_by(account_id=a.id).order_by(PaperOrder.id):
        p = pos.setdefault(o.symbol, {"qty": 0.0, "cost": 0.0, "realized": 0.0}); sgn = 1 if o.side == "BUY" else -1
        if sgn > 0: p["cost"] += o.qty * o.fill_price; p["qty"] += o.qty
        else:
            avg = p["cost"] / p["qty"] if p["qty"] else o.fill_price
            p["realized"] += o.qty * (o.fill_price - avg); p["cost"] -= avg * o.qty; p["qty"] -= o.qty
    out, eq = [], a.cash
    for sym, p in pos.items():
        if p["qty"] < 1e-9 and not p["realized"]: continue
        px = market.get_bars(sym, "1d", 60)[0].close.iloc[-1] if p["qty"] > 1e-9 else 0
        avg = p["cost"] / p["qty"] if p["qty"] > 1e-9 else 0; eq += p["qty"] * px
        out.append({"symbol": sym, "qty": round(p["qty"], 6), "avg_price": round(avg, 2), "last": round(px, 2), "unrealized": round(p["qty"] * (px - avg), 2), "realized": round(p["realized"], 2)})
    return {"id": a.id, "name": a.name, "status": a.status, "cash": round(a.cash, 2), "equity": round(eq, 2), "starting_cash": a.starting_cash,
            "pnl": round(eq - a.starting_cash, 2), "positions": out, "strategy_id": a.strategy_id, "label": "PAPER/SIMULATED"}
def _fill(db, a, symbol, side, qty, reason):
    if a.status != "RUNNING": raise HTTPException(409, f"Account is {a.status}; orders blocked.")
    px = float(market.get_bars(symbol, "1d", 60)[0].close.iloc[-1]); cost = qty * px
    if side == "BUY" and cost > a.cash: raise HTTPException(422, "Insufficient simulated cash.")
    held = sum((o.qty if o.side == "BUY" else -o.qty) for o in db.query(PaperOrder).filter_by(account_id=a.id, symbol=symbol))
    if side == "SELL" and qty > held + 1e-9: raise HTTPException(422, "Cannot sell more than held (no shorting in MVP).")
    a.cash += -cost if side == "BUY" else cost
    o = PaperOrder(account_id=a.id, symbol=symbol, side=side, qty=qty, fill_price=px, reason=reason); db.add(o); db.commit(); return o
@router.get("/accounts")
def accounts(db: Session = Depends(get_db)): return [_state(db, a) for a in db.query(PaperAccount).order_by(PaperAccount.id)]
@router.post("/accounts")
def create(body: AccountIn, db: Session = Depends(get_db)):
    a = PaperAccount(name=body.name, starting_cash=body.starting_cash, cash=body.starting_cash); db.add(a); db.commit(); db.refresh(a); return _state(db, a)
@router.get("/accounts/{aid}")
def get(aid: int, db: Session = Depends(get_db)):
    a = _acct(db, aid); s = _state(db, a)
    s["orders"] = [{"id": o.id, "symbol": o.symbol, "side": o.side, "qty": o.qty, "fill_price": o.fill_price, "reason": o.reason, "ts": o.ts.isoformat(), "label": o.label}
                   for o in db.query(PaperOrder).filter_by(account_id=aid).order_by(PaperOrder.id.desc()).limit(50)]
    return s
@router.post("/accounts/{aid}/orders")
def order(aid: int, body: OrderIn, db: Session = Depends(get_db)):
    o = _fill(db, _acct(db, aid), body.symbol.upper(), body.side, body.qty, "manual"); return {"order_id": o.id, "fill_price": o.fill_price, "label": o.label}
@router.post("/accounts/{aid}/control/{action}")
def control(aid: int, action: str, db: Session = Depends(get_db)):
    a = _acct(db, aid); m = {"pause": "PAUSED", "resume": "RUNNING", "stop": "STOPPED", "kill": "KILLED"}
    if action not in m: raise HTTPException(400, "Unknown action")
    if a.status == "KILLED" and action != "kill": raise HTTPException(409, "Kill switch engaged; create a new account.")
    a.status = m[action]; db.commit(); return _state(db, a)
@router.post("/accounts/{aid}/deploy")
def deploy(aid: int, body: DeployIn, db: Session = Depends(get_db)):
    """Gate: strategy must have a latest backtest that passes validation."""
    a = _acct(db, aid); s = db.get(Strategy, body.strategy_id)
    if not s: raise HTTPException(404, "Strategy not found")
    run = db.query(BacktestRun).filter_by(strategy_id=s.id, strategy_version=s.version).order_by(BacktestRun.id.desc()).first()
    gate = validation.validate(StrategySpec(**s.spec), run.metrics if run else None)
    if not gate["passed"]: raise HTTPException(422, {"validation": gate})
    a.strategy_id = s.id; db.commit(); return _state(db, a)
@router.post("/accounts/{aid}/step")
def step(aid: int, db: Session = Depends(get_db)):
    """Evaluate the deployed strategy on the latest closed bar and place a simulated order if the signal fires."""
    a = _acct(db, aid)
    if not a.strategy_id: raise HTTPException(409, "No strategy deployed.")
    spec = StrategySpec(**db.get(Strategy, a.strategy_id).spec); sym = spec.instruments[0]
    df, _ = market.get_bars(sym, spec.timeframe, 300); e, x = backtest.signals(backtest.compute(df, spec.indicators), spec)
    held = sum((o.qty if o.side == "BUY" else -o.qty) for o in db.query(PaperOrder).filter_by(account_id=a.id, symbol=sym))
    if e.iloc[-1] and held < 1e-9:
        _fill(db, a, sym, "BUY", round(a.cash * spec.risk.max_position_pct / 100 / float(df.close.iloc[-1]), 6), "strategy_entry"); return {"action": "BUY"}
    if x.iloc[-1] and held > 1e-9:
        _fill(db, a, sym, "SELL", held, "strategy_exit"); return {"action": "SELL"}
    return {"action": "HOLD"}
