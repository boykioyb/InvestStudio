"""Schema (DTO) cho trợ lý hỏi–đáp RAG."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000,
                          description="Câu hỏi bằng ngôn ngữ tự nhiên")
    #  Giới hạn tìm kiếm trong một mã (tùy chọn) — VD chỉ hỏi về FPT.
    ticker: Optional[str] = Field(None, max_length=12)


class Citation(BaseModel):
    """Nguồn được dùng để trả lời — để người dùng kiểm chứng, không phải trang trí."""

    ticker: str
    doc_type: str
    title: str
    snippet: str = Field(..., description="Trích đoạn ngắn của tài liệu gốc")


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation] = []
    note: str = Field(
        "Trợ lý chỉ tổng hợp dữ liệu đã lập chỉ mục — KHÔNG phải khuyến nghị đầu tư.",
        description="Nhắc nhở cố định kèm mỗi câu trả lời",
    )


class IndexStatus(BaseModel):
    documents: int = Field(..., description="Số đoạn văn bản đang có trong kho")
    tickers: int = Field(..., description="Số mã đã được lập chỉ mục")
    running: bool = Field(False, description="Có job lập chỉ mục đang chạy không")
    last_message: str = ""
    task_id: Optional[str] = Field(None, description="Mã job Celery gần nhất")
