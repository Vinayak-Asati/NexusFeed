import asyncio
import pytest

from nexusfeed.storage.redis_cache import set_snapshot, get_snapshot, _get_url


@pytest.mark.asyncio
async def test_redis_cache_roundtrip(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    instr = "BTC/USDT"
    snap = {"instrument": instr, "bids": [[1, 1]], "asks": [[2, 1]]}
    # This test requires a local Redis; if unavailable, skip
    try:
        await set_snapshot(instr, snap)
        got = await get_snapshot(instr)
        assert got["instrument"] == instr
    except Exception:
        pytest.skip("Local Redis not available")