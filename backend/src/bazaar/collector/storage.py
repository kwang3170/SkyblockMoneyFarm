import re
import time

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from bazaar.collector.candles import INTERVALS, new_candle, update_candle
from bazaar.collector.metrics import calculate
from bazaar.collector.normalize import BazaarResponse, ItemsResponse, order_book, serialize_levels
from bazaar.config import Settings
from bazaar.models import Candle, OrderBook, Product, ProductSnapshot, Snapshot


def save_metadata(factory: sessionmaker[Session], payload: ItemsResponse) -> None:
    if not payload.success:
        raise ValueError("Item metadata response was unsuccessful")
    with factory.begin() as session:
        for item in payload.items:
            session.merge(
                Product(
                    product_id=item.id,
                    name=re.sub(r"§.", "", item.name),
                    npc_sell_price=item.npc_sell_price,
                    metadata_updated_at=int(time.time() * 1000),
                )
            )


def ingest(
    factory: sessionmaker[Session], payload: BazaarResponse, settings: Settings, source: str = "hypixel"
) -> bool:
    if not payload.success or not payload.products:
        raise ValueError("Empty or unsuccessful Bazaar response")
    timestamp = payload.lastUpdated
    with factory.begin() as session:
        latest = session.scalar(select(func.max(Snapshot.timestamp)))
        if latest is not None and session.get(Snapshot, latest).source != source:
            raise ValueError("Use separate databases for synthetic and live data")
        # A regressed upstream cache is not a new live snapshot.
        if latest is not None and timestamp <= latest:
            return False
        elapsed_ms = min(timestamp - latest, int(settings.poll_interval * 1000)) if latest else 0
        session.add(
            Snapshot(
                timestamp=timestamp,
                received_at=int(time.time() * 1000),
                tax_rate=settings.tax_rate,
                depth=settings.order_book_depth,
                source=source,
            )
        )
        products = {p.product_id: p for p in session.scalars(select(Product))}
        rows: list[ProductSnapshot] = []
        books: list[OrderBook] = []
        pending_candles: list[Candle] = []
        # Read only the six current candle buckets, once per snapshot, not once per product.
        from sqlalchemy import or_

        conditions = [
            (Candle.interval == interval) & (Candle.bucket_start == timestamp // duration * duration)
            for interval, duration in INTERVALS.items()
        ]
        existing = {
            (c.product_id, c.price_type, c.interval): c
            for c in session.scalars(select(Candle).where(or_(*conditions)))
        }
        for product_id, raw in payload.products.items():
            product = products.get(product_id)
            if product is None:
                product = Product(product_id=product_id, name=product_id.replace("_", " ").title())
                session.add(product)
            bids, asks = order_book(raw, settings.order_book_depth)
            metrics = calculate(raw, bids, asks, product.npc_sell_price, settings.tax_rate)
            rows.append(ProductSnapshot(product_id=product_id, timestamp=timestamp, **metrics.values()))
            books.append(
                OrderBook(
                    product_id=product_id,
                    timestamp=timestamp,
                    bids=serialize_levels(bids),
                    asks=serialize_levels(asks),
                )
            )
            # Uniform weekly-throughput proxy over observed time, capped across outages.
            volume = metrics.estimated_hourly_volume * elapsed_ms / 3_600_000
            for price_type in ("insta_buy_price", "insta_sell_price"):
                price = getattr(metrics, price_type)
                if price is None:
                    continue
                for interval in INTERVALS:
                    candle = existing.get((product_id, price_type, interval))
                    if candle is None:
                        pending_candles.append(
                            new_candle(product_id, price_type, interval, timestamp, price, volume)
                        )
                    else:
                        update_candle(candle, timestamp, price, volume)
        session.flush()  # Products and parent snapshot precede the dependent rows.
        session.add_all(pending_candles)
        session.add_all(rows)
        session.flush()
        session.add_all(books)
    return True
