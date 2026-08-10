"""Lớp cơ sở (Base) cho mọi ORM model.

Tách riêng khỏi `session.py` để tránh import vòng: model chỉ cần `Base`,
còn `session.py` (engine, khởi tạo) mới cần biết tới toàn bộ model.
"""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Gốc khai báo bảng — mọi model kế thừa lớp này."""
