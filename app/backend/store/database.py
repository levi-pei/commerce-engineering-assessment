from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skus (
    id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES products(id),
    colour TEXT NOT NULL,
    size TEXT NOT NULL,
    price_cents INTEGER NOT NULL CHECK (price_cents >= 0),
    stock INTEGER NOT NULL CHECK (stock >= 0),
    is_available INTEGER NOT NULL CHECK (is_available IN (0, 1)),
    image_url TEXT NOT NULL,
    UNIQUE(product_id, colour, size)
);

CREATE TABLE IF NOT EXISTS cart_items (
    sku_id TEXT PRIMARY KEY REFERENCES skus(id),
    quantity INTEGER NOT NULL CHECK (quantity > 0)
);

CREATE TABLE IF NOT EXISTS idempotency_records (
    key TEXT PRIMARY KEY,
    request_hash TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    response_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


SEED_PRODUCT = (
    "everyday-shell",
    "Fieldwork Utility Shell",
    "A weather-ready overshirt with a clean workwear cut, reinforced pockets, and a soft recycled lining.",
)

SEED_SKUS = [
    ("shell-graphite-s", "Graphite", "Small", 12900, 5, 1, "/assets/shell-graphite.png"),
    ("shell-graphite-m", "Graphite", "Medium", 12900, 3, 1, "/assets/shell-graphite.png"),
    ("shell-graphite-l", "Graphite", "Large", 12900, 2, 1, "/assets/shell-graphite.png"),
    ("shell-graphite-xl", "Graphite", "XL", 12900, 4, 0, "/assets/shell-graphite.png"),
    ("shell-red-s", "Signal Red", "Small", 13400, 4, 1, "/assets/shell-red.png"),
    ("shell-red-m", "Signal Red", "Medium", 13400, 1, 1, "/assets/shell-red.png"),
    ("shell-red-l", "Signal Red", "Large", 13400, 0, 1, "/assets/shell-red.png"),
]


class Database:
    def __init__(self, path: str | Path) -> None:
        self.path = str(path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    @contextmanager
    def transaction(self, *, immediate: bool = False) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            connection.execute(
                "INSERT OR IGNORE INTO products(id, name, description) VALUES (?, ?, ?)",
                SEED_PRODUCT,
            )
            connection.executemany(
                """
                INSERT OR IGNORE INTO skus(
                    id, product_id, colour, size, price_cents, stock, is_available, image_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (sku_id, SEED_PRODUCT[0], colour, size, price, stock, available, image)
                    for sku_id, colour, size, price, stock, available, image in SEED_SKUS
                ],
            )

    @staticmethod
    def decode_json(value: str) -> dict:
        return json.loads(value)

