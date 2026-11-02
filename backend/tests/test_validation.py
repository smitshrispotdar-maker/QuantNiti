"""Tests for the validation gate (services/validation.py)."""
import pytest

from app.services.validation import validate
from app.schemas import StrategySpec, IndicatorSpec, Rule, RiskLimits


class TestValidation:
    """Tests for the validation gate."""
    
    def test_valid_spec_passes_structural(self):
        spec = StrategySpec(
            name="Valid Strategy",
            instruments=["BTC-USD"],
            timeframe="1d",
            indicators=[
                IndicatorSpec(id="ema_20", type="EMA", params={"period": 20}),
                IndicatorSpec(id="ema_50", type="EMA", params={"period": 50}),
            ],
            entry_rules=[Rule(left="ema_20", op="crosses_above", right="ema_50")],
            exit_rules=[Rule(left="ema_20", op="crosses_below", right="ema_50")],
            risk=RiskLimits(max_position_pct=25, stop_loss_pct=5, max_drawdown_pct=20),
        )
        
        # Pass fake metrics for structural check (like router does)
        result = validate(spec, {"trades": 99, "max_drawdown_pct": 0})
        assert result["passed"] is True
        assert result["errors"] == []
    
    def test_no_instruments_fails(self):
        spec = StrategySpec(
            instruments=[],
            entry_rules=[Rule(left="price", op=">", right=100)],
        )
        
        result = validate(spec, {"trades": 99, "max_drawdown_pct": 0})
        assert result["passed"] is False
        assert "No instruments selected." in result["errors"]
    
    def test_no_entry_rules_fails(self):
        spec = StrategySpec(
            instruments=["BTC-USD"],
            entry_rules=[],
            exit_rules=[Rule(left="price", op="<", right=100)],
        )
        
        result = validate(spec, {"trades": 99, "max_drawdown_pct": 0})
        assert result["passed"] is False
        assert "Strategy has no entry rule." in result["errors"]
    
    def test_no_exit_rules_and_no_stop_loss_fails(self):
        spec = StrategySpec(
            instruments=["BTC-USD"],
            entry_rules=[Rule(left="price", op=">", right=100)],
            exit_rules=[],
            risk=RiskLimits(stop_loss_pct=None),
        )
        
        result = validate(spec, {"trades": 99, "max_drawdown_pct": 0})
        assert result["passed"] is False
        assert "Need an exit rule or a stop-loss." in result["errors"]
    
    def test_stop_loss_satisfies_exit_requirement(self):
        spec = StrategySpec(
            instruments=["BTC-USD"],
            entry_rules=[Rule(left="price", op=">", right=100)],
            exit_rules=[],
            risk=RiskLimits(stop_loss_pct=5),
        )
        
        result = validate(spec, {"trades": 99, "max_drawdown_pct": 0})
        # Should pass structural (has stop loss as exit mechanism)
        assert "Need an exit rule or a stop-loss" not in result["errors"]
    
    def test_take_profit_does_not_satisfy_exit_requirement(self):
        """Take profit alone is not considered an exit rule."""
        spec = StrategySpec(
            instruments=["BTC-USD"],
            entry_rules=[Rule(left="price", op=">", right=100)],
            exit_rules=[],
            risk=RiskLimits(take_profit_pct=10, stop_loss_pct=None),
        )
        
        result = validate(spec, {"trades": 99, "max_drawdown_pct": 0})
        assert result["passed"] is False
        assert "Need an exit rule or a stop-loss." in result["errors"]
    
    def test_invalid_indicator_reference_in_entry(self):
        spec = StrategySpec(
            instruments=["BTC-USD"],
            indicators=[IndicatorSpec(id="ema_20", type="EMA", params={"period": 20})],
            entry_rules=[Rule(left="nonexistent", op=">", right="price")],
            exit_rules=[Rule(left="ema_20", op="<", right="price")],
        )
        
        result = validate(spec, {"trades": 99, "max_drawdown_pct": 0})
        assert result["passed"] is False
        assert any("unknown indicator" in e.lower() for e in result["errors"])
    
    def test_invalid_indicator_reference_in_exit(self):
        spec = StrategySpec(
            instruments=["BTC-USD"],
            indicators=[IndicatorSpec(id="ema_20", type="EMA", params={"period": 20})],
            entry_rules=[Rule(left="ema_20", op=">", right="price")],
            exit_rules=[Rule(left="missing", op="<", right="price")],
        )
        
        result = validate(spec, {"trades": 99, "max_drawdown_pct": 0})
        assert result["passed"] is False
        assert any("unknown indicator" in e.lower() for e in result["errors"])
    
    def test_valid_price_reference(self):
        """Price is always a valid reference."""
        spec = StrategySpec(
            instruments=["BTC-USD"],
            indicators=[],
            entry_rules=[Rule(left="price", op=">", right=100)],
            exit_rules=[Rule(left="price", op="<", right=90)],
        )
        
        result = validate(spec, {"trades": 99, "max_drawdown_pct": 0})
        assert result["passed"] is True
    
    def test_valid_numeric_right_side(self):
        """Numeric right side is always valid."""
        spec = StrategySpec(
            instruments=["BTC-USD"],
            indicators=[IndicatorSpec(id="rsi_14", type="RSI", params={"period": 14})],
            entry_rules=[Rule(left="rsi_14", op="<", right=30)],
            exit_rules=[Rule(left="rsi_14", op=">", right=70)],
        )
        
        result = validate(spec, {"trades": 99, "max_drawdown_pct": 0})
        assert result["passed"] is True
    
    def test_aggressive_position_size_warning(self):
        spec = StrategySpec(
            instruments=["BTC-USD"],
            entry_rules=[Rule(left="price", op=">", right=100)],
            exit_rules=[Rule(left="price", op="<", right=90)],
            risk=RiskLimits(max_position_pct=75),
        )
        
        result = validate(spec, {"trades": 99, "max_drawdown_pct": 0})
        assert result["passed"] is True  # Warning, not error
        assert any("aggressive" in w.lower() for w in result["warnings"])
    
    def test_position_size_50_ok(self):
        """50% should not warn."""
        spec = StrategySpec(
            instruments=["BTC-USD"],
            entry_rules=[Rule(left="price", op=">", right=100)],
            exit_rules=[Rule(left="price", op="<", right=90)],
            risk=RiskLimits(max_position_pct=50),
        )
        
        result = validate(spec, {"trades": 99, "max_drawdown_pct": 0})
        assert not any("aggressive" in w.lower() for w in result["warnings"])
    
    def test_backtest_trades_too_few_fails(self):
        spec = StrategySpec(
            instruments=["BTC-USD"],
            entry_rules=[Rule(left="price", op=">", right=100)],
            exit_rules=[Rule(left="price", op="<", right=90)],
        )
        
        metrics = {"trades": 3, "max_drawdown_pct": 10}
        result = validate(spec, metrics)
        
        assert result["passed"] is False
        assert any("too few" in e.lower() for e in result["errors"])
    
    def test_backtest_trades_minimum_passes(self):
        spec = StrategySpec(
            instruments=["BTC-USD"],
            entry_rules=[Rule(left="price", op=">", right=100)],
            exit_rules=[Rule(left="price", op="<", right=90)],
        )
        
        metrics = {"trades": 5, "max_drawdown_pct": 10}
        result = validate(spec, metrics)
        
        assert not any("too few" in e.lower() for e in result["errors"])
    
    def test_backtest_max_drawdown_exceeds_limit_fails(self):
        spec = StrategySpec(
            instruments=["BTC-USD"],
            entry_rules=[Rule(left="price", op=">", right=100)],
            exit_rules=[Rule(left="price", op="<", right=90)],
            risk=RiskLimits(max_drawdown_pct=15),
        )
        
        metrics = {"trades": 10, "max_drawdown_pct": 25}
        result = validate(spec, metrics)
        
        assert result["passed"] is False
        assert any("exceeds your limit" in e.lower() for e in result["errors"])
    
    def test_backtest_max_drawdown_within_limit_passes(self):
        spec = StrategySpec(
            instruments=["BTC-USD"],
            entry_rules=[Rule(left="price", op=">", right=100)],
            exit_rules=[Rule(left="price", op="<", right=90)],
            risk=RiskLimits(max_drawdown_pct=25),
        )
        
        metrics = {"trades": 10, "max_drawdown_pct": 15}
        result = validate(spec, metrics)
        
        assert not any("exceeds your limit" in e.lower() for e in result["errors"])
    
    def test_no_metrics_requires_backtest_error(self):
        spec = StrategySpec(
            instruments=["BTC-USD"],
            entry_rules=[Rule(left="price", op=">", right=100)],
            exit_rules=[Rule(left="price", op="<", right=90)],
        )
        
        result = validate(spec, metrics=None)
        
        assert result["passed"] is False
        assert "Run a backtest before deployment." in result["errors"]
    
    def test_structural_errors_checked_first(self):
        """Structural errors should be caught even without metrics."""
        spec = StrategySpec(
            instruments=[],  # Structural error
            entry_rules=[],  # Structural error
            exit_rules=[],
            risk=RiskLimits(stop_loss_pct=None),
        )
        
        # Even with perfect metrics, structural errors should fail
        metrics = {"trades": 100, "max_drawdown_pct": 1}
        result = validate(spec, metrics)
        
        assert result["passed"] is False
        assert "No instruments selected." in result["errors"]
        assert "Strategy has no entry rule." in result["errors"]
    
    def test_multiple_errors_reported(self):
        spec = StrategySpec(
            instruments=[],
            entry_rules=[],
            exit_rules=[],
            risk=RiskLimits(stop_loss_pct=None, max_position_pct=80),
        )
        
        result = validate(spec)
        
        assert result["passed"] is False
        assert len(result["errors"]) >= 3  # instruments, entry, exit
        assert any("aggressive" in w.lower() for w in result["warnings"])
    
    def test_warnings_not_blocking(self):
        spec = StrategySpec(
            instruments=["BTC-USD"],
            entry_rules=[Rule(left="price", op=">", right=100)],
            exit_rules=[Rule(left="price", op="<", right=90)],
            risk=RiskLimits(max_position_pct=75),  # Warning only
        )
        
        result = validate(spec, {"trades": 99, "max_drawdown_pct": 0})
        
        assert result["passed"] is True  # Warnings don't block
        assert len(result["warnings"]) > 0


class TestValidationIntegration:
    """Integration tests with realistic scenarios."""
    
    def test_ema_crossover_strategy_valid(self):
        spec = StrategySpec(
            name="EMA Crossover",
            instruments=["BTC-USD"],
            timeframe="1d",
            indicators=[
                IndicatorSpec(id="ema_20", type="EMA", params={"period": 20}),
                IndicatorSpec(id="ema_50", type="EMA", params={"period": 50}),
            ],
            entry_rules=[Rule(left="ema_20", op="crosses_above", right="ema_50")],
            exit_rules=[Rule(left="ema_20", op="crosses_below", right="ema_50")],
            risk=RiskLimits(max_position_pct=25, stop_loss_pct=5, max_drawdown_pct=20),
        )
        
        # Structural validation
        result = validate(spec, {"trades": 99, "max_drawdown_pct": 0})
        assert result["passed"] is True
        
        # With good metrics
        metrics = {"trades": 15, "max_drawdown_pct": 12}
        result = validate(spec, metrics)
        assert result["passed"] is True
    
    def test_rsi_mean_reversion_strategy_valid(self):
        spec = StrategySpec(
            name="RSI Mean Reversion",
            instruments=["BTC-USD"],
            timeframe="1h",
            indicators=[
                IndicatorSpec(id="rsi_14", type="RSI", params={"period": 14}),
            ],
            entry_rules=[Rule(left="rsi_14", op="<", right=30)],
            exit_rules=[Rule(left="rsi_14", op=">", right=70)],
            risk=RiskLimits(max_position_pct=20, stop_loss_pct=3, max_drawdown_pct=15),
        )
        
        result = validate(spec, {"trades": 99, "max_drawdown_pct": 0})
        assert result["passed"] is True
        
        metrics = {"trades": 25, "max_drawdown_pct": 10}
        result = validate(spec, metrics)
        assert result["passed"] is True
    
    def test_macd_strategy_valid(self):
        spec = StrategySpec(
            name="MACD Strategy",
            instruments=["BTC-USD"],
            indicators=[
                IndicatorSpec(id="macd", type="MACD", params={"fast": 12, "slow": 26, "signal": 9}),
            ],
            entry_rules=[Rule(left="macd", op="crosses_above", right=0)],
            exit_rules=[Rule(left="macd", op="crosses_below", right=0)],
            risk=RiskLimits(max_position_pct=30, stop_loss_pct=4, max_drawdown_pct=25),
        )
        
        result = validate(spec, {"trades": 99, "max_drawdown_pct": 0})
        assert result["passed"] is True
    
    def test_bbands_strategy_valid(self):
        # Note: validation only knows indicator IDs, not extra columns like _upper/_lower
        # So we use the middle band (bb_20) for rules
        spec = StrategySpec(
            name="Bollinger Bands",
            instruments=["BTC-USD"],
            indicators=[
                IndicatorSpec(id="bb_20", type="BBANDS", params={"period": 20, "k": 2}),
            ],
            entry_rules=[Rule(left="price", op="<", right="bb_20")],
            exit_rules=[Rule(left="price", op=">", right="bb_20")],
            risk=RiskLimits(max_position_pct=25, stop_loss_pct=5, max_drawdown_pct=20),
        )
        
        result = validate(spec, {"trades": 99, "max_drawdown_pct": 0})
        assert result["passed"] is True
    
    def test_strategy_without_exit_rule_but_with_stop_loss(self):
        """Strategy with only stop loss (no exit rules) should pass structural."""
        spec = StrategySpec(
            instruments=["BTC-USD"],
            indicators=[
                IndicatorSpec(id="ema_20", type="EMA", params={"period": 20}),
            ],
            entry_rules=[Rule(left="price", op=">", right="ema_20")],
            exit_rules=[],  # No exit rules
            risk=RiskLimits(stop_loss_pct=5, max_position_pct=25, max_drawdown_pct=20),
        )
        
        result = validate(spec, {"trades": 99, "max_drawdown_pct": 0})
        assert result["passed"] is True
    
    def test_complex_multi_rule_strategy(self):
        """Test strategy with multiple entry/exit rules."""
        spec = StrategySpec(
            instruments=["BTC-USD"],
            indicators=[
                IndicatorSpec(id="ema_20", type="EMA", params={"period": 20}),
                IndicatorSpec(id="ema_50", type="EMA", params={"period": 50}),
                IndicatorSpec(id="rsi_14", type="RSI", params={"period": 14}),
            ],
            entry_rules=[
                Rule(left="ema_20", op="crosses_above", right="ema_50"),
                Rule(left="rsi_14", op="<", right=60),
            ],
            exit_rules=[
                Rule(left="ema_20", op="crosses_below", right="ema_50"),
                Rule(left="rsi_14", op=">", right=75),
            ],
            risk=RiskLimits(max_position_pct=30, stop_loss_pct=4, max_drawdown_pct=20),
        )
        
        result = validate(spec, {"trades": 99, "max_drawdown_pct": 0})
        assert result["passed"] is True


class TestEnhancedValidation:
    """Tests for enhanced validation features added in Phase 4 continuation."""
    
    def test_invalid_indicator_type_rejected(self):
        """Unsupported indicator types should be rejected by schema."""
        # This is caught at schema level - test passes if it raises
        with pytest.raises(Exception):
            StrategySpec(
                instruments=["BTC-USD"],
                indicators=[IndicatorSpec(id="custom", type="CUSTOM", params={"period": 10})],
                entry_rules=[Rule(left="custom", op=">", right="price")],
                exit_rules=[Rule(left="price", op="<", right=100)],
            )
    
    def test_indicator_param_out_of_range_rejected(self):
        """Indicator parameters outside valid ranges should be rejected by our validation."""
        # Schema allows period up to 500 for EMA, so test with 600 which passes schema but fails our validation
        spec = StrategySpec(
            instruments=["BTC-USD"],
            indicators=[IndicatorSpec(id="ema_20", type="EMA", params={"period": 600})],  # > 500 (our limit)
            entry_rules=[Rule(left="ema_20", op=">", right="price")],
            exit_rules=[Rule(left="price", op="<", right=100)],
        )
        
        result = validate(spec, {"trades": 99, "max_drawdown_pct": 0})
        assert result["passed"] is False
        assert any("must be between" in e for e in result["errors"])
    
    def test_indicator_unknown_param_rejected(self):
        """Unknown indicator parameters should be rejected by our validation."""
        spec = StrategySpec(
            instruments=["BTC-USD"],
            indicators=[IndicatorSpec(id="ema_20", type="EMA", params={"unknown_param": 20})],
            entry_rules=[Rule(left="ema_20", op=">", right="price")],
            exit_rules=[Rule(left="price", op="<", right=100)],
        )
        
        result = validate(spec, {"trades": 99, "max_drawdown_pct": 0})
        assert result["passed"] is False
        assert any("unknown parameter" in e for e in result["errors"])
    
    def test_unsupported_instrument_rejected(self):
        """Unsupported instruments should be rejected by our validation."""
        spec = StrategySpec(
            instruments=["INVALID-SYM"],
            entry_rules=[Rule(left="price", op=">", right=100)],
            exit_rules=[Rule(left="price", op="<", right=90)],
        )
        
        result = validate(spec, {"trades": 99, "max_drawdown_pct": 0})
        assert result["passed"] is False
        assert any("Unsupported instrument" in e for e in result["errors"])
    
    def test_unsupported_timeframe_rejected(self):
        """Unsupported timeframes should be rejected by schema."""
        with pytest.raises(Exception):
            StrategySpec(
                instruments=["BTC-USD"],
                timeframe="1w",  # Not supported
                entry_rules=[Rule(left="price", op=">", right=100)],
                exit_rules=[Rule(left="price", op="<", right=90)],
            )
    
    def test_invalid_stop_loss_range_rejected(self):
        """Stop loss outside 0-50% should be rejected by schema."""
        with pytest.raises(Exception):
            RiskLimits(stop_loss_pct=150)
    
    def test_invalid_take_profit_range_rejected(self):
        """Take profit outside 0-500% should be rejected by schema."""
        with pytest.raises(Exception):
            RiskLimits(take_profit_pct=2000)
    
    def test_invalid_max_drawdown_range_rejected(self):
        """Max drawdown outside 0-100% should be rejected by schema."""
        with pytest.raises(Exception):
            RiskLimits(max_drawdown_pct=150)
    
    def test_invalid_date_range_rejected(self):
        """Invalid date range (start >= end) should be rejected by our validation."""
        spec = StrategySpec(
            instruments=["BTC-USD"],
            entry_rules=[Rule(left="price", op=">", right=100)],
            exit_rules=[Rule(left="price", op="<", right=90)],
        )
        
        result = validate(spec, {"trades": 99, "max_drawdown_pct": 0}, 
                         start_date="2024-01-10", end_date="2024-01-01")
        assert result["passed"] is False
        assert any("start_date must be before end_date" in e for e in result["errors"])
    
    def test_valid_date_range_accepted(self):
        """Valid date range should be accepted."""
        spec = StrategySpec(
            instruments=["BTC-USD"],
            entry_rules=[Rule(left="price", op=">", right=100)],
            exit_rules=[Rule(left="price", op="<", right=90)],
        )
        
        result = validate(spec, {"trades": 99, "max_drawdown_pct": 0}, 
                         start_date="2024-01-01", end_date="2024-12-31")
        assert result["passed"] is True
    
    def test_insufficient_bars_for_timeframe_rejected(self):
        """Insufficient bars for timeframe should be rejected by our validation."""
        spec = StrategySpec(
            instruments=["BTC-USD"],
            timeframe="1d",
            entry_rules=[Rule(left="price", op=">", right=100)],
            exit_rules=[Rule(left="price", op="<", right=90)],
        )
        
        # Only 10 bars for 1d timeframe (needs 30)
        result = validate(spec, {"trades": 99, "max_drawdown_pct": 0}, bars_count=10)
        assert result["passed"] is False
        assert any("Insufficient data" in e for e in result["errors"])
    
    def test_insufficient_bars_for_indicator_rejected(self):
        """Insufficient bars for indicator initialization should be rejected."""
        spec = StrategySpec(
            instruments=["BTC-USD"],
            timeframe="1d",
            indicators=[IndicatorSpec(id="ema_200", type="EMA", params={"period": 200})],
            entry_rules=[Rule(left="ema_200", op=">", right="price")],
            exit_rules=[Rule(left="price", op="<", right=90)],
        )
        
        # 100 bars but EMA(200) needs 200
        result = validate(spec, {"trades": 99, "max_drawdown_pct": 0}, bars_count=100)
        assert result["passed"] is False
        assert any("Insufficient data" in e for e in result["errors"])
    
    def test_sufficient_bars_for_indicator_accepted(self):
        """Sufficient bars for indicator should be accepted."""
        spec = StrategySpec(
            instruments=["BTC-USD"],
            timeframe="1d",
            indicators=[IndicatorSpec(id="ema_20", type="EMA", params={"period": 20})],
            entry_rules=[Rule(left="ema_20", op=">", right="price")],
            exit_rules=[Rule(left="price", op="<", right=90)],
        )
        
        # 50 bars for EMA(20) - should be enough
        result = validate(spec, {"trades": 99, "max_drawdown_pct": 0}, bars_count=50)
        assert result["passed"] is True
    
    def test_macd_insufficient_bars_rejected(self):
        """MACD with slow+signal periods needs enough bars."""
        spec = StrategySpec(
            instruments=["BTC-USD"],
            timeframe="1d",
            indicators=[IndicatorSpec(id="macd", type="MACD", params={"fast": 12, "slow": 26, "signal": 9})],
            entry_rules=[Rule(left="macd", op="crosses_above", right=0)],
            exit_rules=[Rule(left="macd", op="crosses_below", right=0)],
        )
        
        # MACD needs slow + signal = 26 + 9 = 35 bars minimum
        result = validate(spec, {"trades": 99, "max_drawdown_pct": 0}, bars_count=30)
        assert result["passed"] is False
        assert any("Insufficient data" in e for e in result["errors"])
    
    def test_multi_instrument_rejected(self):
        """Multi-instrument strategies not yet supported."""
        spec = StrategySpec(
            instruments=["BTC-USD", "ETH-USD"],
            entry_rules=[Rule(left="price", op=">", right=100)],
            exit_rules=[Rule(left="price", op="<", right=90)],
        )
        
        result = validate(spec, {"trades": 99, "max_drawdown_pct": 0})
        assert result["passed"] is False
        assert any("Multi-instrument" in e for e in result["errors"])