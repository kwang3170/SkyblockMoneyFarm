import pytest
from conftest import snapshot
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from bazaar.collector.candles import INTERVALS, new_candle, update_candle
from bazaar.collector.storage import ingest
from bazaar.config import Settings
from bazaar.models import Candle, OrderBook, ProductSnapshot, Snapshot


def test_out_of_order_ohlc() -> None:
    candle = new_candle("TEST", "insta_buy_price", "1m", 150000, 12, 2)
    update_candle(candle, 140000, 10, 3)
    update_candle(candle, 160000, 9, 4)
    assert (candle.open, candle.high, candle.low, candle.close) == (10, 12, 9, 9)
    assert candle.sample_count == 3 and candle.estimated_volume == 9


@pytest.mark.parametrize("interval,duration", INTERVALS.items())
def test_bucket_boundary(interval: str, duration: int) -> None:
    assert new_candle("T", "insta_buy_price", interval, duration - 1, 1, 0).bucket_start == 0
    assert new_candle("T", "insta_buy_price", interval, duration, 1, 0).bucket_start == duration


def test_ingestion_dedup_and_incremental_candles(factory: sessionmaker[Session]) -> None:
    settings = Settings()
    assert ingest(factory, snapshot(), settings)
    assert not ingest(factory, snapshot(), settings)
    assert ingest(factory, snapshot(150000, ask=110), settings)
    assert ingest(factory, snapshot(180000, ask=105), settings)
    assert not ingest(factory, snapshot(140000), settings)
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(Snapshot)) == 3
        assert session.scalar(select(func.count()).select_from(ProductSnapshot)) == 3
        assert session.scalar(select(func.count()).select_from(OrderBook)) == 3
        first = session.get(Candle, ("TEST", "insta_buy_price", "1m", 120000))
        assert (first.open, first.high, first.low, first.close) == (100, 110, 100, 110)
        assert first.sample_count == 2
        assert first.estimated_volume == pytest.approx(100 * 30 / 3600)
        hour = session.get(Candle, ("TEST", "insta_buy_price", "1h", 0))
        assert hour.sample_count == 3 and hour.close == 105


def test_outage_does_not_invent_volume(factory: sessionmaker[Session]) -> None:
    ingest(factory, snapshot(), Settings())
    ingest(factory, snapshot(3_720_000), Settings())
    with factory() as session:
        candle = session.get(Candle, ("TEST", "insta_buy_price", "1m", 3_720_000))
        assert candle.estimated_volume == pytest.approx(100 * 30 / 3600)
