"""Schema (DTO) cho danh sách mã yêu thích / theo dõi."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class WatchlistItemIn(BaseModel):
    ticker: str = Field(..., min_length=2, max_length=12, description="Mã cổ phiếu, VD: FPT")
    note: str = Field("", max_length=500, description="Ghi chú riêng của bạn")
    target_price: Optional[float] = Field(None, gt=0, description="Giá mục tiêu theo dõi (nghìn đ)")
    target_score: Optional[float] = Field(None, ge=0, le=100, description="Điểm mục tiêu (/100)")

    @field_validator("ticker")
    @classmethod
    def _normalize_ticker(cls, value: str) -> str:
        code = value.upper().strip()
        if not code.isalnum():
            raise ValueError("Mã cổ phiếu chỉ gồm chữ và số.")
        return code


class WatchlistItemUpdate(BaseModel):
    """Cập nhật ghi chú / ngưỡng của một mục đã có (không đổi được mã)."""

    note: Optional[str] = Field(None, max_length=500)
    target_price: Optional[float] = Field(None, gt=0)
    target_score: Optional[float] = Field(None, ge=0, le=100)


class WatchlistItemOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    ticker: str
    note: str
    target_price: Optional[float] = None
    target_score: Optional[float] = None
    created_at: datetime
