# Biên bản bàn giao & nghiệm thu — Phân Tích Mã

> Ngày: 2026-09-08 · Nhánh `feat/bao-mat-han-muc` (**24 commit, chưa push**)
> Người thực hiện: Claude · Người nghiệm thu: chủ sản phẩm
> Trạng thái: **HOÀN THÀNH PHẦN KỸ THUẬT — chờ 4 việc cấu hình của chủ sản phẩm**

---

## 1. Đã làm gì

Bắt đầu từ nhận định "chưa ship được: tính năng chưa rõ, thiếu bảo mật", công việc
đi qua 7 pha:

| Pha | Nội dung | Tài liệu |
|---|---|---|
| **Khảo sát** | Đọc mã, dựng bản đồ 13 rủi ro có dẫn `file:dòng` | [SHIP_PLAN.md](SHIP_PLAN.md) |
| **S0** | Chặn đường công khai đốt quota Gemini | [S0_DONE.md](S0_DONE.md) |
| **S1** | Nền tài khoản + hạn mức theo thiết bị | [S1_DONE.md](S1_DONE.md) |
| **S2** | Khu quản trị lõi (app riêng) | [S2_DONE.md](S2_DONE.md) |
| **S3** | 8 trang quản trị còn lại | — |
| **S4** | Rõ sản phẩm: luồng tài khoản, onboarding, trang lỗi | — |
| **S5** | Vận hành: prod compose, sao lưu, CI, pháp lý, log JSON | — |
| **S6** | Tính năng & bảo mật còn treo | [S6_PLAN.md](S6_PLAN.md) · [S6_TEST.md](S6_TEST.md) |

**Lỗ hổng nghiêm trọng nhất đã đóng:** endpoint phân tích công khai (`/api/stocks/{mã}`)
tự đẩy job nhúng Gemini cho mỗi mã mới. Bất kỳ ai lặp qua ~1.600 mã sàn đều đốt sạch
quota của cả hệ thống mà **không cần tài khoản**. Đo lại sau khi sửa: đợt tấn công
1.000 request phát sinh **0 lệnh gọi Gemini**.

---

## 2. Bằng chứng nghiệm thu (chạy lại lúc bàn giao)

| Hạng mục | Kết quả |
|---|---|
| Test backend | **153 passed** |
| Kiểm kiểu frontend | **0 lỗi** |
| Test khói giao diện (Playwright) | **6/6 passed** |
| `/api/health` | `ok` · database 9ms · redis 2ms · gemini OK |
| 15 đường dẫn công khai | tất cả **200** |
| 13 đường dẫn khu quản trị | tất cả **200** |

**Hồi quy các rào bảo mật:**

| Phép thử | Kết quả |
|---|---|
| Mở luồng SSE không có vé (H11) | 401 / 400 |
| `/api/admin/*` chưa đăng nhập | **401** |
| `POST /chat/reindex` chưa đăng nhập (H3) | **401** |
| `POST /portfolio/review` chưa đăng nhập (H7) | **401** |
| `GET /api/stocks/FPT` với tư cách khách | **200** (đọc cache — đúng thiết kế) |
| 20 request với 20 IP giả khác nhau (H4) | Rơi vào **1 rổ đếm duy nhất** |
| Số lệnh gọi Gemini trong cả đợt kiểm tra | **0** |

---

## 3. Bàn giao: 4 việc cần chủ sản phẩm làm

Đây là **cấu hình**, không phải mã nguồn — tôi không có thông tin để làm thay.

| # | Việc | Vì sao chặn | Làm ở đâu |
|---|---|---|---|
| 1 | **Cấu hình SMTP** | Chưa có thì thư xác minh chỉ nằm trong log máy chủ → **người dùng mới mắc kẹt ngay bước đầu**, và không ai tự lấy lại được mật khẩu | `.env`: `APP_SMTP_HOST/PORT/USER/PASSWORD/FROM` + `APP_PUBLIC_BASE_URL` |
| 2 | **Bật 2 lớp cho tài khoản admin** | `hoatq.dev@gmail.com` chưa có TOTP nên đang bị chặn khỏi mọi trang quản trị (trừ đúng chỗ để bật) | <http://localhost:3020/settings> → "Tạo mã bật 2 lớp" |
| 3 | **Đọc quota thật trong AI Studio** | `gemini_daily_call_cap` đang để ước lượng 1.400 | `/admin/settings` hoặc `.env` |
| 4 | **Khai `APP_ADMIN_IP_ALLOWLIST`** | Rỗng = khu quản trị không giới hạn IP | `.env.prod` |

Cách kiểm nhanh mục 1 sau khi cấu hình:

```bash
docker compose exec -T backend python -c "
from app.core import mailer; print('SMTP đã cấu hình:', mailer.smtp_configured())"
```

---

## 4. Hai quyết định còn chờ bạn

1. **Đổi tên thư mục dự án** `InvestStudio` → tên mới. Nó là tên project của Docker
   Compose nên kéo theo tên volume (`investstudio_pg-data`); đổi thư mục là volume cũ
   thành mồ côi, phải chép dữ liệu sang. Tôi làm được nhưng cần bạn đồng ý vì có bước
   dừng dịch vụ.
2. **Dọn nợ kỹ thuật** trong [REFACTOR_PLAN.md](REFACTOR_PLAN.md) (tách `schemas/stock.py`
   556 dòng, tách `rag/agent.py`, gom `useApi()`…). Đây là **chất lượng mã**, không phải
   tính năng — không chặn ship, nhưng càng để lâu càng đắt.

---

## 5. Cách bạn tự nghiệm thu

```bash
# 1. Dựng lại từ đầu
./dev.sh -d

# 2. Test backend
docker compose exec backend pytest tests -q          # kỳ vọng: 153 passed

# 3. Kiểm kiểu frontend
docker compose exec frontend npx nuxt typecheck      # kỳ vọng: không lỗi

# 4. Test khói giao diện (cần Playwright trên máy)
cd frontend && npm ci && npx playwright install chromium && npm run test:e2e

# 5. Mở và bấm thử
#    http://localhost:3010  — web công khai
#    http://localhost:3020  — khu quản trị
```

**Đường đi nên thử tay:** trang chủ → gõ "vietcom" (phải gợi ý VCB) → chấm điểm →
đọc phần Quyết định → ☆ theo dõi → hỏi trợ lý một câu → mở `/account` xem hạn mức còn
lại → vào `/admin` xem lượt hỏi đó đã được ghi nhận ở trang **Sử dụng** và **Hội thoại**.

---

## 6. Điều tôi KHÔNG kiểm được (nói trước, đừng để bạn tưởng đã xong)

- **Gửi email thật** — chưa có SMTP nên toàn bộ luồng thư mới chỉ chạy tới bước dựng
  nội dung; đường ống thật chưa được thử một lần nào.
- **HTTPS và cấu hình prod** — `docker-compose.prod.yml` đã kiểm bằng `compose config`
  (chỉ Caddy publish 80/443), nhưng **chưa từng chạy trên máy chủ thật có tên miền**.
- **Chịu tải** — không có test hiệu năng. Hạn mức và cache thiết kế cho vài chục người
  dùng đồng thời; bản Gemini miễn phí giới hạn khoảng 42–120 người/ngày tùy độ nặng câu hỏi.
- **Giải đố proof-of-work trên máy yếu** — đã kiểm ở tầng API, chưa đo thời gian thực tế
  trên điện thoại đời thấp.
- **Hai trang pháp lý** (`/terms`, `/privacy`) là **bản nháp do đội phát triển soạn**,
  chưa qua luật sư.
