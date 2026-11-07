"""Rule-based natural-language → StrategySpec parser (no LLM key needed). Pure function; never executes anything.
Returns (spec, clarifications). Swap in any LLM by making it emit StrategySpec JSON — it is validated by Pydantic regardless.
Also detects special actions: backtest, deploy, explain."""
import re
from ..schemas import StrategySpec, IndicatorSpec, Rule, RiskLimits
# India-only aliases. Canonical symbols match services.instruments.
TICKERS = {
    "nifty 50": "^NSEI", "nifty50": "^NSEI", "nifty": "^NSEI",
    "bank nifty": "^NSEBANK", "banknifty": "^NSEBANK", "^NSEBANK": "^NSEBANK",
    "finnifty": "NIFTY_FIN_SERVICE.NS", "financial services": "NIFTY_FIN_SERVICE.NS",
    "india vix": "^INDIAVIX", "indiavix": "^INDIAVIX", "vix": "^INDIAVIX",
    "reliance": "RELIANCE.NS", "ril": "RELIANCE.NS",
    "tcs": "TCS.NS", "infosys": "INFY.NS", "infy": "INFY.NS",
    "hdfc bank": "HDFCBANK.NS", "hdfcbank": "HDFCBANK.NS",
    "icici bank": "ICICIBANK.NS", "icicibank": "ICICIBANK.NS",
    "sbi": "SBIN.NS", "state bank": "SBIN.NS", "sbin": "SBIN.NS",
}
TF = {"daily": "1d", "day": "1d", "1d": "1d", "hourly": "1h", "1h": "1h", "15m": "15m", "5m": "5m", "1m": "1m"}
ACTION_KEYWORDS = {
    "backtest": ["backtest", "run backtest", "test strategy", "simulate", "back test"],
    "deploy": ["deploy", "paper trade", "start paper", "go live", "activate"],
    "explain": ["explain", "what is", "describe", "summarize", "show me", "current strategy"],
}
def _detect_action(text: str) -> tuple[str | None, dict]:
    """Detect if user wants to perform a special action."""
    t = text.lower()
    for action, keywords in ACTION_KEYWORDS.items():
        for kw in keywords:
            if kw in t:
                return action, {}
    return None, {}
def parse(text: str, base: StrategySpec | None = None):
    t = text.lower(); spec = base.model_copy(deep=True) if base else StrategySpec(); ask = []
    # Match longer aliases first and mask matched spans so "bank nifty" does not
    # also match the shorter "nifty" alias.
    for w in sorted((k for k in TICKERS if not k.startswith("^")), key=len, reverse=True):
        pattern = rf"\b{re.escape(w.lower())}\b"
        if re.search(pattern, t):
            sym = TICKERS[w]
            if sym not in spec.instruments:
                spec.instruments.append(sym)
            t = re.sub(pattern, lambda m: " " * len(m.group(0)), t)
    for w, tf in TF.items():
        if re.search(rf"\b{w}\b", t): spec.timeframe = tf
    ind = {i.id: i for i in spec.indicators}
    def add(type_, period, id_=None):
        id_ = id_ or f"{type_.lower()}_{int(period)}"
        if id_ not in ind: ind[id_] = IndicatorSpec(id=id_, type=type_, params={"period": float(period)})
        return id_
    entry, exit_ = [], []
    for m in re.finditer(r"(sma|ema)\s*(\d+)\s*(?:crosses|cross|crossing)?\s*(above|over|below|under)\s*(?:the\s*)?(sma|ema)?\s*(\d+)", t):
        a = add(m[1].upper(), m[2]); b = add((m[4] or m[1]).upper(), m[5])
        up = m[3] in ("above", "over")
        entry.append(Rule(left=a, op="crosses_above" if up else "crosses_below", right=b))
        exit_.append(Rule(left=a, op="crosses_below" if up else "crosses_above", right=b))
    for m in re.finditer(r"rsi(?:\s*\(?(\d+)\)?)?\s*(?:is\s*)?(below|under|above|over|<|>)\s*(\d+)", t):
        i = add("RSI", m[1] or 14, "rsi_" + str(m[1] or 14)); low = m[2] in ("below", "under", "<")
        ctx = t[max(0, m.start() - 25):m.start()]
        (exit_ if re.search(r"\b(exit|sell|close)\b", ctx) else entry).append(Rule(left=i, op="<" if low else ">", right=float(m[3])))
    m = re.search(r"stop[- ]?loss(?: of)?\s*(\d+(?:\.\d+)?)\s*%", t) or re.search(r"(\d+(?:\.\d+)?)\s*%\s*stop", t)
    if m: spec.risk.stop_loss_pct = float(m[1])
    m = re.search(r"take[- ]?profit(?: of)?\s*(\d+(?:\.\d+)?)\s*%", t)
    if m: spec.risk.take_profit_pct = float(m[1])
    m = re.search(r"(?:size|position|risk)\D{0,12}(\d+(?:\.\d+)?)\s*%", t)
    if m: spec.risk.max_position_pct = float(m[1])
    spec.indicators = list(ind.values()); spec.entry_rules += entry; spec.exit_rules += exit_
    if re.search(r"\b(buy|long)\b", t) and re.search(r"\b(short|sell short)\b", t): ask.append("You mention both long and short. This MVP supports long-only — should I keep long only?")
    if "rsi" in t and re.search(r"rsi[^.]*(below|under)[^.]*(sell|exit)", t): ask.append("Selling when RSI is low contradicts typical mean-reversion. Did you mean above?")
    if not spec.instruments: ask.append("Which Indian instrument? (e.g. NIFTY 50, BANK NIFTY, RELIANCE, TCS, INFY)")
    if not spec.entry_rules: ask.append("What should trigger an entry? e.g. 'buy when RSI is below 30' or 'EMA 20 crosses above EMA 50'.")
    if not spec.exit_rules and not spec.risk.stop_loss_pct: ask.append("What should trigger an exit? A stop-loss is set at " + f"{spec.risk.stop_loss_pct}% by default.")
    return spec, ask

def detect_action(text: str) -> tuple[str | None, dict]:
    """Public function to detect special actions."""
    return _detect_action(text)