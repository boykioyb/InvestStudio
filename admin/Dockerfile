# Khu quản trị (Nuxt + Nuxt UI) — chạy tách khỏi app công khai.
FROM node:22-alpine
WORKDIR /app
#  npm đi kèm node:22-alpine (10.9.x) vấp lỗi arborist "edgesOut" khi giải phụ
#  thuộc của Nuxt 4 → nâng npm trước rồi mới cài.
RUN npm install -g npm@latest
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3020
CMD ["npm", "run", "dev"]
