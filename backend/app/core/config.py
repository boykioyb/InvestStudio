"""Cấu hình ứng dụng (đọc từ biến môi trường, tiền tố APP_)."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

#  Giá trị JWT secret dùng cho DEV. Nếu còn nguyên chuỗi này ở môi trường thật
#  (cookie_secure=True) thì app TỪ CHỐI khởi động — xem app/main.py.
DEV_JWT_SECRET = "doi-bi-mat-nay-truoc-khi-len-that"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    app_name: str = "InvestStudio API"
    version: str = "3.0.0"
    # Origin của frontend Nuxt được phép gọi API (CORS).
    cors_origins: list[str] = ["http://localhost:3010", "http://127.0.0.1:3010"]
    # Thời gian cache kết quả phân tích (giây) — tránh gọi nguồn liên tục.
    cache_ttl_seconds: int = 900

    # ── Cơ sở dữ liệu (PostgreSQL + pgvector) ────────────────────────────────
    #  Dialect psycopg (psycopg 3). Trong Docker host là "postgres" (tên service).
    database_url: str = "postgresql+psycopg://invest:invest@localhost:5432/investstudio"

    # ── Xác thực (JWT trong cookie httpOnly) ─────────────────────────────────
    #  ⚠️ ĐỔI ở môi trường thật — bí mật này ký toàn bộ token đăng nhập.
    jwt_secret: str = DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 ngày
    #  Cookie chỉ gửi qua HTTPS khi bật. Để False khi chạy http://localhost.
    cookie_secure: bool = False
    cookie_name: str = "access_token"

    # ── RAG / Gemini ─────────────────────────────────────────────────────────
    gemini_api_key: str = ""                       # lấy ở https://aistudio.google.com/apikey
    gemini_chat_model: str = "gemini-3.6-flash"    # model sinh câu trả lời (đổi qua LLM_MODEL)
    gemini_embed_model: str = "gemini-embedding-001"  # model nhúng (đổi qua EMBED_MODEL)
    #  gemini-embedding-001 mặc định 3072 chiều nhưng ép được về 768 (Matryoshka)
    #  bằng output_dimensionality → khớp cột Vector(768), không phải đổi schema.
    embed_dim: int = 768
    rag_top_k: int = 6                            # số đoạn văn bản lấy về cho mỗi câu hỏi
    #  Giãn cách (giây) giữa 2 lần gọi nguồn khi lập chỉ mục — nguồn giới hạn
    #  ~20 request/phút và vnai có thể GIẾT tiến trình khi chạm trần. 6s ≈ 10
    #  req/phút, biên an toàn rộng; job resume được nên chậm mà chắc.
    index_throttle_seconds: float = 6.0

    # ── Celery (hàng đợi job nền) ────────────────────────────────────────────
    #  Mặc định localhost cho chạy máy; Docker ghi đè thành host "redis".
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # ── Giới hạn tần suất đăng nhập (chống dò mật khẩu) ──────────────────────
    rate_limit_redis_url: str = "redis://localhost:6379/2"
    login_max_attempts: int = 10          # số lần/cửa sổ cho mỗi IP
    login_window_seconds: int = 300       # cửa sổ 5 phút
    rag_daily_quota: int = 100            # số lượt hỏi trợ lý/user/ngày (chống cháy Gemini)

    # ── Agentic RAG (trợ lý tự chọn công cụ) ─────────────────────────────────
    #  Bật vòng lặp agent: model tự gọi tool (phân tích/xếp hạng/tìm tri thức)
    #  rồi tổng hợp. Tắt → lui về RAG một-nhịp cũ (retrieve → answer).
    rag_agent_enabled: bool = True
    #  Trần số vòng gọi tool cho MỖI câu hỏi — chặn lặp vô tận + đốt quota Gemini
    #  (1 câu vẫn tính 1 đơn vị quota, nhưng mỗi vòng là 1 lần gọi model).
    rag_agent_max_steps: int = 5
    #  Số lượt hội thoại gần nhất frontend gửi kèm để agent giữ ngữ cảnh ("nó"…).
    rag_history_turns: int = 6


@lru_cache
def get_settings() -> Settings:
    return Settings()
