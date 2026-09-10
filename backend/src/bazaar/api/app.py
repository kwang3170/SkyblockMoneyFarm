import asyncio
import csv
import io
import json
import re
import tempfile
import time
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Literal

import pyarrow as pa
import pyarrow.parquet as pq
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import func, select
from starlette.background import BackgroundTask

from bazaar.api.queries import latest_products
from bazaar.api.schemas import BookView, CandleView, MetricPoint, ProductView
from bazaar.api.websocket import Hub
from bazaar.collector.candles import INTERVALS
from bazaar.collector.service import Collector
from bazaar.config import Settings
from bazaar.database import make_engine, session_factory
from bazaar.models import Candle, OrderBook, ProductSnapshot, Snapshot

PriceType = Literal["insta_buy_price", "insta_sell_price"]
Interval = Literal["1m", "5m", "15m", "1h", "4h", "1d"]
EXPORT_FIELDS = [column.name for column in ProductSnapshot.__table__.columns]
METRICS = set(EXPORT_FIELDS) - {"product_id", "timestamp"}


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    engine = make_engine(settings.database_url)
    factory = session_factory(engine)
    hub = Hub()

    async def publish(timestamp: int) -> None:
        rows = await asyncio.to_thread(latest_products, factory)
        hub.broadcast(
            json.dumps(
                {"type": "snapshot", "timestamp": timestamp, "products": [row.model_dump() for row in rows]}
            )
        )

    collector = Collector(factory, settings, publish)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        with factory() as session:
            collector.status.last_update = session.scalar(select(func.max(Snapshot.timestamp)))
        task = asyncio.create_task(collector.run()) if settings.collector_enabled else None
        if not task:
            collector.status.state = "disabled"
        try:
            yield
        finally:
            if task:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
            else:
                await collector.client.close()
            engine.dispose()

    app = FastAPI(title="Bazaar Terminal", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware, allow_origins=settings.origins, allow_methods=["GET"], allow_headers=["*"]
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        with engine.connect() as connection:
            connection.execute(select(1))
        return {"status": "ok"}

    @app.get("/api/status")
    def status() -> dict[str, object]:
        with factory() as session:
            latest = session.scalar(select(Snapshot).order_by(Snapshot.timestamp.desc()).limit(1))
            first = session.scalar(select(func.min(Snapshot.timestamp)))
        return {
            **collector.status.to_dict(),
            "last_update": latest.timestamp if latest else None,
            "first_update": first,
            "source": latest.source if latest else None,
            "tax_rate": latest.tax_rate if latest else settings.tax_rate,
            "order_book_depth": settings.order_book_depth,
            "stale": latest is None
            or int(time.time() * 1000) - latest.timestamp > max(120_000, settings.poll_interval * 3000),
        }

    @app.get("/api/products", response_model=list[ProductView])
    def products() -> list[ProductView]:
        return latest_products(factory)

    def validate_range(start: int, end: int | None) -> int:
        resolved_end = end if end is not None else int(time.time() * 1000)
        if start > resolved_end:
            raise HTTPException(422, "start must be <= end (UTC epoch milliseconds)")
        return resolved_end

    @app.get("/api/products/{product_id}/candles", response_model=list[CandleView])
    def candles(
        product_id: str,
        interval: Interval = "5m",
        price_type: PriceType = "insta_buy_price",
        start: int = Query(0, ge=0),
        end: int | None = Query(None, ge=0),
        limit: int = Query(2000, ge=1, le=10000),
    ) -> list[CandleView]:
        stop = validate_range(start, end)
        with factory() as session:
            rows = list(
                session.scalars(
                    select(Candle)
                    .where(
                        Candle.product_id == product_id,
                        Candle.interval == interval,
                        Candle.price_type == price_type,
                        Candle.bucket_start >= start,
                        Candle.bucket_start <= stop,
                    )
                    .order_by(Candle.bucket_start.desc())
                    .limit(limit)
                )
            )
            return [CandleView.model_validate(row) for row in reversed(rows)]

    @app.get("/api/products/{product_id}/history", response_model=list[MetricPoint])
    def history(
        product_id: str,
        metric: str = "insta_buy_price",
        start: int = Query(0, ge=0),
        end: int | None = Query(None, ge=0),
        after: int | None = None,
        interval: Interval | None = None,
        limit: int = Query(5000, ge=1, le=20000),
    ) -> list[MetricPoint]:
        stop = validate_range(start, end)
        if metric not in METRICS:
            raise HTTPException(422, f"Unknown metric; choose from {sorted(METRICS)}")
        column = getattr(ProductSnapshot, metric)
        conditions = [
            ProductSnapshot.product_id == product_id,
            ProductSnapshot.timestamp >= start,
            ProductSnapshot.timestamp <= stop,
        ]
        if after is not None:
            conditions.append(ProductSnapshot.timestamp > after)
        with factory() as session:
            if interval:
                bucket = (ProductSnapshot.timestamp // INTERVALS[interval]) * INTERVALS[interval]
                statement = (
                    select(bucket.label("timestamp"), func.avg(column))
                    .where(*conditions)
                    .group_by(bucket)
                    .order_by(bucket)
                )
            else:
                statement = (
                    select(ProductSnapshot.timestamp, column)
                    .where(*conditions)
                    .order_by(ProductSnapshot.timestamp)
                )
            return [
                MetricPoint(timestamp=ts, value=value)
                for ts, value in session.execute(statement.limit(limit))
            ]

    @app.get("/api/products/{product_id}/book", response_model=BookView)
    def book(product_id: str, at: int | None = Query(None, ge=0)) -> BookView:
        with factory() as session:
            row = session.scalar(
                select(OrderBook)
                .where(
                    OrderBook.product_id == product_id,
                    OrderBook.timestamp <= (at if at is not None else int(time.time() * 1000)),
                )
                .order_by(OrderBook.timestamp.desc())
                .limit(1)
            )
            if row is None:
                raise HTTPException(404, "No order book at or before this timestamp")
            return BookView.model_validate(row)

    @app.get("/api/products/{product_id}/snapshots", response_model=list[int])
    def timestamps(
        product_id: str,
        start: int = Query(0, ge=0),
        end: int | None = Query(None, ge=0),
        limit: int = Query(10000, ge=1, le=50000),
    ) -> list[int]:
        stop = validate_range(start, end)
        with factory() as session:
            values = list(
                session.scalars(
                    select(ProductSnapshot.timestamp)
                    .where(
                        ProductSnapshot.product_id == product_id,
                        ProductSnapshot.timestamp >= start,
                        ProductSnapshot.timestamp <= stop,
                    )
                    .order_by(ProductSnapshot.timestamp.desc())
                    .limit(limit)
                )
            )
            return list(reversed(values))

    @app.get("/api/products/{product_id}/export", response_model=None)
    def export(
        product_id: str,
        format: Literal["csv", "parquet"] = "csv",
        start: int = Query(0, ge=0),
        end: int | None = Query(None, ge=0),
    ) -> StreamingResponse | FileResponse:
        stop = validate_range(start, end)
        statement = (
            select(ProductSnapshot, Snapshot.tax_rate, Snapshot.source)
            .join(Snapshot, ProductSnapshot.timestamp == Snapshot.timestamp)
            .where(
                ProductSnapshot.product_id == product_id,
                ProductSnapshot.timestamp >= start,
                ProductSnapshot.timestamp <= stop,
            )
            .order_by(ProductSnapshot.timestamp)
        )
        fields = EXPORT_FIELDS + ["tax_rate", "source"]
        safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", product_id)

        def batches() -> Iterator[list[dict[str, str | float | int | None]]]:
            with factory() as session:
                for partition in session.execute(statement.execution_options(yield_per=2000)).partitions():
                    yield [
                        {
                            **{key: getattr(row, key) for key in EXPORT_FIELDS},
                            "tax_rate": tax,
                            "source": source,
                        }
                        for row, tax, source in partition
                    ]

        if format == "csv":

            def stream() -> Iterator[str]:
                buffer = io.StringIO()
                writer = csv.DictWriter(buffer, fieldnames=fields)
                writer.writeheader()
                yield buffer.getvalue()
                for batch in batches():
                    buffer.seek(0)
                    buffer.truncate(0)
                    writer.writerows(batch)
                    yield buffer.getvalue()

            return StreamingResponse(
                stream(),
                media_type="text/csv",
                headers={"Content-Disposition": f'attachment; filename="{safe_id}.csv"'},
            )
        schema = pa.schema(
            [
                (
                    key,
                    pa.string()
                    if key in ("product_id", "source")
                    else pa.int64()
                    if key in ("timestamp", "buy_order_count", "sell_offer_count")
                    else pa.float64(),
                )
                for key in fields
            ]
        )
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as temp:
            path = Path(temp.name)
        try:
            with pq.ParquetWriter(path, schema) as writer:
                for batch in batches():
                    writer.write_table(pa.Table.from_pylist(batch, schema=schema))
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return FileResponse(
            path,
            filename=f"{safe_id}.parquet",
            media_type="application/vnd.apache.parquet",
            background=BackgroundTask(path.unlink, missing_ok=True),
        )

    @app.websocket("/ws")
    async def websocket(socket: WebSocket) -> None:
        origin = socket.headers.get("origin")
        if origin and "*" not in settings.origins and origin not in settings.origins:
            await socket.close(code=1008)
            return
        await socket.accept()
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=1)
        hub.clients[socket] = queue
        try:
            rows = await asyncio.to_thread(latest_products, factory)
            await socket.send_json({"type": "snapshot", "products": [row.model_dump() for row in rows]})
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=20)
                except TimeoutError:
                    message = json.dumps({"type": "status", **collector.status.to_dict()})
                await asyncio.wait_for(socket.send_text(message), timeout=10)
        except (TimeoutError, WebSocketDisconnect, RuntimeError, OSError):
            pass
        finally:
            hub.clients.pop(socket, None)

    return app
