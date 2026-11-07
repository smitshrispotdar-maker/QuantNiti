"""Tests for the NLP parser (services/nlp.py)."""
import pytest

from app.services.nlp import parse, detect_action
from app.schemas import StrategySpec, IndicatorSpec, Rule, RiskLimits


class TestNLPParser:
    """Tests for the rule-based NLP parser."""
    
    def test_parse_basic_buy(self):
        spec, asks = parse("Buy NIFTY 50")
        assert spec.instruments == ["^NSEI"]
        assert len(asks) > 0  # Should ask for entry/exit details
    
    def test_parse_ema_crossover(self):
        text = "Buy NIFTY 50 when EMA 20 crosses above EMA 50, exit on cross below"
        spec, asks = parse(text)
        
        assert spec.instruments == ["^NSEI"]
        assert len(spec.indicators) == 2
        indicator_ids = {i.id for i in spec.indicators}
        assert "ema_20" in indicator_ids
        assert "ema_50" in indicator_ids
        
        assert len(spec.entry_rules) == 1
        assert spec.entry_rules[0].left == "ema_20"
        assert spec.entry_rules[0].op == "crosses_above"
        assert spec.entry_rules[0].right == "ema_50"
        
        assert len(spec.exit_rules) == 1
        assert spec.exit_rules[0].op == "crosses_below"
    
    def test_parse_sma_crossover(self):
        text = "Buy when SMA 10 crosses above SMA 30"
        spec, asks = parse(text)
        
        indicator_ids = {i.id for i in spec.indicators}
        assert "sma_10" in indicator_ids
        assert "sma_30" in indicator_ids
    
    def test_parse_rsi_below(self):
        text = "Buy NIFTY 50 when RSI is below 30"
        spec, asks = parse(text)
        
        assert spec.instruments == ["^NSEI"]
        rsi_indicators = [i for i in spec.indicators if i.type == "RSI"]
        assert len(rsi_indicators) == 1
        assert rsi_indicators[0].params["period"] == 14  # default
        
        assert len(spec.entry_rules) == 1
        assert spec.entry_rules[0].left == "rsi_14"
        assert spec.entry_rules[0].op == "<"
        assert spec.entry_rules[0].right == 30
    
    def test_parse_rsi_above(self):
        text = "Sell when RSI above 70"
        spec, asks = parse(text)
        
        rsi_indicators = [i for i in spec.indicators if i.type == "RSI"]
        assert len(rsi_indicators) == 1
        
        assert len(spec.exit_rules) == 1
        assert spec.exit_rules[0].left == "rsi_14"
        assert spec.exit_rules[0].op == ">"
        assert spec.exit_rules[0].right == 70
    
    def test_parse_rsi_custom_period(self):
        text = "Buy when RSI(10) below 25"
        spec, asks = parse(text)
        
        rsi_indicators = [i for i in spec.indicators if i.type == "RSI"]
        assert rsi_indicators[0].params["period"] == 10
        assert rsi_indicators[0].id == "rsi_10"
    
    def test_parse_stop_loss(self):
        text = "Buy NIFTY 50, stop loss 5%"
        spec, asks = parse(text)
        
        assert spec.risk.stop_loss_pct == 5
    
    def test_parse_stop_loss_alternative_format(self):
        text = "Buy NIFTY 50 with 3% stop"
        spec, asks = parse(text)
        
        assert spec.risk.stop_loss_pct == 3
    
    def test_parse_take_profit(self):
        text = "Buy NIFTY 50, take profit 10%"
        spec, asks = parse(text)
        
        assert spec.risk.take_profit_pct == 10
    
    def test_parse_position_size(self):
        text = "Buy NIFTY 50 with position size 50%"
        spec, asks = parse(text)
        
        assert spec.risk.max_position_pct == 50
    
    def test_parse_risk_alternative_format(self):
        text = "Buy NIFTY 50 risk 25%"
        spec, asks = parse(text)
        
        assert spec.risk.max_position_pct == 25
    
    def test_parse_timeframe_daily(self):
        text = "Buy NIFTY 50 daily"
        spec, asks = parse(text)
        
        assert spec.timeframe == "1d"
    
    def test_parse_timeframe_hourly(self):
        text = "Buy NIFTY 50 hourly"
        spec, asks = parse(text)
        
        assert spec.timeframe == "1h"
    
    def test_parse_timeframe_15m(self):
        text = "Buy NIFTY 50 15m"
        spec, asks = parse(text)
        
        assert spec.timeframe == "15m"
    
    def test_parse_multiple_instruments(self):
        text = "Buy NIFTY 50 and BANK NIFTY"
        spec, asks = parse(text)
        
        assert set(spec.instruments) == {"^NSEI", "^NSEBANK"}
    
    def test_parse_apple_stock(self):
        text = "Buy RELIANCE"
        spec, asks = parse(text)
        
        assert spec.instruments == ["RELIANCE.NS"]
    
    def test_parse_spy(self):
        text = "Buy TCS"
        spec, asks = parse(text)
        
        assert spec.instruments == ["TCS.NS"]
    
    def test_parse_combined_strategy(self):
        text = "Buy NIFTY 50 when EMA 20 crosses above EMA 50, stop loss 5%, take profit 10%, size 30%"
        spec, asks = parse(text)
        
        assert spec.instruments == ["^NSEI"]
        assert len(spec.indicators) == 2
        assert spec.risk.stop_loss_pct == 5
        assert spec.risk.take_profit_pct == 10
        assert spec.risk.max_position_pct == 30
        assert len(spec.entry_rules) == 1
        assert len(spec.exit_rules) == 1
    
    def test_parse_with_base_spec(self):
        """Test parsing with an existing base spec (conversation continuation)."""
        base = StrategySpec(
            instruments=["^NSEI"],
            indicators=[IndicatorSpec(id="ema_20", type="EMA", params={"period": 20})],
            entry_rules=[Rule(left="ema_20", op=">", right="price")],
        )
        spec, asks = parse("add stop loss 3%", base=base)
        
        # Should preserve base and add stop loss
        assert spec.instruments == ["^NSEI"]
        assert len(spec.indicators) == 1
        assert spec.risk.stop_loss_pct == 3
        assert len(spec.entry_rules) == 1
    
    def test_parse_clarifications_missing_instrument(self):
        spec, asks = parse("Buy when RSI below 30")
        
        assert "instrument" in " ".join(asks).lower()
    
    def test_parse_clarifications_missing_entry(self):
        spec, asks = parse("Buy NIFTY 50")
        
        assert any("entry" in a.lower() for a in asks)
    
    def test_parse_clarifications_missing_exit(self):
        spec, asks = parse("Buy NIFTY 50 when EMA 20 crosses above EMA 50")
        
        # Has entry but no explicit exit (only crossover exit)
        # The parser adds symmetric exit for crossovers
        assert len(spec.exit_rules) == 1
    
    def test_parse_clarifications_long_and_short(self):
        spec, asks = parse("Buy NIFTY 50 and short BANK NIFTY")
        
        assert any("long and short" in a.lower() or "short" in a.lower() for a in asks)
    
    def test_parse_rsi_sell_when_low_clarification(self):
        # The regex expects "rsi...below/under...sell/exit" pattern
        # "rsi below 30 sell" matches: rsi -> below -> sell
        spec, asks = parse("RSI below 30 sell")
        
        # Should warn that selling on low RSI is counter-intuitive
        assert any("sell" in a.lower() and "rsi" in a.lower() and ("low" in a.lower() or "below" in a.lower()) for a in asks)
    
    def test_parse_case_insensitive(self):
        spec1, _ = parse("BUY NIFTY 50")
        spec2, _ = parse("buy nifty 50")
        spec3, _ = parse("Buy Nifty 50")
        
        assert spec1.instruments == spec2.instruments == spec3.instruments == ["^NSEI"]
    
    def test_parse_extra_whitespace(self):
        spec, _ = parse("  Buy   NIFTY 50  when  EMA 20  crosses  above  EMA 50  ")
        
        assert spec.instruments == ["^NSEI"]
        assert len(spec.indicators) == 2
    
    def test_parse_ethereum_alias(self):
        spec, _ = parse("Buy BANK NIFTY")
        
        assert spec.instruments == ["^NSEBANK"]
    
    def test_parse_bitcoin_alias(self):
        spec, _ = parse("Buy NIFTY 50")
        
        assert spec.instruments == ["^NSEI"]


class TestNLPEdgeCases:
    """Edge cases for NLP parser."""
    
    def test_parse_empty_string(self):
        spec, asks = parse("")
        
        assert spec.instruments == []
        assert len(asks) > 0
    
    def test_parse_unknown_ticker(self):
        spec, asks = parse("Buy XYZCOIN")
        
        # Unknown ticker not added, should ask for instrument
        assert "XYZCOIN" not in spec.instruments
        assert any("instrument" in a.lower() for a in asks)
    
    def test_parse_no_matches(self):
        spec, asks = parse("Hello world")
        
        assert spec.instruments == []
        # stop_loss_pct has default 5, so exit clarification not generated
        assert len(asks) >= 2  # instrument, entry
    
    def test_parse_duplicate_indicators(self):
        """Same indicator mentioned twice should not duplicate."""
        text = "Buy NIFTY 50 when EMA 20 crosses above EMA 50 and EMA 20 crosses above EMA 50"
        spec, _ = parse(text)
        
        ema_20_count = sum(1 for i in spec.indicators if i.id == "ema_20")
        assert ema_20_count == 1
    
    def test_parse_rsi_with_parentheses(self):
        text = "Buy when RSI(14) < 30"
        spec, _ = parse(text)
        
        rsi_ind = [i for i in spec.indicators if i.type == "RSI"]
        assert rsi_ind[0].params["period"] == 14
    
    def test_parse_decimal_percentages(self):
        text = "Buy NIFTY 50 stop loss 2.5% take profit 7.5% size 12.5%"
        spec, _ = parse(text)
        
        assert spec.risk.stop_loss_pct == 2.5
        assert spec.risk.take_profit_pct == 7.5
        assert spec.risk.max_position_pct == 12.5


class TestActionDetection:
    """Tests for action detection in natural language."""
    
    def test_detect_backtest_action(self):
        """Test detection of backtest requests."""
        for text in ["run backtest", "backtest this", "test strategy", "simulate", "back test"]:
            action, _ = detect_action(text)
            assert action == "backtest", f"Failed for: {text}"
    
    def test_detect_deploy_action(self):
        """Test detection of deploy/paper trade requests."""
        for text in ["deploy", "paper trade", "start paper", "go live", "activate strategy"]:
            action, _ = detect_action(text)
            assert action == "deploy", f"Failed for: {text}"
    
    def test_detect_explain_action(self):
        """Test detection of explain requests."""
        for text in ["explain", "what is this", "describe strategy", "summarize", "show me", "current strategy"]:
            action, _ = detect_action(text)
            assert action == "explain", f"Failed for: {text}"
    
    def test_no_action_for_regular_text(self):
        """Test that regular strategy text doesn't trigger actions."""
        for text in ["buy NIFTY 50 when RSI below 30", "EMA 20 crosses above EMA 50", "stop loss 5%"]:
            action, _ = detect_action(text)
            assert action is None, f"Unexpected action for: {text}"
    
    def test_case_insensitive_actions(self):
        """Test action detection is case insensitive."""
        for text in ["BACKTEST", "Deploy", "Explain"]:
            action, _ = detect_action(text)
            assert action is not None, f"Failed for: {text}"
    
    def test_action_in_sentence(self):
        """Test action detection within a sentence."""
        text = "Please run backtest on this strategy"
        action, _ = detect_action(text)
        assert action == "backtest"