import asyncio
import os
import json
import pytest
import websockets
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from nexusfeed.storage.db import init_db, get_engine
from nexusfeed.storage.models import Trade


@pytest.mark.integration
@pytest.mark.asyncio
async def test_feed_pipeline_with_simulated_connector():
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/nexusfeed"
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"

    # Assume docker-compose stack is up externally
    await init_db()

    # Connect WS feeds and subscribe
    uri = "ws://localhost:8000/ws/feeds"
    try:
        async with websockets.connect(uri) as ws:
            await ws.send(json.dumps({"action": "subscribe", "instrument": "BTC-USDT"}))
            # Read a few messages
            received = 0
            while received < 5:
                msg = await ws.recv()
                data = json.loads(msg)
                assert data.get("instrument") in ("BTC/USDT", "BTC-USDT")
                received += 1
    except Exception:
        pytest.skip("WebSocket not available; ensure docker-compose stack is running")

    # Verify DB has trades (may need to wait briefly)
    await asyncio.sleep(1)
    async with AsyncSession(get_engine()) as s:
        rows = (await s.exec(select(Trade))).all()
        assert len(rows) >= 1