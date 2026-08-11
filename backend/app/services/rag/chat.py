"""Trả lời câu hỏi bằng RAG: truy xuất đoạn liên quan → để Gemini tổng hợp.

Nguyên tắc: câu trả lời CHỈ được dựa trên ngữ cảnh truy xuất được. Không đủ dữ
liệu thì nói thẳng là không đủ — tuyệt đối không bịa số, không khuyến nghị mua bán.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.schemas.chat import ChatResponse, Citation
from app.services.rag import store
from app.services.rag.gemini import embed_texts, generate_answer

_SYSTEM = (
    "Bạn là trợ lý phân tích cổ phiếu Việt Nam của InvestStudio. "
    "CHỈ được trả lời dựa trên phần 'NGỮ CẢNH' cung cấp bên dưới. "
    "Nếu ngữ cảnh không đủ để trả lời, hãy nói rõ là dữ liệu chưa được lập chỉ mục "
    "hoặc chưa đủ, KHÔNG được bịa số liệu. "
    "Luôn trả lời bằng tiếng Việt, ngắn gọn, có dẫn số cụ thể khi ngữ cảnh có. "
    "Cuối câu trả lời KHÔNG được đưa ra lời khuyên mua/bán — đây là công cụ hỗ trợ "
    "tư duy, không phải khuyến nghị đầu tư."
)


def _snippet(text: str, limit: int = 240) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit].rstrip() + "…"


def answer_question(db: Session, question: str, ticker: Optional[str] = None) -> ChatResponse:
    settings = get_settings()
    query_vector = embed_texts([question], is_query=True)[0]
    hits = store.search(db, query_vector, settings.rag_top_k, ticker=ticker)

    if not hits:
        if ticker:
            answer = (f"Chưa có dữ liệu về {ticker}. Hãy mở màn Phân tích mã {ticker} một lần — "
                      "trợ lý sẽ tự học mã này ngay sau đó. (Hoặc dùng nút 'Lập chỉ mục' ở "
                      "trang Trợ lý để nạp cả rổ VN30.)")
        else:
            answer = ("Kho dữ liệu chưa được lập chỉ mục. Vào trang Trợ lý (💬) rồi bấm "
                      "'Lập chỉ mục VN30 + tin', hoặc cứ phân tích một mã bất kỳ để trợ lý học dần.")
        return ChatResponse(answer=answer, citations=[])

    #  Ghép ngữ cảnh có đánh số để Gemini có thể dẫn nguồn [1], [2]…
    context_blocks = []
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
    answer = generate_answer(_SYSTEM, prompt) or "Xin lỗi, chưa tạo được câu trả lời."
    return ChatResponse(answer=answer, citations=citations)
