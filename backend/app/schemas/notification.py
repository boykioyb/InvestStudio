"""Schema (DTO) cho thông báo trong app."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class NotificationOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    ticker: str
    kind: str  # 'price' | 'score'
    message: str
    is_read: bool
    created_at: datetime
