"""bảng usage_events · usage_daily · audit_logs · app_settings (khu quản trị)

Nền số liệu cho /admin: đo mức tiêu thụ hạn mức, ghi vết thao tác quản trị, và
cho phép TẮT tính năng ngay trong giao diện mà không cần deploy lại.

Idempotent: create_all(checkfirst=True).

Revision ID: 0008
Revises: 0007
"""
from alembic import op

from app.db.base import Base
from app.models.admin import AppSetting, AuditLog  # noqa: F401
from app.models.usage import UsageDaily, UsageEvent  # noqa: F401

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

_TABLES = ["usage_events", "usage_daily", "audit_logs", "app_settings"]


def upgrade() -> None:
    Base.metadata.create_all(op.get_bind(), tables=[
        Base.metadata.tables[name] for name in _TABLES], checkfirst=True)


def downgrade() -> None:
    Base.metadata.drop_all(op.get_bind(), tables=[
        Base.metadata.tables[name] for name in reversed(_TABLES)], checkfirst=True)
