"""Kho văn bản đã nhúng (embedding) cho RAG.

Mỗi dòng là MỘT đoạn văn bản (chunk) về một mã: tóm tắt phân tích, hồ sơ, hay
một tin tức — kèm vector nhúng để tìm theo ngữ nghĩa (semantic search).
"""
from __future__ import annotations

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.db.base import Base

_DIM = get_settings().embed_dim


class IndexJob(Base):
    """Một lần lập chỉ mục RAG — trạng thái bền vững để báo tiến độ cho người dùng.

    Tách khỏi Celery result backend để `GET /api/chat/status` chỉ cần đọc DB,
    không phải hỏi broker; và tiến độ (message) sống sót qua restart worker.
    """

    __tablename__ = "index_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    #  QUEUED | RUNNING | DONE | ERROR
    status: Mapped[str] = mapped_column(String(16), default="QUEUED", nullable=False)
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class RagDocument(Base):
    __tablename__ = "rag_documents"
    __table_args__ = (
        #  Chỉ mục HNSW theo khoảng cách cosine — tìm k đoạn gần nghĩa nhất
        #  nhanh cả khi kho lớn. vector_cosine_ops khớp với phép <=> khi truy vấn.
        Index(
            "ix_rag_documents_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    #  Loại tài liệu: 'summary' | 'analysis' | 'profile' | 'news' ...
    doc_type: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    ticker: Mapped[str] = mapped_column(String(12), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(300), default="")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    #  Khóa ổn định để cập nhật lại đúng đoạn khi lập chỉ mục lần sau (tránh trùng).
    source_key: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)
    embedding: Mapped[list[float]] = mapped_column(Vector(_DIM), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Conversation(Base):
    """Một 'câu chuyện' (thread) hỏi–đáp riêng của người dùng — như ChatGPT/Messenger.

    Mỗi cuộc gom nhiều `ChatMessage`. `ticker` là mã bối cảnh lúc mở cuộc (tùy chọn).
    Xoá cuộc → xoá luôn tin nhắn con (CASCADE).
    """

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), default="")
    ticker: Mapped[str | None] = mapped_column(String(12), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    #  Cập nhật mỗi khi có tin nhắn mới → danh sách xếp theo cuộc gần nhất.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ChatMessage(Base):
    """Một lượt hỏi–đáp RAG đã lưu, để tải lại lịch sử hội thoại của người dùng."""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    #  Thuộc cuộc trò chuyện nào (NULL = tin nhắn phẳng cũ / từ widget nổi).
    conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=True)
    #  Mã đang xem lúc hỏi (NULL = câu hỏi chung, không gắn mã). Cho phép tải lại
    #  lịch sử ĐÚNG theo mã ở widget nổi mà không lẫn hội thoại của mã khác.
    ticker: Mapped[str | None] = mapped_column(String(12), index=True, nullable=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[list] = mapped_column(JSONB, default=list)  # [{ticker,doc_type,title,snippet}]
    #  Tệp đính kèm của lượt hỏi (để hiển thị lại khi tải lịch sử): [{id,filename,mime}]
    attachments: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Attachment(Base):
    """Tệp đính kèm (ảnh/PDF) người dùng gửi kèm câu hỏi cho trợ lý.

    Lưu trên ĐĨA (volume `uploads`); DB chỉ giữ metadata + `stored_name` (tên tệp
    thật trên đĩa, dạng uuid). Xoá user → xoá bản ghi (CASCADE); tệp trên đĩa được
    dọn khi xoá qua API.
    """

    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)  # tên gốc do user đặt
    mime: Mapped[str] = mapped_column(String(80), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)          # byte
    stored_name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
