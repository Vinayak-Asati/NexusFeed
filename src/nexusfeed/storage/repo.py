import asyncio
from datetime import datetime, timezone
from typing import List, Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from .db import get_engine
from .models import Trade, OrderbookSnapshot
from nexusfeed.utils.metrics import trades_ingested_total, db_write_latency_seconds


def _to_dt(value):
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    if isinstance(value, (int, float)):
        if value > 1e12:
            return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return datetime.now(timezone.utc)
    return datetime.now(timezone.utc)


class Repo:
    def __init__(self, engine=None, batch_size: int = 100, flush_interval: float = 1.0):
        self.engine = engine or get_engine()
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._batch: List[Trade] = []
        self._lock = asyncio.Lock()
        self._shutdown = asyncio.Event()
        self._worker = asyncio.create_task(self._run())

    async def insert_trade(self, trade: dict) -> None:
        t = Trade(
            source=trade.get("source"),
            instrument=trade.get("instrument"),
            trade_id=trade.get("trade_id"),
            price=float(trade.get("price")),
            size=float(trade.get("size")),
            side=trade.get("side"),
            ts=_to_dt(trade.get("timestamp") or trade.get("ts")),
        )
        async with self._lock:
            self._batch.append(t)
            if len(self._batch) >= self.batch_size:
                await self._flush_locked()

    async def insert_snapshot(self, snapshot: dict) -> None:
        async with AsyncSession(self.engine) as session:
            src = snapshot.get("source")
            instr = snapshot.get("instrument")
            seq = snapshot.get("sequence")
            bids = snapshot.get("bids") or []
            asks = snapshot.get("asks") or []
            ts = _to_dt(snapshot.get("timestamp") or snapshot.get("ts"))
            res = await session.exec(
                select(OrderbookSnapshot).where(
                    OrderbookSnapshot.source == src,
                    OrderbookSnapshot.instrument == instr,
                )
            )
            existing = res.first()
            if existing:
                existing.sequence = seq
                existing.bids = bids
                existing.asks = asks
                existing.ts = ts
                session.add(existing)
            else:
                obj = OrderbookSnapshot(
                    source=src,
                    instrument=instr,
                    sequence=seq,
                    bids=bids,
                    asks=asks,
                    ts=ts,
                )
                session.add(obj)
            await session.commit()

    async def shutdown(self) -> None:
        self._shutdown.set()
        try:
            await self._worker
        except Exception:
            pass
        async with self._lock:
            if self._batch:
                await self._flush_locked()

    async def _run(self):
        while not self._shutdown.is_set():
            await asyncio.sleep(self.flush_interval)
            async with self._lock:
                if self._batch:
                    await self._flush_locked()

    async def _flush_locked(self):
        if not self._batch:
            return
        to_flush = list(self._batch)
        self._batch.clear()
        async with AsyncSession(self.engine) as session:
            with db_write_latency_seconds.labels(operation="trade_flush").time():
                for t in to_flush:
                    session.add(t)
                await session.commit()
            try:
                trades_ingested_total.inc(len(to_flush))
            except Exception:
                pass

__all__ = ["Repo"]