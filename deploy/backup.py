"""Consistent online SQLite backup; safe with WAL and concurrent collection."""

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from bazaar.config import Settings
from sqlalchemy.engine import make_url


def backup(settings: Settings) -> Path:
    url = make_url(settings.database_url)
    if (
        not url.drivername.startswith("sqlite")
        or not url.database
        or url.database == ":memory:"
    ):
        raise ValueError("This backup script requires a file-backed SQLite database")
    source = Path(url.database).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    settings.backup_directory.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    target = settings.backup_directory / f"bazaar-{now:%Y%m%dT%H%M%S%fZ}.db"
    temporary = target.with_suffix(".partial")
    try:
        with (
            sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True) as src,
            sqlite3.connect(temporary) as dst,
        ):
            src.backup(dst, pages=1024, sleep=0.1)
            if dst.execute("PRAGMA quick_check").fetchone() != ("ok",):
                raise RuntimeError("Backup integrity check failed")
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    cutoff = (now - timedelta(days=settings.backup_retention_days)).timestamp()
    for old in settings.backup_directory.glob("bazaar-*.db"):
        if old.stat().st_mtime < cutoff:
            old.unlink()
    return target


if __name__ == "__main__":
    print(backup(Settings()))
