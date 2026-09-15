"""Gom toàn bộ ORM model để `Base.metadata` biết mọi bảng khi create_all."""
from app.models.admin import AppSetting, AuditLog
from app.models.device import DeviceAccount, DeviceFingerprint
from app.models.portfolio import ImportedHolding, ImportedLot
from app.models.rag import ChatMessage, IndexJob, RagDocument
from app.models.usage import UsageDaily, UsageEvent
from app.models.user import Notification, User, WatchlistItem

__all__ = ["User", "WatchlistItem", "Notification", "RagDocument", "IndexJob", "ChatMessage",
           "DeviceFingerprint", "DeviceAccount", "UsageEvent", "UsageDaily",
           "AuditLog", "AppSetting", "ImportedHolding", "ImportedLot"]
