import asyncio

from fastapi import WebSocket


class Hub:
    """Bounded per-client queues keep slow consumers off the collector's path."""

    def __init__(self) -> None:
        self.clients: dict[WebSocket, asyncio.Queue[str]] = {}

    def broadcast(self, message: str) -> None:
        for queue in self.clients.values():
            if queue.full():
                queue.get_nowait()  # Latest snapshot supersedes an undelivered snapshot.
            queue.put_nowait(message)
