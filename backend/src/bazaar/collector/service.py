import asyncio
import logging
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass

from sqlalchemy.orm import Session, sessionmaker

from bazaar.collector.client import HypixelClient
from bazaar.collector.normalize import BazaarResponse, ItemsResponse
from bazaar.collector.storage import ingest, save_metadata
from bazaar.config import Settings

log = logging.getLogger(__name__)


@dataclass
class CollectorStatus:
    state: str = "starting"
    last_update: int | None = None
    last_attempt: int | None = None
    error: str | None = None
    rate_limit_remaining: int | None = None
    poll_interval: float = 30

    def to_dict(self) -> dict[str, str | int | float | None]:
        return asdict(self)


class Collector:
    def __init__(
        self,
        factory: sessionmaker[Session],
        settings: Settings,
        on_snapshot: Callable[[int], Awaitable[None]] | None = None,
    ) -> None:
        self.factory, self.settings, self.on_snapshot = factory, settings, on_snapshot
        self.status = CollectorStatus(poll_interval=settings.poll_interval)
        self.client = HypixelClient()

    async def run(self) -> None:
        failures = 0
        metadata_due = 0.0
        metadata_failures = 0
        try:
            while True:
                started = time.monotonic()
                if started >= metadata_due:
                    try:
                        items = ItemsResponse.model_validate_json(
                            await self.client.get("/v2/resources/skyblock/items")
                        )
                        await asyncio.to_thread(save_metadata, self.factory, items)
                        metadata_failures = 0
                        metadata_due = time.monotonic() + self.settings.metadata_interval
                    except Exception:
                        metadata_failures += 1
                        metadata_due = time.monotonic() + min(3600, 60 * 2 ** min(metadata_failures, 6))
                        log.exception("Metadata refresh failed; retaining cached names and NPC prices")
                self.status.last_attempt = int(time.time() * 1000)
                try:
                    payload = BazaarResponse.model_validate_json(await self.client.get("/v2/skyblock/bazaar"))
                    changed = await asyncio.to_thread(ingest, self.factory, payload, self.settings)
                    failures = 0
                    self.status.state, self.status.error = "live", None
                    if changed:
                        self.status.last_update = payload.lastUpdated
                        log.info("Stored %s products at %s", len(payload.products), payload.lastUpdated)
                        if self.on_snapshot:
                            await self.on_snapshot(payload.lastUpdated)
                except Exception as exc:
                    failures += 1
                    self.status.state, self.status.error = "retrying", str(exc)
                    log.exception("Collection failed; retaining last good snapshot")
                self.status.rate_limit_remaining = self.client.remaining
                delay = (
                    self.settings.poll_interval
                    if not failures
                    else min(900, self.settings.poll_interval * 2 ** min(failures, 5)) + random.uniform(0, 5)
                )
                await asyncio.sleep(max(0, delay - (time.monotonic() - started)))
        finally:
            await self.client.close()
