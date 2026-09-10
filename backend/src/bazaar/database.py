from pathlib import Path
from sqlite3 import Connection

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from bazaar.models import Base


def make_engine(url: str) -> Engine:
    parsed = make_url(url)
    if parsed.drivername.startswith("sqlite") and parsed.database not in (None, "", ":memory:"):
        Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False, "timeout": 30}
        if parsed.drivername.startswith("sqlite")
        else {},
    )
    if parsed.drivername.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def configure_sqlite(connection: Connection, _record: object) -> None:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=30000")

    return engine


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)


def create_tables(engine: Engine) -> None:
    """For isolated tests; production schema changes use Alembic."""
    Base.metadata.create_all(engine)
