import asyncio
from datetime import datetime, timezone

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from nexusfeed.storage.db import init_db, async_engine
from nexusfeed.storage.models import Trade, OrderbookSnapshot
from nexusfeed.storage.repo import Repo


async def main():
    await init_db()

    repo = Repo(batch_size=2, flush_interval=0.1)

    # enqueue trades
    await repo.insert_trade({
        "source": "binance",
        "instrument": "BTC/USDT",
        "trade_id": "t-1",
        "price": 35000.0,
        "size": 0.01,
        "side": "buy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    await repo.insert_trade({
        "source": "binance",
        "instrument": "BTC/USDT",
        "trade_id": "t-2",
        "price": 35010.0,
        "size": 0.02,
        "side": "sell",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    # upsert snapshot
    await repo.insert_snapshot({
        "source": "binance",
        "instrument": "BTC/USDT",
        "sequence": 1,
        "bids": [[35000.0, 0.5]],
        "asks": [[35010.0, 0.4]],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    await repo.shutdown()

    async with AsyncSession(async_engine) as session:
        trades = (await session.exec(select(Trade))).all()
        snaps = (await session.exec(select(OrderbookSnapshot))).all()
        print("trades", len(trades))
        print("snapshots", len(snaps))


if __name__ == "__main__":
    asyncio.run(main())