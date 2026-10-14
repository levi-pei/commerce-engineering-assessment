from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AddCartItemRequest(BaseModel):
    sku_id: str = Field(min_length=1, max_length=100)
    quantity: int = Field(ge=1, le=100)


class ApiError(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ApiError


def error_body(code: str, message: str, **details: Any) -> dict:
    return {"error": {"code": code, "message": message, "details": details}}

