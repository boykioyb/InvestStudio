"""Lưu/đọc tệp đính kèm trên ĐĨA (volume `uploads`).

DB chỉ giữ metadata (xem model `Attachment`); nội dung tệp nằm ở đây. Tên tệp
trên đĩa là uuid ngẫu nhiên (`stored_name`) để tránh trùng và không lộ tên gốc.
"""
from __future__ import annotations

import os
import uuid

from app.core.config import get_settings

_EXT = {
    "image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp",
    "image/gif": ".gif", "application/pdf": ".pdf",
}


def _dir() -> str:
    directory = get_settings().upload_dir
    os.makedirs(directory, exist_ok=True)
    return directory


def save_bytes(data: bytes, mime: str) -> str:
    """Ghi tệp xuống đĩa, trả về `stored_name` (uuid + đuôi theo mime)."""
    stored_name = f"{uuid.uuid4().hex}{_EXT.get(mime, '')}"
    with open(os.path.join(_dir(), stored_name), "wb") as handle:
        handle.write(data)
    return stored_name


def read_bytes(stored_name: str) -> bytes:
    with open(os.path.join(_dir(), stored_name), "rb") as handle:
        return handle.read()


def delete_file(stored_name: str) -> None:
    try:
        os.remove(os.path.join(_dir(), stored_name))
    except FileNotFoundError:
        pass


#  Chữ ký byte đầu tệp (magic bytes) của các định dạng được phép. Đây là thứ
#  DUY NHẤT nói lên định dạng thật — `Content-Type` là do client tự khai.
_MAGIC: tuple[tuple[bytes, str], ...] = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"%PDF-", "application/pdf"),
)


def sniff_mime(data: bytes) -> str:
    """Đoán mime THẬT từ vài byte đầu. Không nhận ra → chuỗi rỗng.

    WebP đặc biệt: "RIFF" ở byte 0-3 rồi "WEBP" ở byte 8-11.
    """
    for signature, mime in _MAGIC:
        if data.startswith(signature):
            return mime
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return ""
