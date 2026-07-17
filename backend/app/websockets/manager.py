from __future__ import annotations
import asyncio
import json
import logging
from collections import defaultdict
from typing import Dict, List, Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self._connections: Dict[str, List[WebSocket]] = defaultdict(list)
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, websocket: WebSocket, experiment_id: str) -> None:
        await websocket.accept()
        self._connections[experiment_id].append(websocket)
        logger.info(f"WS connected: exp={experiment_id[:8]} total={len(self._connections[experiment_id])}")

    def disconnect(self, websocket: WebSocket, experiment_id: str) -> None:
        conns = self._connections.get(experiment_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self._connections.pop(experiment_id, None)
        logger.info(f"WS disconnected: exp={experiment_id[:8]}")

    async def broadcast(self, experiment_id: str, message: dict) -> None:
        conns = list(self._connections.get(experiment_id, []))
        if not conns:
            return

        data = json.dumps(message)
        dead: List[WebSocket] = []

        for ws in conns:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.disconnect(ws, experiment_id)

    def broadcast_from_thread(self, experiment_id: str, message: dict) -> None:
        if self._loop is None or not self._loop.is_running():
            return
        asyncio.run_coroutine_threadsafe(
            self.broadcast(experiment_id, message),
            self._loop,
        )

    def subscriber_count(self, experiment_id: str) -> int:
        return len(self._connections.get(experiment_id, []))

    def active_experiments(self) -> List[str]:
        return list(self._connections.keys())


manager = ConnectionManager()
