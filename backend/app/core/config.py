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
    #  "dev" | "prod". Ở prod: tắt /docs, /openapi.json và bật header bảo mật.
    env: str = "dev"
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
    #  Số lượt hỏi trợ lý/user/ngày. Đặt 5 vì Gemini đang chạy BẢN MIỄN PHÍ:
    #  quota ngày hữu hạn và KHÔNG mua thêm được — hết là trợ lý im với mọi
    #  người tới 0h hôm sau. Xem thêm app/core/budget.py.
    rag_daily_quota: int = 5

    # ── Giới hạn tần suất chung + IP thật sau proxy ──────────────────────────
    #  Trần request/phút cho MỖI IP trên toàn bộ /api (chống quét, chống DoS rẻ tiền).
    api_rate_limit_per_minute: int = 120
    #  Số lượt phân tích/ngày: khách (theo IP) và thành viên (theo tài khoản).
    guest_analyze_daily: int = 30
    member_analyze_daily: int = 100
    member_refresh_daily: int = 10        # số lần ép crawl lại (bỏ qua cache)
    #  CHỈ tin X-Forwarded-For khi request đến từ các IP này (proxy của mình).
    #  Rỗng = không tin ai → luôn dùng IP kết nối trực tiếp. Trong Docker, Nuxt
    #  proxy nằm cùng mạng nội bộ nên thường là dải 172.16.0.0/12 → khai "*"
    #  CHỈ khi backend chắc chắn không phơi thẳng ra Internet (xem H5).
    trusted_proxies: list[str] = []
    #  Số hop tin cậy tính từ CUỐI chuỗi X-Forwarded-For (phần do proxy của mình
    #  ghi). Lấy từ cuối chứ không phải từ đầu — hop đầu do client tự khai.
    trusted_proxy_hops: int = 1

    # ── Ngân sách Gemini (bản miễn phí: RPM/RPD hữu hạn, không mua thêm) ──────
    #  Trần SỐ REQUEST Gemini/ngày. Đọc quota thật của dự án trong AI Studio rồi
    #  chừa lại ~100 cho job nền (reindex 8h sáng) — hết quota giữa ngày thì job
    #  chết lặng và kho RAG đứng yên mà không ai biết.
    gemini_daily_call_cap: int = 1400
    #  Số câu hỏi được gọi Gemini CÙNG LÚC. Bản miễn phí ~10–15 request/phút mà
    #  một câu hỏi bắn 3–7 request liên tiếp → 2 là biên an toàn.
    gemini_max_concurrent: int = 2
    gemini_slot_wait_seconds: float = 15.0   # chờ tối đa khi đang kẹt hàng đợi
    gemini_retry_attempts: int = 3           # thử lại khi Google trả 429
    #  Hạ cấp mềm theo % quota ngày đã dùng: qua mức này thì TẮT agent, lui về
    #  RAG một nhịp (1 request thay vì 3–7).
    gemini_degrade_at: float = 0.70
    #  Qua mức này thì chỉ người ĐÃ hỏi trong ngày mới được hỏi tiếp.
    gemini_block_new_at: float = 0.90

    # ── Agentic RAG (trợ lý tự chọn công cụ) ─────────────────────────────────
    #  Bật vòng lặp agent: model tự gọi tool (phân tích/xếp hạng/tìm tri thức)
    #  rồi tổng hợp. Tắt → lui về RAG một-nhịp cũ (retrieve → answer).
    rag_agent_enabled: bool = True
    #  Trần số vòng gọi tool cho MỖI câu hỏi — chặn lặp vô tận + đốt quota Gemini
    #  (1 câu vẫn tính 1 đơn vị quota, nhưng mỗi vòng là 1 lần gọi model).
    rag_agent_max_steps: int = 3
    #  Số lượt hội thoại gần nhất frontend gửi kèm để agent giữ ngữ cảnh ("nó"…).
    rag_history_turns: int = 4

    # ── Đính kèm (attachment) ────────────────────────────────────────────────
    upload_dir: str = "/app/uploads"       # thư mục lưu tệp (khớp volume trong compose)
    upload_max_bytes: int = 10_485_760     # 10 MB/tệp
    upload_max_per_message: int = 4        # số tệp tối đa mỗi câu hỏi
    #  Chỉ nhận ảnh + PDF — thứ Gemini đọc được (multimodal). Chặn tệp lạ.
    upload_allowed_mimes: tuple[str, ...] = (
        "image/png", "image/jpeg", "image/webp", "image/gif", "application/pdf",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
