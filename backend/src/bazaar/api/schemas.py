from pydantic import BaseModel, ConfigDict


class ProductView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    product_id: str
    timestamp: int
    insta_buy_price: float | None
    insta_sell_price: float | None
    best_ask: float | None
    best_bid: float | None
    buy_order_volume: float
    sell_offer_volume: float
    insta_buy_moving_week: float
    insta_sell_moving_week: float
    buy_order_count: int
    sell_offer_count: int
    spread: float | None
    spread_pct: float | None
    flip_profit: float | None
    flip_margin_pct: float | None
    estimated_hourly_profit: float | None
    estimated_hourly_volume: float
    npc_sell_price: float | None
    npc_ratio: float | None
    imbalance: float | None
    name: str = ""
    change_24h_pct: float | None = None


class CandleView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    bucket_start: int
    open: float
    high: float
    low: float
    close: float
    sample_count: int
    first_timestamp: int
    last_timestamp: int
    estimated_volume: float


class BookLevel(BaseModel):
    price: float
    amount: float
    orders: int


class BookView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    product_id: str
    timestamp: int
    bids: list[BookLevel]
    asks: list[BookLevel]


class MetricPoint(BaseModel):
    timestamp: int
    value: float | None
