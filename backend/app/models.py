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
class PaperOrder(Base):
    __tablename__ = "paper_orders"
    id = Column(Integer, primary_key=True); account_id = Column(Integer, ForeignKey("paper_accounts.id")); symbol = Column(String)
    side = Column(String); qty = Column(Float); fill_price = Column(Float); reason = Column(String); label = Column(String, default="PAPER/SIMULATED"); ts = Column(DateTime, default=now)
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
