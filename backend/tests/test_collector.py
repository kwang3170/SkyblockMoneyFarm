import asyncio
import time
from unittest.mock import AsyncMock

import httpx
import pytest
from conftest import snapshot
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from bazaar.collector.client import HypixelClient
from bazaar.collector.storage import ingest
from bazaar.config import Settings
from bazaar.models import Snapshot


def test_low_rate_limit_and_429_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    async def exercise() -> None:
        client = HypixelClient()
        await client.http.aclose()
        replies = [
            httpx.Response(200, headers={"RateLimit-Remaining": "2", "RateLimit-Reset": "90"}, json={}),
            httpx.Response(429, headers={"Retry-After": "120"}),
        ]
        client.http = httpx.AsyncClient(
            base_url="https://example.test", transport=httpx.MockTransport(lambda _: replies.pop(0))
        )
        sleep = AsyncMock()
        monkeypatch.setattr(asyncio, "sleep", sleep)
        await client.get("/bazaar")
        assert client.remaining == 2
        assert client.next_request_at - time.monotonic() > 85
        with pytest.raises(httpx.HTTPStatusError):
            await client.get("/bazaar")
        sleep.assert_awaited_once()
        assert client.next_request_at - time.monotonic() > 115
        await client.close()

    asyncio.run(exercise())


def test_ingestion_rolls_back_on_failure(
    factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*_args: object) -> None:
        raise ValueError("bad metric")

    monkeypatch.setattr("bazaar.collector.storage.calculate", fail)
    with pytest.raises(ValueError):
        ingest(factory, snapshot(), Settings())
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(Snapshot)) == 0
