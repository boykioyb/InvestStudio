"""Route danh sách mã yêu thích / theo dõi (yêu cầu đăng nhập).

CRUD thuần trên bảng `watchlist_items`; mọi mục đều gắn với người dùng đang
đăng nhập nên một tài khoản không bao giờ thấy/sửa mục của tài khoản khác.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User, WatchlistItem
from app.schemas.watchlist import WatchlistItemIn, WatchlistItemOut, WatchlistItemUpdate

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("", response_model=list[WatchlistItemOut], summary="Danh sách mã đang theo dõi")
def list_items(user: User = Depends(get_current_user),
               db: Session = Depends(get_db)) -> list[WatchlistItem]:
    return list(db.scalars(
        select(WatchlistItem).where(WatchlistItem.user_id == user.id)
        .order_by(WatchlistItem.created_at.desc())
    ))


@router.post("", response_model=WatchlistItemOut, status_code=status.HTTP_201_CREATED,
             summary="Thêm một mã vào danh sách theo dõi")
def add_item(payload: WatchlistItemIn, user: User = Depends(get_current_user),
             db: Session = Depends(get_db)) -> WatchlistItem:
    exists = db.scalar(
        select(WatchlistItem).where(
            WatchlistItem.user_id == user.id, WatchlistItem.ticker == payload.ticker)
    )
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"{payload.ticker} đã có trong danh sách.")

    item = WatchlistItem(
        user_id=user.id,
        ticker=payload.ticker,
        note=payload.note.strip(),
        target_price=payload.target_price,
        target_score=payload.target_score,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def _owned_item(item_id: int, user: User, db: Session) -> WatchlistItem:
    item = db.get(WatchlistItem, item_id)
    if item is None or item.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy mục theo dõi.")
    return item


@router.patch("/{item_id}", response_model=WatchlistItemOut,
              summary="Sửa ghi chú / ngưỡng của một mục")
def update_item(payload: WatchlistItemUpdate,
                item_id: int = Path(..., ge=1),
                user: User = Depends(get_current_user),
                db: Session = Depends(get_db)) -> WatchlistItem:
    item = _owned_item(item_id, user, db)
    #  Chỉ đụng vào trường thực sự được gửi lên (exclude_unset) → gửi null có
    #  chủ đích vẫn xóa ngưỡng, còn trường bỏ trống thì giữ nguyên.
    data = payload.model_dump(exclude_unset=True)
    if "note" in data and data["note"] is not None:
        data["note"] = data["note"].strip()
    for field, value in data.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Bỏ theo dõi một mã")
def delete_item(item_id: int = Path(..., ge=1),
                user: User = Depends(get_current_user),
                db: Session = Depends(get_db)) -> None:
    item = _owned_item(item_id, user, db)
    db.delete(item)
    db.commit()
