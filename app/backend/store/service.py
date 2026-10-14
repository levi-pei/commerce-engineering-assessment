from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass

from store.database import Database
from store.models import AddCartItemRequest, error_body


@dataclass(frozen=True)
class ServiceResponse:
    status_code: int
    body: dict
    replayed: bool = False


class StoreService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def get_product(self, product_id: str) -> dict | None:
        with self.database.connect() as connection:
            product = connection.execute(
                "SELECT id, name, description FROM products WHERE id = ?", (product_id,)
            ).fetchone()
            if product is None:
                return None
            sku_rows = connection.execute(
                """
                SELECT id, colour, size, price_cents, stock, is_available, image_url
                FROM skus WHERE product_id = ? ORDER BY colour, size, id
                """,
                (product_id,),
            ).fetchall()

        skus = [
            {
                "id": row["id"],
                "price_cents": row["price_cents"],
                "available_quantity": row["stock"],
                "is_available": bool(row["is_available"]),
                "image_url": row["image_url"],
                "options": {"colour": row["colour"], "size": row["size"]},
            }
            for row in sku_rows
        ]
        return {
            "id": product["id"],
            "name": product["name"],
            "description": product["description"],
            "option_dimensions": [
                {"name": "colour", "label": "Colour", "values": ["Graphite", "Signal Red"]},
                {"name": "size", "label": "Size", "values": ["Small", "Medium", "Large", "XL"]},
            ],
            "skus": skus,
        }

    def get_cart(self) -> dict:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT c.sku_id, c.quantity, s.price_cents, s.colour, s.size
                FROM cart_items c JOIN skus s ON s.id = c.sku_id
                ORDER BY c.sku_id
                """
            ).fetchall()
        items = [dict(row) for row in rows]
        return {
            "items": items,
            "total_item_count": sum(item["quantity"] for item in items),
            "subtotal_cents": sum(item["quantity"] * item["price_cents"] for item in items),
        }

    def add_cart_item(self, request: AddCartItemRequest, idempotency_key: str) -> ServiceResponse:
        # 对规范化请求体哈希，避免客户端用同一个幂等键提交不同的加购意图。
        canonical = json.dumps(request.model_dump(), sort_keys=True, separators=(",", ":"))
        request_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        with self.database.transaction(immediate=True) as connection:
            # 将幂等查询与库存变更放进同一写事务：重试要么读取既有响应，
            # 要么仅执行一次实际操作。
            existing = connection.execute(
                "SELECT request_hash, status_code, response_json FROM idempotency_records WHERE key = ?",
                (idempotency_key,),
            ).fetchone()
            if existing is not None:
                if existing["request_hash"] != request_hash:
                    return ServiceResponse(
                        409,
                        error_body(
                            "IDEMPOTENCY_KEY_REUSED",
                            "This Idempotency-Key was already used with a different request.",
                        ),
                    )
                return ServiceResponse(
                    existing["status_code"],
                    self.database.decode_json(existing["response_json"]),
                    replayed=True,
                )

            sku = connection.execute(
                "SELECT id, stock, is_available FROM skus WHERE id = ?", (request.sku_id,)
            ).fetchone()
            if sku is None:
                return self._record(
                    connection,
                    idempotency_key,
                    request_hash,
                    404,
                    error_body("SKU_NOT_FOUND", "The selected SKU does not exist.", sku_id=request.sku_id),
                )
            if not sku["is_available"]:
                return self._record(
                    connection,
                    idempotency_key,
                    request_hash,
                    409,
                    error_body("SKU_UNAVAILABLE", "The selected SKU is unavailable.", sku_id=request.sku_id),
                )

            updated = connection.execute(
                """
                UPDATE skus SET stock = stock - ?
                WHERE id = ? AND is_available = 1 AND stock >= ?
                """,
                (request.quantity, request.sku_id, request.quantity),
            )
            if updated.rowcount != 1:
                # 条件更新是防止超卖的最后一道保护：排队期间库存可能已被其他请求消耗。
                current = connection.execute(
                    "SELECT stock FROM skus WHERE id = ?", (request.sku_id,)
                ).fetchone()
                return self._record(
                    connection,
                    idempotency_key,
                    request_hash,
                    409,
                    error_body(
                        "INSUFFICIENT_STOCK",
                        "There is not enough stock for this quantity.",
                        available_quantity=current["stock"] if current else 0,
                    ),
                )

            connection.execute(
                """
                INSERT INTO cart_items(sku_id, quantity) VALUES (?, ?)
                ON CONFLICT(sku_id) DO UPDATE SET quantity = quantity + excluded.quantity
                """,
                (request.sku_id, request.quantity),
            )
            stock = connection.execute(
                "SELECT stock FROM skus WHERE id = ?", (request.sku_id,)
            ).fetchone()["stock"]
            total = connection.execute("SELECT COALESCE(SUM(quantity), 0) FROM cart_items").fetchone()[0]
            body = {
                "sku_id": request.sku_id,
                "added_quantity": request.quantity,
                "available_quantity": stock,
                "cart_total_item_count": total,
            }
            return self._record(connection, idempotency_key, request_hash, 201, body)

    @staticmethod
    def _record(
        connection: sqlite3.Connection,
        key: str,
        request_hash: str,
        status_code: int,
        body: dict,
    ) -> ServiceResponse:
        # 业务失败同样需要缓存，确保同一客户端意图重试时结果确定，
        # 而不会因无关的库存变化而意外成功。
        connection.execute(
            """
            INSERT INTO idempotency_records(key, request_hash, status_code, response_json)
            VALUES (?, ?, ?, ?)
            """,
            (key, request_hash, status_code, json.dumps(body, separators=(",", ":"))),
        )
        return ServiceResponse(status_code, body)
