"""WebSocket progress manager — tracks connected clients per project."""

import json
import logging
from fastapi import WebSocket

logger = logging.getLogger("autoforge.ws")

# project_id -> list of active WebSocket connections
_connections: dict[str, list[WebSocket]] = {}


async def connect(project_id: str, ws: WebSocket) -> None:
    await ws.accept()
    _connections.setdefault(project_id, []).append(ws)
    logger.info("[%s] WebSocket connected (%d total)", project_id, len(_connections[project_id]))


def disconnect(project_id: str, ws: WebSocket) -> None:
    conns = _connections.get(project_id, [])
    if ws in conns:
        conns.remove(ws)
    if not conns:
        _connections.pop(project_id, None)
    logger.info("[%s] WebSocket disconnected (%d remaining)", project_id, len(conns))


async def broadcast(project_id: str, event: dict) -> None:
    conns = _connections.get(project_id, [])
    dead = []
    for ws in conns:
        try:
            await ws.send_text(json.dumps(event))
        except Exception:
            dead.append(ws)
    for ws in dead:
        conns.remove(ws)
    if not conns:
        _connections.pop(project_id, None)
