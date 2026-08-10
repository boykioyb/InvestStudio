"""Khởi tạo Celery — hàng đợi job nền (broker + result backend là Redis).

Worker chạy bằng:  celery -A app.core.celery_app:celery_app worker -l info
"""
from __future__ import annotations

from celery import Celery

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
)
