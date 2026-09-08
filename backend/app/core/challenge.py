"""Giải đố proof-of-work cho bước đăng ký khi thiết bị có dấu hiệu đáng ngờ.

Vì sao không dùng CAPTCHA của bên thứ ba: nó kéo theo một phụ thuộc ngoài, gửi
dấu vết người dùng sang máy chủ khác, và tự nó cũng là một thứ phải trả tiền/
theo dõi. Với quy mô này, một bài toán băm đơn giản đủ dùng.

Cách chạy: máy chủ phát `nonce` ngẫu nhiên. Client phải tìm `answer` sao cho
`sha256(nonce + answer)` bắt đầu bằng N số 0 (hex). Tìm thì phải thử vét cạn —
người thật mất ~1 giây trên trình duyệt, nhưng kẻ muốn tạo 100 tài khoản phải
trả 100 lần chi phí đó, và không song song hóa miễn phí được như việc gửi form.

⚠️ Đây là MA SÁT, không phải rào chắn — người quyết tâm vẫn vượt được. Nó nằm
cùng tuyến với vân tay thiết bị: đẩy chi phí lách lên đủ cao để chặn phần lớn.
"""
from __future__ import annotations

import hashlib
import secrets

from app.core.ratelimit import redis_client

_TTL = 300  # câu đố sống 5 phút


def _key(nonce: str) -> str:
    return f"pow:{nonce}"


def phat(difficulty: int) -> dict:
    """Phát một câu đố mới. Nonce lưu Redis để không nhận lại nonce tự chế."""
    nonce = secrets.token_urlsafe(16)
    redis_client().set(_key(nonce), str(difficulty), ex=_TTL)
    return {"nonce": nonce, "difficulty": difficulty,
            "huong_dan": ("Tìm chuỗi 'answer' sao cho sha256(nonce + answer) bắt đầu "
                          f"bằng {difficulty} số 0 dạng hex.")}


def kiem(nonce: str, answer: str) -> bool:
    """Đúng đáp án thì XÓA nonce ngay — mỗi câu đố chỉ dùng được một lần."""
    if not nonce or not answer:
        return False
    try:
        client = redis_client()
        raw = client.get(_key(nonce))
        if raw is None:
            return False
        difficulty = int(raw)
        digest = hashlib.sha256(f"{nonce}{answer}".encode()).hexdigest()
        if not digest.startswith("0" * difficulty):
            return False
        client.delete(_key(nonce))
        return True
    except Exception:  # noqa: BLE001 - Redis hỏng → coi như sai, KHÔNG cho qua
        return False
