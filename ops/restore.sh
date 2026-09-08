#!/usr/bin/env bash
# Phục hồi cơ sở dữ liệu từ một bản sao lưu.
#
#   ./ops/restore.sh backups/phantichma-20260908-020000.sql.gz
#
# ⚠️ GHI ĐÈ toàn bộ dữ liệu hiện tại. Dừng backend/worker/beat trước khi chạy,
# nếu không chúng vẫn đang ghi trong lúc bản dump đang được nạp.
#
# Quy trình đầy đủ:
#   docker compose stop backend worker beat
#   ./ops/restore.sh <tệp>
#   docker compose start backend worker beat
set -euo pipefail

FILE="${1:?dùng: ./ops/restore.sh <tệp .sql.gz>}"
DB="${DB:-phantichma}"
USER="${PGUSER:-invest}"

[ -f "$FILE" ] || { echo "Không thấy tệp: $FILE" >&2; exit 1; }

echo "Sắp GHI ĐÈ cơ sở dữ liệu '$DB' bằng $FILE"
read -r -p "Gõ đúng tên cơ sở dữ liệu để xác nhận: " nhap
[ "$nhap" = "$DB" ] || { echo "Không khớp, dừng lại."; exit 1; }

gunzip -c "$FILE" | docker compose exec -T postgres psql -U "$USER" -d "$DB" -v ON_ERROR_STOP=1

echo "Đã phục hồi. Kiểm nhanh:"
docker compose exec -T postgres psql -U "$USER" -d "$DB" -c \
  "SELECT (SELECT count(*) FROM users) AS nguoi_dung,
          (SELECT count(*) FROM rag_documents) AS tai_lieu,
          (SELECT count(*) FROM watchlist_items) AS ma_theo_doi;"
