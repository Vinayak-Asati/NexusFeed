from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field


class Trade(SQLModel, table=True):
    __tablename__ = "trades"
    id: Optional[int] = Field(default=None, primary_key=True)
    source: str = Field(index=True)
    instrument: str = Field(index=True)
    trade_id: Optional[str] = Field(default=None, index=True)
    price: float
    size: float
    side: Optional[str] = Field(default=None)
    ts: datetime
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OrderbookSnapshot(SQLModel, table=True):
    __tablename__ = "orderbook_snapshots"
    id: Optional[int] = Field(default=None, primary_key=True)
    source: str = Field(index=True)
    instrument: str = Field(index=True)
    sequence: Optional[int] = Field(default=None)
    bids: List[List[float]] = Field(sa_column=Column(JSON))
    asks: List[List[float]] = Field(sa_column=Column(JSON))
    ts: datetime