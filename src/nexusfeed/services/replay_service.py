import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, List

from fastapi import WebSocket
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from nexusfeed.storage.models import Trade, OrderbookSnapshot


def _to_dt(v):
    if isinstance(v, datetime):
        return v.astimezone(timezone.utc)
    if isinstance(v, (int, float)):
        if v > 1e12:
            return datetime.fromtimestamp(v / 1000, tz=timezone.utc)
        return datetime.fromtimestamp(v, tz=timezone.utc)
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except Exception:
            return datetime.now(timezone.utc)
    return datetime.now(timezone.utc)


sessions: Dict[str, Dict] = {}


def create_session(instrument: str, from_ts, to_ts, speed: float = 1.0) -> str:
    sid = uuid.uuid4().hex
    sessions[sid] = {
        "instrument": instrument,
        "from_ts": _to_dt(from_ts),
        "to_ts": _to_dt(to_ts),
        "speed": float(speed) if speed else 1.0,
    }
    return sid


def get_session(sid: str) -> Optional[Dict]:
    return sessions.get(sid)


def remove_session(sid: str) -> None:
    sessions.pop(sid, None)


async def stream_replay(session: AsyncSession, ws: WebSocket, instrument: str, from_ts, to_ts, speed: float = 1.0):
    start = _to_dt(from_ts)
    end = _to_dt(to_ts)
    t_res = await session.exec(
        select(Trade).where(
            Trade.instrument == instrument,
            Trade.ts >= start,
            Trade.ts <= end,
        ).order_by(Trade.ts)
    )
    s_res = await session.exec(
        select(OrderbookSnapshot).where(
            OrderbookSnapshot.instrument == instrument,
            OrderbookSnapshot.ts >= start,
            OrderbookSnapshot.ts <= end,
        ).order_by(OrderbookSnapshot.ts)
    )
    trades: List[Trade] = t_res.all()
    snaps: List[OrderbookSnapshot] = s_res.all()
    events = []
    for t in trades:
        events.append({
            "type": "trade",
            "source": t.source,
            "instrument": t.instrument,
            "trade_id": t.trade_id,
            "price": t.price,
            "size": t.size,
            "side": t.side,
            "timestamp": t.ts.isoformat(),
        })
    for b in snaps:
        events.append({
            "type": "book",
            "source": b.source,
            "instrument": b.instrument,
            "sequence": b.sequence,
            "bids": b.bids,
            "asks": b.asks,
            "timestamp": b.ts.isoformat(),
        })
    events.sort(key=lambda e: e["timestamp"])
    prev = None
    for e in events:
        cur = _to_dt(e["timestamp"])
        if prev is not None:
            delta = (cur - prev).total_seconds()
            wait = delta / (speed if speed else 1.0)
            if wait > 0:
                await asyncio.sleep(wait)
        await ws.send_json(e)
        prev = cur

__all__ = [
    "create_session",
    "get_session",
    "remove_session",
    "stream_replay",
]