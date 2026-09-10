import asyncio
import time

import httpx


class HypixelClient:
    def __init__(self) -> None:
        self.http = httpx.AsyncClient(
            base_url="https://api.hypixel.net", timeout=25, headers={"User-Agent": "BazaarTerminal/0.1"}
        )
        self.remaining: int | None = None
        self.next_request_at: float = 0

    async def get(self, path: str) -> bytes:
        delay = self.next_request_at - time.monotonic()
        if delay > 0:
            await asyncio.sleep(delay)
        response = await self.http.get(path)
        remaining = response.headers.get("RateLimit-Remaining")
        try:
            self.remaining = int(remaining) if remaining is not None else None
            reset = float(response.headers.get("RateLimit-Reset", "60"))
        except ValueError:
            self.remaining, reset = None, 60
        if self.remaining is not None and self.remaining <= 5:
            self.next_request_at = time.monotonic() + max(reset, 30)
        if response.status_code == 429:
            try:
                retry = float(response.headers.get("Retry-After", "60"))
            except ValueError:
                retry = 60
            self.next_request_at = time.monotonic() + max(retry, reset, 30)
        response.raise_for_status()
        return response.content

    async def close(self) -> None:
        await self.http.aclose()
