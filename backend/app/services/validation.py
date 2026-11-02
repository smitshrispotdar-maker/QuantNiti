"""Mandatory deterministic validation gate. Nothing deploys unless errors == []."""
from ..schemas import StrategySpec
def validate(spec: StrategySpec, metrics: dict | None = None) -> dict:
    errors, warnings = [], []
    ids = {i.id for i in spec.indicators} | {"price"}
    if not spec.instruments: errors.append("No instruments selected.")
    if not spec.entry_rules: errors.append("Strategy has no entry rule.")
    if not spec.exit_rules and not spec.risk.stop_loss_pct: errors.append("Need an exit rule or a stop-loss.")
    for r in spec.entry_rules + spec.exit_rules:
        for side in (r.left, r.right):
            if isinstance(side, str) and side not in ids: errors.append(f"Rule references unknown indicator '{side}'.")
    if spec.risk.max_position_pct > 50: warnings.append("Position size above 50% of equity is aggressive.")
    if metrics:
        if metrics["trades"] < 5: errors.append(f"Only {metrics['trades']} backtest trades — too few to trust (min 5).")
        if abs(metrics["max_drawdown_pct"]) > spec.risk.max_drawdown_pct:
            errors.append(f"Backtest drawdown {metrics['max_drawdown_pct']}% exceeds your limit of {spec.risk.max_drawdown_pct}%.")
    else: errors.append("Run a backtest before deployment.")
    return {"passed": not errors, "errors": errors, "warnings": warnings}
