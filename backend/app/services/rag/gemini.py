"""Bọc SDK Gemini: nhúng văn bản (embedding) và sinh câu trả lời.

Client khởi tạo LƯỜI (lazy): app vẫn boot được khi chưa có API key; chỉ khi gọi
tính năng RAG mới bắt buộc phải có `APP_GEMINI_API_KEY`.
"""
from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings


class GeminiError(RuntimeError):
    """Lỗi thuộc về Gemini (thiếu key, gọi API hỏng) — tách khỏi ProviderError."""


@lru_cache
def _client():
    settings = get_settings()
    if not settings.gemini_api_key:
        raise GeminiError(
            "Chưa cấu hình APP_GEMINI_API_KEY. Lấy key tại https://aistudio.google.com/apikey"
        )
    try:
        from google import genai
    except ImportError as exc:  # pragma: no cover
        raise GeminiError("Chưa cài thư viện google-genai.") from exc
    return genai.Client(api_key=settings.gemini_api_key)


def embed_texts(texts: list[str], *, is_query: bool = False) -> list[list[float]]:
    """Nhúng một loạt văn bản thành vector.

    `is_query=True` khi nhúng CÂU HỎI (dùng task_type RETRIEVAL_QUERY); mặc định
    nhúng TÀI LIỆU (RETRIEVAL_DOCUMENT) — Gemini tối ưu khác nhau cho hai vế này.
    """
    if not texts:
        return []
    from google.genai import types

    settings = get_settings()
    task = "RETRIEVAL_QUERY" if is_query else "RETRIEVAL_DOCUMENT"
    try:
        resp = _client().models.embed_content(
            model=settings.gemini_embed_model,
            contents=texts,
            config=types.EmbedContentConfig(
                task_type=task, output_dimensionality=settings.embed_dim
            ),
        )
    except GeminiError:
        raise
    except Exception as exc:  # pragma: no cover - lỗi mạng/hạn mức từ Gemini
        raise GeminiError(f"Gemini nhúng văn bản lỗi: {exc}") from exc
    return [list(item.values) for item in resp.embeddings]


def generate_answer(system_instruction: str, prompt: str) -> str:
    """Sinh câu trả lời. Nhiệt độ thấp để bám sát dữ liệu, ít 'sáng tác'."""
    from google.genai import types

    settings = get_settings()
    try:
        resp = _client().models.generate_content(
            model=settings.gemini_chat_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction, temperature=0.2
            ),
        )
    except GeminiError:
        raise
    except Exception as exc:  # pragma: no cover
        raise GeminiError(f"Gemini sinh câu trả lời lỗi: {exc}") from exc
    return (resp.text or "").strip()
