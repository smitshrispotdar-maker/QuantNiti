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
    pre = validation.validate(spec, {"trades": 99, "max_drawdown_pct": 0})  # structural checks first
    structural = [e for e in pre["errors"] if "backtest" not in e.lower()]
    if structural: raise HTTPException(422, {"validation": {"passed": False, "errors": structural, "warnings": pre["warnings"]}})
    df, meta = market.get_bars(spec.instruments[0], spec.timeframe, body.bars)
    metrics, curve, trades = backtest.run(spec, df, body.initial_cash)
    gate = validation.validate(spec, metrics)
    r = BacktestRun(strategy_id=s.id, strategy_version=s.version, metrics=metrics, equity_curve=curve, trades=trades, validation=gate, data_source=meta["source"])
    db.add(r); db.commit(); db.refresh(r)
    return {"id": r.id, "metrics": metrics, "equity_curve": curve, "trades": trades, "validation": gate, "meta": meta}
@router.get("/{rid}")
def get(rid: int, db: Session = Depends(get_db)):
    r = db.get(BacktestRun, rid)
    if not r: raise HTTPException(404, "Run not found")
    return {"id": r.id, "metrics": r.metrics, "equity_curve": r.equity_curve, "trades": r.trades, "validation": r.validation}
