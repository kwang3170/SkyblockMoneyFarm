"""API names describe instant actions, not the owner of each resting order.

buy_summary/buyPrice -> sell offers / instant-buy price (ask).
sell_summary/sellPrice -> buy orders / instant-sell price (bid).
Quick prices are weighted top-2%-by-volume estimates, not best quotes.
"""

from pydantic import BaseModel, ConfigDict, Field


class Level(BaseModel):
    amount: float = Field(ge=0, allow_inf_nan=False)
    pricePerUnit: float = Field(ge=0, allow_inf_nan=False)
    orders: int = Field(ge=0)


class QuickStatus(BaseModel):
    buyPrice: float = Field(ge=0, allow_inf_nan=False)
    sellPrice: float = Field(ge=0, allow_inf_nan=False)
    buyVolume: float = Field(ge=0, allow_inf_nan=False)
    sellVolume: float = Field(ge=0, allow_inf_nan=False)
    buyMovingWeek: float = Field(ge=0, allow_inf_nan=False)
    sellMovingWeek: float = Field(ge=0, allow_inf_nan=False)
    buyOrders: int = Field(ge=0)
    sellOrders: int = Field(ge=0)


class RawProduct(BaseModel):
    quick_status: QuickStatus
    buy_summary: list[Level]
    sell_summary: list[Level]


class BazaarResponse(BaseModel):
    success: bool
    lastUpdated: int = Field(gt=0)
    products: dict[str, RawProduct]


class Item(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    npc_sell_price: float | None = Field(default=None, ge=0, allow_inf_nan=False)


class ItemsResponse(BaseModel):
    success: bool
    items: list[Item]


def order_book(product: RawProduct, depth: int) -> tuple[list[Level], list[Level]]:
    bids = sorted(
        (x for x in product.sell_summary if x.amount > 0), key=lambda x: x.pricePerUnit, reverse=True
    )[:depth]
    asks = sorted((x for x in product.buy_summary if x.amount > 0), key=lambda x: x.pricePerUnit)[:depth]
    return bids, asks


def serialize_levels(levels: list[Level]) -> list[dict[str, float | int]]:
    return [{"price": x.pricePerUnit, "amount": x.amount, "orders": x.orders} for x in levels]
