from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Strategy, BacktestRun
from ..schemas import BacktestIn, StrategySpec
from ..services import market, backtest, validation
router = APIRouter(prefix="/api/backtests", tags=["backtests"])
@router.post("")
def run(body: BacktestIn, db: Session = Depends(get_db)):
    s = db.get(Strategy, body.strategy_id)
    if not s: raise HTTPException(404, "Strategy not found")
    spec = StrategySpec(**s.spec)
    # Structural validation first
    pre = validation.validate(spec, {"trades": 99, "max_drawdown_pct": 0})
    structural = [e for e in pre["errors"] if "backtest" not in e.lower()]
    if structural: raise HTTPException(422, {"validation": {"passed": False, "errors": structural, "warnings": pre["warnings"]}})
    # Additional validation: data availability check
    df, meta = market.get_bars(spec.instruments[0], spec.timeframe, body.bars)
    # Check if sufficient data for the strategy
    if len(df) < 30:
        raise HTTPException(422, {"validation": {"passed": False, "errors": [f"Insufficient data: only {len(df)} bars available, need at least 30"], "warnings": []}})
    # Run backtest with transaction costs and slippage
    metrics, curve, trades = backtest.run(spec, df, body.initial_cash, body.transaction_cost_bps, body.slippage_bps)
    gate = validation.validate(spec, metrics)
    # Save strategy spec snapshot for immutability
    r = BacktestRun(
        strategy_id=s.id, 
        strategy_version=s.version,
        strategy_spec=s.spec,
        initial_cash=body.initial_cash,
        transaction_cost_bps=body.transaction_cost_bps,
        slippage_bps=body.slippage_bps,
        start_date=body.start_date,
        end_date=body.end_date,
        metrics=metrics, 
        equity_curve=curve, 
        trades=trades, 
        validation=gate, 
        data_source=meta["source"]
    )
    db.add(r); db.commit(); db.refresh(r)
    return {"id": r.id, "metrics": metrics, "equity_curve": curve, "trades": trades, "validation": gate, "meta": meta}
@router.get("/{rid}")
def get(rid: int, db: Session = Depends(get_db)):
    r = db.get(BacktestRun, rid)
    if not r: raise HTTPException(404, "Run not found")
    return {"id": r.id, "metrics": r.metrics, "equity_curve": r.equity_curve, "trades": r.trades, "validation": r.validation}
