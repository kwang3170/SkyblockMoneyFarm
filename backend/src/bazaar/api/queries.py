from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from bazaar.api.schemas import ProductView
from bazaar.models import Product, ProductSnapshot, Snapshot


def latest_products(factory: sessionmaker[Session]) -> list[ProductView]:
    with factory() as session:
        latest = session.scalar(select(func.max(Snapshot.timestamp)))
        if latest is None:
            return []
        previous_time = session.scalar(
            select(func.max(Snapshot.timestamp)).where(
                Snapshot.timestamp <= latest - 86_400_000,
                Snapshot.timestamp >= latest - 86_400_000 - 300_000,
            )
        )
        previous = (
            dict(
                session.execute(
                    select(ProductSnapshot.product_id, ProductSnapshot.insta_buy_price).where(
                        ProductSnapshot.timestamp == previous_time
                    )
                ).all()
            )
            if previous_time
            else {}
        )
        result: list[ProductView] = []
        for row, name in session.execute(
            select(ProductSnapshot, Product.name).join(Product).where(ProductSnapshot.timestamp == latest)
        ):
            view = ProductView.model_validate(row)
            view.name = name
            old = previous.get(row.product_id)
            view.change_24h_pct = (
                (row.insta_buy_price / old - 1) * 100 if old and row.insta_buy_price else None
            )
            result.append(view)
        return result
