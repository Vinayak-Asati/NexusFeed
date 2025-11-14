import asyncio
from datetime import datetime, timezone

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from nexusfeed.storage.db import init_db, async_engine
from nexusfeed.storage.models import Trade
from nexusfeed.storage.repo import Repo


async def main(n: int = 25):
    await init_db()
    repo = Repo(batch_size=10, flush_interval=0.1)

    for i in range(n):
        await repo.insert_trade({
            "source": "binance",
            "instrument": "BTC/USDT",
            "trade_id": f"t-{i}",
            "price": 35000.0 + i,
            "size": 0.01,
            "side": "buy" if i % 2 == 0 else "sell",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    await repo.shutdown()

    async with AsyncSession(async_engine) as session:
        rows = (await session.exec(select(Trade))).all()
        print("expected", n)
        print("actual", len(rows))
        print("ok", len(rows) == n)


if __name__ == "__main__":
    asyncio.run(main())