import asyncio
from typing import Dict, Set, Optional

from fastapi import WebSocket


def _norm(instr: str) -> str:
    return instr.replace("-", "/")


class WebSocketPublisher:
    def __init__(self, queue_size: int = 1000):
        self.clients: Set[WebSocket] = set()
        self.subs: Dict[str, Set[WebSocket]] = {}
        self.client_subs: Dict[WebSocket, Set[str]] = {}
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=queue_size)
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        if not self._task:
            self._task = asyncio.create_task(self._run())

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except Exception:
                pass
            self._task = None

    async def register(self, ws: WebSocket):
        self.clients.add(ws)
        self.client_subs[ws] = set()

    async def unregister(self, ws: WebSocket):
        if ws in self.clients:
            self.clients.remove(ws)
        subs = self.client_subs.pop(ws, set())
        for instr in subs:
            s = self.subs.get(instr)
            if s and ws in s:
                s.remove(ws)
                if not s:
                    self.subs.pop(instr, None)

    async def subscribe(self, ws: WebSocket, instrument: str):
        instr = _norm(instrument)
        s = self.subs.get(instr)
        if not s:
            s = set()
            self.subs[instr] = s
        s.add(ws)
        self.client_subs.setdefault(ws, set()).add(instr)

    async def unsubscribe(self, ws: WebSocket, instrument: str):
        instr = _norm(instrument)
        s = self.subs.get(instr)
        if s and ws in s:
            s.remove(ws)
            if not s:
                self.subs.pop(instr, None)
        subs = self.client_subs.get(ws)
        if subs and instr in subs:
            subs.remove(instr)

    async def publish(self, event: dict):
        try:
            self.queue.put_nowait(event)
        except asyncio.QueueFull:
            await self.queue.put(event)

    async def _run(self):
        while True:
            evt = await self.queue.get()
            instr = evt.get("instrument")
            if not instr:
                continue
            targets = self.subs.get(instr) or set()
            to_remove = []
            for ws in list(targets):
                try:
                    await ws.send_json(evt)
                except Exception:
                    to_remove.append(ws)
            for ws in to_remove:
                await self.unregister(ws)

__all__ = ["WebSocketPublisher"]