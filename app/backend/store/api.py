from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from store.database import Database
from store.models import AddCartItemRequest, error_body
from store.service import StoreService


def create_app(database_path: str | Path | None = None) -> FastAPI:
    path = database_path or os.getenv("STORE_DATABASE", "store.db")
    database = Database(path)
    database.initialize()
    service = StoreService(database)

    app = FastAPI(title="Variant PDP API", version="1.0.0")
    app.state.database = database
    app.state.service = service
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Idempotency-Key"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, error: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_body("VALIDATION_ERROR", "The request is invalid.", fields=error.errors()),
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(_: Request, __: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=error_body("INTERNAL_ERROR", "An unexpected server error occurred."),
        )

    @app.get("/api/products/{product_id}")
    def get_product(product_id: str) -> JSONResponse:
        product = service.get_product(product_id)
        if product is None:
            return JSONResponse(
                status_code=404,
                content=error_body("PRODUCT_NOT_FOUND", "The requested product does not exist."),
            )
        return JSONResponse(product)

    @app.post("/api/cart/items")
    def add_cart_item(
        payload: AddCartItemRequest,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> JSONResponse:
        if idempotency_key is None or not idempotency_key.strip():
            return JSONResponse(
                status_code=400,
                content=error_body("IDEMPOTENCY_KEY_REQUIRED", "Idempotency-Key header is required."),
            )
        if len(idempotency_key) > 128:
            return JSONResponse(
                status_code=400,
                content=error_body("IDEMPOTENCY_KEY_INVALID", "Idempotency-Key must be at most 128 characters."),
            )
        response = service.add_cart_item(payload, idempotency_key)
        headers = {"Idempotency-Replayed": "true"} if response.replayed else None
        return JSONResponse(response.body, status_code=response.status_code, headers=headers)

    @app.get("/api/cart")
    def get_cart() -> JSONResponse:
        return JSONResponse(service.get_cart())

    return app


app = create_app()

