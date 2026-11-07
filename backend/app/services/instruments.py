"""India-only instrument catalogue and market-session helpers.

QuantNiti is restricted to NSE / BSE instruments.  This module is the single
source of truth for:
  * the supported instrument universe (indices + NSE/BSE stocks)
  * symbol aliases used by search / the AI studio
  * exchange + market-session metadata

The canonical symbol is the Yahoo Finance ticker (e.g. ``^NSEI``,
``RELIANCE.NS``) because the existing market-data provider is Yahoo Finance.
Presentation names (NIFTY 50, RELIANCE, ...) are kept separately so the UI can
show Indian market names without leaking provider tickers everywhere.
"""
from __future__ import annotations

import math
from datetime import datetime, time, timedelta
from typing import Any, Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

# ---------------------------------------------------------------------------
# Instrument universe
# ---------------------------------------------------------------------------
# ``yahoo`` is None when the configured provider does not expose the index.
# We deliberately keep those instruments searchable but mark them UNAVAILABLE
# instead of fabricating prices.
INSTRUMENTS: List[Dict[str, Any]] = [
    # ---- NSE indices -----------------------------------------------------
    {"symbol": "^NSEI", "name": "NIFTY 50", "exchange": "NSE", "kind": "index",
     "yahoo": "^NSEI", "aliases": ["nifty", "nifty50", "nifty 50", "nsei"], "default": True},
    {"symbol": "^NSEBANK", "name": "BANK NIFTY", "exchange": "NSE", "kind": "index",
     "yahoo": "^NSEBANK", "aliases": ["banknifty", "bank nifty", "nsebank"], "default": True},
    {"symbol": "NIFTY_FIN_SERVICE.NS", "name": "FINNIFTY", "exchange": "NSE", "kind": "index",
     "yahoo": "NIFTY_FIN_SERVICE.NS", "aliases": ["finnifty", "financial services", "fin nifty"], "default": True},
    {"symbol": "NIFTY_NEXT_50", "name": "NIFTY NEXT 50", "exchange": "NSE", "kind": "index",
     "yahoo": None, "aliases": ["nifty next 50", "next50", "junior nifty"], "default": False,
     "unavailable_reason": "The configured market-data provider does not expose NIFTY NEXT 50."},
    {"symbol": "^NSMIDCP", "name": "NIFTY MIDCAP 100", "exchange": "NSE", "kind": "index",
     "yahoo": "^NSMIDCP", "aliases": ["midcap", "nifty midcap", "midcap100"], "default": False},
    {"symbol": "^INDIAVIX", "name": "INDIA VIX", "exchange": "NSE", "kind": "index",
     "yahoo": "^INDIAVIX", "aliases": ["vix", "india vix", "indiavix"], "default": True},
    {"symbol": "^CNXFIN", "name": "NIFTY FINANCIAL SERVICES", "exchange": "NSE", "kind": "index",
     "yahoo": "^CNXFIN", "aliases": ["nifty financial", "cnxfin"], "default": False},
    {"symbol": "^CNXIT", "name": "NIFTY IT", "exchange": "NSE", "kind": "index",
     "yahoo": "^CNXIT", "aliases": ["nifty it", "cnxit"], "default": False},

    # ---- NSE large-cap stocks (default watchlist) ------------------------
    {"symbol": "RELIANCE.NS", "name": "RELIANCE", "exchange": "NSE", "kind": "stock",
     "yahoo": "RELIANCE.NS", "aliases": ["reliance", "ril"], "default": True},
    {"symbol": "TCS.NS", "name": "TCS", "exchange": "NSE", "kind": "stock",
     "yahoo": "TCS.NS", "aliases": ["tcs", "tata consultancy"], "default": True},
    {"symbol": "INFY.NS", "name": "INFY", "exchange": "NSE", "kind": "stock",
     "yahoo": "INFY.NS", "aliases": ["infosys", "infy"], "default": True},
    {"symbol": "HDFCBANK.NS", "name": "HDFCBANK", "exchange": "NSE", "kind": "stock",
     "yahoo": "HDFCBANK.NS", "aliases": ["hdfc bank", "hdfcbank"], "default": True},
    {"symbol": "ICICIBANK.NS", "name": "ICICIBANK", "exchange": "NSE", "kind": "stock",
     "yahoo": "ICICIBANK.NS", "aliases": ["icici bank", "icicibank"], "default": True},
    {"symbol": "SBIN.NS", "name": "SBIN", "exchange": "NSE", "kind": "stock",
     "yahoo": "SBIN.NS", "aliases": ["sbi", "state bank", "sbin"], "default": True},

    # ---- Additional liquid NSE names (movers / search) -------------------
    {"symbol": "BHARTIARTL.NS", "name": "BHARTIARTL", "exchange": "NSE", "kind": "stock",
     "yahoo": "BHARTIARTL.NS", "aliases": ["airtel", "bharti"], "default": False},
    {"symbol": "ITC.NS", "name": "ITC", "exchange": "NSE", "kind": "stock",
     "yahoo": "ITC.NS", "aliases": ["itc"], "default": False},
    {"symbol": "LT.NS", "name": "LARSEN & TOUBRO", "exchange": "NSE", "kind": "stock",
     "yahoo": "LT.NS", "aliases": ["l&t", "larsen", "lt"], "default": False},
    {"symbol": "KOTAKBANK.NS", "name": "KOTAKBANK", "exchange": "NSE", "kind": "stock",
     "yahoo": "KOTAKBANK.NS", "aliases": ["kotak"], "default": False},
    {"symbol": "AXISBANK.NS", "name": "AXISBANK", "exchange": "NSE", "kind": "stock",
     "yahoo": "AXISBANK.NS", "aliases": ["axis bank", "axis"], "default": False},
    {"symbol": "HINDUNILVR.NS", "name": "HINDUNILVR", "exchange": "NSE", "kind": "stock",
     "yahoo": "HINDUNILVR.NS", "aliases": ["hindustan unilever", "hul"], "default": False},
    {"symbol": "BAJFINANCE.NS", "name": "BAJFINANCE", "exchange": "NSE", "kind": "stock",
     "yahoo": "BAJFINANCE.NS", "aliases": ["bajaj finance"], "default": False},
    {"symbol": "MARUTI.NS", "name": "MARUTI", "exchange": "NSE", "kind": "stock",
     "yahoo": "MARUTI.NS", "aliases": ["maruti suzuki"], "default": False},
    {"symbol": "ASIANPAINT.NS", "name": "ASIANPAINT", "exchange": "NSE", "kind": "stock",
     "yahoo": "ASIANPAINT.NS", "aliases": ["asian paints"], "default": False},
    {"symbol": "TATAMOTORS.NS", "name": "TATAMOTORS", "exchange": "NSE", "kind": "stock",
     "yahoo": "TATAMOTORS.NS", "aliases": ["tata motors"], "default": False},
    {"symbol": "SUNPHARMA.NS", "name": "SUNPHARMA", "exchange": "NSE", "kind": "stock",
     "yahoo": "SUNPHARMA.NS", "aliases": ["sun pharma"], "default": False},
    {"symbol": "WIPRO.NS", "name": "WIPRO", "exchange": "NSE", "kind": "stock",
     "yahoo": "WIPRO.NS", "aliases": ["wipro"], "default": False},
    {"symbol": "ADANIENT.NS", "name": "ADANIENT", "exchange": "NSE", "kind": "stock",
     "yahoo": "ADANIENT.NS", "aliases": ["adani enterprises", "adani"], "default": False},
    {"symbol": "TITAN.NS", "name": "TITAN", "exchange": "NSE", "kind": "stock",
     "yahoo": "TITAN.NS", "aliases": ["titan company"], "default": False},
    {"symbol": "NTPC.NS", "name": "NTPC", "exchange": "NSE", "kind": "stock",
     "yahoo": "NTPC.NS", "aliases": ["ntpc"], "default": False},
    {"symbol": "POWERGRID.NS", "name": "POWERGRID", "exchange": "NSE", "kind": "stock",
     "yahoo": "POWERGRID.NS", "aliases": ["power grid"], "default": False},

    # ---- BSE listings ----------------------------------------------------
    {"symbol": "RELIANCE.BO", "name": "RELIANCE (BSE)", "exchange": "BSE", "kind": "stock",
     "yahoo": "RELIANCE.BO", "aliases": ["reliance bse"], "default": False},
    {"symbol": "TCS.BO", "name": "TCS (BSE)", "exchange": "BSE", "kind": "stock",
     "yahoo": "TCS.BO", "aliases": ["tcs bse"], "default": False},
    {"symbol": "INFY.BO", "name": "INFY (BSE)", "exchange": "BSE", "kind": "stock",
     "yahoo": "INFY.BO", "aliases": ["infosys bse"], "default": False},
    {"symbol": "HDFCBANK.BO", "name": "HDFCBANK (BSE)", "exchange": "BSE", "kind": "stock",
     "yahoo": "HDFCBANK.BO", "aliases": ["hdfc bank bse"], "default": False},
    {"symbol": "SBIN.BO", "name": "SBIN (BSE)", "exchange": "BSE", "kind": "stock",
     "yahoo": "SBIN.BO", "aliases": ["sbi bse"], "default": False},
]

_BY_SYMBOL: Dict[str, Dict[str, Any]] = {}
_ALIASES: Dict[str, str] = {}
for _item in INSTRUMENTS:
    _BY_SYMBOL[_item["symbol"].upper()] = _item
    _ALIASES[_item["symbol"].lower()] = _item["symbol"]
    _ALIASES[_item["name"].lower()] = _item["symbol"]
    for _alias in _item.get("aliases", []):
        _ALIASES[_alias.lower()] = _item["symbol"]

# Every symbol that the UI / API may return.  Only Indian instruments.
SUPPORTED_INSTRUMENTS = set(_BY_SYMBOL.keys())
# Required default watchlist order for new users.
DEFAULT_WATCHLIST = [
    "^NSEI",                  # NIFTY 50
    "^NSEBANK",               # BANK NIFTY
    "NIFTY_FIN_SERVICE.NS",   # FINNIFTY
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "^INDIAVIX",              # INDIA VIX
]
NIFTY_SYMBOL = "^NSEI"

# Symbols used to compute market movers.  Kept modest to bound provider calls.
MOVERS_UNIVERSE = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "LT.NS", "KOTAKBANK.NS",
    "AXISBANK.NS", "HINDUNILVR.NS", "BAJFINANCE.NS", "MARUTI.NS",
    "ASIANPAINT.NS", "TATAMOTORS.NS", "SUNPHARMA.NS", "WIPRO.NS",
    "ADANIENT.NS", "TITAN.NS", "NTPC.NS", "POWERGRID.NS",
]

# Public name / exchange lookups (re-exported by services.market for
# backwards-compatible imports).
SYMBOL_NAMES: Dict[str, str] = {i["symbol"]: i["name"] for i in INSTRUMENTS}
EXCHANGES: Dict[str, str] = {i["symbol"]: i["exchange"] for i in INSTRUMENTS}
PROVIDER_SYMBOLS: Dict[str, Optional[str]] = {i["symbol"]: i.get("yahoo") for i in INSTRUMENTS}


def get_instrument(symbol: str) -> Optional[Dict[str, Any]]:
    """Return catalogue metadata for a canonical symbol or alias."""
    if not symbol:
        return None
    raw = str(symbol).strip()
    item = _BY_SYMBOL.get(raw.upper())
    if item:
        return item
    resolved = _ALIASES.get(raw.lower())
    return _BY_SYMBOL.get(resolved.upper()) if resolved else None


def resolve_symbol(symbol: str) -> Optional[str]:
    """Resolve a user-entered name/alias to a canonical Indian symbol."""
    item = get_instrument(symbol)
    return item["symbol"] if item else None


def is_supported(symbol: str) -> bool:
    return resolve_symbol(symbol) is not None


def provider_symbol(symbol: str) -> Optional[str]:
    """Return the provider ticker, or ``None`` when coverage is unavailable."""
    item = get_instrument(symbol)
    if item is None:
        return None
    return item.get("yahoo")


def name_for(symbol: str) -> str:
    item = get_instrument(symbol)
    return item["name"] if item else str(symbol)


def exchange_for(symbol: str) -> str:
    item = get_instrument(symbol)
    return item["exchange"] if item else "NSE"


def timezone_for(_symbol: str) -> str:
    return "Asia/Kolkata"


def unavailable_reason(symbol: str) -> Optional[str]:
    item = get_instrument(symbol)
    if item is None:
        return "Instrument is not part of the supported NSE/BSE universe."
    if not item.get("yahoo"):
        return item.get("unavailable_reason") or "The configured market-data provider does not expose this instrument."
    return None


def search(query: str, limit: int = 25) -> List[Dict[str, Any]]:
    """Search the India-only universe by symbol, display name or alias."""
    q = (query or "").strip().lower()
    rows: List[Dict[str, Any]] = []
    for item in INSTRUMENTS:
        haystack = " ".join([
            item["symbol"].lower(), item["name"].lower(), item["exchange"].lower(),
            *[a.lower() for a in item.get("aliases", [])],
        ])
        if q and q not in haystack:
            continue
        rows.append({
            "symbol": item["symbol"],
            "name": item["name"],
            "exchange": item["exchange"],
            "kind": item["kind"],
            "timezone": "Asia/Kolkata",
            "available": bool(item.get("yahoo")),
            "reason": unavailable_reason(item["symbol"]),
        })
    # Default watchlist / exact matches first.
    rows.sort(key=lambda r: (not r["symbol"].lower().startswith(q), not r["available"], r["symbol"]))
    return rows[:limit]


def session_status(now: Optional[datetime] = None) -> Dict[str, Any]:
    """NSE/BSE cash-market session status in IST.

    This is an informational calendar helper, not an exchange feed.  Exchange
    holidays are not inferred here; the UI shows the clock status explicitly.
    """
    now = now or datetime.now(IST)
    if now.tzinfo is None:
        now = now.replace(tzinfo=IST)
    else:
        now = now.astimezone(IST)

    weekday = now.weekday()  # Monday=0
    t = now.time()
    pre_open = time(9, 0)
    open_ = time(9, 15)
    close = time(15, 30)

    if weekday >= 5:
        status, label = "CLOSED", "Weekend — markets closed"
    elif t < pre_open:
        status, label = "CLOSED", "Pre-market — markets closed"
    elif t < open_:
        status, label = "PRE_OPEN", "Pre-open session"
    elif t <= close:
        status, label = "OPEN", "Market open"
    else:
        status, label = "CLOSED", "Market closed"

    return {
        "status": status,
        "label": label,
        "exchange": "NSE / BSE",
        "timezone": "Asia/Kolkata",
        "ist_time": now.isoformat(),
        "open": "09:15",
        "close": "15:30",
        "is_open": status == "OPEN",
    }


def _num(value, ndigits: Optional[int] = 2) -> Optional[float]:
    """Coerce a provider value to a JSON-safe number (or ``None``)."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return round(number, ndigits) if ndigits is not None else number


def quote_summary(symbol: str, bars, meta: Dict[str, Any]) -> Dict[str, Any]:
    """Build an overview payload from the latest OHLCV bars.

    ``bars`` is a pandas DataFrame with open/high/low/close/volume columns.
    Missing values are returned as ``None``; nothing is invented.
    """
    item = get_instrument(symbol) or {}
    last = bars.iloc[-1] if len(bars) else None
    prev_close = _num(bars["close"].iloc[-2]) if len(bars) > 1 else None
    price = _num(last["close"]) if last is not None else None
    change = (price - prev_close) if price is not None and prev_close is not None else None
    change_pct = (change / prev_close * 100) if change is not None and prev_close else None
    status = meta.get("status", "UNAVAILABLE")
    simulated = status == "SIMULATED"
    return {
        "symbol": symbol,
        "name": item.get("name", name_for(symbol)),
        "exchange": item.get("exchange", exchange_for(symbol)),
        "kind": item.get("kind", "stock"),
        "price": _num(price),
        "change": _num(change),
        "change_pct": _num(change_pct),
        "open": _num(last["open"]) if last is not None else None,
        "high": _num(last["high"]) if last is not None else None,
        "low": _num(last["low"]) if last is not None else None,
        "prev_close": _num(prev_close),
        "volume": _num(last["volume"], None) if last is not None and "volume" in last else None,
        "last_bar": meta.get("last_bar"),
        "fetched_at": meta.get("fetched_at"),
        "provider": meta.get("source"),
        "status": status,
        "is_simulated": simulated,
        "is_live": status == "LIVE",
        "available": status != "UNAVAILABLE",
        "reason": (
            (meta.get("data_quality", {}).get("issues") or [None])[0]
            or unavailable_reason(symbol)
            if status == "UNAVAILABLE"
            else None
        ),
        "timeframe": meta.get("timeframe"),
        "market_session": session_status(),
    }
