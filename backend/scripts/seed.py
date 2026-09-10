"""Deterministic synthetic history in a separate database by default."""

import argparse
import math
import random
import time

from sqlalchemy import func, select

from bazaar.collector.normalize import BazaarResponse, ItemsResponse
from bazaar.collector.storage import ingest, save_metadata
from bazaar.config import Settings
from bazaar.database import make_engine, session_factory
from bazaar.models import Snapshot

ITEMS: list[tuple[str, str, float, float]] = [
    ("ENCHANTED_DIAMOND", "Enchanted Diamond", 1320, 1280),
    ("ENCHANTED_EMERALD", "Enchanted Emerald", 1040, 960),
    ("ENCHANTED_GOLD", "Enchanted Gold", 830, 640),
    ("ENCHANTED_IRON", "Enchanted Iron", 570, 480),
    ("ENCHANTED_REDSTONE", "Enchanted Redstone", 235, 160),
    ("ENCHANTED_LAPIS_LAZULI", "Enchanted Lapis Lazuli", 430, 160),
    ("ENCHANTED_COAL", "Enchanted Coal", 970, 320),
    ("ENCHANTED_QUARTZ", "Enchanted Quartz", 1880, 640),
    ("ENCHANTED_SUGAR", "Enchanted Sugar", 620, 320),
    ("ENCHANTED_COBBLESTONE", "Enchanted Cobblestone", 320, 160),
    ("ENCHANTED_ENDER_PEARL", "Enchanted Ender Pearl", 215, 200),
    ("ENCHANTED_OBSIDIAN", "Enchanted Obsidian", 2100, 1920),
    ("ENCHANTED_BLAZE_ROD", "Enchanted Blaze Rod", 320000, 307200),
    ("ENCHANTED_SLIME_BALL", "Enchanted Slimeball", 2500, 800),
    ("ENCHANTED_STRING", "Enchanted String", 1450, 480),
    ("ENCHANTED_BONE", "Enchanted Bone", 680, 320),
    ("BOOSTER_COOKIE", "Booster Cookie", 12500000, 0),
    ("SUMMONING_EYE", "Summoning Eye", 1200000, 0),
    ("STOCK_OF_STONKS", "Stock of Stonks", 8700000, 0),
    ("RECOMBOBULATOR_3000", "Recombobulator 3000", 6500000, 0),
]


def seed(settings: Settings, hours: float = 6) -> None:
    rng = random.Random(42)
    engine = make_engine(settings.database_url)
    factory = session_factory(engine)
    with factory() as session:
        if session.scalar(select(func.count()).select_from(Snapshot)):
            raise ValueError("Seed requires an empty migrated database; use a separate demo database")
    save_metadata(
        factory,
        ItemsResponse.model_validate(
            {
                "success": True,
                "items": [
                    {"id": key, "name": name, "npc_sell_price": npc or None} for key, name, _, npc in ITEMS
                ],
            }
        ),
    )
    end = int(time.time() * 1000) // 30000 * 30000
    steps = int(hours * 120)
    prices = {key: price for key, _, price, _ in ITEMS}
    for step in range(steps + 1):
        products: dict[str, object] = {}
        for i, (key, _, base, _) in enumerate(ITEMS):
            prices[key] *= 1 + rng.gauss(0, 0.0008) + math.sin(step / 40 + i) * 0.00015
            ask = prices[key]
            bid = ask * (0.975 - 0.008 * math.sin(step / 80 + i))
            volume = 8000000 / (1 + base / 600)
            products[key] = {
                "quick_status": {
                    "buyPrice": ask,
                    "sellPrice": bid,
                    "buyVolume": volume * 0.8,
                    "sellVolume": volume,
                    "buyMovingWeek": volume * 20,
                    "sellMovingWeek": volume * 17,
                    "buyOrders": 170 + i * 12,
                    "sellOrders": 230 + i * 8,
                },
                "buy_summary": [
                    {
                        "pricePerUnit": ask * (1 + n * 0.0007),
                        "amount": max(1, round(volume / 80 * rng.uniform(0.3, 2))),
                        "orders": rng.randint(1, 12),
                    }
                    for n in range(30)
                ],
                "sell_summary": [
                    {
                        "pricePerUnit": bid * (1 - n * 0.0007),
                        "amount": max(1, round(volume / 70 * rng.uniform(0.3, 2))),
                        "orders": rng.randint(1, 12),
                    }
                    for n in range(30)
                ],
            }
        ingest(
            factory,
            BazaarResponse.model_validate(
                {"success": True, "lastUpdated": end - (steps - step) * 30000, "products": products}
            ),
            settings,
            source="synthetic",
        )
    engine.dispose()
    print(f"Seeded {steps + 1} snapshots × {len(ITEMS)} products ({hours} hours), source=synthetic")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=float, default=6)
    args = parser.parse_args()
    if not 0 < args.hours <= 48:
        parser.error("hours must be between 0 and 48")
    seed(Settings(), args.hours)
