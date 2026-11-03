"""Strategy Lineage Service.

Builds lineage/timeline from conversations → strategies → backtests → research → journal → deployments.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from ..models import (
    Conversation, Strategy, BacktestRun, ResearchRun, JournalEntry, PaperDeployment
)
from ..schemas import StrategySpec


class LineageEvent:
    """Represents a single event in the strategy lineage timeline."""
    def __init__(self, event_type: str, timestamp: datetime, title: str, 
                 details: Dict[str, Any], entity_id: Optional[int] = None,
                 entity_type: Optional[str] = None):
        self.event_type = event_type  # conversation, strategy, backtest, research, journal, deployment
        self.timestamp = timestamp
        self.title = title
        self.details = details
        self.entity_id = entity_id
        self.entity_type = entity_type

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "title": self.title,
            "details": self.details,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
        }


def build_lineage(
    db: Session,
    strategy_id: Optional[int] = None,
    conversation_id: Optional[int] = None,
    user_id: int = 1,
) -> List[Dict[str, Any]]:
    """
    Build a complete lineage timeline for a strategy or conversation.
    
    Returns a list of events sorted chronologically.
    """
    events = []
    
    # Determine the strategy/conversation to trace
    strategy = None
    conversation = None
    
    if conversation_id:
        conversation = db.get(Conversation, conversation_id)
        if conversation and conversation.user_id != user_id:
            return []  # Not authorized
    elif strategy_id:
        strategy = db.query(Strategy).filter_by(id=strategy_id, user_id=user_id).first()
    else:
        # Get latest strategy for user
        strategy = db.query(Strategy).filter_by(user_id=user_id).order_by(Strategy.id.desc()).first()
    
    if not strategy and not conversation:
        return []
    
    # If we have a conversation but no strategy, try to get strategy from draft_spec
    if conversation and not strategy:
        if conversation.draft_spec:
            # Try to find a strategy with matching spec
            pass  # Strategy matching would be complex, skip for now
    
    # If we have a strategy but no conversation, find related conversations
    if strategy and not conversation:
        conversations = db.query(Conversation).filter_by(user_id=user_id).all()
        for conv in conversations:
            if conv.draft_spec and conv.draft_spec.get("name") == strategy.name:
                conversation = conv
                break
    
    # 1. Strategy Creation Event
    if strategy:
        events.append(LineageEvent(
            event_type="strategy",
            timestamp=strategy.created_at,
            title=f"Strategy Created: {strategy.name} v{strategy.version}",
            details={
                "strategy_id": strategy.id,
                "version": strategy.version,
                "instruments": strategy.spec.get("instruments", []),
                "timeframe": strategy.spec.get("timeframe"),
                "indicators_count": len(strategy.spec.get("indicators", [])),
                "entry_rules_count": len(strategy.spec.get("entry_rules", [])),
                "exit_rules_count": len(strategy.spec.get("exit_rules", [])),
            },
            entity_id=strategy.id,
            entity_type="strategy",
        ).to_dict())
    
    # 2. Conversation Events
    if conversation:
        # Initial conversation creation
        first_msg = conversation.messages[0] if conversation.messages else None
        events.append(LineageEvent(
            event_type="conversation",
            timestamp=conversation.created_at or conversation.updated_at,
            title=f"Conversation Started: {conversation.messages[0]['text'][:50] if conversation.messages else 'Empty'}",
            details={
                "conversation_id": conversation.id,
                "message_count": len(conversation.messages),
                "has_draft": conversation.draft_spec is not None,
            },
            entity_id=conversation.id,
            entity_type="conversation",
        ).to_dict())
        
        # Draft strategy updates (if available)
        if conversation.draft_spec:
            events.append(LineageEvent(
                event_type="draft_update",
                timestamp=conversation.updated_at,
                title="Strategy Draft Updated",
                details={
                    "conversation_id": conversation.id,
                    "strategy_name": conversation.draft_spec.get("name"),
                    "instruments": conversation.draft_spec.get("instruments", []),
                    "indicators_count": len(conversation.draft_spec.get("indicators", [])),
                },
                entity_id=conversation.id,
                entity_type="conversation",
            ).to_dict())
    
    # 3. Backtest Events
    backtests = db.query(BacktestRun).filter_by(
        strategy_id=strategy.id if strategy else None
    ).order_by(BacktestRun.created_at).all() if strategy else []
    
    for bt in backtests:
        # Filter by user via strategy
        if strategy and strategy.user_id != user_id:
            continue
        metrics = bt.metrics or {}
        events.append(LineageEvent(
            event_type="backtest",
            timestamp=bt.created_at,
            title=f"Backtest #{bt.id}: {metrics.get('total_return_pct', 0):.1f}% return, {metrics.get('trades', 0)} trades",
            details={
                "backtest_id": bt.id,
                "strategy_version": bt.strategy_version,
                "total_return_pct": metrics.get("total_return_pct"),
                "max_drawdown_pct": metrics.get("max_drawdown_pct"),
                "sharpe": metrics.get("sharpe"),
                "win_rate_pct": metrics.get("win_rate_pct"),
                "profit_factor": metrics.get("profit_factor"),
                "trades": metrics.get("trades"),
                "validation_passed": bt.validation.get("passed") if bt.validation else None,
                "data_source": bt.data_source,
                "transaction_cost_bps": bt.transaction_cost_bps,
                "slippage_bps": bt.slippage_bps,
            },
            entity_id=bt.id,
            entity_type="backtest",
        ).to_dict())
    
    # 4. Research Events
    research_runs = db.query(ResearchRun).filter_by(user_id=user_id).order_by(ResearchRun.created_at).all()
    for rr in research_runs:
        # Filter by strategy if specified
        if strategy_id and rr.strategy_id != strategy_id:
            continue
            
        events.append(LineageEvent(
            event_type="research",
            timestamp=rr.created_at,
            title=f"Research Run #{rr.id}: {rr.label or 'Analysis'}",
            details={
                "research_run_id": rr.id,
                "strategy_id": rr.strategy_id,
                "strategy_version": rr.strategy_version,
                "backtest_run_id": rr.backtest_run_id,
                "deployment_id": rr.deployment_id,
                "facts_count": len(rr.facts) if rr.facts else 0,
                "bull_signals": len(rr.interpretations.get("bull", [])) if rr.interpretations else 0,
                "bear_signals": len(rr.interpretations.get("bear", [])) if rr.interpretations else 0,
                "is_simulated": rr.is_simulated,
                "data_source": rr.data_source,
            },
            entity_id=rr.id,
            entity_type="research",
        ).to_dict())
    
    # 5. Journal Entry Events
    journals = db.query(JournalEntry).filter_by(user_id=user_id).order_by(JournalEntry.created_at).all()
    for je in journals:
        # Filter by strategy if specified
        if strategy_id and je.strategy_id != strategy_id:
            continue
            
        events.append(LineageEvent(
            event_type="journal",
            timestamp=je.created_at,
            title=f"Journal: {je.title} ({je.decision_type}, {je.status})",
            details={
                "journal_id": je.id,
                "decision_type": je.decision_type,
                "status": je.status,
                "strategy_id": je.strategy_id,
                "strategy_version": je.strategy_version,
                "conversation_id": je.conversation_id,
                "backtest_run_id": je.backtest_run_id,
                "research_run_id": je.research_run_id,
                "deployment_id": je.deployment_id,
                "has_outcome_review": bool(je.outcome_review),
            },
            entity_id=je.id,
            entity_type="journal",
        ).to_dict())
    
    # 6. Paper Deployment Events
    deployments = db.query(PaperDeployment).order_by(PaperDeployment.activated_at).all()
    for dep in deployments:
        # Filter by strategy if specified
        if strategy_id and dep.strategy_id != strategy_id:
            continue
        # Filter by user via strategy
        if dep.strategy_id:
            strat = db.get(Strategy, dep.strategy_id)
            if strat and strat.user_id != user_id:
                continue
            
        events.append(LineageEvent(
            event_type="deployment",
            timestamp=dep.activated_at,
            title=f"Paper Deployment #{dep.id}: {dep.status}",
            details={
                "deployment_id": dep.id,
                "strategy_id": dep.strategy_id,
                "strategy_version": dep.strategy_version,
                "status": dep.status,
                "initial_cash": dep.initial_cash,
                "transaction_cost_bps": dep.transaction_cost_bps,
                "slippage_bps": dep.slippage_bps,
                "max_position_pct": dep.max_position_pct,
                "stop_loss_pct": dep.stop_loss_pct,
                "take_profit_pct": dep.take_profit_pct,
                "data_source": dep.data_source,
                "closed_at": dep.closed_at.isoformat() if dep.closed_at else None,
            },
            entity_id=dep.id,
            entity_type="deployment",
        ).to_dict())
        
        # Add closure event if closed
        if dep.closed_at:
            events.append(LineageEvent(
                event_type="deployment_closed",
                timestamp=dep.closed_at,
                title=f"Deployment #{dep.id} Closed",
                details={
                    "deployment_id": dep.id,
                    "reason": "Manual closure",
                },
                entity_id=dep.id,
                entity_type="deployment",
            ).to_dict())
    
    # Sort events by timestamp
    events.sort(key=lambda e: e["timestamp"] or "")
    
    return events


def get_entity_lineage(db: Session, entity_type: str, entity_id: int, user_id: int = 1) -> List[Dict[str, Any]]:
    """
    Get lineage for a specific entity (strategy, backtest, deployment, etc.).
    """
    if entity_type == "strategy":
        strategy = db.get(Strategy, entity_id)
        if not strategy or strategy.user_id != user_id:
            return []
        return build_lineage(db, strategy_id=entity_id, user_id=user_id)
    elif entity_type == "conversation":
        conv = db.get(Conversation, entity_id)
        if not conv or conv.user_id != user_id:
            return []
        return build_lineage(db, conversation_id=entity_id, user_id=user_id)
    elif entity_type == "backtest":
        bt = db.get(BacktestRun, entity_id)
        if not bt:
            return []
        strat = db.get(Strategy, bt.strategy_id)
        if not strat or strat.user_id != user_id:
            return []
        return build_lineage(db, strategy_id=bt.strategy_id, user_id=user_id)
    elif entity_type == "deployment":
        dep = db.get(PaperDeployment, entity_id)
        if not dep:
            return []
        strat = db.get(Strategy, dep.strategy_id)
        if not strat or strat.user_id != user_id:
            return []
        return build_lineage(db, strategy_id=dep.strategy_id, user_id=user_id)
    elif entity_type == "journal":
        je = db.get(JournalEntry, entity_id)
        if not je or je.user_id != user_id:
            return []
        return build_lineage(db, strategy_id=je.strategy_id, user_id=user_id)
    elif entity_type == "research":
        rr = db.get(ResearchRun, entity_id)
        if not rr or rr.user_id != user_id:
            return []
        return build_lineage(db, strategy_id=rr.strategy_id, user_id=user_id)
    
    return []