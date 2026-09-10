import pytest
from conftest import snapshot

from bazaar.collector.metrics import calculate
from bazaar.collector.normalize import order_book


def test_metrics_and_api_mapping() -> None:
    raw = snapshot().products["TEST"]
    bids, asks = order_book(raw, 30)
    m = calculate(raw, bids, asks, 95, 0.01125)
    assert m.insta_buy_price == 100 and m.insta_sell_price == 90
    assert m.buy_order_volume == 400 and m.sell_offer_volume == 200
    assert m.spread == 10 and m.spread_pct == 10
    assert m.flip_profit == pytest.approx(8.875)
    assert m.flip_margin_pct == pytest.approx(8.875 / 90 * 100)
    assert m.estimated_hourly_profit == pytest.approx(887.5)
    assert m.imbalance == 2
    assert m.npc_ratio == pytest.approx(90 / 95)


def test_missing_side_and_zero_npc_are_null() -> None:
    raw = snapshot().products["TEST"]
    m = calculate(raw, [], [], 0, 0.01125)
    assert m.insta_buy_price is None and m.insta_sell_price is None
    assert m.spread is None and m.flip_margin_pct is None
    assert m.npc_ratio is None and m.imbalance is None


def test_negative_profit_preserved() -> None:
    raw = snapshot(ask=100, bid=99.9).products["TEST"]
    bids, asks = order_book(raw, 30)
    assert calculate(raw, bids, asks, None, 0.01125).flip_profit < 0
