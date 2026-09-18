"""Beacon số liệu sản phẩm: frontend báo về các sự kiện GIAO DIỆN để đo NSM.

Chỉ nhận HAI loại sự kiện do người dùng tạo ở trình duyệt:
  · why_open      — mở phần "vì sao điểm này" (đo giả định "user có tin điểm không")
  · score_action  — hành động sau khi xem điểm (VD theo dõi mã)

Sự kiện `analyze`/`assistant` KHÔNG nhận ở đây: máy chủ tự ghi tại nơi việc thật
xảy ra (routes/stocks.py, routes/chat.py) nên không ai giả được số đếm.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_user_optional
from app.core import fingerprint, ratelimit
from app.models.user import User
from app.services import analytics

router = APIRouter(prefix="/metrics", tags=["metrics"])

#  FE chỉ được ghi hai sự kiện giao diện này.
_CLIENT_EVENTS = {"why_open", "score_action"}


class MetricEventIn(BaseModel):
    event: str = Field(..., max_length=24)
    ticker: str = Field("", max_length=12)
    ref: str = Field("", max_length=48)


@router.post("/event", status_code=status.HTTP_204_NO_CONTENT,
             summary="Ghi một sự kiện giao diện để đo North Star Metric")
def log_metric_event(
    payload: MetricEventIn,
    request: Request,
    user: User | None = Depends(get_current_user_optional),
) -> Response:
    if payload.event not in _CLIENT_EVENTS:
        #  Không lộ danh sách hợp lệ; chỉ từ chối gọn.
        return Response(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

    #  Chống spam beacon: trần rộng, Redis lỗi thì cho qua (số liệu không đáng chặn trang).
    ratelimit.enforce_window(request, "metrics", limit=240, window_seconds=60)

    analytics.log_event(
        payload.event,
        user_id=(user.id if user else None),
        fp_hash=fingerprint.device_fp(request),
        ticker=payload.ticker,
        ref=payload.ref,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
