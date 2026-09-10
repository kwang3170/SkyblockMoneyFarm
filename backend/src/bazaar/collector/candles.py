from bazaar.models import Candle

INTERVALS: dict[str, int] = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}


def update_candle(candle: Candle, timestamp: int, price: float, estimated_volume: float) -> None:
    """Update one observed-price candle; timestamp ordering determines open/close."""
    candle.high = max(candle.high, price)
    candle.low = min(candle.low, price)
    if timestamp < candle.first_timestamp:
        candle.open, candle.first_timestamp = price, timestamp
    if timestamp > candle.last_timestamp:
        candle.close, candle.last_timestamp = price, timestamp
    candle.sample_count += 1
    candle.estimated_volume += estimated_volume


def new_candle(
    product_id: str, price_type: str, interval: str, timestamp: int, price: float, estimated_volume: float
) -> Candle:
    return Candle(
        product_id=product_id,
        price_type=price_type,
        interval=interval,
        bucket_start=timestamp // INTERVALS[interval] * INTERVALS[interval],
        open=price,
        high=price,
        low=price,
        close=price,
        sample_count=1,
        first_timestamp=timestamp,
        last_timestamp=timestamp,
        estimated_volume=estimated_volume,
    )
