#!/usr/bin/env bash
# Chạy Phân Tích Mã ở chế độ DEV (hot-reload cho frontend + backend).
#
#   ./dev.sh              # khởi động, bám log  (mặc định: up)
#   ./dev.sh -d           # chạy nền            (→ up -d)
#   ./dev.sh --build      # build lại image rồi chạy (khi đổi requirements/package.json)
#   ./dev.sh down         # dừng
#   ./dev.sh logs -f      # xem log
#
# Bên dưới chỉ là `docker compose` ghép thêm docker-compose.dev.yml.
set -euo pipefail
cd "$(dirname "$0")"

# Không tham số → `up`. Tham số đầu là cờ (-d, --build) → coi như thuộc `up`.
if [ "$#" -eq 0 ]; then
  set -- up
else
  case "$1" in
    -*) set -- up "$@" ;;
  esac
fi

exec docker compose -f docker-compose.yml -f docker-compose.dev.yml "$@"
