"""Personal watchlist API — India-only, persisted per user."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..db import get_db
from ..models import WatchlistItem, User
from ..services import market as m
from ..services import instruments as inst
from ..schemas import WatchlistAdd, WatchlistItemResponse, WatchlistResponse, SymbolInfo
from ..services.auth import get_current_user_dep

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


def _resolve_or_400(symbol: str) -> str:
    resolved = inst.resolve_symbol(symbol)
    if not resolved:
        raise HTTPException(status_code=400, detail=f"Unsupported instrument: {symbol}. QuantNiti supports NSE/BSE instruments only.")
    return resolved


def _quote_fields(symbol: str) -> dict:
    try:
        q = m.quote(symbol)
        return {
            "price": q.get("price"),
            "change": q.get("change"),
            "change_pct": q.get("change_pct"),
            "status": q.get("status", "UNAVAILABLE"),
            "provider": q.get("provider"),
            "exchange": q.get("exchange", inst.exchange_for(symbol)),
            "last_bar": q.get("last_bar"),
            "reason": None if q.get("available", True) else (q.get("reason") or "Provider unavailable"),
        }
    except Exception as e:
        return _unavailable_fields(symbol, str(e)[:160])


def _unavailable_fields(symbol: str, reason: str) -> dict:
    return {
        "price": None, "change": None, "change_pct": None,
        "status": "UNAVAILABLE", "provider": None,
        "exchange": inst.exchange_for(symbol), "last_bar": None, "reason": reason,
    }


def _fields_from_quote(symbol: str, q: dict) -> dict:
    return {
        "price": q.get("price"),
        "change": q.get("change"),
        "change_pct": q.get("change_pct"),
        "status": q.get("status", "UNAVAILABLE"),
        "provider": q.get("provider"),
        "exchange": q.get("exchange", inst.exchange_for(symbol)),
        "last_bar": q.get("last_bar"),
        "reason": None if q.get("available", True) else (q.get("reason") or "Provider unavailable"),
    }


def _responses(items: List[WatchlistItem]) -> List[WatchlistItemResponse]:
    """Serialize a watchlist using one batched provider request."""
    try:
        quotes = m.quotes_batch([i.symbol for i in items]) if items else {}
    except Exception as e:
        quotes = {i.symbol: _unavailable_fields(i.symbol, str(e)[:160]) for i in items}
    return [_response(i, quotes.get(i.symbol)) for i in items]


def _response(item: WatchlistItem, quote_fields: dict = None) -> WatchlistItemResponse:
    q = quote_fields or _quote_fields(item.symbol)
    return WatchlistItemResponse(
        id=item.id,
        symbol=item.symbol,
        name=inst.name_for(item.symbol),
        price=q["price"],
        change=q["change"],
        change_pct=q["change_pct"],
        status=q["status"],
        provider=q["provider"],
        exchange=q["exchange"],
        last_bar=q["last_bar"],
        reason=q["reason"],
        created_at=item.created_at,
    )


@router.get("", response_model=WatchlistResponse)
def get_watchlist(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dep),
):
    """Get the current user's watchlist with current quotes.

    New users receive the default Indian watchlist on first access. Existing
    items are preserved; legacy non-Indian entries are hidden (not deleted) so
    they cannot leak into the India-only terminal.
    """
    items = db.query(WatchlistItem).filter(WatchlistItem.user_id == current_user.id).order_by(WatchlistItem.position, WatchlistItem.id).all()
    if not items:
        for pos, symbol in enumerate(inst.DEFAULT_WATCHLIST):
            db.add(WatchlistItem(user_id=current_user.id, symbol=symbol, position=pos))
        db.commit()
        items = db.query(WatchlistItem).filter(WatchlistItem.user_id == current_user.id).order_by(WatchlistItem.position, WatchlistItem.id).all()

    legacy = [i for i in items if not inst.is_supported(i.symbol)]
    visible = [i for i in items if inst.is_supported(i.symbol)]
    return WatchlistResponse(
        items=_responses(visible),
        hidden_legacy_symbols=[i.symbol for i in legacy],
    )


@router.post("", response_model=WatchlistItemResponse, status_code=status.HTTP_201_CREATED)
def add_to_watchlist(
    payload: WatchlistAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dep),
):
    """Add an Indian instrument to the user's watchlist."""
    symbol = _resolve_or_400(payload.symbol)

    existing = db.query(WatchlistItem).filter(
        WatchlistItem.user_id == current_user.id,
        WatchlistItem.symbol == symbol,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"{inst.name_for(symbol)} is already in your watchlist")

    max_pos = db.query(WatchlistItem).filter(WatchlistItem.user_id == current_user.id).count()
    item = WatchlistItem(user_id=current_user.id, symbol=symbol, position=max_pos)
    db.add(item)
    try:
        db.commit()
        db.refresh(item)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"{inst.name_for(symbol)} is already in your watchlist")

    return _response(item)


@router.delete("/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_watchlist(
    symbol: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dep),
):
    """Remove an instrument from the user's watchlist."""
    symbol = inst.resolve_symbol(symbol) or symbol.upper()
    item = db.query(WatchlistItem).filter(
        WatchlistItem.user_id == current_user.id,
        WatchlistItem.symbol == symbol,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"{symbol} is not in your watchlist")
    db.delete(item)
    db.commit()


@router.put("/reorder", response_model=WatchlistResponse)
def reorder_watchlist(
    symbols: List[str] = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dep),
):
    """Persist watchlist ordering. Unknown symbols are ignored."""
    canonical = [inst.resolve_symbol(s) for s in symbols]
    canonical = [s for s in canonical if s]
    items = db.query(WatchlistItem).filter(WatchlistItem.user_id == current_user.id).all()
    by_symbol = {i.symbol: i for i in items}
    for pos, symbol in enumerate(canonical):
        if symbol in by_symbol:
            by_symbol[symbol].position = pos
    # Keep any items not present in the payload after the requested order.
    next_pos = len(canonical)
    for item in items:
        if item.symbol not in canonical and inst.is_supported(item.symbol):
            item.position = next_pos
            next_pos += 1
    db.commit()
    ordered = db.query(WatchlistItem).filter(WatchlistItem.user_id == current_user.id).order_by(WatchlistItem.position, WatchlistItem.id).all()
    visible = [i for i in ordered if inst.is_supported(i.symbol)]
    return WatchlistResponse(items=_responses(visible), hidden_legacy_symbols=[])


@router.get("/symbols", response_model=List[SymbolInfo])
def get_supported_symbols():
    """All supported Indian instruments with metadata."""
    return [
        {
            "symbol": item["symbol"],
            "name": item["name"],
            "timezone": "Asia/Kolkata",
            "exchange": item["exchange"],
            "kind": item["kind"],
            "available": bool(item.get("yahoo")),
            "reason": inst.unavailable_reason(item["symbol"]),
        }
        for item in inst.INSTRUMENTS
    ]
