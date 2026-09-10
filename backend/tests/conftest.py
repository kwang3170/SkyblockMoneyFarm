from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker

from bazaar.collector.normalize import BazaarResponse
from bazaar.database import create_tables, make_engine, session_factory


@pytest.fixture
def factory(tmp_path: Path) -> Iterator[sessionmaker[Session]]:
    engine = make_engine(f"sqlite:///{tmp_path}/test.db")
    create_tables(engine)
    yield session_factory(engine)
    engine.dispose()


def snapshot(timestamp: int = 120000, ask: float = 100, bid: float = 90) -> BazaarResponse:
    return BazaarResponse.model_validate(
        {
            "success": True,
            "lastUpdated": timestamp,
            "products": {
                "TEST": {
                    "quick_status": {
                        "buyPrice": ask,
                        "sellPrice": bid,
                        "buyVolume": 200,
                        "sellVolume": 400,
                        "buyMovingWeek": 16800,
                        "sellMovingWeek": 33600,
                        "buyOrders": 3,
                        "sellOrders": 6,
                    },
                    "buy_summary": [{"pricePerUnit": ask, "amount": 200, "orders": 3}],
                    "sell_summary": [{"pricePerUnit": bid, "amount": 400, "orders": 6}],
                }
            },
        }
    )
