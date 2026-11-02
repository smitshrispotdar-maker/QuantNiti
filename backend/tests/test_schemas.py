"""Tests for Pydantic schemas (StrategySpec and related models)."""
import pytest
from pydantic import ValidationError

from app.schemas import (
    StrategySpec,
    IndicatorSpec,
    Rule,
    RiskLimits,
    ChatIn,
    StrategyIn,
    BacktestIn,
    OrderIn,
    AccountIn,
    DeployIn,
    JournalIn,
    ReviewIn,
)


class TestIndicatorSpec:
    """Tests for IndicatorSpec model."""
    
    def test_valid_sma_indicator(self):
        ind = IndicatorSpec(id="sma_20", type="SMA", params={"period": 20})
        assert ind.id == "sma_20"
        assert ind.type == "SMA"
        assert ind.params == {"period": 20}
    
    def test_valid_ema_indicator(self):
        ind = IndicatorSpec(id="ema_50", type="EMA", params={"period": 50})
        assert ind.type == "EMA"
    
    def test_valid_rsi_indicator(self):
        ind = IndicatorSpec(id="rsi_14", type="RSI", params={"period": 14})
        assert ind.type == "RSI"
    
    def test_valid_macd_indicator(self):
        ind = IndicatorSpec(id="macd_12_26_9", type="MACD", params={"fast": 12, "slow": 26, "signal": 9})
        assert ind.type == "MACD"
        assert ind.params["fast"] == 12
    
    def test_valid_bbands_indicator(self):
        ind = IndicatorSpec(id="bb_20_2", type="BBANDS", params={"period": 20, "k": 2})
        assert ind.type == "BBANDS"
        assert ind.params["k"] == 2
    
    def test_invalid_indicator_type(self):
        with pytest.raises(ValidationError):
            IndicatorSpec(id="test", type="INVALID", params={})
    
    def test_invalid_id_format(self):
        with pytest.raises(ValidationError):
            IndicatorSpec(id="SMA 20", type="SMA", params={"period": 20})  # spaces not allowed
    
    def test_empty_params_allowed(self):
        ind = IndicatorSpec(id="sma_20", type="SMA", params={})
        assert ind.params == {}


class TestRule:
    """Tests for Rule model."""
    
    def test_valid_rule_greater_than(self):
        rule = Rule(left="price", op=">", right="ema_20")
        assert rule.left == "price"
        assert rule.op == ">"
        assert rule.right == "ema_20"
    
    def test_valid_rule_crosses_above(self):
        rule = Rule(left="ema_20", op="crosses_above", right="ema_50")
        assert rule.op == "crosses_above"
    
    def test_valid_rule_with_numeric_right(self):
        rule = Rule(left="rsi_14", op="<", right=30)
        assert rule.right == 30
    
    def test_invalid_operator(self):
        with pytest.raises(ValidationError):
            Rule(left="price", op=">=", right="ema_20")


class TestRiskLimits:
    """Tests for RiskLimits model."""
    
    def test_default_risk_limits(self):
        risk = RiskLimits()
        assert risk.max_position_pct == 25
        assert risk.stop_loss_pct == 5
        assert risk.take_profit_pct is None
        assert risk.max_drawdown_pct == 25
    
    def test_custom_risk_limits(self):
        risk = RiskLimits(
            max_position_pct=50,
            stop_loss_pct=3,
            take_profit_pct=15,
            max_drawdown_pct=15,
        )
        assert risk.max_position_pct == 50
        assert risk.stop_loss_pct == 3
        assert risk.take_profit_pct == 15
        assert risk.max_drawdown_pct == 15
    
    def test_max_position_pct_validation(self):
        with pytest.raises(ValidationError):
            RiskLimits(max_position_pct=0)  # must be > 0
        
        with pytest.raises(ValidationError):
            RiskLimits(max_position_pct=101)  # must be <= 100
    
    def test_stop_loss_validation(self):
        with pytest.raises(ValidationError):
            RiskLimits(stop_loss_pct=0)  # must be > 0
        
        with pytest.raises(ValidationError):
            RiskLimits(stop_loss_pct=51)  # must be <= 50
    
    def test_take_profit_validation(self):
        with pytest.raises(ValidationError):
            RiskLimits(take_profit_pct=0)
        
        with pytest.raises(ValidationError):
            RiskLimits(take_profit_pct=501)  # must be <= 500
    
    def test_max_drawdown_validation(self):
        with pytest.raises(ValidationError):
            RiskLimits(max_drawdown_pct=0)
        
        with pytest.raises(ValidationError):
            RiskLimits(max_drawdown_pct=101)


class TestStrategySpec:
    """Tests for StrategySpec model (canonical schema)."""
    
    def test_minimal_valid_spec(self):
        spec = StrategySpec(
            name="Minimal",
            instruments=["BTC-USD"],
            timeframe="1d",
        )
        assert spec.name == "Minimal"
        assert spec.instruments == ["BTC-USD"]
        assert spec.timeframe == "1d"
        assert spec.indicators == []
        assert spec.entry_rules == []
        assert spec.exit_rules == []
        assert spec.schema_version == "1.0"
    
    def test_full_valid_spec(self, sample_strategy_spec):
        assert sample_strategy_spec.name == "Test Strategy"
        assert len(sample_strategy_spec.indicators) == 2
        assert len(sample_strategy_spec.entry_rules) == 1
        assert len(sample_strategy_spec.exit_rules) == 1
        assert sample_strategy_spec.risk.max_position_pct == 25
    
    def test_instrument_uppercase_conversion(self):
        spec = StrategySpec(instruments=["btc-usd", "eth-usd"])
        assert spec.instruments == ["BTC-USD", "ETH-USD"]
    
    def test_empty_instruments_allowed(self):
        spec = StrategySpec(instruments=[])
        assert spec.instruments == []
    
    def test_invalid_timeframe(self):
        with pytest.raises(ValidationError):
            StrategySpec(timeframe="1w")  # not in allowed list
    
    def test_valid_timeframes(self):
        for tf in ["1m", "5m", "15m", "1h", "1d"]:
            spec = StrategySpec(timeframe=tf)
            assert spec.timeframe == tf
    
    def test_rule_references_validated_by_consumer(self):
        """Note: StrategySpec doesn't validate rule references internally.
        Validation is done by validation.py service."""
        spec = StrategySpec(
            instruments=["BTC-USD"],
            indicators=[IndicatorSpec(id="ema_20", type="EMA", params={"period": 20})],
            entry_rules=[Rule(left="ema_20", op=">", right="price")],
            exit_rules=[Rule(left="nonexistent", op="<", right="price")],  # invalid ref
        )
        # Schema allows this; validation service catches it
        assert spec.exit_rules[0].left == "nonexistent"


class TestRequestDTOs:
    """Tests for request/response DTOs."""
    
    def test_chat_in(self):
        chat = ChatIn(message="Buy BTC", conversation_id=1)
        assert chat.message == "Buy BTC"
        assert chat.conversation_id == 1
    
    def test_chat_in_optional_conversation(self):
        chat = ChatIn(message="Hello")
        assert chat.conversation_id is None
    
    def test_strategy_in(self, sample_strategy_spec):
        strategy_in = StrategyIn(spec=sample_strategy_spec)
        assert strategy_in.spec == sample_strategy_spec
    
    def test_backtest_in(self):
        bt = BacktestIn(strategy_id=1, bars=500, initial_cash=50000)
        assert bt.strategy_id == 1
        assert bt.bars == 500
        assert bt.initial_cash == 50000
    
    def test_backtest_in_defaults(self):
        bt = BacktestIn(strategy_id=1)
        assert bt.bars == 500
        assert bt.initial_cash == 100_000
    
    def test_order_in(self):
        order = OrderIn(symbol="BTC-USD", side="BUY", qty=0.5)
        assert order.symbol == "BTC-USD"
        assert order.side == "BUY"
        assert order.qty == 0.5
    
    def test_order_in_invalid_side(self):
        with pytest.raises(ValidationError):
            OrderIn(symbol="BTC-USD", side="HOLD", qty=1)
    
    def test_order_in_qty_positive(self):
        with pytest.raises(ValidationError):
            OrderIn(symbol="BTC-USD", side="BUY", qty=0)
        
        with pytest.raises(ValidationError):
            OrderIn(symbol="BTC-USD", side="BUY", qty=-1)
    
    def test_account_in(self):
        account = AccountIn(name="Test Account", starting_cash=25000)
        assert account.name == "Test Account"
        assert account.starting_cash == 25000
    
    def test_account_in_defaults(self):
        account = AccountIn()
        assert account.name == "Paper account"
        assert account.starting_cash == 100_000
    
    def test_deploy_in(self):
        deploy = DeployIn(strategy_id=5)
        assert deploy.strategy_id == 5
    
    def test_journal_in(self):
        journal = JournalIn(strategy_id=1, recommendation="Buy", evidence={"rsi": 25})
        assert journal.strategy_id == 1
        assert journal.recommendation == "Buy"
        assert journal.evidence == {"rsi": 25}
    
    def test_journal_in_optional_strategy(self):
        journal = JournalIn(recommendation="Note")
        assert journal.strategy_id is None
    
    def test_review_in(self):
        review = ReviewIn(outcome_review="Profitable")
        assert review.outcome_review == "Profitable"