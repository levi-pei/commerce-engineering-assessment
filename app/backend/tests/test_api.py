from __future__ import annotations

import asyncio

import httpx


def test_product_contains_options_and_required_sku_states(client) -> None:
    response = client.get("/api/products/everyday-shell")
    assert response.status_code == 200
    product = response.json()
    assert [dimension["name"] for dimension in product["option_dimensions"]] == ["colour", "size"]
    assert len(product["skus"]) >= 6
    assert any(not sku["is_available"] for sku in product["skus"])
    assert any(sku["available_quantity"] == 0 for sku in product["skus"])
    assert not any(
        sku["options"] == {"colour": "Signal Red", "size": "XL"} for sku in product["skus"]
    )


def test_add_to_cart_and_get_cart(client) -> None:
    response = client.post(
        "/api/cart/items",
        headers={"Idempotency-Key": "add-one"},
        json={"sku_id": "shell-graphite-m", "quantity": 2},
    )
    assert response.status_code == 201
    assert response.json()["available_quantity"] == 1

    cart = client.get("/api/cart").json()
    assert cart["total_item_count"] == 2
    assert cart["subtotal_cents"] == 25_800


def test_repeated_idempotency_key_replays_without_adding_twice(client) -> None:
    request = {
        "headers": {"Idempotency-Key": "same-intent"},
        "json": {"sku_id": "shell-red-m", "quantity": 1},
    }
    first = client.post("/api/cart/items", **request)
    second = client.post("/api/cart/items", **request)

    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()
    assert second.headers["Idempotency-Replayed"] == "true"
    assert client.get("/api/cart").json()["total_item_count"] == 1


def test_idempotency_key_cannot_be_reused_for_another_payload(client) -> None:
    headers = {"Idempotency-Key": "conflicting-intent"}
    assert client.post(
        "/api/cart/items", headers=headers, json={"sku_id": "shell-graphite-s", "quantity": 1}
    ).status_code == 201
    conflict = client.post(
        "/api/cart/items", headers=headers, json={"sku_id": "shell-graphite-m", "quantity": 1}
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_validation_and_business_errors_are_structured(client) -> None:
    cases = [
        ({}, {"sku_id": "shell-graphite-s", "quantity": 1}, 400, "IDEMPOTENCY_KEY_REQUIRED"),
        ({"Idempotency-Key": "bad-qty"}, {"sku_id": "shell-graphite-s", "quantity": 0}, 422, "VALIDATION_ERROR"),
        ({"Idempotency-Key": "missing"}, {"sku_id": "not-real", "quantity": 1}, 404, "SKU_NOT_FOUND"),
        ({"Idempotency-Key": "unavailable"}, {"sku_id": "shell-graphite-xl", "quantity": 1}, 409, "SKU_UNAVAILABLE"),
        ({"Idempotency-Key": "empty"}, {"sku_id": "shell-red-l", "quantity": 1}, 409, "INSUFFICIENT_STOCK"),
    ]
    for headers, body, expected_status, expected_code in cases:
        response = client.post("/api/cart/items", headers=headers, json=body)
        assert response.status_code == expected_status
        assert response.json()["error"]["code"] == expected_code


def test_only_one_concurrent_request_reserves_the_final_unit(app) -> None:
    async def race() -> list[httpx.Response]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await asyncio.gather(
                client.post(
                    "/api/cart/items",
                    headers={"Idempotency-Key": "racer-a"},
                    json={"sku_id": "shell-red-m", "quantity": 1},
                ),
                client.post(
                    "/api/cart/items",
                    headers={"Idempotency-Key": "racer-b"},
                    json={"sku_id": "shell-red-m", "quantity": 1},
                ),
            )

    responses = asyncio.run(race())
    assert sorted(response.status_code for response in responses) == [201, 409]
    failure = next(response for response in responses if response.status_code == 409)
    assert failure.json()["error"]["code"] == "INSUFFICIENT_STOCK"

