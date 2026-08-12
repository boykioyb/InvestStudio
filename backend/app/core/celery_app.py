"""Khởi tạo Celery — hàng đợi job nền (broker + result backend là Redis).

Worker chạy bằng:  celery -A app.core.celery_app:celery_app worker -l info
"""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

_settings = get_settings()

celery_app = Celery(
    "investstudio",
    broker=_settings.celery_broker_url,
    backend=_settings.celery_result_backend,
    include=["app.services.rag.tasks"],  # nạp để task được đăng ký
)

celery_app.conf.update(
    task_track_started=True,             # có trạng thái STARTED, không chỉ PENDING→SUCCESS
    broker_connection_retry_on_startup=True,
    result_expires=3600,                 # kết quả job giữ 1 giờ
    timezone="Asia/Ho_Chi_Minh",
    enable_utc=False,                    # để crontab hiểu theo giờ VN
)

#  Lịch chạy nền (cần service `beat`). Reindex RAG mỗi sáng trước phiên; quét
#  ngưỡng theo dõi mỗi 30 phút.
celery_app.conf.beat_schedule = {
    "reindex-vn30-daily": {
        "task": "rag.reindex",
        "schedule": crontab(hour=8, minute=0),
        "args": (None, True, False),  # (symbols, include_news, deep)
    },
    "check-watchlist-alerts": {
        "task": "watchlist.check_alerts",
        "schedule": 1800.0,  # 30 phút
    },
}
