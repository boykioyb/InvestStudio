"""Trả lời câu hỏi bằng RAG: truy xuất đoạn liên quan → để Gemini tổng hợp.

Nguyên tắc: câu trả lời CHỈ được dựa trên ngữ cảnh truy xuất được. Không đủ dữ
liệu thì nói thẳng là không đủ — tuyệt đối không bịa số; đưa kết luận dựa trên dữ
liệu kèm rủi ro, không phải lời mời chào đầu tư.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.schemas.chat import ChatResponse, Citation
from app.services.rag import store
from app.services.rag.gemini import embed_texts, generate_answer, generate_answer_stream

_SYSTEM = (
    "Bạn là trợ lý phân tích cổ phiếu Việt Nam của Phân Tích Mã. "
    "CHỈ được dùng số liệu trong phần 'NGỮ CẢNH' bên dưới — không bịa; nếu ngữ cảnh "
    "không đủ, nói rõ là dữ liệu chưa được lập chỉ mục/chưa đủ. "
    "KHÔNG chỉ liệt kê thông tin: sau khi đọc ngữ cảnh, hãy đưa ra MỘT kết luận rõ "
    "ràng và bảo vệ nó bằng con số có trong ngữ cảnh. "
    "Với câu hỏi cần quyết định (mua/chờ/bán, 'giá X đã hợp lý chưa'), trả lời theo: "
    "KẾT LUẬN (một lập trường dứt khoát + mức tin cậy) → CĂN CỨ (2–4 ý, mỗi ý gắn "
    "một con số) → RỦI RO/điều kiện đảo chiều. Nếu ngữ cảnh chưa đủ để kết luận, nói "
    "thẳng còn thiếu dữ liệu gì thay vì né bằng 'tùy khẩu vị'. "
    "Trả lời bằng tiếng Việt, súc tích, kết bằng đúng một dòng: đây là phân tích "
    "tham khảo, quyết định cuối cùng thuộc về bạn."
)


def _snippet(text: str, limit: int = 240) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit].rstrip() + "…"


def _empty_answer(ticker: Optional[str]) -> str:
    if ticker:
        return (f"Chưa có dữ liệu về {ticker}. Hãy mở màn Phân tích mã {ticker} một lần — "
                "trợ lý sẽ tự học mã này ngay sau đó. (Hoặc dùng nút 'Lập chỉ mục' ở "
                "trang Trợ lý để nạp cả rổ VN30.)")
    return ("Kho dữ liệu chưa được lập chỉ mục. Vào trang Trợ lý (💬) rồi bấm "
            "'Lập chỉ mục VN30 + tin', hoặc cứ phân tích một mã bất kỳ để trợ lý học dần.")


def _retrieve(db: Session, question: str, ticker: Optional[str]):
    """Trả (prompt, citations). prompt=None nghĩa là kho chưa có dữ liệu phù hợp."""
    settings = get_settings()
    query_vector = embed_texts([question], is_query=True)[0]
    hits = store.search(db, query_vector, settings.rag_top_k, ticker=ticker)
    if not hits:
        return None, []

    #  Ghép ngữ cảnh có đánh số để Gemini có thể dẫn nguồn [1], [2]…
    context_blocks: list[str] = []
    citations: list[Citation] = []
    for index, (doc, _score) in enumerate(hits, start=1):
        context_blocks.append(f"[{index}] ({doc.ticker} · {doc.title})\n{doc.content}")
        citations.append(Citation(
            ticker=doc.ticker, doc_type=doc.doc_type, title=doc.title,
            snippet=_snippet(doc.content),
        ))
    prompt = (
        f"CÂU HỎI: {question}\n\n"
        "NGỮ CẢNH (mỗi khối là một nguồn, đánh số trong ngoặc vuông):\n"
        + "\n\n".join(context_blocks)
        + "\n\nHãy trả lời câu hỏi chỉ dựa trên ngữ cảnh trên."
    )
    return prompt, citations


def answer_question(db: Session, question: str, ticker: Optional[str] = None) -> ChatResponse:
    prompt, citations = _retrieve(db, question, ticker)
    if prompt is None:
        return ChatResponse(answer=_empty_answer(ticker), citations=[])
    answer = generate_answer(_SYSTEM, prompt) or "Xin lỗi, chưa tạo được câu trả lời."
    return ChatResponse(answer=answer, citations=citations)


def answer_stream(db: Session, question: str, ticker: Optional[str] = None):
    """Generator: yield ('delta', text) nhiều lần rồi ('final', ChatResponse)."""
    prompt, citations = _retrieve(db, question, ticker)
    if prompt is None:
        yield ("final", ChatResponse(answer=_empty_answer(ticker), citations=[]))
        return
    parts: list[str] = []
    for delta in generate_answer_stream(_SYSTEM, prompt):
        parts.append(delta)
        yield ("delta", delta)
    answer = "".join(parts).strip() or "Xin lỗi, chưa tạo được câu trả lời."
    yield ("final", ChatResponse(answer=answer, citations=citations))
