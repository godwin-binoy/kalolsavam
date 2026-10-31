"""In-process async event bus powering Server-Sent Events (SSE) fan-out.

Publishers: db.emit_change() after any mutation.
Subscribers: /api/public/stream (anonymous, sanitized payloads only) and
/api/live/stream (authenticated staff views).
"""
from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator


class EventBus:
    def __init__(self, max_queue: int = 256, max_connections: int = 400):
        self._subs: set[asyncio.Queue] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._max = max_queue
        self._max_conn = max_connections   # hard cap → stream-connection DoS guard
        self._seq = 0

    def attach_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Called once at app startup so publish() (which runs in worker
        threads) can hand payloads to the loop safely via call_soon_threadsafe."""
        self._loop = loop

    def subscribe(self) -> asyncio.Queue | None:
        """Register a subscriber; returns None when the connection cap is hit
        (callers must answer 503 — unbounded open streams would exhaust file
        descriptors and memory)."""
        if len(self._subs) >= self._max_conn:
            return None
        q: asyncio.Queue = asyncio.Queue(maxsize=self._max)
        self._subs.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subs.discard(q)

    @property
    def connections(self) -> int:
        return len(self._subs)

    def publish(self, entity: str, change: dict) -> None:
        """Thread-safe publish from sync code into the running event loop."""
        loop = self._loop
        if loop is None or loop.is_closed():
            return  # no loop yet (e.g., during seeding) — changelog table is truth
        subs = list(self._subs)
        if not subs:
            return  # nobody listening — skip serialization entirely
        # seq advances ONLY on real deliveries and never resets: SSE clients
        # can rely on strictly increasing ids across restarts of subscribers.
        self._seq += 1
        payload = json.dumps({"id": self._seq, "entity": entity, **change},
                             default=str)
        loop.call_soon_threadsafe(self._deliver, payload, subs)

    def _deliver(self, payload: str, subs: list) -> None:
        for q in subs:
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
