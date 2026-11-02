"""Watchlist API endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..db import get_db
from ..models import WatchlistItem, User
from ..services import market as m
from ..schemas import WatchlistAdd, WatchlistItemResponse, WatchlistResponse, SymbolInfo

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


def get_current_user(db: Session = Depends(get_db)) -> User:
    """Get the current user (MVP: single seeded user)."""
    user = db.get(User, 1)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("", response_model=WatchlistResponse)
def get_watchlist(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get the current user's watchlist with current prices."""
    items = db.query(WatchlistItem).filter(WatchlistItem.user_id == user.id).all()
    
    items_with_price = []
    for item in items:
        try:
            df, meta = m.get_bars(item.symbol, "1d", 60)
            price = round(df.close.iloc[-1], 2)
            change_pct = round((df.close.iloc[-1] / df.close.iloc[-2] - 1) * 100, 2)
        except Exception:
            price = 0.0
            change_pct = 0.0
        
        items_with_price.append(WatchlistItemResponse(
            id=item.id,
            symbol=item.symbol,
            name=m.SYMBOL_NAMES.get(item.symbol, item.symbol),
            created_at=item.created_at,
        ))
    
    return WatchlistResponse(items=items_with_price)


@router.post("", response_model=WatchlistItemResponse, status_code=status.HTTP_201_CREATED)
def add_to_watchlist(
    payload: WatchlistAdd,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Add a symbol to the user's watchlist."""
    symbol = payload.symbol.upper().replace("/", "-")
    
    # Validate symbol format
    if not symbol or len(symbol) > 20:
        raise HTTPException(status_code=400, detail="Invalid symbol format")
    
    # Check if symbol is supported (either in watchlist or searchable)
    supported_symbols = set(m.WATCHLIST + ["MSFT", "TSLA", "QQQ", "SOL-USD"])
    if symbol not in supported_symbols:
        raise HTTPException(status_code=400, detail=f"Unsupported symbol: {symbol}")
    
    # Check if already in watchlist
    existing = db.query(WatchlistItem).filter(
        WatchlistItem.user_id == user.id,
        WatchlistItem.symbol == symbol
    ).first()
    
    if existing:
        raise HTTPException(status_code=409, detail=f"Symbol {symbol} already in watchlist")
    
    # Create new watchlist item
    item = WatchlistItem(user_id=user.id, symbol=symbol)
    db.add(item)
    
    try:
        db.commit()
        db.refresh(item)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Symbol {symbol} already in watchlist")
    
    return WatchlistItemResponse(
        id=item.id,
        symbol=item.symbol,
        name=m.SYMBOL_NAMES.get(item.symbol, item.symbol),
        created_at=item.created_at,
    )


@router.delete("/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_watchlist(
    symbol: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Remove a symbol from the user's watchlist."""
    symbol = symbol.upper().replace("/", "-")
    
    item = db.query(WatchlistItem).filter(
        WatchlistItem.user_id == user.id,
        WatchlistItem.symbol == symbol
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not in watchlist")
    
    db.delete(item)
    db.commit()


@router.get("/symbols", response_model=List[SymbolInfo])
def get_supported_symbols():
    """Get all supported symbols with metadata."""
    return [
        {
            "symbol": s,
            "name": m.SYMBOL_NAMES.get(s, s),
            "timezone": m.EXCHANGE_TIMEZONES.get(s, "UTC"),
        }
        for s in m.WATCHLIST
    ]