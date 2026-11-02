"""Canonical Strategy Schema v1.0 — the single contract shared by chat studio, visual builder, backtester and paper engine."""
from datetime import datetime
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


# Market Data Schemas
class DataQuality(BaseModel):
    issues: List[str] = []
    gaps: List[str] = []
    duplicates: List[str] = []
    bar_count: int = 0
    cached: bool = False
    cache_age_seconds: Optional[float] = None

class MarketMeta(BaseModel):
    symbol: str
    name: str
    timeframe: str
    source: str
    status: str
    last_bar: Optional[str] = None
    fetched_at: str
    label: str = "PAPER/SIMULATED"
    exchange_timezone: str = "UTC"
    data_quality: DataQuality

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

class MarketBarsResponse(BaseModel):
    meta: MarketMeta
    bars: List[MarketBarRow]

class WatchlistItem(BaseModel):
    symbol: str
    name: str
    timeframe: str
    source: str
    status: str
    last_bar: str
    fetched_at: str
    label: str
    price: float
    change_pct: float

class SymbolInfo(BaseModel):
    symbol: str
    name: str
    timezone: str


class ChatIn(BaseModel):
    conversation_id: Optional[int] = None
    message: str

class StrategyIn(BaseModel):
    spec: StrategySpec

class BacktestIn(BaseModel):
    strategy_id: int
    bars: int = 500
    initial_cash: float = 100_000

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


class WatchlistAdd(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)


class WatchlistItemResponse(BaseModel):
    id: int
    symbol: str
    name: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class WatchlistResponse(BaseModel):
    items: List[WatchlistItemResponse]