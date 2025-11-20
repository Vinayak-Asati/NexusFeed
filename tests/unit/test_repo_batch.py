import asyncio
import pytest
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from nexusfeed.storage.db import init_db, get_engine
from nexusfeed.storage.models import Trade
from nexusfeed.storage.repo import Repo


@pytest.mark.asyncio
async def test_repo_batch_flush_in_memory(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    await init_db()
    repo = Repo(batch_size=5, flush_interval=0.1)

    for i in range(12):
        await repo.insert_trade({
            "source": "sim",
            "instrument": "BTC/USDT",
            "trade_id": f"t-{i}",
            "price": 1.0 + i,
            "size": 0.01,
            "side": "buy",
            "timestamp": 1609459200000,
        })

    await repo.shutdown()
    async with AsyncSession(get_engine()) as session:
        rows = (await session.exec(select(Trade))).all()
        assert len(rows) == 12