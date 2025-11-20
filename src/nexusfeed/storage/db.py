import os
from typing import AsyncGenerator

from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool


_current_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./nexusfeed.db")


def _create_engine(url: str) -> AsyncEngine:
    if url.startswith("sqlite+aiosqlite") and ":memory:" in url:
        return create_async_engine(
            url,
            echo=False,
            future=True,
            poolclass=StaticPool,
        )
    return create_async_engine(
        url,
        echo=False,
        future=True,
    )


async_engine: AsyncEngine = _create_engine(_current_url)


def get_engine() -> AsyncEngine:
    global async_engine, _current_url
    env_url = os.getenv("DATABASE_URL", _current_url)
    if env_url != _current_url:
        _current_url = env_url
        async_engine = _create_engine(_current_url)
    return async_engine


async def init_db() -> None:
    eng = get_engine()
    async with eng.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    eng = get_engine()
    async with AsyncSession(eng) as session:
        yield session