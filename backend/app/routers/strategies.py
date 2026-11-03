from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc, String
from typing import List, Optional
from datetime import datetime
from ..db import get_db
from ..models import Strategy, Conversation, ResearchRun, BacktestRun, JournalEntry
from ..schemas import (
    StrategyIn, StrategySpec, ChatIn, StrategyVersionInfo, StrategyDiff,
    ResearchComparisonRequest, ResearchComparisonResponse,
    ExportFormat, ExportRequest, ConversationSearchRequest, ConversationSearchResult,
    ScheduledResearchConfig
)
from ..services import nlp, backtest, market, validation, paper, research
from datetime import datetime
import base64
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
router = APIRouter(prefix="/api/strategies", tags=["strategies"])

@router.get("")
def list_(db: Session = Depends(get_db)):
    return [{"id": s.id, "name": s.name, "version": s.version, "spec": s.spec} for s in db.query(Strategy).order_by(Strategy.id.desc())]

@router.post("")
def save(body: StrategyIn, db: Session = Depends(get_db)):
    """Create a strategy, or a new VERSION when a strategy with the same name exists."""
    prev = db.query(Strategy).filter(Strategy.name == body.spec.name).order_by(Strategy.version.desc()).first()
    s = Strategy(user_id=1, name=body.spec.name, version=(prev.version + 1 if prev else 1), spec=body.spec.model_dump())
    db.add(s); db.commit(); db.refresh(s)
    return {"id": s.id, "version": s.version, "spec": s.spec}

@router.get("/{sid}")
def get(sid: int, db: Session = Depends(get_db)):
    s = db.get(Strategy, sid)
    if not s: raise HTTPException(404, "Strategy not found")
    return {"id": s.id, "version": s.version, "spec": s.spec}

# --- Conversation Management ---

@router.get("/conversations")
def list_conversations(db: Session = Depends(get_db)):
    """List all conversations for the current user."""
    conversations = db.query(Conversation).filter_by(user_id=1).order_by(Conversation.updated_at.desc()).all()
    return [
        {
            "id": c.id,
            "title": c.messages[0]["text"][:50] if c.messages else "Empty conversation",
            "message_count": len(c.messages),
            "has_draft": c.draft_spec is not None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in conversations
    ]

@router.delete("/conversations/{cid}")
def delete_conversation(cid: int, db: Session = Depends(get_db)):
    """Delete a conversation."""
    c = db.get(Conversation, cid)
    if not c: raise HTTPException(404, "Conversation not found")
    if c.user_id != 1: raise HTTPException(403, "Not authorized")
    db.delete(c)
    db.commit()
    return {"deleted": True, "id": cid}

@router.post("/conversations/{cid}/rename")
def rename_conversation(cid: int, body: dict, db: Session = Depends(get_db)):
    """Rename a conversation (stores title in first user message or metadata)."""
    c = db.get(Conversation, cid)
    if not c: raise HTTPException(404, "Conversation not found")
    if c.user_id != 1: raise HTTPException(403, "Not authorized")
    # For now, prepend a system message with the title
    title = body.get("title", "").strip()
    if not title:
        raise HTTPException(400, "Title required")
    # Store title as a special message or in draft_spec metadata
    if c.draft_spec is None:
        c.draft_spec = {}
    c.draft_spec["_title"] = title
    c.updated_at = datetime.utcnow()
    db.commit()
    return {"id": c.id, "title": title}

# --- Existing Endpoints ---

@router.get("/chat/{cid}")
def history(cid: int, db: Session = Depends(get_db)):
    c = db.get(Conversation, cid)
    if not c: raise HTTPException(404, "Conversation not found")
    return {"id": c.id, "messages": c.messages, "draft_spec": c.draft_spec}

@router.post("/chat")
def chat(body: ChatIn, db: Session = Depends(get_db)):
    c = db.get(Conversation, body.conversation_id) if body.conversation_id else None
    if not c: c = Conversation(user_id=1, messages=[]); db.add(c)
    base = StrategySpec(**c.draft_spec) if c.draft_spec else None
    spec, ask = nlp.parse(body.message, base)
    
    # Check for special actions
    action, action_params = nlp.detect_action(body.message)
    
    if action == "backtest":
        # Trigger backtest
        result = _run_backtest_from_spec(db, spec, body.message)
        reply = _format_backtest_result(result)
        # Store backtest reference
        if "backtest_refs" not in c.draft_spec:
            c.draft_spec["backtest_refs"] = []
        c.draft_spec["backtest_refs"].append({
            "id": result["id"],
            "timestamp": datetime.utcnow().isoformat(),
            "summary": f"Return: {result['metrics']['total_return_pct']}%, Trades: {result['metrics']['trades']}"
        })
    elif action == "deploy":
        # Paper trading deployment
        result = _deploy_from_spec(db, spec, body.message)
        reply = _format_deploy_result(result)
        if "deployment_refs" not in c.draft_spec:
            c.draft_spec["deployment_refs"] = []
        c.draft_spec["deployment_refs"].append({
            "id": result["id"],
            "timestamp": datetime.utcnow().isoformat(),
            "summary": f"Deployed to paper trading"
        })
    elif action == "explain":
        # Explain current draft or backtest
        reply = _explain_strategy(spec, body.message)
    else:
        # Default: update draft strategy
        reply = "Updated the draft strategy." + ("" if not ask else " I need a few details:")
    
    c.messages = c.messages + [
        {"role": "user", "text": body.message},
        {"role": "assistant", "text": reply, "clarifications": ask}
    ]
    c.draft_spec = spec.model_dump()
    c.updated_at = datetime.utcnow()
    db.commit(); db.refresh(c)
    return {"conversation_id": c.id, "messages": c.messages, "draft_spec": c.draft_spec, "clarifications": ask}

# --- Helper Functions ---

from datetime import datetime
from ..schemas import BacktestIn, DeployIn
from ..models import PaperAccount, PaperDeployment

def _run_backtest_from_spec(db: Session, spec: StrategySpec, user_message: str) -> dict:
    """Run a backtest from the current strategy spec."""
    if not spec.instruments:
        raise HTTPException(400, "No instrument specified for backtest")
    
    # Get market data
    df, meta = market.get_bars(spec.instruments[0], spec.timeframe, 500)
    
    if len(df) < 30:
        raise HTTPException(422, {"validation": {"passed": False, "errors": [f"Insufficient data: only {len(df)} bars available, need at least 30"], "warnings": []}})
    
    # Run backtest
    metrics, curve, trades = backtest.run(spec, df, 100_000, 0, 0)
    gate = validation.validate(spec, metrics)
    
    # Save backtest run
    from ..models import BacktestRun
    # Find or create a strategy for this spec
    strategy_name = spec.name or "Chat Strategy"
    strategy = db.query(Strategy).filter(Strategy.name == strategy_name).order_by(Strategy.version.desc()).first()
    if not strategy:
        strategy = Strategy(user_id=1, name=strategy_name, version=1, spec=spec.model_dump())
        db.add(strategy)
        db.commit()
        db.refresh(strategy)
    
    run = BacktestRun(
        strategy_id=strategy.id,
        strategy_version=strategy.version,
        strategy_spec=spec.model_dump(),
        initial_cash=100_000,
        transaction_cost_bps=0,
        slippage_bps=0,
        metrics=metrics,
        equity_curve=curve,
        trades=trades,
        validation=gate,
        data_source=meta["source"]
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    
    return {"id": run.id, "metrics": metrics, "equity_curve": curve, "trades": trades, "validation": gate, "meta": meta}

def _deploy_from_spec(db: Session, spec: StrategySpec, user_message: str) -> dict:
    """Create a paper trading deployment from the current strategy spec."""
    if not spec.instruments:
        raise HTTPException(400, "No instrument specified for deployment")
    
    # Create a paper account if needed
    account = db.query(PaperAccount).filter_by(user_id=1, status="RUNNING").first()
    if not account:
        account = PaperAccount(user_id=1, name="Chat Paper Account", starting_cash=100_000, cash=100_000, status="RUNNING")
        db.add(account)
        db.commit()
        db.refresh(account)
    
    # Check for existing active deployment
    existing = db.query(PaperDeployment).filter_by(account_id=account.id, status="ACTIVE").first()
    if existing:
        raise HTTPException(409, "Account already has an active deployment. Close it first.")
    
    # Find or create strategy
    strategy_name = spec.name or "Chat Strategy"
    strategy = db.query(Strategy).filter(Strategy.name == strategy_name).order_by(Strategy.version.desc()).first()
    if not strategy:
        strategy = Strategy(user_id=1, name=strategy_name, version=1, spec=spec.model_dump())
        db.add(strategy)
        db.commit()
        db.refresh(strategy)
    
    # Get latest backtest for validation
    run = db.query(BacktestRun).filter_by(strategy_id=strategy.id, strategy_version=strategy.version).order_by(BacktestRun.id.desc()).first()
    if not run:
        raise HTTPException(422, {"validation": {"passed": False, "errors": ["No backtest found for this strategy version"], "warnings": []}})
    
    gate = validation.validate(StrategySpec(**spec.model_dump()), run.metrics)
    if not gate["passed"]:
        raise HTTPException(422, {"validation": gate})
    
    # Create deployment
    deployment = PaperDeployment(
        account_id=account.id,
        strategy_id=strategy.id,
        strategy_version=strategy.version,
        strategy_spec=spec.model_dump(),
        initial_cash=account.cash,
        transaction_cost_bps=run.transaction_cost_bps,
        slippage_bps=run.slippage_bps,
        max_position_pct=spec.risk.max_position_pct,
        stop_loss_pct=spec.risk.stop_loss_pct,
        take_profit_pct=spec.risk.take_profit_pct,
        max_drawdown_pct=spec.risk.max_drawdown_pct,
        data_source=run.data_source,
        status="ACTIVE",
    )
    db.add(deployment)
    db.commit()
    db.refresh(deployment)
    
    return {"id": deployment.id, "status": deployment.status, "strategy_id": strategy.id}

def _format_backtest_result(result: dict) -> str:
    m = result["metrics"]
    return (f"Backtest completed (ID: {result['id']}). "
            f"Total Return: {m['total_return_pct']}%, "
            f"Max Drawdown: {m['max_drawdown_pct']}%, "
            f"Sharpe: {m['sharpe']}, "
            f"Win Rate: {m['win_rate_pct']}%, "
            f"Trades: {m['trades']}. "
            f"Validation: {'PASSED' if result['validation']['passed'] else 'FAILED'}.")

def _format_deploy_result(result: dict) -> str:
    return f"Paper trading deployment created (ID: {result['id']}). Strategy deployed successfully."

def _explain_strategy(spec: StrategySpec, user_message: str) -> str:
    parts = []
    if spec.instruments:
        parts.append(f"Instrument: {', '.join(spec.instruments)}")
    if spec.timeframe:
        parts.append(f"Timeframe: {spec.timeframe}")
    if spec.indicators:
        ind_desc = ", ".join([f"{i.type}({i.params.get('period', '?')})" for i in spec.indicators])
        parts.append(f"Indicators: {ind_desc}")
    if spec.entry_rules:
        parts.append(f"Entry rules: {len(spec.entry_rules)}")
    if spec.exit_rules:
        parts.append(f"Exit rules: {len(spec.exit_rules)}")
    if spec.risk.stop_loss_pct:
        parts.append(f"Stop loss: {spec.risk.stop_loss_pct}%")
    if spec.risk.take_profit_pct:
        parts.append(f"Take profit: {spec.risk.take_profit_pct}%")
    if spec.risk.max_position_pct:
        parts.append(f"Position size: {spec.risk.max_position_pct}%")
    return "Current strategy: " + "; ".join(parts) + "."


# --- Strategy Versioning & Diff ---

@router.get("/{sid}/versions")
def list_versions(sid: int, db: Session = Depends(get_db)):
    """List all versions of a strategy."""
    strategy = db.get(Strategy, sid)
    if not strategy:
        raise HTTPException(404, "Strategy not found")
    versions = db.query(Strategy).filter(Strategy.name == strategy.name).order_by(Strategy.version).all()
    return [{"id": v.id, "version": v.version, "created_at": v.created_at.isoformat()} for v in versions]


@router.get("/{sid}/diff")
def diff_versions(sid: int, from_version: int = Query(...), to_version: int = Query(...), db: Session = Depends(get_db)):
    """Compare two versions of a strategy."""
    strategy = db.get(Strategy, sid)
    if not strategy:
        raise HTTPException(404, "Strategy not found")
    
    v_from = db.query(Strategy).filter(Strategy.name == strategy.name, Strategy.version == from_version).first()
    v_to = db.query(Strategy).filter(Strategy.name == strategy.name, Strategy.version == to_version).first()
    
    if not v_from or not v_to:
        raise HTTPException(404, "One or both versions not found")
    
    spec_from = v_from.spec
    spec_to = v_to.spec
    
    # Simple diff - in production, use a proper diff library
    diff = {
        "strategy_name": strategy.name,
        "from_version": from_version,
        "to_version": to_version,
        "changes": {},
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Compare key fields
    for key in ["instruments", "timeframe", "indicators", "entry_rules", "exit_rules", "risk"]:
        val_from = spec_from.get(key)
        val_to = spec_to.get(key)
        if val_from != val_to:
            diff["changes"][key] = {"from": val_from, "to": val_to}
    
    return diff


# --- Research Comparison ---

@router.post("/research/compare")
def compare_research(body: ResearchComparisonRequest, db: Session = Depends(get_db)):
    """Compare multiple research runs."""
    if len(body.run_ids) < 2:
        raise HTTPException(400, "At least 2 run IDs required")
    if len(body.run_ids) > 5:
        raise HTTPException(400, "Maximum 5 runs for comparison")
    
    runs = db.query(ResearchRun).filter(ResearchRun.id.in_(body.run_ids)).all()
    if len(runs) != len(body.run_ids):
        raise HTTPException(404, "One or more research runs not found")
    
    # Run comparison
    comparison = research.compare_runs(runs)
    
    # Store comparison result
    comparison_run = ResearchRun(
        user_id=1,  # TODO: replace with actual auth
        strategy_id=runs[0].strategy_id if runs[0].strategy_id else None,
        conversation_id=None,
        backtest_run_id=None,
        deployment_id=None,
        strategy_spec_snapshot={},
        backtest_metrics_snapshot={},
        facts={},
        interpretations={"comparison": comparison},
        label="COMPARISON",
        data_source="COMPARISON",
        is_simulated=True,
    )
    db.add(comparison_run)
    db.commit()
    db.refresh(comparison_run)
    
    return ResearchComparisonResponse(
        runs=[{
            "id": r.id,
            "strategy_id": r.strategy_id,
            "created_at": r.created_at.isoformat(),
            "label": r.label
        } for r in runs],
        comparison=comparison
    )


def generate_pdf_export(data: dict, body: ExportRequest) -> str:
    """Generate a PDF report from the export data."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        textColor=HexColor('#1E3A5F'),
        spaceAfter=6,
        alignment=TA_CENTER,
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=HexColor('#666666'),
        spaceAfter=20,
        alignment=TA_CENTER,
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=HexColor('#1E3A5F'),
        spaceBefore=16,
        spaceAfter=8,
        borderWidth=0,
        borderPadding=0,
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubheading',
        parent=styles['Heading3'],
        fontSize=11,
        textColor=HexColor('#333333'),
        spaceBefore=10,
        spaceAfter=4,
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=9,
        textColor=HexColor('#333333'),
        spaceAfter=3,
        leading=12,
    )
    
    mono_style = ParagraphStyle(
        'CustomMono',
        parent=styles['Code'],
        fontSize=8,
        textColor=HexColor('#333333'),
        fontName='Courier',
        spaceAfter=2,
        leading=10,
    )
    
    elements = []
    
    # Title page
    elements.append(Paragraph("QuantNiti Export Report", title_style))
    elements.append(Paragraph(
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
        subtitle_style
    ))
    elements.append(Paragraph(
        "PAPER/SIMULATED · NO REAL MONEY",
        ParagraphStyle('Disclaimer', parent=subtitle_style, textColor=HexColor('#AA0000'), fontSize=10)
    ))
    elements.append(Spacer(1, 30))
    
    # Table of contents
    elements.append(Paragraph("Contents", heading_style))
    toc_items = []
    if data.get("journal"): toc_items.append("Journal Entries")
    if data.get("strategies"): toc_items.append("Strategies")
    if data.get("backtests"): toc_items.append("Backtest Runs")
    if data.get("research"): toc_items.append("Research Runs")
    
    for item in toc_items:
        elements.append(Paragraph(f"• {item}", body_style))
    
    elements.append(PageBreak())
    
    # Journal Entries
    if data.get("journal"):
        elements.append(Paragraph("Journal Entries", heading_style))
        for entry in data["journal"]:
            elements.append(Paragraph(f"Entry #{entry['id']}", subheading_style))
            
            entry_data = [
                ["Field", "Value"],
                ["Strategy ID", str(entry.get('strategy_id', '—'))],
                ["Strategy Version", str(entry.get('strategy_version', '—'))],
                ["Created", entry.get('created_at', '—')],
                ["Recommendation", entry.get('recommendation', '—') or '—'],
                ["Outcome Review", entry.get('outcome_review', '—') or '—'],
            ]
            
            if entry.get('evidence'):
                entry_data.append(["Evidence", str(entry['evidence'])[:200] + ("..." if len(str(entry['evidence'])) > 200 else "")])
            
            table = Table(entry_data, colWidths=[1.5*inch, 4.5*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1E3A5F')),
                ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#FFFFFF')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), HexColor('#F8F9FA')),
                ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#DDDDDD')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 12))
    
    # Strategies
    if data.get("strategies"):
        elements.append(Paragraph("Strategies", heading_style))
        for strategy in data["strategies"]:
            elements.append(Paragraph(f"{strategy['name']} v{strategy['version']} (ID: {strategy['id']})", subheading_style))
            elements.append(Paragraph(f"Created: {strategy.get('created_at', '—')}", body_style))
            
            spec = strategy.get('spec', {})
            if spec:
                elements.append(Paragraph("Strategy Specification", ParagraphStyle('SpecHead', parent=body_style, fontSize=10, textColor=HexColor('#1E3A5F'), spaceBefore=6)))
                
                # Key spec fields
                spec_fields = [
                    ("Instruments", ", ".join(spec.get('instruments', [])) or '—'),
                    ("Timeframe", spec.get('timeframe', '—')),
                    ("Indicators", str(len(spec.get('indicators', [])))),
                    ("Entry Rules", str(len(spec.get('entry_rules', [])))),
                    ("Exit Rules", str(len(spec.get('exit_rules', [])))),
                ]
                
                risk = spec.get('risk', {})
                if risk:
                    spec_fields.extend([
                        ("Max Position %", str(risk.get('max_position_pct', '—'))),
                        ("Stop Loss %", str(risk.get('stop_loss_pct', '—'))),
                        ("Take Profit %", str(risk.get('take_profit_pct', '—'))),
                        ("Max Drawdown %", str(risk.get('max_drawdown_pct', '—'))),
                    ])
                
                spec_data = [["Parameter", "Value"]] + spec_fields
                table = Table(spec_data, colWidths=[1.5*inch, 4.5*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1E3A5F')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#FFFFFF')),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                    ('TOPPADDING', (0, 0), (-1, 0), 6),
                    ('BACKGROUND', (0, 1), (-1, -1), HexColor('#F8F9FA')),
                    ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#DDDDDD')),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
                ]))
                elements.append(table)
            elements.append(Spacer(1, 12))
    
    # Backtest Runs
    if data.get("backtests"):
        elements.append(Paragraph("Backtest Runs", heading_style))
        for bt in data["backtests"]:
            elements.append(Paragraph(f"Backtest Run #{bt['id']}", subheading_style))
            
            metrics = bt.get('metrics', {})
            validation_result = bt.get('validation', {})
            
            bt_data = [
                ["Metric", "Value"],
                ["Strategy ID", str(bt.get('strategy_id', '—'))],
                ["Strategy Version", str(bt.get('strategy_version', '—'))],
                ["Created", bt.get('created_at', '—')],
                ["Data Source", bt.get('data_source', '—')],
                ["Validation", "PASSED" if validation_result.get('passed') else "FAILED"],
            ]
            
            if metrics:
                metric_fields = [
                    ("Total Return %", f"{metrics.get('total_return_pct', 0):.2f}%"),
                    ("Max Drawdown %", f"{metrics.get('max_drawdown_pct', 0):.2f}%"),
                    ("Sharpe Ratio", f"{metrics.get('sharpe', 0):.2f}"),
                    ("Win Rate %", f"{metrics.get('win_rate_pct', 0):.2f}%"),
                    ("Profit Factor", f"{metrics.get('profit_factor', 0):.2f}"),
                    ("Total Trades", str(metrics.get('trades', 0))),
                    ("Avg Trade %", f"{metrics.get('avg_trade_pct', 0):.2f}%"),
                ]
                bt_data.extend(metric_fields)
            
            table = Table(bt_data, colWidths=[1.5*inch, 4.5*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1E3A5F')),
                ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#FFFFFF')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('TOPPADDING', (0, 0), (-1, 0), 6),
                ('BACKGROUND', (0, 1), (-1, -1), HexColor('#F8F9FA')),
                ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#DDDDDD')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 12))
    
    # Research Runs
    if data.get("research"):
        elements.append(Paragraph("Research Runs", heading_style))
        for research in data["research"]:
            elements.append(Paragraph(f"Research Run #{research['id']}", subheading_style))
            
            r_data = [
                ["Field", "Value"],
                ["Strategy ID", str(research.get('strategy_id', '—'))],
                ["Conversation ID", str(research.get('conversation_id', '—'))],
                ["Created", research.get('created_at', '—')],
                ["Label", research.get('label', '—') or '—'],
                ["Data Source", research.get('data_source', '—') or '—'],
                ["Simulated", "Yes" if research.get('is_simulated') else "No"],
            ]
            
            table = Table(r_data, colWidths=[1.5*inch, 4.5*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1E3A5F')),
                ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#FFFFFF')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('TOPPADDING', (0, 0), (-1, 0), 6),
                ('BACKGROUND', (0, 1), (-1, -1), HexColor('#F8F9FA')),
                ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#DDDDDD')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ]))
            elements.append(table)
            
            # Facts
            facts = research.get('facts', {})
            if facts:
                elements.append(Paragraph("Key Facts", ParagraphStyle('FactsHead', parent=body_style, fontSize=10, textColor=HexColor('#1E3A5F'), spaceBefore=8)))
                facts_data = [["Metric", "Value"]]
                for k, v in facts.items():
                    facts_data.append([k.replace('_', ' ').title(), str(v)])
                table = Table(facts_data, colWidths=[2*inch, 4*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1E3A5F')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#FFFFFF')),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
                    ('TOPPADDING', (0, 0), (-1, 0), 5),
                    ('BACKGROUND', (0, 1), (-1, -1), HexColor('#F8F9FA')),
                    ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#DDDDDD')),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
                ]))
                elements.append(table)
            
            # Interpretations
            interpretations = research.get('interpretations', {})
            if interpretations:
                elements.append(Paragraph("Interpretations", ParagraphStyle('InterpHead', parent=body_style, fontSize=10, textColor=HexColor('#1E3A5F'), spaceBefore=8)))
                for key, value in interpretations.items():
                    if isinstance(value, list):
                        if value:
                            elements.append(Paragraph(f"<b>{key.replace('_', ' ').title()}:</b>", body_style))
                            for item in value:
                                elements.append(Paragraph(f"• {item}", ParagraphStyle('Bullet', parent=body_style, leftIndent=20)))
                    elif isinstance(value, str) and value:
                        elements.append(Paragraph(f"<b>{key.replace('_', ' ').title()}:</b> {value}", body_style))
            
            elements.append(Spacer(1, 12))
    
    # Footer
    elements.append(Spacer(1, 30))
    elements.append(Paragraph(
        "— End of Report —",
        ParagraphStyle('Footer', parent=body_style, alignment=TA_CENTER, textColor=HexColor('#999999'))
    ))
    elements.append(Paragraph(
        "QuantNiti · Paper/Simulated Trading Platform · No Real Money Involved",
        ParagraphStyle('Footer2', parent=body_style, alignment=TA_CENTER, textColor=HexColor('#999999'), fontSize=8)
    ))
    
    doc.build(elements)
    buffer.seek(0)
    pdf_bytes = buffer.read()
    buffer.close()
    
    return base64.b64encode(pdf_bytes).decode('utf-8')


# --- Export ---

@router.post("/export")
def export_data(body: ExportRequest, db: Session = Depends(get_db)):
    """Export journal entries, strategies, backtests, or research runs."""
    data = {}
    
    if body.journal_entry_ids:
        entries = db.query(JournalEntry).filter(JournalEntry.id.in_(body.journal_entry_ids)).all()
        data["journal"] = [{
            "id": e.id, "strategy_id": e.strategy_id, "strategy_version": e.strategy_version,
            "recommendation": e.recommendation, "evidence": e.evidence,
            "outcome_review": e.outcome_review, "created_at": e.created_at.isoformat()
        } for e in entries]
    
    if body.strategy_ids:
        strategies = db.query(Strategy).filter(Strategy.id.in_(body.strategy_ids)).all()
        data["strategies"] = [{
            "id": s.id, "name": s.name, "version": s.version, "spec": s.spec, "created_at": s.created_at.isoformat()
        } for s in strategies]
    
    if body.backtest_run_ids:
        runs = db.query(BacktestRun).filter(BacktestRun.id.in_(body.backtest_run_ids)).all()
        data["backtests"] = [{
            "id": r.id, "strategy_id": r.strategy_id, "strategy_version": r.strategy_version,
            "metrics": r.metrics, "trades": r.trades, "validation": r.validation,
            "created_at": r.created_at.isoformat()
        } for r in runs]
    
    if body.research_run_ids:
        runs = db.query(ResearchRun).filter(ResearchRun.id.in_(body.research_run_ids)).all()
        data["research"] = [{
            "id": r.id, "strategy_id": r.strategy_id, "conversation_id": r.conversation_id,
            "facts": r.facts, "interpretations": r.interpretations, "label": r.label,
            "data_source": r.data_source, "is_simulated": r.is_simulated, "created_at": r.created_at.isoformat()
        } for r in runs]
    
    # Format output
    if body.format == ExportFormat.JSON:
        return data
    elif body.format == ExportFormat.MARKDOWN:
        # Simple markdown export
        lines = ["# QuantNiti Export", f"Generated: {datetime.utcnow().isoformat()}", ""]
        for key, items in data.items():
            if items:
                lines.append(f"## {key.title()}")
                for item in items:
                    lines.append(f"- {item}")
                lines.append("")
        return {"markdown": "\n".join(lines)}
    else:
        # PDF export using reportlab
        pdf_base64 = generate_pdf_export(data, body)
        return {"pdf_base64": pdf_base64, "filename": f"quantniti-export-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.pdf"}


# --- Conversation Search ---

@router.get("/conversations/search")
def search_conversations(
    query: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """Search conversations by content."""
    query_obj = db.query(Conversation).filter(Conversation.user_id == 1)
    
    if query:
        # Simple text search in messages
        query_obj = query_obj.filter(Conversation.messages.cast(String).ilike(f"%{query}%"))
    
    if date_from:
        query_obj = query_obj.filter(Conversation.updated_at >= date_from)
    if date_to:
        query_obj = query_obj.filter(Conversation.updated_at <= date_to)
    
    total = query_obj.count()
    conversations = query_obj.order_by(desc(Conversation.updated_at)).offset(offset).limit(limit).all()
    
    return ConversationSearchResult(
        conversations=[{
            "id": c.id,
            "title": c.messages[0]["text"][:50] if c.messages else "Empty",
            "message_count": len(c.messages),
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        } for c in conversations],
        total=total
    )


# --- Scheduled Research Configuration ---

@router.get("/research/schedule")
def get_research_schedule(db: Session = Depends(get_db)):
    """Get scheduled research configuration."""
    # In a real implementation, this would come from a config table
    return ScheduledResearchConfig()

@router.post("/research/schedule")
def update_research_schedule(config: ScheduledResearchConfig, db: Session = Depends(get_db)):
    """Update scheduled research configuration."""
    # In a real implementation, this would save to a config table
    return {"status": "updated", "config": config}
