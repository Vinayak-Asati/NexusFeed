import asyncio
from datetime import datetime, timezone

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from nexusfeed.storage.db import init_db, async_engine
from nexusfeed.storage.models import Trade


async def main():
    await init_db()
    async with AsyncSession(async_engine) as session:
        trade = Trade(
            source="binance",
            instrument="BTC/USDT",
            trade_id="t1",
            price=34000.5,
            size=0.01,
            side="buy",
            ts=datetime.now(timezone.utc),
        )
        session.add(trade)
        await session.commit()

        res = await session.exec(select(Trade))
        rows = res.all()
        print("trades_count", len(rows))


if __name__ == "__main__":
    asyncio.run(main())