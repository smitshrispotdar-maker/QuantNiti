"""Paper trading engine with simulated execution matching backtest model."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import PaperAccount, PaperOrder, PaperDeployment, PaperPosition, Strategy, BacktestRun, User
from ..schemas import AccountIn, OrderIn, DeployIn, StrategySpec
from ..services import market, backtest, validation, paper
from ..services import instruments as inst
from ..services.auth import get_current_user_dep
router = APIRouter(prefix="/api/paper", tags=["paper"])

def _resolve_symbol(symbol: str) -> str:
    resolved = inst.resolve_symbol(symbol)
    if not resolved:
        raise HTTPException(400, f"Unsupported instrument: {symbol}. QuantNiti supports NSE/BSE instruments only.")
    return resolved

def _acct(db: Session, aid: int) -> PaperAccount:
    a = db.get(PaperAccount, aid)
    if not a: raise HTTPException(404, "Account not found")
    return a

def _deployment(db: Session, did: int) -> PaperDeployment:
    d = db.get(PaperDeployment, did)
    if not d: raise HTTPException(404, "Deployment not found")
    return d

def _legacy_state(db: Session, a: PaperAccount) -> dict:
    """Legacy state computation for backwards compatibility with manual accounts."""
    pos = {}
    for o in db.query(PaperOrder).filter_by(account_id=a.id).order_by(PaperOrder.id):
        p = pos.setdefault(o.symbol, {"qty": 0.0, "cost": 0.0, "realized": 0.0,
                                      "stop_loss_price": None, "take_profit_price": None})
        sgn = 1 if o.side == "BUY" else -1
        if sgn > 0:
            p["cost"] += o.qty * o.fill_price; p["qty"] += o.qty
            p["stop_loss_price"] = getattr(o, "stop_price", None) or p["stop_loss_price"]
            p["take_profit_price"] = getattr(o, "take_profit_price", None) or p["take_profit_price"]
        else:
            avg = p["cost"] / p["qty"] if p["qty"] else o.fill_price
            p["realized"] += o.qty * (o.fill_price - avg); p["cost"] -= avg * o.qty; p["qty"] -= o.qty
    out, eq = [], a.cash
    for sym, p in pos.items():
        if p["qty"] < 1e-9 and not p["realized"]: continue
        px = market.get_bars(sym, "1d", 60)[0].close.iloc[-1] if p["qty"] > 1e-9 else 0
        avg = p["cost"] / p["qty"] if p["qty"] > 1e-9 else 0; eq += p["qty"] * px
        out.append({
            "symbol": sym, "name": inst.name_for(sym), "qty": round(p["qty"], 6),
            "avg_price": round(avg, 2), "last": round(px, 2),
            "unrealized": round(p["qty"] * (px - avg), 2), "realized": round(p["realized"], 2),
            "stop_loss_price": p["stop_loss_price"], "take_profit_price": p["take_profit_price"],
        })
    return {"id": a.id, "name": a.name, "status": a.status, "cash": round(a.cash, 2), "equity": round(eq, 2), "starting_cash": a.starting_cash,
            "pnl": round(eq - a.starting_cash, 2), "positions": out, "strategy_id": a.strategy_id, "label": "PAPER/SIMULATED"}

# Alias for backwards compatibility with tests
_state = _legacy_state

# --- Backwards compatibility functions for tests ---
def _fill(db: Session, a: PaperAccount, symbol: str, side: str, qty: float, reason: str) -> PaperOrder:
    """Legacy fill function for test compatibility."""
    if a.status != "RUNNING": raise HTTPException(409, f"Account is {a.status}; orders blocked.")
    px = float(market.get_bars(symbol, "1d", 60)[0].close.iloc[-1]); cost = qty * px
    if side == "BUY" and cost > a.cash: raise HTTPException(422, "Insufficient simulated cash.")
    held = sum((o.qty if o.side == "BUY" else -o.qty) for o in db.query(PaperOrder).filter_by(account_id=a.id, symbol=symbol))
    if side == "SELL" and qty > held + 1e-9: raise HTTPException(422, "Cannot sell more than held (no shorting in MVP).")
    a.cash += -cost if side == "BUY" else cost
    o = PaperOrder(account_id=a.id, symbol=symbol, side=side, qty=qty, fill_price=px, reason=reason); db.add(o); db.commit(); return o

@router.get("/accounts")
def accounts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user_dep)):
    """List all paper accounts with their state."""
    results = []
    for a in db.query(PaperAccount).filter_by(user_id=current_user.id).order_by(PaperAccount.id):
        if a.strategy_id:
            # Has deployment - get deployment state
            deployment = db.query(PaperDeployment).filter_by(account_id=a.id, status="ACTIVE").first()
            if deployment:
                results.append(paper.get_deployment_state(db, deployment))
            else:
                results.append(_legacy_state(db, a))
        else:
            results.append(_legacy_state(db, a))
    return results

@router.post("/accounts")
def create(body: AccountIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_dep)):
    """Create a new paper trading account."""
    a = PaperAccount(user_id=current_user.id, name=body.name, starting_cash=body.starting_cash, cash=body.starting_cash)
    db.add(a); db.commit(); db.refresh(a)
    return _legacy_state(db, a)

@router.get("/accounts/{aid}")
def get(aid: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_dep)):
    """Get account state (legacy or deployment)."""
    a = _acct(db, aid)
    if a.user_id != current_user.id:
        raise HTTPException(403, "Not authorized")
    if a.strategy_id:
        deployment = db.query(PaperDeployment).filter_by(account_id=aid, status="ACTIVE").first()
        if deployment:
            return paper.get_deployment_state(db, deployment)
    s = _legacy_state(db, a)
    s["orders"] = [{"id": o.id, "symbol": o.symbol, "side": o.side, "qty": o.qty, "fill_price": o.fill_price,
                    "reason": o.reason, "ts": o.ts.isoformat(), "label": o.label,
                    "stop_loss_price": getattr(o, "stop_price", None),
                    "take_profit_price": getattr(o, "take_profit_price", None)}
                   for o in db.query(PaperOrder).filter_by(account_id=aid).order_by(PaperOrder.id.desc()).limit(50)]
    return s

@router.post("/accounts/{aid}/orders")
def order(aid: int, body: OrderIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_dep)):
    """Place a manual order (legacy endpoint for non-deployment accounts)."""
    a = _acct(db, aid)
    if a.user_id != current_user.id:
        raise HTTPException(403, "Not authorized")
    if a.status != "RUNNING": raise HTTPException(409, f"Account is {a.status}; orders blocked.")
    symbol = _resolve_symbol(body.symbol)
    if body.stop_loss_price and body.take_profit_price and body.stop_loss_price >= body.take_profit_price:
        raise HTTPException(422, "Stop-loss must be below take-profit.")
    df, _ = market.get_bars(symbol, "1d", 60)
    if df.empty:
        raise HTTPException(503, "Market data unavailable; cannot fill a simulated order right now.")
    px = float(df.close.iloc[-1]); cost = body.qty * px
    if body.side == "BUY" and cost > a.cash: raise HTTPException(422, "Insufficient simulated cash.")
    held = sum((o.qty if o.side == "BUY" else -o.qty) for o in db.query(PaperOrder).filter_by(account_id=a.id, symbol=symbol))
    if body.side == "SELL" and body.qty > held + 1e-9: raise HTTPException(422, "Cannot sell more than held (no shorting in MVP).")
    a.cash += -cost if body.side == "BUY" else cost
    o = PaperOrder(account_id=a.id, symbol=symbol, side=body.side, qty=body.qty, fill_price=px, reason="manual",
                   stop_price=body.stop_loss_price, take_profit_price=body.take_profit_price)
    db.add(o); db.commit()
    return {"order_id": o.id, "fill_price": o.fill_price, "label": o.label,
            "symbol": symbol, "side": body.side, "qty": body.qty}

@router.post("/accounts/{aid}/control/{action}")
def control(aid: int, action: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_dep)):
    """Control account status (pause/resume/stop/kill)."""
    a = _acct(db, aid)
    if a.user_id != current_user.id:
        raise HTTPException(403, "Not authorized")
    m = {"pause": "PAUSED", "resume": "RUNNING", "stop": "STOPPED", "kill": "KILLED"}
    if action not in m: raise HTTPException(400, "Unknown action")
    if a.status == "KILLED" and action != "kill": raise HTTPException(409, "Kill switch engaged; create a new account.")
    a.status = m[action]; db.commit()
    return _legacy_state(db, a)

# --- Legacy API for backwards compatibility ---

@router.post("/accounts/{aid}/deploy")
def deploy(aid: int, body: DeployIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_dep)):
    """Legacy deploy endpoint - creates deployment and returns account state."""
    # This maintains the old API: deploy to account, not deployment ID
    a = _acct(db, aid)
    if a.user_id != current_user.id:
        raise HTTPException(403, "Not authorized")
    result = create_deployment(aid, body, db)
    # Return legacy state for backwards compatibility
    return _legacy_state(db, a)

@router.post("/accounts/{aid}/step")
def step(aid: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_dep)):
    """Legacy step endpoint - evaluates strategy on account's deployed strategy."""
    a = _acct(db, aid)
    if a.user_id != current_user.id:
        raise HTTPException(403, "Not authorized")
    if not a.strategy_id:
        raise HTTPException(409, "No strategy deployed.")
    
    # Find active deployment for this account
    deployment = db.query(PaperDeployment).filter_by(account_id=aid, status="ACTIVE").first()
    if not deployment:
        raise HTTPException(409, "No active deployment found.")
    
    try:
        result = paper.evaluate_strategy_step(db, deployment, force=False)
        return result
    except paper.PaperExecutionError as e:
        raise HTTPException(422 if e.code != "DEPLOYMENT_NOT_ACTIVE" and e.code != "ACCOUNT_NOT_RUNNING" else 409,
                           {"error": e.code, "message": e.message})

# --- Deployment Endpoints ---

@router.post("/accounts/{aid}/deployments")
def create_deployment(aid: int, body: DeployIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_dep)):
    """
    Create a new paper trading deployment from a validated strategy.
    
    Requirements:
    - Strategy must exist
    - Strategy must have a passing backtest (same version)
    - Account must be RUNNING
    - Account must not have an active deployment
    """
    a = _acct(db, aid)
    if a.user_id != current_user.id:
        raise HTTPException(403, "Not authorized")
    if a.status != "RUNNING":
        raise HTTPException(409, f"Account is {a.status}; cannot deploy.")
    
    # Check for existing active deployment
    existing = db.query(PaperDeployment).filter_by(account_id=aid, status="ACTIVE").first()
    if existing:
        raise HTTPException(409, "Account already has an active deployment. Close it first.")
    
    s = db.get(Strategy, body.strategy_id)
    if not s:
        raise HTTPException(404, "Strategy not found")
    
    # Get latest backtest for this strategy version
    run = db.query(BacktestRun).filter_by(strategy_id=s.id, strategy_version=s.version).order_by(BacktestRun.id.desc()).first()
    if not run:
        raise HTTPException(422, {"validation": {"passed": False, "errors": ["No backtest found for this strategy version"], "warnings": []}})
    
    # Validate strategy with backtest metrics
    gate = validation.validate(StrategySpec(**s.spec), run.metrics)
    if not gate["passed"]:
        raise HTTPException(422, {"validation": gate})
    
    # Create deployment with immutable snapshot
    deployment = PaperDeployment(
        account_id=a.id,
        strategy_id=s.id,
        strategy_version=s.version,
        strategy_spec=s.spec,
        initial_cash=a.cash,  # Use current account cash as starting capital
        transaction_cost_bps=run.transaction_cost_bps,
        slippage_bps=run.slippage_bps,
        max_position_pct=StrategySpec(**s.spec).risk.max_position_pct,
        stop_loss_pct=StrategySpec(**s.spec).risk.stop_loss_pct,
        take_profit_pct=StrategySpec(**s.spec).risk.take_profit_pct,
        max_drawdown_pct=StrategySpec(**s.spec).risk.max_drawdown_pct,
        data_source=run.data_source,
        status="ACTIVE",
    )
    db.add(deployment)
    db.commit()
    db.refresh(deployment)
    
    # Update account strategy_id for legacy compatibility
    a.strategy_id = s.id
    db.commit()
    
    return paper.get_deployment_state(db, deployment)

@router.get("/deployments/{did}")
def get_deployment(did: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_dep)):
    """Get deployment state with positions, orders, trades, metrics."""
    deployment = _deployment(db, did)
    if deployment.account.user_id != current_user.id:
        raise HTTPException(403, "Not authorized")
    return paper.get_deployment_state(db, deployment)

@router.get("/accounts/{aid}/deployments")
def list_deployments(aid: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_dep)):
    """List all deployments for an account."""
    _acct(db, aid)  # Verify account exists
    if current_user.id != db.get(PaperAccount, aid).user_id:
        raise HTTPException(403, "Not authorized")
    deployments = db.query(PaperDeployment).filter_by(account_id=aid).order_by(PaperDeployment.id.desc()).all()
    return [{
        "id": d.id,
        "strategy_id": d.strategy_id,
        "strategy_version": d.strategy_version,
        "status": d.status,
        "activated_at": d.activated_at.isoformat() if d.activated_at else None,
        "closed_at": d.closed_at.isoformat() if d.closed_at else None,
        "initial_cash": d.initial_cash,
        "transaction_cost_bps": d.transaction_cost_bps,
        "slippage_bps": d.slippage_bps,
        "max_position_pct": d.max_position_pct,
        "stop_loss_pct": d.stop_loss_pct,
        "take_profit_pct": d.take_profit_pct,
    } for d in deployments]

@router.post("/deployments/{did}/step")
def step_deployment(did: int, force: bool = Query(False), db: Session = Depends(get_db), current_user: User = Depends(get_current_user_dep)):
    """
    Evaluate deployed strategy on latest market data and execute signals.
    
    Matches backtest execution model:
    - Signals evaluated on CLOSED bars (no look-ahead)
    - Orders fill at NEXT bar OPEN
    - Slippage and transaction costs applied
    - Stop loss / take profit checked intra-bar
    """
    deployment = _deployment(db, did)
    if deployment.account.user_id != current_user.id:
        raise HTTPException(403, "Not authorized")
    try:
        result = paper.evaluate_strategy_step(db, deployment, force=force)
        return result
    except paper.PaperExecutionError as e:
        raise HTTPException(422 if e.code != "DEPLOYMENT_NOT_ACTIVE" and e.code != "ACCOUNT_NOT_RUNNING" else 409, 
                           {"error": e.code, "message": e.message})

@router.post("/deployments/{did}/control/{action}")
def control_deployment(did: int, action: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_dep)):
    """Control deployment status (pause/resume/stop/close)."""
    deployment = _deployment(db, did)
    if deployment.account.user_id != current_user.id:
        raise HTTPException(403, "Not authorized")
    valid_actions = {"pause": "PAUSED", "resume": "ACTIVE", "stop": "STOPPED", "close": "CLOSED"}
    if action not in valid_actions:
        raise HTTPException(400, "Unknown action. Use: pause, resume, stop, close")
    
    if action == "close":
        # Liquidate positions and close
        paper.close_deployment(db, did)
    else:
        if deployment.status == "CLOSED":
            raise HTTPException(409, "Cannot modify closed deployment.")
        deployment.status = valid_actions[action]
        db.commit()
    
    return paper.get_deployment_state(db, deployment)

@router.post("/deployments/{did}/orders")
def place_deployment_order(did: int, body: OrderIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_dep)):
    """Place a manual order within a deployment."""
    deployment = _deployment(db, did)
    if deployment.account.user_id != current_user.id:
        raise HTTPException(403, "Not authorized")
    if deployment.status != "ACTIVE":
        raise HTTPException(409, f"Deployment is {deployment.status}; orders blocked.")
    symbol = _resolve_symbol(body.symbol)
    
    try:
        order = paper.place_manual_order(
            db, did, symbol, body.side, body.qty, "manual",
            stop_loss_price=body.stop_loss_price, take_profit_price=body.take_profit_price,
        )
        state = paper.get_deployment_state(db, deployment)
        # Additive field: lets the terminal show the actual simulated fill
        # without changing the existing deployment state contract.
        state["order"] = next(
            (o for o in state.get("orders", []) if o.get("id") == order.id),
            None,
        )
        return state
    except paper.PaperExecutionError as e:
        raise HTTPException(422 if e.code != "DEPLOYMENT_NOT_ACTIVE" and e.code != "ACCOUNT_NOT_RUNNING" else 409,
                           {"error": e.code, "message": e.message})

@router.get("/deployments/{did}/trades")
def get_deployment_trades(did: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_dep)):
    """Get all completed trades for a deployment."""
    deployment = _deployment(db, did)
    if deployment.account.user_id != current_user.id:
        raise HTTPException(403, "Not authorized")
    from ..models import PaperTrade
    trades = db.query(PaperTrade).filter_by(deployment_id=did).order_by(PaperTrade.entry_ts).all()
    return [{
        "id": t.id,
        "symbol": t.symbol,
        "side": t.side,
        "qty": t.qty,
        "entry_price": t.entry_price,
        "exit_price": t.exit_price,
        "entry_ts": t.entry_ts.isoformat() if t.entry_ts else None,
        "exit_ts": t.exit_ts.isoformat() if t.exit_ts else None,
        "pnl": round(t.pnl, 2),
        "ret": round(t.ret * 100, 2),
        "reason": t.reason,
        "fees": round(t.fees, 2),
        "slippage": round(t.slippage, 2),
    } for t in trades]

# Aliases for backwards compatibility with tests
deploy = create_deployment
