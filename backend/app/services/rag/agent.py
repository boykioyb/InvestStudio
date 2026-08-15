"""Agentic RAG: trợ lý TỰ CHỌN công cụ để lấy dữ liệu thật rồi tổng hợp.

Khác RAG một-nhịp (`chat.py`, chỉ 1 lần tìm vector → 1 lần trả lời), agent để
Gemini điều phối: mỗi vòng model chọn gọi một CÔNG CỤ (tool = hàm backend đã có),
ta chạy rồi nạp kết quả lại, lặp tới khi đủ để trả lời.

3 công cụ Pha 1 — đều bọc service sẵn có, KHÔNG thêm nguồn dữ liệu mới:
  · tim_kiem_tri_thuc  → store.search   (kho vector: tin tức / tổng quan / phân tích)
  · phan_tich_ma       → analyzer.analyze (chấm điểm 100, dữ liệu TƯƠI)
  · xep_hang_ro        → screener.fetch_list (xếp hạng rổ VN30/VN100/HNX30/HOSE)

Nguyên tắc bất di bất dịch (giữ như RAG cũ): số liệu chỉ đến từ công cụ — không
bịa; không khuyên mua/bán; trả lời tiếng Việt, có dẫn nguồn. Thiếu key/agent lỗi
thì LUI về RAG một-nhịp (`chat.py`) cho chắc — app không bao giờ mất tính năng.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.schemas.chat import AgentStep, ChatResponse, ChatTurnInput, Citation
from app.services import analyzer, screener
from app.services.providers.base import ProviderError
from app.services.rag import chat, gemini, store
from app.services.rag.gemini import GeminiError, embed_texts

_SYSTEM = (
    "Bạn là trợ lý phân tích cổ phiếu Việt Nam của InvestStudio. Bạn có các CÔNG CỤ "
    "để lấy dữ liệu THẬT: phân tích chấm điểm một mã, xếp hạng rổ chỉ số, và tìm "
    "trong kho tri thức đã lập chỉ mục (tin tức, tổng quan).\n"
    "QUY TẮC:\n"
    "1) Mọi CON SỐ trong câu trả lời phải đến từ kết quả công cụ — TUYỆT ĐỐI không bịa.\n"
    "2) Công cụ trả lỗi/thiếu dữ liệu thì nói thẳng là chưa có, gợi ý người dùng phân "
    "tích hoặc lập chỉ mục mã đó — không suy đoán.\n"
    "3) Dùng lịch sử hội thoại để hiểu câu hỏi nối tiếp (đại từ 'nó', 'mã này'…).\n"
    "4) KHÔNG đưa lời khuyên MUA/BÁN — đây là công cụ hỗ trợ tư duy, không phải khuyến "
    "nghị đầu tư.\n"
    "5) Trả lời bằng tiếng Việt, ngắn gọn, dẫn số cụ thể. Khi đã đủ dữ liệu thì trả "
    "lời thẳng, đừng gọi thêm công cụ."
)

#  Khai báo công cụ cho Gemini (JSON Schema kiểu VIẾT HOA theo yêu cầu function calling).
_SORT_KEYS = ["market_cap", "value", "volume", "change_pct", "price", "foreign_net"]
_GROUPS = ["VN30", "VN100", "HNX30", "HOSE"]

TOOL_DECLARATIONS: list[dict] = [
    {
        "name": "tim_kiem_tri_thuc",
        "description": ("Tìm trong kho tri thức đã lập chỉ mục (tin tức, tổng quan, "
                        "phân tích cũ) theo ngữ nghĩa. Dùng cho câu hỏi định tính, tin "
                        "tức, bối cảnh — KHÔNG dùng để lấy số liệu tài chính mới nhất."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "cau_hoi": {"type": "STRING", "description": "Nội dung cần tìm, bằng tiếng Việt"},
                "ma": {"type": "STRING", "description": "Giới hạn trong một mã, VD 'FPT' (tùy chọn)"},
            },
            "required": ["cau_hoi"],
        },
    },
    {
        "name": "phan_tich_ma",
        "description": ("Phân tích & chấm điểm MỘT mã theo dữ liệu TƯƠI: điểm 100, 4 nhóm "
                        "tiêu chí, các chỉ số (ROE, P/E, P/B, tăng trưởng, D/E, cổ tức…), "
                        "và khối quyết định. Dùng khi cần con số cơ bản/điểm số của mã."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "ma": {"type": "STRING", "description": "Mã chứng khoán, VD 'FPT'"},
            },
            "required": ["ma"],
        },
    },
    {
        "name": "xep_hang_ro",
        "description": ("Xếp hạng các mã trong một rổ chỉ số theo một cột. Dùng cho câu "
                        "hỏi so sánh/hơn-kém ('mã nào vốn hóa lớn nhất', 'thanh khoản cao "
                        "nhất', 'tăng mạnh nhất')."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "ro": {"type": "STRING", "enum": _GROUPS, "description": "Rổ chỉ số"},
                "sap_xep": {"type": "STRING", "enum": _SORT_KEYS,
                            "description": "Cột sắp xếp (mặc định market_cap = vốn hóa)"},
                "chieu": {"type": "STRING", "enum": ["giam", "tang"],
                          "description": "giam = cao→thấp (mặc định), tang = thấp→cao"},
            },
            "required": ["ro"],
        },
    },
]


def _make_dispatch(db: Session, default_ticker: Optional[str], citations: list[Citation]):
    """Trả về hàm `dispatch(name, args) -> dict` chạy tool thật + gom trích dẫn.

    `citations` được bồi vào tại chỗ (closure) để đính vào câu trả lời cuối.
    """
    settings = get_settings()

    def _tim_kiem_tri_thuc(args: dict) -> dict:
        cau_hoi = str(args.get("cau_hoi") or "").strip()
        ma = (args.get("ma") or default_ticker or None)
        if not cau_hoi:
            return {"loi": "Thiếu nội dung tìm kiếm."}
        query_vector = embed_texts([cau_hoi], is_query=True)[0]
        hits = store.search(db, query_vector, settings.rag_top_k, ticker=ma)
        if not hits:
            return {"ket_qua": [], "ghi_chu": (
                "Kho chưa có dữ liệu phù hợp. Hãy phân tích mã một lần hoặc lập chỉ mục.")}
        blocks = []
        for doc, _score in hits:
            citations.append(Citation(ticker=doc.ticker, doc_type=doc.doc_type,
                                      title=doc.title, snippet=chat._snippet(doc.content)))
            blocks.append({"ma": doc.ticker, "loai": doc.doc_type,
                           "tieu_de": doc.title, "noi_dung": chat._snippet(doc.content, 600)})
        return {"ket_qua": blocks}

    def _phan_tich_ma(args: dict) -> dict:
        ma = str(args.get("ma") or default_ticker or "").strip().upper()
        if not ma:
            return {"loi": "Thiếu mã cần phân tích."}
        try:
            a = analyzer.analyze(ma)
        except ProviderError as exc:
            return {"loi": f"Không phân tích được {ma}: {exc}"}
        citations.append(Citation(
            ticker=a.ticker, doc_type="analysis", title=f"Phân tích {a.ticker}",
            snippet=f"{a.score.total}/100 — {a.score.verdict.text}"))
        return {
            "ma": a.ticker, "ten": a.name, "nganh": a.sector, "gia": a.price,
            "diem": a.score.total, "xep_loai": a.score.verdict.text,
            "nhom_diem": [{"ten": c.name, "diem": c.sum, "toi_da": c.max}
                         for c in a.score.categories],
            "chi_so": a.metrics.model_dump(exclude_none=True),
            "quyet_dinh": {
                "tom_tat": a.score.decision.summary,
                "co_cau_vi_the": a.score.decision.position_size,
                "cat_lo": a.score.decision.stop_loss,
            },
            "thieu_du_lieu": a.missing,
        }

    def _xep_hang_ro(args: dict) -> dict:
        ro = str(args.get("ro") or "VN30").strip().upper()
        sort = str(args.get("sap_xep") or "market_cap")
        order = "asc" if str(args.get("chieu") or "giam") == "tang" else "desc"
        try:
            listing = screener.fetch_list(ro, sort, order)
        except ProviderError as exc:
            return {"loi": f"Không lấy được rổ {ro}: {exc}"}
        top = [{"ma": r.symbol, "ten": r.name, "gia": r.price,
                "thay_doi_pct": r.change_pct, "kl_trieu_cp": r.volume,
                "gt_ty": r.value, "von_hoa_ty": r.market_cap} for r in listing.rows[:15]]
        return {"ro": ro, "sap_xep": sort, "chieu": order,
                "so_ma": listing.count, "top": top}

    handlers = {
        "tim_kiem_tri_thuc": _tim_kiem_tri_thuc,
        "phan_tich_ma": _phan_tich_ma,
        "xep_hang_ro": _xep_hang_ro,
    }

    def dispatch(name: str, args: dict) -> dict:
        handler = handlers.get(name)
        if handler is None:
            return {"loi": f"Không có công cụ tên '{name}'."}
        return handler(args or {})

    return dispatch


def _to_history(history: Optional[list[ChatTurnInput]]) -> list[tuple[str, str]]:
    """Ép về [(role, text)] và cắt còn N lượt gần nhất (chặn phình prompt/token)."""
    if not history:
        return []
    turns = history[-get_settings().rag_history_turns:]
    pairs: list[tuple[str, str]] = []
    for turn in turns:
        if turn.question:
            pairs.append(("user", turn.question))
        if turn.answer:
            pairs.append(("model", turn.answer))
    return pairs


def _augment(question: str, ticker: Optional[str]) -> str:
    if ticker:
        return f"(Bối cảnh: người dùng đang xem mã {ticker}.)\n{question}"
    return question


def _step_label(tool: str, args: dict) -> str:
    if tool == "phan_tich_ma":
        return f"Phân tích mã {str(args.get('ma') or '').upper()}".strip()
    if tool == "xep_hang_ro":
        return f"Xếp hạng rổ {str(args.get('ro') or '').upper()}".strip()
    if tool == "tim_kiem_tri_thuc":
        return f"Tìm tri thức: {str(args.get('cau_hoi') or '')[:40]}".strip()
    return tool


def _dedup(citations: list[Citation]) -> list[Citation]:
    seen: set[tuple[str, str]] = set()
    out: list[Citation] = []
    for c in citations:
        key = (c.ticker, c.title)
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


def answer_question(db: Session, question: str, ticker: Optional[str] = None,
                    history: Optional[list[ChatTurnInput]] = None) -> ChatResponse:
    """Trả lời bằng agent. Agent tắt/hỏng → lui về RAG một-nhịp (`chat.py`)."""
    settings = get_settings()
    if not settings.rag_agent_enabled:
        return chat.answer_question(db, question, ticker)

    citations: list[Citation] = []
    steps: list[AgentStep] = []
    dispatch = _make_dispatch(db, ticker, citations)
    try:
        answer = ""
        for kind, data in gemini.run_agent(
                _SYSTEM, _to_history(history), _augment(question, ticker),
                TOOL_DECLARATIONS, dispatch, settings.rag_agent_max_steps):
            if kind == "step":
                steps.append(AgentStep(tool=data["tool"],
                                       label=_step_label(data["tool"], data["args"])))
            else:
                answer = str(data)
    except GeminiError:
        #  Agent hỏng (thiếu key / API đổi / lỗi định dạng) → RAG một-nhịp cho chắc.
        return chat.answer_question(db, question, ticker)

    return ChatResponse(answer=answer or "Xin lỗi, chưa tạo được câu trả lời.",
                        citations=_dedup(citations), steps=steps)


def answer_stream(db: Session, question: str, ticker: Optional[str] = None,
                  history: Optional[list[ChatTurnInput]] = None):
    """Generator: yield ('step', {...}) mỗi bước công cụ, rồi ('final', ChatResponse).

    Agent tắt → uỷ thác cho `chat.answer_stream` (yield 'delta'/'final'). Agent hỏng
    giữa chừng → lui về RAG một-nhịp.
    """
    settings = get_settings()
    if not settings.rag_agent_enabled:
        yield from chat.answer_stream(db, question, ticker)
        return

    citations: list[Citation] = []
    steps: list[AgentStep] = []
    dispatch = _make_dispatch(db, ticker, citations)
    answer = ""
    try:
        for kind, data in gemini.run_agent(
                _SYSTEM, _to_history(history), _augment(question, ticker),
                TOOL_DECLARATIONS, dispatch, settings.rag_agent_max_steps):
            if kind == "step":
                step = AgentStep(tool=data["tool"],
                                 label=_step_label(data["tool"], data["args"]))
                steps.append(step)
                yield ("step", {"tool": step.tool, "label": step.label})
            else:
                answer = str(data)
    except GeminiError:
        yield from chat.answer_stream(db, question, ticker)
        return

    yield ("final", ChatResponse(answer=answer or "Xin lỗi, chưa tạo được câu trả lời.",
                                 citations=_dedup(citations), steps=steps))
