import asyncio
from typing import List

from nexusfeed.normalizer import normalize_trade, normalize_book
from nexusfeed.storage.repo import Repo
from nexusfeed.storage.redis_cache import set_snapshot
from nexusfeed.publisher.websocket_pub import WebSocketPublisher
from nexusfeed.utils.metrics import messages_received_total


class FeedManager:
    def __init__(self, repo: Repo, poll_trades_interval: float = 2.0, poll_books_interval: float = 5.0, publisher: WebSocketPublisher | None = None):
        self.repo = repo
        self.poll_trades_interval = poll_trades_interval
        self.poll_books_interval = poll_books_interval
        self.connectors: List = []
        self.tasks: List[asyncio.Task] = []
        self._stopping = asyncio.Event()
        self.publisher = publisher

    def register(self, connector) -> None:
        self.connectors.append(connector)

    async def start_all(self) -> None:
        for connector in self.connectors:
            source = connector.exchange_name
            symbols = connector.symbols or []
            for sym in symbols:
                self.tasks.append(asyncio.create_task(self._poll_trades(connector, source, sym)))
                self.tasks.append(asyncio.create_task(self._poll_books(connector, source, sym)))

    async def stop_all(self) -> None:
        self._stopping.set()
        for t in self.tasks:
            t.cancel()
        for t in self.tasks:
            try:
                await t
            except Exception:
                pass
        await self.repo.shutdown()

    async def ingest_trade(self, raw: dict, source: str) -> None:
        out = normalize_trade(raw, source)
        await self.repo.insert_trade(out)
        try:
            messages_received_total.labels(type="trade").inc()
        except Exception:
            pass
        if self.publisher:
            try:
                await self.publisher.publish(out)
            except Exception:
                pass

    async def ingest_book(self, raw: dict, source: str) -> None:
        out = normalize_book(raw, source)
        await self.repo.insert_snapshot(out)
        try:
            instrument = out.get("instrument")
            if instrument:
                await set_snapshot(instrument, out)
        except Exception:
            pass
        try:
            messages_received_total.labels(type="book").inc()
        except Exception:
            pass
        if self.publisher:
            try:
                await self.publisher.publish(out)
            except Exception:
                pass

    async def _poll_trades(self, connector, source: str, symbol: str):
        while not self._stopping.is_set():
            try:
                trades = await asyncio.to_thread(connector.get_trades, symbol)
                for tr in trades:
                    await self.ingest_trade(tr, source)
            except Exception:
                await asyncio.sleep(self.poll_trades_interval)
            await asyncio.sleep(self.poll_trades_interval)

    async def _poll_books(self, connector, source: str, symbol: str):
        while not self._stopping.is_set():
            try:
                book = await asyncio.to_thread(connector.get_orderbook, symbol)
                await self.ingest_book(book, source)
            except Exception:
                await asyncio.sleep(self.poll_books_interval)
            await asyncio.sleep(self.poll_books_interval)