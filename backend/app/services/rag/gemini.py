"""Bọc SDK Gemini: nhúng văn bản (embedding) và sinh câu trả lời.

Client khởi tạo LƯỜI (lazy): app vẫn boot được khi chưa có API key; chỉ khi gọi
tính năng RAG mới bắt buộc phải có `APP_GEMINI_API_KEY`.
"""
from __future__ import annotations

import time
from functools import lru_cache
from typing import Callable, Iterator

from app.core import budget
from app.core.config import get_settings


class GeminiError(RuntimeError):
    """Lỗi thuộc về Gemini (thiếu key, gọi API hỏng) — tách khỏi ProviderError."""


class QuotaError(GeminiError):
    """Hết hạn mức / đang xếp hàng — KHÔNG phải lỗi kỹ thuật.

    Tách riêng vì cách xử lý khác hẳn: lỗi kỹ thuật thì lui về RAG một nhịp cho
    chắc, còn hết hạn mức thì lui cũng vô ích (vẫn phải gọi Gemini) — phải nói
    thật với người dùng là hôm nay hết lượt.
    """


_RATE_LIMIT_MARKS = ("429", "RESOURCE_EXHAUSTED", "rate limit", "quota")


def _is_rate_limited(exc: Exception) -> bool:
    """Google trả 429 (chạm request/phút) — đáng thử lại sau vài giây."""
    text = str(exc).lower()
    return any(mark.lower() in text for mark in _RATE_LIMIT_MARKS)


def _guarded(call: Callable[[], object], what: str):
    """Gọi Gemini qua NGÂN SÁCH: tính vào quota ngày, xếp hàng, thử lại khi 429.

    Mọi lệnh gọi Gemini trong file này đều đi qua đây — đó là lý do bộ đếm phản
    ánh đúng số request THẬT, không phải số "lượt hỏi" (một lượt = 3–7 request).
    """
    attempts = max(1, get_settings().gemini_retry_attempts)
    for attempt in range(attempts):
        try:
            with budget.slot():
                return call()
        except budget.BudgetError as exc:
            raise QuotaError(str(exc)) from exc
        except GeminiError:
            raise
        except Exception as exc:  # pragma: no cover - lỗi mạng/hạn mức từ Gemini
            if _is_rate_limited(exc) and attempt < attempts - 1:
                #  Giãn cách tăng dần: 1s → 2s → 4s. Google tính theo phút nên
                #  chờ vài giây thường là qua.
                time.sleep(2 ** attempt)
                continue
            raise GeminiError(f"{what} lỗi: {exc}") from exc
    raise GeminiError(f"{what} lỗi: hết lượt thử lại.")  # pragma: no cover


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
    resp = _guarded(lambda: _client().models.embed_content(
        model=settings.gemini_embed_model,
        contents=texts,
        config=types.EmbedContentConfig(
            task_type=task, output_dimensionality=settings.embed_dim),
    ), "Gemini nhúng văn bản")
    return [list(item.values) for item in resp.embeddings]


def generate_answer_stream(system_instruction: str, prompt: str):
    """Sinh câu trả lời theo LUỒNG — yield từng mẩu văn bản khi Gemini trả về."""
    from google.genai import types

    settings = get_settings()
    #  Giữ suất trong SUỐT lúc stream (khác các lệnh gọi một-phát): kết nối còn
    #  mở là Google vẫn đang phục vụ ta, nên vẫn phải tính là một chỗ đang chạy.
    try:
        with budget.slot():
            stream = _client().models.generate_content_stream(
                model=settings.gemini_chat_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction, temperature=0.2),
            )
            for chunk in stream:
                if chunk.text:
                    yield chunk.text
    except budget.BudgetError as exc:
        raise QuotaError(str(exc)) from exc
    except GeminiError:
        raise
    except Exception as exc:  # pragma: no cover
        raise GeminiError(f"Gemini sinh câu trả lời (stream) lỗi: {exc}") from exc


def run_agent(
    system_instruction: str,
    history: list[tuple[str, str]],
    question: str,
    tool_declarations: list[dict],
    dispatch: Callable[[str, dict], dict],
    max_steps: int = 5,
    attachment_parts: list[tuple[bytes, str]] | None = None,
) -> Iterator[tuple[str, dict | str]]:
    """Vòng lặp Agentic (gọi hàm — function calling).

    Model tự chọn tool → ta chạy `dispatch(name, args)` → nạp kết quả lại cho
    model → lặp tới khi model chốt câu trả lời (hoặc chạm `max_steps`).

    - `history`: các lượt trước dạng `[(role, text)]`, role ∈ {"user", "model"}.
    - `tool_declarations`: mỗi tool là dict `{name, description, parameters}` với
      `parameters` là JSON Schema (kiểu VIẾT HOA: OBJECT/STRING… theo yêu cầu Gemini).
    - `dispatch(name, args) -> dict`: chạy tool thật, trả kết quả JSON cho model đọc.

    Là GENERATOR: yield `("step", {"tool", "args"})` mỗi lần gọi tool, rồi yield
    đúng một `("answer", text)` ở cuối. Mọi thao tác chạm SDK Gemini nằm gọn ở đây.
    """
    from google.genai import types

    settings = get_settings()
    client = _client()

    tool = types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name=decl["name"], description=decl["description"],
            parameters=decl["parameters"],
        )
        for decl in tool_declarations
    ])
    agent_config = types.GenerateContentConfig(
        system_instruction=system_instruction, tools=[tool], temperature=0.2)

    contents = [
        types.Content(role=role, parts=[types.Part.from_text(text=text)])
        for role, text in history
    ]
    #  Lượt hỏi hiện tại: chữ + (nếu có) các tệp ảnh/PDF cho Gemini đọc (multimodal).
    user_parts = [types.Part.from_text(text=question)]
    for data, mime in (attachment_parts or []):
        user_parts.append(types.Part.from_bytes(data=data, mime_type=mime))
    contents.append(types.Content(role="user", parts=user_parts))

    try:
        for _ in range(max_steps):
            #  MỖI vòng là MỘT request Gemini → đếm riêng. Suất chỉ giữ trong lúc
            #  gọi model, nhả ra khi chạy tool (tool đi crawl, không đụng Gemini).
            resp = _guarded(lambda: client.models.generate_content(
                model=settings.gemini_chat_model, contents=contents, config=agent_config),
                "Gemini agent")
            calls = list(resp.function_calls or [])
            if not calls:
                yield ("answer", (resp.text or "").strip())
                return
            #  Giữ lại lượt model (chứa các function_call) rồi trả kết quả từng tool.
            contents.append(resp.candidates[0].content)
            for call in calls:
                args = dict(call.args or {})
                yield ("step", {"tool": call.name, "args": args})
                result = dispatch(call.name, args)
                contents.append(types.Content(role="user", parts=[
                    types.Part.from_function_response(
                        name=call.name, response={"result": result})]))
        #  Chạm trần số bước → ép model chốt (bỏ tools để không gọi thêm nữa).
        final = _guarded(lambda: client.models.generate_content(
            model=settings.gemini_chat_model, contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction, temperature=0.2)), "Gemini agent")
        yield ("answer", (final.text or "").strip())
    except GeminiError:
        raise
    except Exception as exc:  # pragma: no cover - lỗi mạng/hạn mức/định dạng từ Gemini
        raise GeminiError(f"Gemini agent lỗi: {exc}") from exc


def generate_answer(system_instruction: str, prompt: str) -> str:
    """Sinh câu trả lời. Nhiệt độ thấp để bám sát dữ liệu, ít 'sáng tác'."""
    from google.genai import types

    settings = get_settings()
    resp = _guarded(lambda: _client().models.generate_content(
        model=settings.gemini_chat_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction, temperature=0.2),
    ), "Gemini sinh câu trả lời")
    return (resp.text or "").strip()
