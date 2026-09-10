from sqlalchemy import JSON, BigInteger, Float, ForeignKey, ForeignKeyConstraint, Index, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"
    product_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    name: Mapped[str] = mapped_column(String(240))
    npc_sell_price: Mapped[float | None] = mapped_column(Float)
    metadata_updated_at: Mapped[int | None] = mapped_column(BigInteger)


class Snapshot(Base):
    __tablename__ = "snapshots"
    timestamp: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    received_at: Mapped[int] = mapped_column(BigInteger)
    tax_rate: Mapped[float] = mapped_column(Float)
    depth: Mapped[int] = mapped_column(Integer)
    normalization_version: Mapped[int] = mapped_column(Integer, default=1)
    source: Mapped[str] = mapped_column(String(16), default="hypixel")


class ProductSnapshot(Base):
    __tablename__ = "product_snapshots"
    product_id: Mapped[str] = mapped_column(ForeignKey("products.product_id"), primary_key=True)
    timestamp: Mapped[int] = mapped_column(ForeignKey("snapshots.timestamp"), primary_key=True)
    insta_buy_price: Mapped[float | None] = mapped_column(Float)
    insta_sell_price: Mapped[float | None] = mapped_column(Float)
    best_ask: Mapped[float | None] = mapped_column(Float)
    best_bid: Mapped[float | None] = mapped_column(Float)
    buy_order_volume: Mapped[float] = mapped_column(Float)
    sell_offer_volume: Mapped[float] = mapped_column(Float)
    insta_buy_moving_week: Mapped[float] = mapped_column(Float)
    insta_sell_moving_week: Mapped[float] = mapped_column(Float)
    buy_order_count: Mapped[int] = mapped_column(Integer)
    sell_offer_count: Mapped[int] = mapped_column(Integer)
    spread: Mapped[float | None] = mapped_column(Float)
    spread_pct: Mapped[float | None] = mapped_column(Float)
    flip_profit: Mapped[float | None] = mapped_column(Float)
    flip_margin_pct: Mapped[float | None] = mapped_column(Float)
    estimated_hourly_profit: Mapped[float | None] = mapped_column(Float)
    estimated_hourly_volume: Mapped[float] = mapped_column(Float)
    npc_sell_price: Mapped[float | None] = mapped_column(Float)
    npc_ratio: Mapped[float | None] = mapped_column(Float)
    imbalance: Mapped[float | None] = mapped_column(Float)
    __table_args__ = (Index("ix_product_snapshots_timestamp", "timestamp"),)


class OrderBook(Base):
    __tablename__ = "order_books"
    product_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    timestamp: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    bids: Mapped[list[dict[str, float | int]]] = mapped_column(JSON)
    asks: Mapped[list[dict[str, float | int]]] = mapped_column(JSON)
    __table_args__ = (
        ForeignKeyConstraint(
            ["product_id", "timestamp"], ["product_snapshots.product_id", "product_snapshots.timestamp"]
        ),
    )


class Candle(Base):
    __tablename__ = "candles"
    __table_args__ = (Index("ix_candles_interval_bucket", "interval", "bucket_start"),)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.product_id"), primary_key=True)
    price_type: Mapped[str] = mapped_column(String(24), primary_key=True)
    interval: Mapped[str] = mapped_column(String(4), primary_key=True)
    bucket_start: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    sample_count: Mapped[int] = mapped_column(Integer)
    first_timestamp: Mapped[int] = mapped_column(BigInteger)
    last_timestamp: Mapped[int] = mapped_column(BigInteger)
    estimated_volume: Mapped[float] = mapped_column(Float)
