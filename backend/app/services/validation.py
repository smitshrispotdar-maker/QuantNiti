"""Mandatory deterministic validation gate. Nothing deploys unless errors == []."""
from ..schemas import StrategySpec, IndicatorSpec, INDICATOR_TYPES
from typing import Optional
from datetime import datetime

# Supported instruments — India-only (NSE/BSE). Keep in sync with
# services.instruments.INSTRUMENTS.
from .instruments import SUPPORTED_INSTRUMENTS, provider_symbol

# Supported timeframes
SUPPORTED_TIMEFRAMES = {"1m", "5m", "15m", "1h", "1d"}

# Indicator parameter specifications with valid ranges
INDICATOR_PARAM_SPECS = {
    "SMA": {"period": (1, 500)},
    "EMA": {"period": (1, 500)},
    "RSI": {"period": (2, 100)},
    "MACD": {"fast": (1, 100), "slow": (1, 200), "signal": (1, 100)},
    "BBANDS": {"period": (2, 500), "k": (0.1, 5.0)},
}

# Minimum bars required for each indicator type to produce valid values
INDICATOR_MIN_BARS = {
    "SMA": lambda params: params.get("period", 20),
    "EMA": lambda params: params.get("period", 20),
    "RSI": lambda params: params.get("period", 14) + 1,
    "MACD": lambda params: params.get("slow", 26) + params.get("signal", 9),
    "BBANDS": lambda params: params.get("period", 20),
}

# Minimum bars required per timeframe for statistical significance
TIMEFRAME_MIN_BARS = {
    "1m": 100,
    "5m": 100,
    "15m": 100,
    "1h": 100,
    "1d": 30,
}


def _validate_indicator_params(indicator: IndicatorSpec) -> list[str]:
    """Validate indicator parameters against allowed ranges."""
    errors = []
    spec = INDICATOR_PARAM_SPECS.get(indicator.type)
    if not spec:
        return [f"Unsupported indicator type: {indicator.type}"]
    for param, value in indicator.params.items():
        if param not in spec:
            errors.append(f"Indicator {indicator.id}: unknown parameter '{param}' for {indicator.type}")
            continue
        min_val, max_val = spec[param]
        if not (min_val <= value <= max_val):
            errors.append(f"Indicator {indicator.id}: parameter '{param}' must be between {min_val} and {max_val}, got {value}")
    return errors


def _validate_fast_slow_relationships(spec: StrategySpec) -> list[str]:
    """Validate fast/slow period relationships for indicators that have both."""
    errors = []
    indicator_by_id = {i.id: i for i in spec.indicators}
    for ind in spec.indicators:
        if ind.type in ("SMA", "EMA") and "period" in ind.params:
            # Check if there's another indicator of same type that could be fast/slow
            for other_id, other in indicator_by_id.items():
                if other_id != ind.id and other.type == ind.type and "period" in other.params:
                    # Could add warning if periods are too close, but not an error
                    pass
    return errors


def _validate_date_range(start_date: Optional[str], end_date: Optional[str]) -> list[str]:
    """Validate date range if provided."""
    errors = []
    if start_date and end_date:
        try:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            if start >= end:
                errors.append("start_date must be before end_date")
        except ValueError:
            errors.append("Invalid date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS).")
    return errors


def _check_data_availability(spec: StrategySpec, bars_count: int) -> list[str]:
    """Check if enough historical data is available for the strategy."""
    errors = []
    min_bars = TIMEFRAME_MIN_BARS.get(spec.timeframe, 30)
    
    # Check indicator initialization requirements
    for ind in spec.indicators:
        min_bars_func = INDICATOR_MIN_BARS.get(ind.type)
        if min_bars_func:
            required = min_bars_func(ind.params)
            min_bars = max(min_bars, required)
    
    if bars_count < min_bars:
        errors.append(f"Insufficient data: {bars_count} bars available, need at least {min_bars} for {spec.timeframe} timeframe with configured indicators")
    
    return errors


def validate(spec: StrategySpec, metrics: dict | None = None, bars_count: int | None = None, 
             start_date: Optional[str] = None, end_date: Optional[str] = None) -> dict:
    errors, warnings = [], []
    ids = {i.id for i in spec.indicators} | {"price"}
    
    # Supported strategy types (currently only single-instrument long-only)
    if len(spec.instruments) > 1:
        errors.append("Multi-instrument strategies not yet supported. Select one instrument.")
    
    # Validate instruments
    for inst in spec.instruments:
        if inst not in SUPPORTED_INSTRUMENTS:
            errors.append(f"Unsupported instrument: {inst}. Supported: {', '.join(sorted(SUPPORTED_INSTRUMENTS))}")
        elif provider_symbol(inst) is None:
            errors.append(f"Market data unavailable for {inst} from the configured provider. Choose a supported NSE/BSE instrument with provider coverage.")
    
    # Validate timeframe
    if spec.timeframe not in SUPPORTED_TIMEFRAMES:
        errors.append(f"Unsupported timeframe: {spec.timeframe}. Supported: {', '.join(SUPPORTED_TIMEFRAMES)}")
    
    # Basic structural validation
    if not spec.instruments: errors.append("No instruments selected.")
    if not spec.entry_rules: errors.append("Strategy has no entry rule.")
    if not spec.exit_rules and not spec.risk.stop_loss_pct: errors.append("Need an exit rule or a stop-loss.")
    
    # Validate indicator references in rules
    for r in spec.entry_rules + spec.exit_rules:
        for side in (r.left, r.right):
            if isinstance(side, str) and side not in ids:
                errors.append(f"Rule references unknown indicator '{side}'.")
    
    # Validate indicator types and parameters
    for ind in spec.indicators:
        if ind.type not in INDICATOR_TYPES:
            errors.append(f"Unsupported indicator type: {ind.type}. Supported: {', '.join(INDICATOR_TYPES)}")
            continue
        param_errors = _validate_indicator_params(ind)
        errors.extend(param_errors)
    
    # Validate fast/slow relationships
    errors.extend(_validate_fast_slow_relationships(spec))
    
    # Risk limits validation
    if spec.risk.max_position_pct > 50:
        warnings.append("Position size above 50% of equity is aggressive.")
    if spec.risk.stop_loss_pct and (spec.risk.stop_loss_pct <= 0 or spec.risk.stop_loss_pct > 100):
        errors.append("Stop-loss percentage must be between 0 and 100.")
    if spec.risk.take_profit_pct and (spec.risk.take_profit_pct <= 0 or spec.risk.take_profit_pct > 1000):
        errors.append("Take-profit percentage must be between 0 and 1000.")
    if spec.risk.max_drawdown_pct <= 0 or spec.risk.max_drawdown_pct > 100:
        errors.append("Max drawdown percentage must be between 0 and 100.")
    
    # Validate date range
    errors.extend(_validate_date_range(start_date, end_date))
    
    # Data availability check
    if bars_count is not None:
        errors.extend(_check_data_availability(spec, bars_count))
    
    # Metrics-based validation
    if metrics:
        if metrics.get("trades", 0) < 5:
            errors.append(f"Only {metrics['trades']} backtest trades — too few to trust (min 5).")
        if abs(metrics.get("max_drawdown_pct", 0)) > spec.risk.max_drawdown_pct:
            errors.append(f"Backtest drawdown {metrics['max_drawdown_pct']}% exceeds your limit of {spec.risk.max_drawdown_pct}%.")
    else:
        errors.append("Run a backtest before deployment.")
    
    return {"passed": not errors, "errors": errors, "warnings": warnings}
