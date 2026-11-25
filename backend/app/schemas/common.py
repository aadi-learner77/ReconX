from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str = ""


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


class HealthResponse(BaseModel):
    status: str
    database: str
    version: str = "1.0.0"
    timestamp: datetime


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


def paginate_params(page: int = 1, page_size: int = 25) -> tuple[int, int, int]:
    safe_page = max(1, page)
    safe_size = min(max(1, page_size), 200)
    offset = (safe_page - 1) * safe_size
    return safe_page, safe_size, offset
