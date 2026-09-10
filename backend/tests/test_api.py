import io
from pathlib import Path

import pyarrow.parquet as pq
from conftest import snapshot
from fastapi.testclient import TestClient

from bazaar.api.app import create_app
from bazaar.collector.storage import ingest
from bazaar.config import Settings
from bazaar.database import create_tables, make_engine, session_factory


def test_rest_export_websocket(tmp_path: Path) -> None:
    settings = Settings(database_url=f"sqlite:///{tmp_path}/api.db", collector_enabled=False)
    engine = make_engine(settings.database_url)
    create_tables(engine)
    factory = session_factory(engine)
    ingest(factory, snapshot(), settings)
    ingest(factory, snapshot(150000, ask=110), settings)
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/products").json()[0]["insta_buy_price"] == 110
        assert client.get("/api/products/TEST/book?at=140000").json()["timestamp"] == 120000
        assert client.get("/api/products/TEST/book?at=1").status_code == 404
        assert len(client.get("/api/products/TEST/candles?interval=1m").json()) == 1
        assert len(client.get("/api/products/TEST/history?metric=spread").json()) == 2
        assert client.get("/api/products/TEST/history?metric=invalid").status_code == 422
        assert client.get("/api/products/TEST/history?start=10&end=1").status_code == 422
        csv = client.get("/api/products/TEST/export?format=csv").text
        assert len(csv.splitlines()) == 3 and "tax_rate" in csv
        parquet = client.get("/api/products/TEST/export?format=parquet").content
        table = pq.read_table(io.BytesIO(parquet))
        assert table.num_rows == 2 and table.column("insta_buy_price").to_pylist() == [100, 110]
        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["products"][0]["product_id"] == "TEST"
    engine.dispose()
