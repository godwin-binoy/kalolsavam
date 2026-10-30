"""In-process async event bus powering Server-Sent Events (SSE) fan-out.

Publishers: db.emit_change() after any mutation.
Subscribers: /api/public/stream (anonymous, sanitized payloads only) and
/api/live/stream (authenticated staff views).
"""
from __future__ import annotations

import asyncio
import json
from collections import deque
from typing import AsyncIterator


class Subscriber:
    def __init__(self, queue: "asyncio.Queue[str]", name: str):
        self.queue = queue
        self.name = name


class EventBus:
    def __init__(self, max_queue: int = 256):
        self._subs: set[asyncio.Queue] = set()
        self._max = max_queue
        self.history: deque[tuple[int, str, dict]] = deque(maxlen=512)
        self._seq = 0

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=self._max)
        self._subs.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subs.discard(q)

    @property
    def connections(self) -> int:
        return len(self._subs)

    def publish(self, entity: str, change: dict) -> None:
        """Thread-safe-ish publish from sync code via the running loop."""
        self._seq += 1
        payload = json.dumps({"id": self._seq, "entity": entity, **change},
                             default=str)
        self.history.append((self._seq, entity, change))
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return  # no loop yet (e.g., during seeding) — changelog table is truth
        for q in list(self._subs):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                # slow consumer: drop it (client will resync from snapshot)
                self._subs.discard(q)

    async def stream(self, q: asyncio.Queue, *, heartbeat: float = 20.0
                     ) -> AsyncIterator[str]:
        while True:
            try:
                data = await asyncio.wait_for(q.get(), timeout=heartbeat)
                yield f"event: change\ndata: {data}\n\n"
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"


BUS = EventBus()
