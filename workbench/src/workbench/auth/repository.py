"""SQLite 用户仓储。"""

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path


@dataclass
class User:
    id: int
    username: str
    password_hash: str


class UserRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        # closing 关连接，conn 自身作事务上下文（commit/rollback）
        with closing(self._connect()) as conn, conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )

    def create_user(self, username: str, password_hash: str) -> User:
        with closing(self._connect()) as conn, conn:
            try:
                cur = conn.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, password_hash),
                )
            except sqlite3.IntegrityError:
                raise ValueError(f"username already exists: {username}")
            return User(id=int(cur.lastrowid or 0), username=username, password_hash=password_hash)

    def get_by_username(self, username: str) -> User | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT id, username, password_hash FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if row is None:
                return None
            return User(id=row["id"], username=row["username"], password_hash=row["password_hash"])
