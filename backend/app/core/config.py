"""Cấu hình ứng dụng (đọc từ biến môi trường)."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    app_name: str = "InvestStudio API"
    version: str = "2.0.0"
    # Origin của frontend Nuxt được phép gọi API (CORS).
    cors_origins: list[str] = ["http://localhost:3010", "http://127.0.0.1:3010"]
    # Thời gian cache kết quả phân tích (giây) — tránh gọi nguồn liên tục.
    cache_ttl_seconds: int = 900


@lru_cache
def get_settings() -> Settings:
    return Settings()
