"""Ghi nhật ký kiểm toán cho mọi thao tác quản trị.

Quy tắc: MỌI thao tác ghi trong /admin, và mọi lần XEM dữ liệu cá nhân của một
người cụ thể, đều để lại một dòng. Việc ghi không bao giờ chặn thao tác — nó là
bằng chứng, không phải cái khóa.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.ratelimit import client_ip



logger = logging.getLogger("app.audit")

def log(db: Session, actor, action: str, *, request: Request | None = None,
        target_type: str = "", target_id: str | int = "",
        before: dict[str, Any] | None = None, after: dict[str, Any] | None = None,
        reason: str = "") -> None:
    from app.models.admin import AuditLog
    try:
        db.add(AuditLog(
            actor_user_id=getattr(actor, "id", None),
            actor_email=getattr(actor, "email", "")[:255],
            actor_ip=(client_ip(request) if request is not None else "")[:45],
            action=action[:64], target_type=target_type[:32], target_id=str(target_id)[:64],
            before=before or {}, after=after or {}, reason=reason))
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.error("Không ghi được nhật ký kiểm toán", extra={"action": action, "error": str(exc)})
