from dataclasses import asdict, dataclass

from bazaar.collector.normalize import Level, RawProduct


def ratio(numerator: float | None, denominator: float | None) -> float | None:
    return (
        numerator / denominator
        if numerator is not None and denominator is not None and denominator > 0
        else None
    )


@dataclass(frozen=True)
class Metrics:
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

    def values(self) -> dict[str, float | int | None]:
        return asdict(self)


def calculate(
    product: RawProduct, bids: list[Level], asks: list[Level], npc: float | None, tax_rate: float
) -> Metrics:
    q = product.quick_status
    ask = q.buyPrice if asks and q.buyPrice > 0 else None
    bid = q.sellPrice if bids and q.sellPrice > 0 else None
    spread = ask - bid if ask is not None and bid is not None else None
    profit = ask * (1 - tax_rate) - bid if ask is not None and bid is not None else None
    spread_ratio, margin = ratio(spread, ask), ratio(profit, bid)
    hourly = min(q.buyMovingWeek, q.sellMovingWeek) / 168
    return Metrics(
        ask,
        bid,
        asks[0].pricePerUnit if asks else None,
        bids[0].pricePerUnit if bids else None,
        q.sellVolume,
        q.buyVolume,
        q.buyMovingWeek,
        q.sellMovingWeek,
        q.sellOrders,
        q.buyOrders,
        spread,
        spread_ratio * 100 if spread_ratio is not None else None,
        profit,
        margin * 100 if margin is not None else None,
        profit * hourly if profit is not None else None,
        hourly,
        npc,
        ratio(bid, npc),
        ratio(sum(x.amount for x in bids), sum(x.amount for x in asks)),
    )
