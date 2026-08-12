"""Route thông báo trong app (cảnh báo ngưỡng theo dõi). Yêu cầu đăng nhập."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import Notification, User
from app.schemas.notification import NotificationOut

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut], summary="Danh sách thông báo (mới nhất trước)")
def list_notifications(user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)) -> list[Notification]:
    return list(db.scalars(
        select(Notification).where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc()).limit(100)
    ))


@router.get("/unread-count", summary="Số thông báo chưa đọc")
def unread_count(user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)) -> dict[str, int]:
    count = db.scalar(select(func.count()).select_from(Notification).where(
        Notification.user_id == user.id, Notification.is_read.is_(False))) or 0
    return {"count": int(count)}


@router.post("/{notif_id}/read", status_code=status.HTTP_204_NO_CONTENT,
             summary="Đánh dấu một thông báo đã đọc")
def mark_read(notif_id: int = Path(..., ge=1),
              user: User = Depends(get_current_user),
              db: Session = Depends(get_db)) -> None:
    notif = db.get(Notification, notif_id)
    if notif is None or notif.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy thông báo.")
    notif.is_read = True
    db.commit()


@router.post("/read-all", summary="Đánh dấu tất cả đã đọc")
def mark_all_read(user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(update(Notification).where(
        Notification.user_id == user.id, Notification.is_read.is_(False))
        .values(is_read=True))
    db.commit()
    return {"detail": "Đã đánh dấu tất cả là đã đọc."}
