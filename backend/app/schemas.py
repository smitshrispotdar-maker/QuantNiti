"""Canonical Strategy Schema v1.0 — the single contract shared by chat studio, visual builder, backtester and paper engine."""
from datetime import datetime
from enum import Enum
from typing import Literal, Union, Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator

INDICATOR_TYPES = ("SMA", "EMA", "RSI", "MACD", "BBANDS")

class IndicatorSpec(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    type: Literal["SMA", "EMA", "RSI", "MACD", "BBANDS"]
    params: dict[str, float] = {}

class Rule(BaseModel):
    left: str                       # "price" or an indicator id
    op: Literal[">", "<", "crosses_above", "crosses_below"]
    right: Union[str, float]        # "price", indicator id, or a number

class RiskLimits(BaseModel):
    max_position_pct: float = Field(default=25, gt=0, le=100)
    stop_loss_pct: Optional[float] = Field(default=5, gt=0, le=50)
    take_profit_pct: Optional[float] = Field(default=None, gt=0, le=500)
    max_drawdown_pct: float = Field(default=25, gt=0, le=100)

class StrategySpec(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    name: str = "Untitled strategy"
    instruments: list[str] = []
    timeframe: Literal["1m", "5m", "15m", "1h", "1d"] = "1d"
    indicators: list[IndicatorSpec] = []
    entry_rules: list[Rule] = []
    exit_rules: list[Rule] = []
    risk: RiskLimits = RiskLimits()

    @field_validator("instruments")
    @classmethod
    def up(cls, v): return [s.upper() for s in v]


# Strategy Versioning & Diff Schemas
class StrategyVersionInfo(BaseModel):
    version: int
    spec: StrategySpec
    created_at: datetime
    description: Optional[str] = None


class StrategyDiff(BaseModel):
    strategy_id: int
    from_version: int
    to_version: int
    diff_summary: Dict[str, Any]
    created_at: datetime


# Research Comparison Schemas
class ResearchComparisonRequest(BaseModel):
    run_ids: List[int] = Field(min_length=2, max_length=5)


class ResearchComparisonResponse(BaseModel):
    runs: List[Dict[str, Any]]
    comparison: Dict[str, Any]


# Export Schemas
class ExportFormat(str, Enum):
    JSON = "json"
    MARKDOWN = "markdown"
    PDF = "pdf"


class ExportRequest(BaseModel):
    format: ExportFormat
    journal_entry_ids: Optional[List[int]] = None
    strategy_ids: Optional[List[int]] = None
    backtest_run_ids: Optional[List[int]] = None
    research_run_ids: Optional[List[int]] = None
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None


# Conversation Search Schemas
class ConversationSearchRequest(BaseModel):
    query: str
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class ConversationSearchResult(BaseModel):
    conversations: List[Dict[str, Any]]
    total: int


# API Request Schemas
class ChatIn(BaseModel):
    conversation_id: Optional[int] = None
    message: str

class StrategyIn(BaseModel):
    spec: StrategySpec

class BacktestIn(BaseModel):
    strategy_id: int
    bars: int = 500
    initial_cash: float = Field(default=100_000, gt=0)
    transaction_cost_bps: float = Field(default=0, ge=0, le=1000)
    slippage_bps: float = Field(default=0, ge=0, le=1000)
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class OrderIn(BaseModel):
    symbol: str
    side: Literal["BUY", "SELL"]
    qty: float = Field(gt=0)

class AccountIn(BaseModel):
    name: str = "Paper account"
    starting_cash: float = Field(default=100_000, gt=0)

class DeployIn(BaseModel):
    strategy_id: int

class JournalIn(BaseModel):
    strategy_id: Optional[int] = None
    recommendation: str
    evidence: dict = {}

class ReviewIn(BaseModel):
    outcome_review: str


# Journal Entry Schemas
class JournalEntryCreate(BaseModel):
    strategy_id: Optional[int] = None
    conversation_id: Optional[int] = None
    title: Optional[str] = None
    decision_type: Optional[str] = None
    status: Optional[str] = None
    recommendation: Optional[str] = None
    evidence: dict = {}
    hypothesis_rationale: Optional[str] = None
    evidence_summary: Optional[str] = None
    risks_assumptions: Optional[str] = None
    decision_next_steps: Optional[str] = None
    expected_outcome: Optional[str] = None
    actual_outcome: Optional[str] = None
    backtest_run_id: Optional[int] = None
    research_run_id: Optional[int] = None
    deployment_id: Optional[int] = None
    hypothesis_rationale: Optional[str] = None
    evidence_summary: Optional[str] = None
    risks_assumptions: Optional[str] = None
    decision_next_steps: Optional[str] = None
    expected_outcome: Optional[str] = None
    actual_outcome: Optional[str] = None
    backtest_run_id: Optional[int] = None
    research_run_id: Optional[int] = None
    deployment_id: Optional[int] = None
    hypothesis_rationale: Optional[str] = None
    evidence_summary: Optional[str] = None
    risks_assumptions: Optional[str] = None
    decision_next_steps: Optional[str] = None
    expected_outcome: Optional[str] = None
    actual_outcome: Optional[str] = None
    backtest_run_id: Optional[int] = None
    research_run_id: Optional[int] = None
    deployment_id: Optional[int] = None
    evidence: dict = {}
    strategy_version: Optional[int] = None

class JournalEntryUpdate(BaseModel):
    title: Optional[str] = None
    decision_type: Optional[str] = None
    status: Optional[str] = None
    recommendation: Optional[str] = None
    evidence: Optional[dict] = None
    hypothesis_rationale: Optional[str] = None
    evidence_summary: Optional[str] = None
    risks_assumptions: Optional[str] = None
    decision_next_steps: Optional[str] = None
    expected_outcome: Optional[str] = None
    actual_outcome: Optional[str] = None
    backtest_run_id: Optional[int] = None
    research_run_id: Optional[int] = None
    deployment_id: Optional[int] = None
    hypothesis_rationale: Optional[str] = None
    evidence_summary: Optional[str] = None
    risks_assumptions: Optional[str] = None
    decision_next_steps: Optional[str] = None
    expected_outcome: Optional[str] = None
    actual_outcome: Optional[str] = None
    backtest_run_id: Optional[int] = None
    research_run_id: Optional[int] = None
    deployment_id: Optional[int] = None
    outcome_review: Optional[str] = None


class JournalEntryResponse(BaseModel):
    id: int
    title: Optional[str] = None
    decision_type: Optional[str] = None
    status: Optional[str] = None
    strategy_id: Optional[int] = None
    strategy_version: Optional[int] = None
    conversation_id: Optional[int] = None
    backtest_run_id: Optional[int] = None
    research_run_id: Optional[int] = None
    deployment_id: Optional[int] = None
    hypothesis_rationale: Optional[str] = None
    evidence_summary: Optional[str] = None
    risks_assumptions: Optional[str] = None
    decision_next_steps: Optional[str] = None
    expected_outcome: Optional[str] = None
    actual_outcome: Optional[str] = None
    recommendation: str
    evidence: dict = {}
    outcome_review: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class JournalEntryListResponse(BaseModel):
    items: List[JournalEntryResponse]
    total: int
    page: int
    page_size: int


# Scheduled Research Schemas
class ScheduledResearchConfig(BaseModel):
    enabled: bool = False
    cron_schedule: str = "0 6 * * *"  # Daily at 6 AM
    strategies: List[int] = Field(default_factory=list)
    symbols: List[str] = Field(default_factory=list)
    timeframes: List[str] = Field(default_factory=list)
    max_runs_per_day: int = 5


# Research Schemas
class ResearchRunCreate(BaseModel):
    strategy_id: Optional[int] = None
    strategy_version: Optional[int] = None
    conversation_id: Optional[int] = None
    backtest_run_id: Optional[int] = None
    deployment_id: Optional[int] = None
    strategy_spec_snapshot: Optional[dict] = None
    backtest_metrics_snapshot: Optional[dict] = None
    label: Optional[str] = None


class ResearchRunResponse(BaseModel):
    id: int
    user_id: int
    strategy_id: Optional[int] = None
    strategy_version: Optional[int] = None
    conversation_id: Optional[int] = None
    backtest_run_id: Optional[int] = None
    deployment_id: Optional[int] = None
    strategy_spec_snapshot: Optional[dict] = None
    backtest_metrics_snapshot: Optional[dict] = None
    facts: Optional[dict] = None
    interpretations: Optional[dict] = None
    label: Optional[str] = None
    data_source: Optional[str] = None
    data_quality: Optional[dict] = None
    is_simulated: bool = False
    created_at: datetime
    updated_at: datetime


class ResearchRunListResponse(BaseModel):
    items: List[ResearchRunResponse]
    total: int
    page: int
    page_size: int


# Market Data Schemas
class MarketMeta(BaseModel):
    symbol: str
    name: str
    timeframe: str
    source: str
    status: str
    last_bar: Optional[str] = None
    fetched_at: str
    label: str
    exchange_timezone: str
    data_quality: Dict[str, Any] = {}


class MarketBarRow(BaseModel):
    ts: str
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[float] = None
    sma20: Optional[float] = None
    ema20: Optional[float] = None
    ema50: Optional[float] = None
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_hist: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_lower: Optional[float] = None
    range: Optional[List[float]] = None


class MarketBarsResponse(BaseModel):
    meta: MarketMeta
    bars: List[MarketBarRow]


# Market Watchlist Item (for /api/market/watchlist endpoint)
class WatchlistItem(BaseModel):
    symbol: str
    name: str
    timeframe: str
    source: str
    status: str
    last_bar: Optional[str] = None
    fetched_at: str
    label: str
    exchange_timezone: str
    data_quality: Dict[str, Any]
    price: Optional[float] = None
    change_pct: Optional[float] = None


class SymbolInfo(BaseModel):
    symbol: str
    name: str
    timezone: str


# Personal Watchlist Schemas
class WatchlistAdd(BaseModel):
    symbol: str


class WatchlistItemResponse(BaseModel):
    id: int
    symbol: str
    name: str
    price: Optional[float] = None
    change_pct: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class WatchlistResponse(BaseModel):
    items: List[WatchlistItemResponse]


# Authentication Schemas
class UserRegister(BaseModel):
    email: str
    password: str = Field(min_length=12, max_length=128)


class UserLogin(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserResponseSafe(BaseModel):
    """Safe user response without sensitive fields."""
    id: int
    email: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"