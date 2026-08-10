"""Lập chỉ mục kho RAG từ dòng lệnh.

Mặc định ĐẨY VÀO HÀNG ĐỢI Celery (worker xử lý nền, xem `docker compose logs -f worker`):

    docker compose exec backend python -m scripts.reindex            # cả VN30 + tin
    docker compose exec backend python -m scripts.reindex FPT VCB    # vài mã (chỉ tin)
    docker compose exec backend python -m scripts.reindex --deep     # + điểm số/ROE (CHẬM)
    docker compose exec backend python -m scripts.reindex --inline   # chạy NGAY, không cần worker
    docker compose exec backend python -m scripts.reindex --full     # lập lại từ đầu (bỏ resume)

Nội dung mặc định (nhẹ, an toàn với trần 20 request/phút): tóm tắt VN30 (1
request cho cả rổ) + tin tức từng mã. `--deep` gọi thêm `analyze()` cho từng mã.
Mặc định RESUME: bỏ qua mã đã có tin nên chạy lại sẽ đi tiếp từ chỗ dừng (hữu ích
vì vnai có thể giết tiến trình khi chạm trần). `--full` để ép lập lại toàn bộ.
"""
from __future__ import annotations

import sys


def main() -> None:
    args = sys.argv[1:]
    deep = "--deep" in args
    inline = "--inline" in args
    skip_existing = "--full" not in args
    symbols = [a.upper() for a in args if not a.startswith("--")] or None

    scope = "toàn bộ VN30" if not symbols else ", ".join(symbols)
    tail = " + phân tích sâu" if deep else ""

    if inline:
        from app.db.session import init_db
        from app.services.rag import indexer

        init_db()
        print(f"[inline] Lập chỉ mục ({scope}){tail}…")
        print(indexer.reindex_blocking(symbols=symbols, include_news=True, deep=deep,
                                       skip_existing=skip_existing))
        return

    #  Đẩy vào hàng đợi — cần Redis + worker đang chạy.
    from app.services.rag.tasks import reindex_task

    task = reindex_task.delay(symbols, True, deep, skip_existing)
    print(f"Đã đưa vào hàng đợi ({scope}){tail}. Task id: {task.id}")
    print("Theo dõi: docker compose logs -f worker  |  hoặc GET /api/chat/status")


if __name__ == "__main__":
    main()
