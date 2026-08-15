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
