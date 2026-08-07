# Ảnh phục vụ phát triển cục bộ (đây là công cụ chạy trên máy cá nhân).
FROM node:22-alpine

WORKDIR /app

# Cài phụ thuộc trước để tận dụng cache của Docker layer.
COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund

# Mã nguồn
COPY . .

ENV NODE_ENV=development
ENV NUXT_TELEMETRY_DISABLED=1
ENV HOST=0.0.0.0
ENV PORT=3010
# Backend chạy cùng mạng docker; ghi đè khi cần:
# Trình duyệt gọi /api cùng origin; Nuxt proxy sang backend qua mạng nội bộ Docker.
# KHÔNG đặt NUXT_PUBLIC_API_BASE ở đây — tên "backend" chỉ giải được bên trong Docker,
# đặt vào sẽ làm trình duyệt (nhất là máy khác trong LAN) không gọi được API.
ENV NUXT_API_PROXY_TARGET=http://backend:8000

EXPOSE 3010

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
