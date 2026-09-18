"""In-process pub/sub hub fanning campaign events out to WebSocket clients."""

from __future__ import annotations

import asyncio
from collections import deque
from typing import Any

from fastapi import WebSocket


class EventHub:
    def __init__(self, history_size: int = 200) -> None:
        self._clients: set[WebSocket] = set()
        self._history: deque[dict[str, Any]] = deque(maxlen=history_size)
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, run_id: int | None = None) -> None:
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)
        for event in list(self._history):
            if run_id is None or event.get("run_id") == run_id:
                await websocket.send_json(event)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(websocket)

    async def publish(self, event: dict[str, Any]) -> None:
        self._history.append(event)
        async with self._lock:
            clients = list(self._clients)
        for client in clients:
            try:
                await client.send_json(event)
            except Exception:  # noqa: BLE001 - drop dead sockets
                await self.disconnect(client)


hub = EventHub()
