#!/usr/bin/env bash
# Sao lưu cơ sở dữ liệu hằng đêm.
#
# Chạy như một service trong docker-compose.prod.yml. Ngủ tới giờ đã hẹn, chạy
# pg_dump, nén, rồi xóa bản cũ hơn BACKUP_KEEP_DAYS ngày.
#
# ⚠️ Bản sao lưu CHƯA ĐƯỢC THỬ PHỤC HỒI thì chưa phải bản sao lưu. Xem
# ops/restore.sh và chạy thử ít nhất một lần trước khi mở cho người dùng thật.
set -euo pipefail

HOST="${PGHOST:-postgres}"
USER="${PGUSER:-invest}"
DB="${PGDATABASE:-phantichma}"
AT="${BACKUP_AT:-02:00}"
KEEP="${BACKUP_KEEP_DAYS:-14}"
DIR="/backups"

mkdir -p "$DIR"
echo "[backup] hẹn giờ $AT hằng ngày · giữ $KEEP ngày · thư mục $DIR"

sao_luu() {
  local ts file
  ts="$(date +%Y%m%d-%H%M%S)"
  file="$DIR/${DB}-${ts}.sql.gz"

  echo "[backup] bắt đầu $file"
  #  --clean --if-exists: bản dump tự dọn schema cũ khi phục hồi, không cần
  #  người vận hành nhớ xóa tay giữa lúc đang cuống.
  if pg_dump -h "$HOST" -U "$USER" -d "$DB" --clean --if-exists | gzip > "$file.tmp"; then
    mv "$file.tmp" "$file"
    echo "[backup] xong $(du -h "$file" | cut -f1) $file"
  else
    rm -f "$file.tmp"
    echo "[backup] THẤT BẠI lúc $ts" >&2
    return 1
  fi

  #  Chỉ xóa bản cũ SAU KHI bản mới đã ghi xong — mất điện giữa chừng thì vẫn
  #  còn bản hôm qua.
  find "$DIR" -name "${DB}-*.sql.gz" -type f -mtime "+$KEEP" -print -delete
}

while true; do
  now="$(date +%s)"
  target="$(date -d "today $AT" +%s 2>/dev/null || date -j -f "%Y-%m-%d %H:%M" "$(date +%F) $AT" +%s)"
  [ "$target" -le "$now" ] && target=$((target + 86400))
  echo "[backup] ngủ $((target - now))s tới lần chạy kế tiếp"
  sleep "$((target - now))"
  sao_luu || true   # một đêm hỏng không được làm chết service
done
