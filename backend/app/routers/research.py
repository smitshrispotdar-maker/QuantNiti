from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import ResearchRun, Strategy, Conversation, BacktestRun, PaperDeployment, User
from ..schemas import ResearchRunCreate, ResearchRunResponse, ResearchRunListResponse
from ..services import research, market, backtest
from typing import Optional
from datetime import datetime
from ..services.auth import get_current_user_dep

router = APIRouter(prefix="/api/research", tags=["research"])


def _to_response(r: ResearchRun) -> ResearchRunResponse:
    return ResearchRunResponse(
        id=r.id,
        user_id=r.user_id,
        strategy_id=r.strategy_id,
        strategy_version=r.strategy_version,
        conversation_id=r.conversation_id,
        backtest_run_id=r.backtest_run_id,
        deployment_id=r.deployment_id,
        strategy_spec_snapshot=r.strategy_spec_snapshot,
        backtest_metrics_snapshot=r.backtest_metrics_snapshot,
        facts=r.facts,
        interpretations=r.interpretations,
        label=r.label,
        data_source=r.data_source,
        data_quality=r.data_quality,
        is_simulated=r.is_simulated,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


@router.get("")
def list_runs(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    strategy_id: Optional[int] = None,
    conversation_id: Optional[int] = None,
    backtest_run_id: Optional[int] = None,
    deployment_id: Optional[int] = None,
    current_user: User = Depends(get_current_user_dep),
):
    """List research runs with pagination and filtering."""
    query = db.query(ResearchRun).filter(ResearchRun.user_id == current_user.id)
    
    if strategy_id:
        query = query.filter(ResearchRun.strategy_id == strategy_id)
    if conversation_id:
        query = query.filter(ResearchRun.conversation_id == conversation_id)
    if backtest_run_id:
        query = query.filter(ResearchRun.backtest_run_id == backtest_run_id)
    if deployment_id:
        query = query.filter(ResearchRun.deployment_id == deployment_id)
    
    total = query.count()
    runs = query.order_by(ResearchRun.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    return ResearchRunListResponse(
        items=[_to_response(r) for r in runs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("")
def create_run(body: ResearchRunCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_dep)):
    """Create a new research run with automatic analysis."""
    # Validate references
    if body.strategy_id:
        strategy = db.get(Strategy, body.strategy_id)
        if not strategy:
            raise HTTPException(404, "Strategy not found")
        if strategy.user_id != current_user.id:
            raise HTTPException(403, "Not authorized")
    
    if body.conversation_id:
        conv = db.get(Conversation, body.conversation_id)
        if not conv:
            raise HTTPException(404, "Conversation not found")
        if conv.user_id != current_user.id:
            raise HTTPException(403, "Not authorized")
    
    if body.backtest_run_id:
        run = db.get(BacktestRun, body.backtest_run_id)
        if not run:
            raise HTTPException(404, "Backtest run not found")
    
    if body.deployment_id:
        dep = db.get(PaperDeployment, body.deployment_id)
        if not dep:
            raise HTTPException(404, "Deployment not found")
    
    # Determine strategy spec and backtest metrics
    strategy_spec = body.strategy_spec_snapshot
    backtest_metrics = body.backtest_metrics_snapshot
    
    # If not provided, try to fetch from linked objects
    if not strategy_spec and body.strategy_id:
        strategy = db.get(Strategy, body.strategy_id)
        strategy_spec = strategy.spec
    if not backtest_metrics and body.backtest_run_id:
        backtest_run = db.get(BacktestRun, body.backtest_run_id)
        backtest_metrics = backtest_run.metrics
    
    # Get market data for research
    if body.strategy_id:
        strategy = db.get(Strategy, body.strategy_id)
        symbol = strategy.spec.get("instruments", ["BTC-USD"])[0]
        timeframe = strategy.spec.get("timeframe", "1d")
    elif body.deployment_id:
        dep = db.get(PaperDeployment, body.deployment_id)
        spec = StrategySpec(**dep.strategy_spec)
        symbol = spec.instruments[0]
        timeframe = spec.timeframe
    elif body.backtest_run_id:
        run = db.get(BacktestRun, body.backtest_run_id)
        symbol = run.strategy_spec.get("instruments", ["BTC-USD"])[0]
        timeframe = run.strategy_spec.get("timeframe", "1d")
    else:
        # Default to BTC-USD daily
        symbol = "BTC-USD"
        timeframe = "1d"
    
    # Fetch market data
    df, meta = market.get_bars(symbol, timeframe, 500)
    
    # Run research analysis
    research_result = research.run(df)
    
    # Determine data source and quality
    is_simulated = meta.get("status") == "SIMULATED"
    
    # Create research run record
    run = ResearchRun(
        user_id=current_user.id,
        strategy_id=body.strategy_id,
        strategy_version=body.strategy_version,
        conversation_id=body.conversation_id,
        backtest_run_id=body.backtest_run_id,
        deployment_id=body.deployment_id,
        strategy_spec_snapshot=strategy_spec,
        backtest_metrics_snapshot=backtest_metrics,
        facts=research_result.get("facts"),
        interpretations=research_result.get("interpretations"),
        label=research_result.get("label", "AI-GENERATED INTERPRETATION · PAPER/SIMULATED"),
        data_source=meta.get("source"),
        data_quality=meta.get("data_quality"),
        is_simulated=is_simulated,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    
    # If linked to conversation, add research reference
    if body.conversation_id:
        conv = db.get(Conversation, body.conversation_id)
        if conv and conv.draft_spec is not None:
            if "research_refs" not in conv.draft_spec:
                conv.draft_spec["research_refs"] = []
            conv.draft_spec["research_refs"].append({
                "id": run.id,
                "timestamp": datetime.utcnow().isoformat(),
                "summary": f"Research completed for {symbol} {timeframe}"
            })
            db.commit()
    
    return _to_response(run)


@router.get("/{rid}")
def get_run(rid: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_dep)):
    """Get a single research run."""
    run = db.get(ResearchRun, rid)
    if not run:
        raise HTTPException(404, "Research run not found")
    if run.user_id != current_user.id:
        raise HTTPException(403, "Not authorized")
    return _to_response(run)


@router.post("/from-chat")
def create_from_chat(
    conversation_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dep),
):
    """Create a research run from the current conversation's draft strategy."""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(404, "Conversation not found")
    if conv.user_id != current_user.id:
        raise HTTPException(403, "Not authorized")
    
    if not conv.draft_spec:
        raise HTTPException(400, "No draft strategy in conversation")
    
    spec = conv.draft_spec
    symbol = spec.get("instruments", ["BTC-USD"])[0]
    timeframe = spec.get("timeframe", "1d")
    
    # Fetch market data
    df, meta = market.get_bars(symbol, timeframe, 500)
    
    # Run research
    research_result = research.run(df)
    
    # Determine if we have a backtest or deployment to link
    backtest_run_id = None
    deployment_id = None
    backtest_metrics = None
    strategy_id = None
    strategy_version = None
    
    if conv.draft_spec and "backtest_refs" in conv.draft_spec and conv.draft_spec["backtest_refs"]:
        backtest_run_id = conv.draft_spec["backtest_refs"][-1]["id"]
        # Fetch backtest metrics for snapshot
        backtest_run = db.get(BacktestRun, backtest_run_id)
        if backtest_run:
            backtest_metrics = backtest_run.metrics
    
    if conv.draft_spec and "deployment_refs" in conv.draft_spec and conv.draft_spec["deployment_refs"]:
        deployment_id = conv.draft_spec["deployment_refs"][-1]["id"]
    
    # Try to find a matching saved strategy by name and spec
    strategy_name = spec.get("name")
    if strategy_name:
        strategy = db.query(Strategy).filter(
            Strategy.name == strategy_name,
            Strategy.user_id == current_user.id
        ).order_by(Strategy.version.desc()).first()
        if strategy:
            strategy_id = strategy.id
            strategy_version = strategy.version
    
    # Run research
    research_result = research.run(df)
    is_simulated = meta.get("status") == "SIMULATED"
    
    # Create research run
    run = ResearchRun(
        user_id=current_user.id,
        conversation_id=conversation_id,
        strategy_id=strategy_id,
        strategy_version=strategy_version,
        backtest_run_id=backtest_run_id,
        deployment_id=deployment_id,
        strategy_spec_snapshot=spec,
        backtest_metrics_snapshot=backtest_metrics,
        facts=research_result.get("facts"),
        interpretations=research_result.get("interpretations"),
        label=research_result.get("label", "AI-GENERATED INTERPRETATION · PAPER/SIMULATED"),
        data_source=meta.get("source"),
        data_quality=meta.get("data_quality"),
        is_simulated=is_simulated,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    
    # Add research reference to conversation
    if conv.draft_spec is not None:
        if "research_refs" not in conv.draft_spec:
            conv.draft_spec["research_refs"] = []
        conv.draft_spec["research_refs"].append({
            "id": run.id,
            "timestamp": datetime.utcnow().isoformat(),
            "summary": f"Research completed for {symbol} {timeframe}"
        })
        db.commit()
    
    return _to_response(run)