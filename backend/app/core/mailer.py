"""Gửi email giao dịch (xác minh tài khoản, đặt lại mật khẩu).

Chưa cấu hình SMTP thì KHÔNG chết: link được in ra log máy chủ để còn dùng khi
chạy máy/lúc dev. Cố ý không dùng thư viện ngoài — chỉ `smtplib` của Python.

⚠️ Trước khi mở cho người lạ PHẢI cấu hình SMTP thật, nếu không người dùng không
bao giờ nhận được thư xác minh và cũng không tự lấy lại được mật khẩu.
"""
from __future__ import annotations

import smtplib
import sys
from email.message import EmailMessage

from app.core.config import get_settings


def smtp_configured() -> bool:
    settings = get_settings()
    return bool(settings.smtp_host and settings.smtp_from)


def send(to: str, subject: str, body: str) -> bool:
    """Gửi một email dạng văn bản thuần. Trả True nếu đã gửi qua SMTP thật.

    Lỗi SMTP KHÔNG được ném ra ngoài: đăng ký/đổi mật khẩu vẫn phải chạy được,
    người dùng chỉ cần bấm "gửi lại thư xác minh" sau đó.
    """
    settings = get_settings()
    if not smtp_configured():
        #  Chế độ dev: in ra log để tự lấy link, không im lặng nuốt mất.
        print(f"[mailer] (CHƯA CẤU HÌNH SMTP) gửi tới {to}: {subject}\n{body}",
              file=sys.stderr)
        return False

    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    try:
        if settings.smtp_ssl:
            server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)
            if settings.smtp_starttls:
                server.starttls()
        with server:
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(message)
        return True
    except Exception as exc:  # noqa: BLE001 - hạ tầng thư hỏng không được chặn đăng ký
        print(f"[mailer] gửi thất bại tới {to}: {exc}", file=sys.stderr)
        return False


def send_verification(to: str, token: str) -> bool:
    link = f"{get_settings().public_base_url}/xac-minh?token={token}"
    return send(to, "Xác minh tài khoản InvestStudio", (
        "Chào bạn,\n\n"
        "Bấm vào liên kết dưới đây để xác minh email và mở khóa trợ lý:\n\n"
        f"{link}\n\n"
        "Liên kết có hiệu lực trong 24 giờ. Nếu bạn không đăng ký InvestStudio, "
        "hãy bỏ qua thư này.\n"))


def send_password_reset(to: str, token: str) -> bool:
    link = f"{get_settings().public_base_url}/dat-lai-mat-khau?token={token}"
    return send(to, "Đặt lại mật khẩu InvestStudio", (
        "Chào bạn,\n\n"
        "Bấm vào liên kết dưới đây để đặt mật khẩu mới:\n\n"
        f"{link}\n\n"
        "Liên kết có hiệu lực trong 30 phút và chỉ dùng được một lần. Nếu bạn "
        "không yêu cầu đổi mật khẩu, hãy bỏ qua thư này — tài khoản vẫn an toàn.\n"))
