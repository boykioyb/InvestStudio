"""Schema (DTO) cho trợ lý hỏi–đáp RAG."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ChatTurnInput(BaseModel):
    """Một lượt hỏi–đáp TRƯỚC ĐÓ của hội thoại hiện tại, do frontend gửi kèm.

    Nhờ vậy agent hiểu câu hỏi nối tiếp ("ROE của NÓ?") mà không cần lấy lịch
    sử global theo user (tránh trộn nhầm mã của hội thoại cũ).
    """

    question: str = Field(..., max_length=1000)
    answer: str = Field("", max_length=4000)


class AgentStep(BaseModel):
    """Một bước công cụ agent đã chạy — để UI hiện 'đang làm gì' và minh bạch."""

    tool: str
    label: str = ""


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000,
                          description="Câu hỏi bằng ngôn ngữ tự nhiên")
    #  Giới hạn tìm kiếm trong một mã (tùy chọn) — VD chỉ hỏi về FPT.
    ticker: Optional[str] = Field(None, max_length=12)
    #  Vài lượt gần nhất của hội thoại hiện tại (để giữ ngữ cảnh nối tiếp).
    history: list[ChatTurnInput] = Field(default_factory=list)
    #  Thuộc cuộc trò chuyện nào; None + start_conversation=True → tạo cuộc mới.
    conversation_id: Optional[int] = None
    start_conversation: bool = Field(
        False, description="True = tạo cuộc trò chuyện mới cho lượt này (trang Trợ lý)")
    #  Id các tệp đã upload (qua /chat/upload) để gửi kèm câu hỏi (ảnh/PDF).
    attachment_ids: list[int] = Field(default_factory=list)


class AttachmentOut(BaseModel):
    """Tệp đã upload — trả về cho FE để xem trước & gửi kèm."""

    id: int
    filename: str
    mime: str
    size: int
    url: str = Field(..., description="Đường dẫn tải/hiển thị tệp (cùng origin)")


class AttachmentRef(BaseModel):
    """Tệp đính kèm gắn với một lượt hỏi (lưu trong ChatMessage, để hiển thị lại)."""

    id: int
    filename: str
    mime: str


class ConversationOut(BaseModel):
    """Một câu chuyện trong danh sách bên trái trang Trợ lý."""

    id: int
    title: str
    ticker: Optional[str] = None
    updated_at: str = Field(..., description="ISO thời điểm cập nhật gần nhất")


class ConversationRename(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


class Citation(BaseModel):
    """Nguồn được dùng để trả lời — để người dùng kiểm chứng, không phải trang trí."""

    ticker: str
    doc_type: str
    title: str
    snippet: str = Field(..., description="Trích đoạn ngắn của tài liệu gốc")


class ChatResponse(BaseModel):
    answer: str
    #  Cuộc trò chuyện chứa lượt này (mới tạo hoặc đang tiếp) — để FE bám theo.
    conversation_id: Optional[int] = None
    citations: list[Citation] = []
    steps: list[AgentStep] = Field(
        default_factory=list,
        description="Các bước công cụ agent đã dùng để tới câu trả lời",
    )
    note: str = Field(
        "Trợ lý chỉ tổng hợp dữ liệu đã lập chỉ mục — KHÔNG phải khuyến nghị đầu tư.",
        description="Nhắc nhở cố định kèm mỗi câu trả lời",
    )


class ChatHistoryItem(BaseModel):
    """Một lượt hỏi–đáp đã lưu, để tải lại lịch sử."""

    question: str
    answer: str
    citations: list[Citation] = []
    attachments: list[AttachmentRef] = []


class IndexStatus(BaseModel):
    documents: int = Field(..., description="Số đoạn văn bản đang có trong kho")
    tickers: int = Field(..., description="Số mã đã được lập chỉ mục")
    running: bool = Field(False, description="Có job lập chỉ mục đang chạy không")
    last_message: str = ""
    task_id: Optional[str] = Field(None, description="Mã job Celery gần nhất")
