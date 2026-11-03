"""Multi-agent research. FACTS are computed from data; AGENT views are templated interpretations of those facts
(deterministic stand-ins — replace with an LLM that only receives `facts`). Agents cannot trade."""
import numpy as np
from typing import List, Dict, Any
from .indicators import rsi, ema, sma, macd


def run(df):
    """Run multi-agent research analysis on market data.
    
    Returns structured results with facts and agent interpretations.
    """
    c = df.close
    r = rsi(c).iloc[-1]
    e20, e50 = ema(c, 20).iloc[-1], ema(c, 50).iloc[-1]
    h = macd(c)[2].iloc[-1]
    vol = c.pct_change().tail(30).std() * np.sqrt(252) * 100
    dd = (c / c.cummax() - 1).iloc[-1] * 100
    
    facts = {
        "last_close": round(c.iloc[-1], 2),
        "rsi14": round(r, 1),
        "ema20": round(e20, 2),
        "ema50": round(e50, 2),
        "macd_hist": round(h, 3),
        "ann_vol_30d_pct": round(vol, 1),
        "drawdown_from_peak_pct": round(dd, 1),
        "return_30bar_pct": round((c.iloc[-1] / c.iloc[-31] - 1) * 100, 1)
    }
    
    bull, bear = [], []
    (bull if e20 > e50 else bear).append("EMA20 is " + ("above" if e20 > e50 else "below") + " EMA50.")
    (bull if h > 0 else bear).append("MACD histogram is " + ("positive" if h > 0 else "negative") + ".")
    if r < 35:
        bull.append(f"RSI {r:.0f} is oversold — mean-reversion setup.")
    if r > 65:
        bear.append(f"RSI {r:.0f} is overbought — pullback risk.")
    if facts["return_30bar_pct"] > 0:
        bull.append("Positive 30-bar momentum.")
    else:
        bear.append("Negative 30-bar momentum.")
    
    risk = "HIGH" if vol > 60 or dd < -25 else "MODERATE" if vol > 30 else "LOW"
    stance = ("LEAN LONG" if len(bull) - len(bear) >= 2 
              else "LEAN FLAT" if len(bear) - len(bull) >= 2 
              else "NEUTRAL")
    
    return {
        "facts": facts,
        "interpretations": {
            "market_analyst": f"Trend {'up' if e20 > e50 else 'down'}, volatility {vol:.0f}% annualised.",
            "bull": bull,
            "bear": bear,
            "risk_analyst": f"Risk level {risk}. Suggest stop-loss ≥ {max(2, round(vol / 16, 1))}% of price.",
            "strategy_manager": f"{stance}. Evidence: {len(bull)} bullish vs {len(bear)} bearish. Research only — not advice."
        },
        "label": "AI-GENERATED INTERPRETATION · PAPER/SIMULATED"
    }


def compare_runs(runs: List) -> Dict[str, Any]:
    """Compare multiple research runs.
    
    Args:
        runs: List of ResearchRun objects with facts and interpretations
        
    Returns:
        Dictionary with comparison results including:
        - facts comparison across runs
        - interpretations comparison
        - risk observations
        - data provenance
        - summary
    """
    if len(runs) < 2:
        return {"error": "At least 2 runs required for comparison"}
    if len(runs) > 5:
        return {"error": "Maximum 5 runs for comparison"}
    
    comparison = {
        "facts": {},
        "interpretations": {},
        "risk": {},
        "provenance": {},
        "summary": ""
    }
    
    # Collect all unique fact keys
    all_fact_keys = set()
    for run in runs:
        if run.facts:
            all_fact_keys.update(run.facts.keys())
    
    # Compare facts
    for key in sorted(all_fact_keys):
        comparison["facts"][key] = {}
        for run in runs:
            val = run.facts.get(key) if run.facts else None
            comparison["facts"][key][f"run_{run.id}"] = val
    
    # Compare interpretations
    for run in runs:
        run_key = f"run_{run.id}"
        comparison["interpretations"][run_key] = run.interpretations or {}
    
    # Compare risk
    for run in runs:
        run_key = f"run_{run.id}"
        interpretations = run.interpretations or {}
        risk_text = interpretations.get("risk_analyst", "")
        comparison["risk"][run_key] = risk_text
    
    # Compare provenance
    for run in runs:
        run_key = f"run_{run.id}"
        comparison["provenance"][run_key] = {
            "data_source": run.data_source,
            "is_simulated": run.is_simulated,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "strategy_id": run.strategy_id,
            "backtest_run_id": run.backtest_run_id,
        }
    
    # Generate summary
    bull_counts = []
    bear_counts = []
    risk_levels = []
    
    for run in runs:
        interpretations = run.interpretations or {}
        bull_counts.append(len(interpretations.get("bull", [])))
        bear_counts.append(len(interpretations.get("bear", [])))
        risk_text = interpretations.get("risk_analyst", "")
        if "HIGH" in risk_text:
            risk_levels.append("HIGH")
        elif "MODERATE" in risk_text:
            risk_levels.append("MODERATE")
        else:
            risk_levels.append("LOW")
    
    if bull_counts and bear_counts:
        max_bull = max(bull_counts)
        max_bear = max(bear_counts)
        avg_risk = max(set(risk_levels), key=risk_levels.count) if risk_levels else "UNKNOWN"
        
        comparison["summary"] = (
            f"Compared {len(runs)} research runs. "
            f"Max bullish signals: {max_bull}, max bearish signals: {max_bear}. "
            f"Predominant risk level: {avg_risk}. "
            f"Recommend reviewing individual agent findings for details."
        )
    else:
        comparison["summary"] = f"Compared {len(runs)} research runs. Insufficient interpretation data for detailed summary."
    
    return comparison
