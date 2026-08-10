"""Thao tác trên kho vector: upsert tài liệu và tìm theo ngữ nghĩa.

`source_key` là khóa ổn định (VD 'analysis:FPT') để lập chỉ mục lại thì GHI ĐÈ
đúng đoạn cũ thay vì đẻ ra bản trùng.
"""
from __future__ import annotations

from typing import Optional, TypedDict

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.rag import RagDocument


class DocInput(TypedDict):
    source_key: str
    doc_type: str
    ticker: str
    title: str
    content: str
    meta: dict
    embedding: list[float]


def upsert_documents(db: Session, docs: list[DocInput]) -> int:
    """Chèn mới hoặc cập nhật theo `source_key`. Trả số dòng đã xử lý."""
    if not docs:
        return 0
    stmt = insert(RagDocument).values(docs)
    stmt = stmt.on_conflict_do_update(
        index_elements=[RagDocument.source_key],
        set_={
            "doc_type": stmt.excluded.doc_type,
            "ticker": stmt.excluded.ticker,
            "title": stmt.excluded.title,
            "content": stmt.excluded.content,
            "meta": stmt.excluded.meta,
            "embedding": stmt.excluded.embedding,
        },
    )
    db.execute(stmt)
    db.commit()
    return len(docs)


def search(db: Session, query_embedding: list[float], top_k: int,
           ticker: Optional[str] = None) -> list[tuple[RagDocument, float]]:
    """k tài liệu gần nghĩa nhất, kèm điểm tương đồng cosine (1.0 = trùng khớp).

    Dùng toán tử `<=>` của pgvector (cosine distance); tương đồng = 1 − distance.
    """
    distance = RagDocument.embedding.cosine_distance(query_embedding)
    stmt = select(RagDocument, distance.label("distance"))
    if ticker:
        stmt = stmt.where(RagDocument.ticker == ticker.upper().strip())
    stmt = stmt.order_by(distance.asc()).limit(top_k)
    return [(doc, 1.0 - float(dist)) for doc, dist in db.execute(stmt)]


def stats(db: Session) -> tuple[int, int]:
    """(số tài liệu, số mã) đang có trong kho."""
    documents = db.scalar(select(func.count()).select_from(RagDocument)) or 0
    tickers = db.scalar(select(func.count(func.distinct(RagDocument.ticker)))) or 0
    return int(documents), int(tickers)


def existing_source_keys(db: Session, prefix: Optional[str] = None) -> set[str]:
    """Tập `source_key` đã có (lọc theo tiền tố như 'news:'). Dùng để lập chỉ mục
    RESUME được — bỏ qua mã đã xong, chạy lại là đi tiếp từ chỗ dừng."""
    stmt = select(RagDocument.source_key)
    if prefix:
        stmt = stmt.where(RagDocument.source_key.like(f"{prefix}%"))
    return set(db.scalars(stmt))
