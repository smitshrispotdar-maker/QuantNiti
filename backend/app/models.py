from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from .db import Base
now = datetime.utcnow
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True); email = Column(String, unique=True); created_at = Column(DateTime, default=now)
class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True); user_id = Column(Integer, ForeignKey("users.id"))
    messages = Column(JSONB, default=list); draft_spec = Column(JSONB); updated_at = Column(DateTime, default=now)
class Strategy(Base):
    __tablename__ = "strategies"
    id = Column(Integer, primary_key=True); user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String); version = Column(Integer, default=1); spec = Column(JSONB); created_at = Column(DateTime, default=now)
class MarketBar(Base):
    __tablename__ = "market_bars"
    __table_args__ = (UniqueConstraint("symbol", "timeframe", "ts"),)
    id = Column(Integer, primary_key=True); symbol = Column(String, index=True); timeframe = Column(String); ts = Column(DateTime)
    open = Column(Float); high = Column(Float); low = Column(Float); close = Column(Float); volume = Column(Float); source = Column(String)
class BacktestRun(Base):
    __tablename__ = "backtest_runs"
    id = Column(Integer, primary_key=True); strategy_id = Column(Integer, ForeignKey("strategies.id")); strategy_version = Column(Integer)
    # Strategy spec snapshot for immutability
    strategy_spec = Column(JSONB)
    # Backtest configuration
    initial_cash = Column(Float, default=100_000)
    transaction_cost_bps = Column(Float, default=0)
    slippage_bps = Column(Float, default=0)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    # Results
    metrics = Column(JSONB); equity_curve = Column(JSONB); trades = Column(JSONB); validation = Column(JSONB); data_source = Column(String); created_at = Column(DateTime, default=now)
class PaperAccount(Base):
    __tablename__ = "paper_accounts"
    id = Column(Integer, primary_key=True); name = Column(String); starting_cash = Column(Float); cash = Column(Float)
    status = Column(String, default="RUNNING")  # RUNNING | PAUSED | STOPPED | KILLED
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=True); created_at = Column(DateTime, default=now)

class PaperDeployment(Base):
    __tablename__ = "paper_deployments"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("paper_accounts.id"), nullable=False)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)
    strategy_version = Column(Integer, nullable=False)
    # Immutable strategy spec snapshot at activation
    strategy_spec = Column(JSONB, nullable=False)
    # Execution configuration snapshot
    initial_cash = Column(Float, default=100_000)
    transaction_cost_bps = Column(Float, default=0)
    slippage_bps = Column(Float, default=0)
    max_position_pct = Column(Float, default=25)
    stop_loss_pct = Column(Float, nullable=True)
    take_profit_pct = Column(Float, nullable=True)
    max_drawdown_pct = Column(Float, default=25)
    # Status
    status = Column(String, default="ACTIVE")  # ACTIVE | PAUSED | STOPPED | CLOSED
    # Data source
    data_source = Column(String)
    # Timestamps
    activated_at = Column(DateTime, default=now)
    closed_at = Column(DateTime, nullable=True)
    last_step_at = Column(DateTime, nullable=True)
    # Idempotency
    last_processed_bar_ts = Column(String, nullable=True)

class PaperOrder(Base):
    __tablename__ = "paper_orders"
    id = Column(Integer, primary_key=True); account_id = Column(Integer, ForeignKey("paper_accounts.id")); symbol = Column(String)
    side = Column(String); qty = Column(Float); fill_price = Column(Float); reason = Column(String); label = Column(String, default="PAPER/SIMULATED"); ts = Column(DateTime, default=now)
    # Link to deployment for traceability
    deployment_id = Column(Integer, ForeignKey("paper_deployments.id"), nullable=True)
    # Execution details
    transaction_cost_bps = Column(Float, default=0)
    slippage_bps = Column(Float, default=0)
    # For stop loss / take profit tracking
    stop_price = Column(Float, nullable=True)
    limit_price = Column(Float, nullable=True)

class PaperPosition(Base):
    __tablename__ = "paper_positions"
    id = Column(Integer, primary_key=True)
    deployment_id = Column(Integer, ForeignKey("paper_deployments.id"), nullable=False)
    symbol = Column(String, nullable=False)
    qty = Column(Float, default=0.0)
    avg_entry_price = Column(Float, nullable=True)
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    # Stop loss / take profit tracking
    stop_loss_price = Column(Float, nullable=True)
    take_profit_price = Column(Float, nullable=True)
    # Last update
    updated_at = Column(DateTime, default=now, onupdate=now)
    # Unique constraint: one position per symbol per deployment
    __table_args__ = (UniqueConstraint("deployment_id", "symbol", name="uq_deployment_symbol"),)

class PaperTrade(Base):
    __tablename__ = "paper_trades"
    id = Column(Integer, primary_key=True)
    deployment_id = Column(Integer, ForeignKey("paper_deployments.id"), nullable=False)
    symbol = Column(String, nullable=False)
    side = Column(String, nullable=False)  # BUY/SELL
    qty = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)  # Null if open
    entry_ts = Column(DateTime, nullable=False)
    exit_ts = Column(DateTime, nullable=True)
    pnl = Column(Float, default=0.0)
    ret = Column(Float, default=0.0)
    reason = Column(String)  # strategy_entry, strategy_exit, stop_loss, take_profit, manual
    fees = Column(Float, default=0.0)
    slippage = Column(Float, default=0.0)
class JournalEntry(Base):
    __tablename__ = "journal"
    id = Column(Integer, primary_key=True); strategy_id = Column(Integer, nullable=True); strategy_version = Column(Integer, nullable=True)
    recommendation = Column(Text); evidence = Column(JSONB); outcome_review = Column(Text, nullable=True); created_at = Column(DateTime, default=now)

class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (UniqueConstraint("user_id", "symbol"),)
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, nullable=False)
    created_at = Column(DateTime, default=now)
