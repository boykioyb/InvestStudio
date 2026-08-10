"""Gom toàn bộ ORM model để `Base.metadata` biết mọi bảng khi create_all."""
from app.models.rag import IndexJob, RagDocument
from app.models.user import User, WatchlistItem

__all__ = ["User", "WatchlistItem", "RagDocument", "IndexJob"]
