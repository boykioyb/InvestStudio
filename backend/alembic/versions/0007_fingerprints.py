"""bảng device_fingerprints + device_accounts (hạn mức theo THIẾT BỊ)

Hạn mức theo tài khoản bị vô hiệu chỉ bằng việc đăng ký thêm email. Hai bảng này
cho phép đếm theo thiết bị và soi cụm tài khoản dùng chung một máy.

Idempotent: create_all(checkfirst=True).

Revision ID: 0007
Revises: 0006
"""
from alembic import op

from app.db.base import Base
from app.models.device import DeviceAccount, DeviceFingerprint  # noqa: F401

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

_TABLES = ["device_fingerprints", "device_accounts"]


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind, tables=[
        Base.metadata.tables[name] for name in _TABLES], checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind, tables=[
        Base.metadata.tables[name] for name in reversed(_TABLES)], checkfirst=True)
