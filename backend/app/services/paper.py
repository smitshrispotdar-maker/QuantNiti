"""Paper Trading Execution Service.

Matches the backtest engine's execution model:
- Signal evaluation on closed bars (no look-ahead)
- Order fills at NEXT bar OPEN
- Slippage: buy higher, sell lower
- Transaction costs on both entry and exit
- Stop loss / take profit checked intra-bar on HIGH/LOW
"""

import math
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from ..schemas import StrategySpec, IndicatorSpec, Rule, RiskLimits
from ..services.indicators import compute
from ..services import backtest, validation
from ..models import (
    PaperAccount, PaperDeployment, PaperOrder, PaperPosition, PaperTrade, PaperAccount as PaperAccountModel
)


class PaperExecutionError(Exception):
    """Custom exception for paper execution errors."""
    def __init__(self, message: str, code: str = "EXECUTION_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


def _side(df: pd.DataFrame, x: Any) -> pd.Series:
    """Get series from dataframe column or constant value."""
    return df[x] if isinstance(x, str) else pd.Series(float(x), index=df.index)


def eval_rule(df: pd.DataFrame, r: Rule) -> pd.Series:
    """Evaluate a single rule on dataframe (copied from backtest for consistency)."""
    a, b = _side(df, r.left), _side(df, r.right)
    if r.op == ">": return a > b
    if r.op == "<": return a < b
    if r.op == "crosses_above": return (a > b) & (a.shift() <= b.shift())
    return (a < b) & (a.shift() >= b.shift())


def signals(df: pd.DataFrame, spec: StrategySpec) -> Tuple[pd.Series, pd.Series]:
    """Generate entry/exit signals (copied from backtest for consistency)."""
    full = pd.Series(False, index=df.index)
    entry = pd.concat([eval_rule(df, r) for r in spec.entry_rules], axis=1).all(axis=1) if spec.entry_rules else full
    exit_ = pd.concat([eval_rule(df, r) for r in spec.exit_rules], axis=1).any(axis=1) if spec.exit_rules else full
    return entry.fillna(False), exit_.fillna(False)


def _compute_slippage_price(price: float, slippage_bps: float, side: str) -> float:
    """Apply slippage: buy at higher price, sell at lower price."""
    if slippage_bps <= 0:
        return price
    factor = slippage_bps / 10000
    return price * (1 + factor) if side == "BUY" else price * (1 - factor)


def _apply_transaction_cost(price: float, cost_bps: float, side: str) -> float:
    """Apply transaction cost: buy pays more, sell receives less."""
    if cost_bps <= 0:
        return price
    factor = cost_bps / 10000
    return price * (1 + factor) if side == "BUY" else price * (1 - factor)


def _check_data_freshness(meta: Dict[str, Any], max_age_seconds: int = 3600) -> Tuple[bool, Optional[str]]:
    """Check if market data is fresh enough for execution."""
    if meta.get("status") == "SIMULATED":
        return True, None  # Mock data is always "fresh"
    
    # Check cache age if available
    cache_age = meta.get("data_quality", {}).get("cache_age_seconds")
    if cache_age is not None and cache_age > max_age_seconds:
        return False, f"Market data is stale: {cache_age:.0f}s old (max {max_age_seconds}s)"
    
    return True, None


def evaluate_strategy_step(
    db: Session,
    deployment: PaperDeployment,
    force: bool = False
) -> Dict[str, Any]:
    """
    Evaluate deployed strategy on latest market data and execute signals.
    
    Execution model (matches backtest):
    1. Get latest bars up to current time
    2. Compute indicators and signals on CLOSED bars only
    3. Check signals on the LAST CLOSED bar (index -1)
    4. If signal fires, execute at NEXT bar OPEN (which is current/latest price)
    5. Apply slippage and transaction costs
    6. Check stop loss / take profit on current bar HIGH/LOW
    
    Args:
        db: Database session
        deployment: PaperDeployment to evaluate
        force: If True, skip idempotency check
    
    Returns:
        Dict with action taken: {"action": "BUY"|"SELL"|"HOLD", "details": {...}}
    """
    # Get account
    account = db.get(PaperAccount, deployment.account_id)
    if not account:
        raise PaperExecutionError("Account not found", "ACCOUNT_NOT_FOUND")
    
    if deployment.status != "ACTIVE":
        raise PaperExecutionError(f"Deployment is {deployment.status}", "DEPLOYMENT_NOT_ACTIVE")
    
    if account.status != "RUNNING":
        raise PaperExecutionError(f"Account is {account.status}", "ACCOUNT_NOT_RUNNING")
    
    # Load strategy spec from deployment snapshot (immutable)
    spec = StrategySpec(**deployment.strategy_spec)
    symbol = spec.instruments[0]
    
    # Fetch market data (need enough bars for indicators + 1 for next-open execution)
    bars_needed = max(300, deployment.max_position_pct * 2)  # At least 300 bars
    df, meta = backtest.compute_market_data(symbol, spec.timeframe, bars_needed, db)
    
    # Check data freshness
    fresh, warning = _check_data_freshness(meta)
    if not fresh and not force:
        raise PaperExecutionError(warning or "Stale market data", "STALE_DATA")
    
    # Idempotency check: has this bar already been processed?
    last_bar_ts = str(df.index[-1])
    if deployment.last_processed_bar_ts == last_bar_ts and not force:
        return {"action": "HOLD", "reason": "Bar already processed", "bar_ts": last_bar_ts}
    
    # Compute indicators and signals
    df_with_indicators = compute(df, spec.indicators)
    entry_series, exit_series = signals(df_with_indicators, spec)
    
    # Get current position
    position = db.query(PaperPosition).filter_by(
        deployment_id=deployment.id, symbol=symbol
    ).first()
    
    held_qty = position.qty if position else 0.0
    entry_price = position.avg_entry_price if position else 0.0
    
    # Check stop loss / take profit on CURRENT bar (intra-bar, like backtest)
    current_bar = df_with_indicators.iloc[-1]
    stop_triggered = False
    tp_triggered = False
    stop_reason = None
    
    if held_qty > 0:
        # Stop loss: check if LOW <= stop_price
        if deployment.stop_loss_pct and entry_price > 0:
            stop_price = entry_price * (1 - deployment.stop_loss_pct / 100)
            if current_bar.low <= stop_price:
                stop_triggered = True
                stop_reason = "stop_loss"
        
        # Take profit: check if HIGH >= limit_price
        if not stop_triggered and deployment.take_profit_pct and entry_price > 0:
            limit_price = entry_price * (1 + deployment.take_profit_pct / 100)
            if current_bar.high >= limit_price:
                tp_triggered = True
                stop_reason = "take_profit"
    
    # Determine signal from LAST CLOSED bar (index -2 to avoid look-ahead)
    # The last bar (index -1) is the current forming bar
    if len(df_with_indicators) < 2:
        return {"action": "HOLD", "reason": "Insufficient bars", "bar_ts": last_bar_ts}
    
    prev_bar_idx = -2  # Last CLOSED bar
    entry_signal = entry_series.iloc[prev_bar_idx]
    exit_signal = exit_series.iloc[prev_bar_idx]
    
    # Execution price is NEXT bar OPEN = current bar OPEN (index -1)
    exec_price = float(df_with_indicators.iloc[-1].open)
    
    action_taken = "HOLD"
    details = {"bar_ts": last_bar_ts, "exec_price": exec_price}
    
    # BUY logic
    if entry_signal and held_qty < 1e-9 and not math.isnan(exec_price):
        # Calculate position size
        buy_price = _compute_slippage_price(exec_price, deployment.slippage_bps, "BUY")
        buy_price_net = _apply_transaction_cost(buy_price, deployment.transaction_cost_bps, "BUY")
        
        max_position_value = account.cash * (deployment.max_position_pct / 100)
        qty = max_position_value / buy_price_net
        
        if qty > 1e-9 and qty * buy_price_net <= account.cash + 1e-9:
            # Execute buy
            account.cash -= qty * buy_price_net
            
            # Create order record
            order = PaperOrder(
                account_id=account.id,
                deployment_id=deployment.id,
                symbol=symbol,
                side="BUY",
                qty=qty,
                fill_price=buy_price_net,
                reason="strategy_entry",
                transaction_cost_bps=deployment.transaction_cost_bps,
                slippage_bps=deployment.slippage_bps,
                stop_price=entry_price * (1 - deployment.stop_loss_pct / 100) if deployment.stop_loss_pct else None,
                limit_price=entry_price * (1 + deployment.take_profit_pct / 100) if deployment.take_profit_pct else None,
            )
            db.add(order)
            
            # Create/update position
            if position:
                position.qty = qty
                position.avg_entry_price = buy_price_net
                position.stop_loss_price = entry_price * (1 - deployment.stop_loss_pct / 100) if deployment.stop_loss_pct else None
                position.take_profit_price = entry_price * (1 + deployment.take_profit_pct / 100) if deployment.take_profit_pct else None
            else:
                position = PaperPosition(
                    deployment_id=deployment.id,
                    symbol=symbol,
                    qty=qty,
                    avg_entry_price=buy_price_net,
                    stop_loss_price=entry_price * (1 - deployment.stop_loss_pct / 100) if deployment.stop_loss_pct else None,
                    take_profit_price=entry_price * (1 + deployment.take_profit_pct / 100) if deployment.take_profit_pct else None,
                )
                db.add(position)
            
            action_taken = "BUY"
            details.update({
                "qty": qty,
                "entry_price": buy_price_net,
                "slippage_price": buy_price,
                "raw_price": exec_price,
            })
    
    # SELL logic (exit signal or stop loss / take profit)
    elif (exit_signal or stop_triggered or tp_triggered) and held_qty > 1e-9:
        # Calculate exit price with slippage and costs
        sell_price = _compute_slippage_price(exec_price, deployment.slippage_bps, "SELL")
        sell_price_net = _apply_transaction_cost(sell_price, deployment.transaction_cost_bps, "SELL")
        
        # Calculate P&L
        pnl = held_qty * (sell_price_net - entry_price)
        ret = sell_price_net / entry_price - 1
        reason = "strategy_exit"
        if stop_triggered:
            reason = "stop_loss"
        elif tp_triggered:
            reason = "take_profit"
        
        # Execute sell
        account.cash += held_qty * sell_price_net
        
        # Create order record
        order = PaperOrder(
            account_id=account.id,
            deployment_id=deployment.id,
            symbol=symbol,
            side="SELL",
            qty=held_qty,
            fill_price=sell_price_net,
            reason=reason,
            transaction_cost_bps=deployment.transaction_cost_bps,
            slippage_bps=deployment.slippage_bps,
        )
        db.add(order)
        
        # Create trade record
        trade = PaperTrade(
            deployment_id=deployment.id,
            symbol=symbol,
            side="SELL",
            qty=held_qty,
            entry_price=entry_price,
            exit_price=sell_price_net,
            entry_ts=position.updated_at if position else datetime.utcnow(),
            exit_ts=datetime.utcnow(),
            pnl=pnl,
            ret=ret,
            reason=reason,
            fees=held_qty * (exec_price - sell_price_net),  # Approximate fees
            slippage=held_qty * (exec_price - sell_price),
        )
        db.add(trade)
        
        # Update position
        if position:
            position.realized_pnl += pnl
            position.qty = 0.0
            position.avg_entry_price = None
            position.stop_loss_price = None
            position.take_profit_price = None
        
        action_taken = "SELL"
        details.update({
            "qty": held_qty,
            "exit_price": sell_price_net,
            "slippage_price": sell_price,
            "raw_price": exec_price,
            "pnl": pnl,
            "ret": ret,
            "reason": reason,
        })
    
    # Update deployment last processed timestamp
    deployment.last_processed_bar_ts = last_bar_ts
    deployment.last_step_at = datetime.utcnow()
    
    db.commit()
    
    return {"action": action_taken, "details": details, "warning": warning}


def place_manual_order(
    db: Session,
    deployment_id: int,
    symbol: str,
    side: str,
    qty: float,
    reason: str = "manual"
) -> PaperOrder:
    """Place a manual order for a deployment."""
    deployment = db.get(PaperDeployment, deployment_id)
    if not deployment:
        raise PaperExecutionError("Deployment not found", "DEPLOYMENT_NOT_FOUND")
    
    account = db.get(PaperAccount, deployment.account_id)
    if not account:
        raise PaperExecutionError("Account not found", "ACCOUNT_NOT_FOUND")
    
    if deployment.status != "ACTIVE":
        raise PaperExecutionError(f"Deployment is {deployment.status}", "DEPLOYMENT_NOT_ACTIVE")
    
    if account.status != "RUNNING":
        raise PaperExecutionError(f"Account is {account.status}", "ACCOUNT_NOT_RUNNING")
    
    # Get current price
    df, meta = backtest.compute_market_data(symbol, deployment.strategy_spec.get("timeframe", "1d"), 2, db)
    exec_price = float(df.iloc[-1].open)  # Next bar open
    
    if side == "BUY":
        buy_price = _compute_slippage_price(exec_price, deployment.slippage_bps, "BUY")
        buy_price_net = _apply_transaction_cost(buy_price, deployment.transaction_cost_bps, "BUY")
        cost = qty * buy_price_net
        
        if cost > account.cash + 1e-9:
            raise PaperExecutionError("Insufficient simulated cash", "INSUFFICIENT_CASH")
        
        account.cash -= cost
        
        order = PaperOrder(
            account_id=account.id,
            deployment_id=deployment.id,
            symbol=symbol,
            side="BUY",
            qty=qty,
            fill_price=buy_price_net,
            reason=reason,
            transaction_cost_bps=deployment.transaction_cost_bps,
            slippage_bps=deployment.slippage_bps,
        )
        
        # Update position
        position = db.query(PaperPosition).filter_by(deployment_id=deployment.id, symbol=symbol).first()
        if position:
            # Average down/up
            total_qty = position.qty + qty
            position.avg_entry_price = (position.avg_entry_price * position.qty + buy_price_net * qty) / total_qty
            position.qty = total_qty
        else:
            position = PaperPosition(
                deployment_id=deployment.id,
                symbol=symbol,
                qty=qty,
                avg_entry_price=buy_price_net,
            )
            db.add(position)
    
    else:  # SELL
        position = db.query(PaperPosition).filter_by(deployment_id=deployment.id, symbol=symbol).first()
        held = position.qty if position else 0.0
        
        if qty > held + 1e-9:
            raise PaperExecutionError("Cannot sell more than held", "INSUFFICIENT_HOLDINGS")
        
        sell_price = _compute_slippage_price(exec_price, deployment.slippage_bps, "SELL")
        sell_price_net = _apply_transaction_cost(sell_price, deployment.transaction_cost_bps, "SELL")
        
        entry_price = position.avg_entry_price if position else exec_price
        pnl = qty * (sell_price_net - entry_price)
        
        account.cash += qty * sell_price_net
        
        order = PaperOrder(
            account_id=account.id,
            deployment_id=deployment.id,
            symbol=symbol,
            side="SELL",
            qty=qty,
            fill_price=sell_price_net,
            reason=reason,
            transaction_cost_bps=deployment.transaction_cost_bps,
            slippage_bps=deployment.slippage_bps,
        )
        
        if position:
            position.qty -= qty
            position.realized_pnl += pnl
            if position.qty < 1e-9:
                position.avg_entry_price = None
        
        # Create trade record
        trade = PaperTrade(
            deployment_id=deployment.id,
            symbol=symbol,
            side="SELL",
            qty=qty,
            entry_price=entry_price,
            exit_price=sell_price_net,
            entry_ts=position.updated_at if position else datetime.utcnow(),
            exit_ts=datetime.utcnow(),
            pnl=pnl,
            ret=sell_price_net / entry_price - 1 if entry_price else 0,
            reason=reason,
            fees=qty * (exec_price - sell_price_net),
            slippage=qty * (exec_price - sell_price),
        )
        db.add(trade)
    
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def get_deployment_state(db: Session, deployment: PaperDeployment) -> Dict[str, Any]:
    """Get complete deployment state including positions, orders, trades, metrics."""
    account = db.get(PaperAccount, deployment.account_id)
    
    # Get positions
    positions = db.query(PaperPosition).filter_by(deployment_id=deployment.id).all()
    
    # Get current prices for unrealized P&L
    position_data = []
    total_unrealized = 0.0
    for pos in positions:
        if pos.qty > 1e-9:
            df, _ = backtest.compute_market_data(pos.symbol, deployment.strategy_spec.get("timeframe", "1d"), 2, db)
            current_price = float(df.iloc[-1].close)
            unrealized = pos.qty * (current_price - pos.avg_entry_price)
            pos.unrealized_pnl = unrealized
            total_unrealized += unrealized
            
            position_data.append({
                "symbol": pos.symbol,
                "qty": round(pos.qty, 6),
                "avg_entry_price": round(pos.avg_entry_price, 2) if pos.avg_entry_price else 0,
                "current_price": round(current_price, 2),
                "unrealized_pnl": round(unrealized, 2),
                "realized_pnl": round(pos.realized_pnl, 2),
                "stop_loss_price": pos.stop_loss_price,
                "take_profit_price": pos.take_profit_price,
            })
        else:
            position_data.append({
                "symbol": pos.symbol,
                "qty": 0,
                "avg_entry_price": 0,
                "current_price": 0,
                "unrealized_pnl": round(pos.realized_pnl, 2),
                "realized_pnl": round(pos.realized_pnl, 2),
                "stop_loss_price": None,
                "take_profit_price": None,
            })
    
    # Get orders
    orders = db.query(PaperOrder).filter_by(deployment_id=deployment.id).order_by(PaperOrder.ts.desc()).limit(100).all()
    order_data = [{
        "id": o.id,
        "symbol": o.symbol,
        "side": o.side,
        "qty": o.qty,
        "fill_price": o.fill_price,
        "reason": o.reason,
        "ts": o.ts.isoformat(),
        "label": o.label,
        "transaction_cost_bps": o.transaction_cost_bps,
        "slippage_bps": o.slippage_bps,
    } for o in orders]
    
    # Get trades for metrics
    trades = db.query(PaperTrade).filter_by(deployment_id=deployment.id).all()
    
    # Calculate metrics
    total_realized = sum(t.pnl for t in trades)
    total_fees = sum(t.fees for t in trades)
    total_slippage = sum(t.slippage for t in trades)
    
    equity = account.cash + total_unrealized
    total_return = equity - deployment.initial_cash
    total_return_pct = (total_return / deployment.initial_cash) * 100 if deployment.initial_cash else 0
    
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl < 0]
    win_rate = (len(wins) / len(trades) * 100) if trades and len(trades) > 0 else 0
    profit_factor = abs(sum(t.pnl for t in wins) / sum(t.pnl for t in losses)) if losses else (None if not wins else 999)
    
    # Max drawdown from trade history (simplified)
    if trades:
        equity_curve = [deployment.initial_cash]
        running = deployment.initial_cash
        for t in sorted(trades, key=lambda x: x.entry_ts):
            running += t.pnl
            equity_curve.append(running)
        peak = equity_curve[0]
        max_dd = 0
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd = (eq - peak) / peak
            if dd < max_dd:
                max_dd = dd
        max_drawdown_pct = max_dd * 100
    else:
        max_drawdown_pct = 0.0
    
    return {
        "deployment": {
            "id": deployment.id,
            "account_id": deployment.account_id,
            "strategy_id": deployment.strategy_id,
            "strategy_version": deployment.strategy_version,
            "status": deployment.status,
            "activated_at": deployment.activated_at.isoformat() if deployment.activated_at else None,
            "closed_at": deployment.closed_at.isoformat() if deployment.closed_at else None,
            "last_step_at": deployment.last_step_at.isoformat() if deployment.last_step_at else None,
            "initial_cash": deployment.initial_cash,
            "transaction_cost_bps": deployment.transaction_cost_bps,
            "slippage_bps": deployment.slippage_bps,
            "max_position_pct": deployment.max_position_pct,
            "stop_loss_pct": deployment.stop_loss_pct,
            "take_profit_pct": deployment.take_profit_pct,
            "max_drawdown_pct": deployment.max_drawdown_pct,
            "data_source": deployment.data_source,
        },
        "account": {
            "id": account.id,
            "name": account.name,
            "status": account.status,
            "cash": round(account.cash, 2),
            "equity": round(equity, 2),
            "starting_cash": account.starting_cash,
        },
        "positions": position_data,
        "orders": order_data,
        "metrics": {
            "total_return": round(total_return, 2),
            "total_return_pct": round(total_return_pct, 2),
            "total_realized_pnl": round(total_realized, 2),
            "total_unrealized_pnl": round(total_unrealized, 2),
            "total_fees": round(total_fees, 2),
            "total_slippage": round(total_slippage, 2),
            "total_trades": len(trades),
            "win_rate_pct": round(win_rate, 1),
            "profit_factor": round(profit_factor, 2) if profit_factor and profit_factor != 999 else profit_factor,
            "max_drawdown_pct": round(max_drawdown_pct, 2),
            "cash": round(account.cash, 2),
            "equity": round(equity, 2),
        },
        "label": "PAPER TRADING ONLY — NO REAL MONEY OR BROKER ORDERS",
    }


def close_deployment(db: Session, deployment_id: int) -> PaperDeployment:
    """Close a deployment (liquidate positions, mark as CLOSED)."""
    deployment = db.get(PaperDeployment, deployment_id)
    if not deployment:
        raise PaperExecutionError("Deployment not found", "DEPLOYMENT_NOT_FOUND")
    
    if deployment.status == "CLOSED":
        return deployment
    
    # Liquidate all positions
    positions = db.query(PaperPosition).filter_by(deployment_id=deployment.id).all()
    account = db.get(PaperAccount, deployment.account_id)
    
    for pos in positions:
        if pos.qty > 1e-9:
            df, _ = backtest.compute_market_data(pos.symbol, deployment.strategy_spec.get("timeframe", "1d"), 2, db)
            exec_price = float(df.iloc[-1].open)
            sell_price = _compute_slippage_price(exec_price, deployment.slippage_bps, "SELL")
            sell_price_net = _apply_transaction_cost(sell_price, deployment.transaction_cost_bps, "SELL")
            
            pnl = pos.qty * (sell_price_net - pos.avg_entry_price)
            account.cash += pos.qty * sell_price_net
            
            # Create closing order
            order = PaperOrder(
                account_id=account.id,
                deployment_id=deployment.id,
                symbol=pos.symbol,
                side="SELL",
                qty=pos.qty,
                fill_price=sell_price_net,
                reason="deployment_close",
                transaction_cost_bps=deployment.transaction_cost_bps,
                slippage_bps=deployment.slippage_bps,
            )
            db.add(order)
            
            # Create trade record
            trade = PaperTrade(
                deployment_id=deployment.id,
                symbol=pos.symbol,
                side="SELL",
                qty=pos.qty,
                entry_price=pos.avg_entry_price,
                exit_price=sell_price_net,
                entry_ts=pos.updated_at,
                exit_ts=datetime.utcnow(),
                pnl=pnl,
                ret=sell_price_net / pos.avg_entry_price - 1,
                reason="deployment_close",
                fees=pos.qty * (exec_price - sell_price_net),
                slippage=pos.qty * (exec_price - sell_price),
            )
            db.add(trade)
            
            pos.realized_pnl += pnl
            pos.qty = 0.0
    
    deployment.status = "CLOSED"
    deployment.closed_at = datetime.utcnow()
    db.commit()
    db.refresh(deployment)
    return deployment