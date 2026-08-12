"""Gom toàn bộ ORM model để `Base.metadata` biết mọi bảng khi create_all."""
from app.models.rag import ChatMessage, IndexJob, RagDocument
from app.models.user import Notification, User, WatchlistItem

__all__ = ["User", "WatchlistItem", "Notification", "RagDocument", "IndexJob", "ChatMessage"]
