import os
import sqlite3
import subprocess
import sys
from pathlib import Path


def test_online_backup_and_retention(tmp_path: Path) -> None:
    database = tmp_path / "market.db"
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("CREATE TABLE test (value INTEGER)")
        connection.execute("INSERT INTO test VALUES (42)")
        connection.commit()
        backups = tmp_path / "backups"
        backups.mkdir()
        old = backups / "bazaar-old.db"
        old.touch()
        os.utime(old, (1, 1))
        subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parents[2] / "deploy/backup.py")],
            env={**os.environ, "DATABASE_URL": f"sqlite:///{database}", "BACKUP_DIRECTORY": str(backups)},
            check=True,
            capture_output=True,
        )
        assert not old.exists()
        copies = list(backups.glob("*.db"))
        assert len(copies) == 1
        with sqlite3.connect(copies[0]) as restored:
            assert restored.execute("SELECT value FROM test").fetchone() == (42,)
