# Ảnh chạy phan_tich_ma.py (crawl + chấm điểm cổ phiếu VN) trong container.
FROM python:3.12-slim

# Múi giờ VN cho ngày dữ liệu (date.today() dùng giờ container).
ENV TZ=Asia/Ho_Chi_Minh \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Cài phụ thuộc trước (tận dụng cache layer khi chỉ sửa code).
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy script (khi mount volume ở compose, file host sẽ đè bản này — vẫn ổn).
COPY phan_tich_ma.py .

# ENTRYPOINT cố định là tool → mọi tham số sau lệnh `run` là mã CK + cờ.
#   docker compose run --rm analyzer FPT --source auto
ENTRYPOINT ["python", "phan_tich_ma.py"]
CMD ["--help"]
