# S6 — Báo cáo kiểm thử (STLC)

> Ngày: 2026-09-08 · Nhánh `feat/bao-mat-han-muc`
> Kế hoạch & tiêu chí nghiệm thu: [S6_PLAN.md](S6_PLAN.md)
> Trạng thái: **ĐẠT TIÊU CHÍ THOÁT** — chờ chủ sản phẩm nghiệm thu cuối.

## 1. Phạm vi & môi trường

| Mục | Giá trị |
|---|---|
| Phạm vi | 6 yêu cầu R1–R6 của S6 + hồi quy toàn bộ hệ thống |
| Môi trường | Docker compose (dev): FastAPI · Nuxt 3 · Nuxt UI 4 · PostgreSQL 16 + pgvector · Redis 7 |
| Dữ liệu | DB test riêng `phantichma_test` (truncate trước mỗi test); nguồn ngoài được giả lập, trừ các phép thử live ghi rõ bên dưới |
| Công cụ | pytest (backend), Playwright + Chromium (giao diện), curl + psql (thử thật) |

## 2. Thiết kế test — điều kiện kiểm thử & kỹ thuật

| AC | Điều kiện kiểm thử | Kỹ thuật | Test |
|---|---|---|---|
| AC1.1 | Mở luồng SSE không kèm vé | Bảng quyết định | `test_ac1_1_khong_ve_thi_khong_mo_duoc_luong` |
| AC1.2 | Dùng lại đúng một vé hai lần | Chuyển trạng thái | `test_ac1_2_ve_chi_dung_duoc_mot_lan` |
| AC1.3 | Vé của A dùng ở phiên của B | Đoán lỗi | `test_ac1_3_ve_cua_nguoi_khac_khong_dung_duoc` |
| AC1.4 | Vé có TTL | Giá trị biên | `test_ac1_4_ve_co_han_su_dung` |
| AC2.1 | Tài liệu tự chứa thẻ đóng `</du_lieu>` | Đoán lỗi | `test_ac2_1_boc_nhan_va_vo_hieu_hoa_the_gia` |
| AC2.2 | Prompt hệ thống của cả hai đường có dặn dò an toàn | Kiểm tra tĩnh | `test_ac2_2_prompt_he_thong_co_dan_do_an_toan` |
| AC2.3 | 4 mẫu nhồi lệnh · 3 câu hỏi thật | Phân hoạch tương đương | `test_ac2_3_*` (7 ca) |
| AC3.1/3.2 | 0/1/2 tài khoản → đi thẳng; tại ngưỡng → bắt giải; sai/thiếu đáp án → 400 | Biên + phân hoạch | `test_ac3_1_va_3_2_qua_nguong_thi_bat_buoc_giai_dung` |
| AC3.3 | Thiết bị mới | Phân hoạch | `test_ac3_3_thiet_bi_moi_khong_bi_hoi_cau_do` |
| — | Câu đố dùng lại lần hai | Chuyển trạng thái | `test_cau_do_chi_dung_duoc_mot_lan` |
| AC4.1/4.2 | (đã xác minh?) × (bật cảnh báo?) — 3 tổ hợp | Bảng quyết định | `test_ac4_2_chi_gui_cho_tai_khoan_da_xac_minh_va_bat_canh_bao` |
| AC4.3 | Tắt email cảnh báo | Đường đi thuận | `test_ac4_3_nguoi_dung_tat_duoc_email_canh_bao` |
| AC4.4 | SMTP ném lỗi | Đoán lỗi | `test_ac4_4_smtp_hong_khong_lam_chet_job` |
| AC5.1 | Gõ tên thương hiệu | Phân hoạch | `test_ac5_1_go_ten_thuong_hieu_ra_dung_ma` |
| AC5.2 | Gõ đúng mã | Phân hoạch | `test_ac5_2_go_ma_thi_ma_do_dung_dau` |
| AC5.3 | Nguồn ném lỗi | Đoán lỗi | `test_ac5_3_nguon_hong_thi_tra_rong_chu_khong_no` |
| AC5.4 | Ba lần tìm liên tiếp | Đếm lời gọi | `test_ac5_4_danh_ba_duoc_cache` |
| — | Gõ không dấu · lọc chứng quyền | Đoán lỗi | `test_go_ten_khong_dau_van_khop`, `test_loai_chung_quyen_khoi_goi_y` |
| AC6.1/6.2 | 6 luồng giao diện chính | Test khói | `frontend/tests/smoke.spec.ts` |

## 3. Kết quả thực thi

| Bộ test | Số ca | Kết quả |
|---|---|---|
| `pytest tests` (toàn bộ backend) | **153** | ✅ tất cả xanh |
| trong đó `tests/test_s6.py` | 25 | ✅ |
| `nuxt typecheck` | — | ✅ 0 lỗi |
| Playwright `smoke.spec.ts` | 6 | ✅ 6/6 (9,4s) |

**Thử thật (không giả lập), có bằng chứng:**

| Phép thử | Kết quả |
|---|---|
| `GET /api/stocks/search?q=vietcom` | `VCB · Ngân hàng TMCP Ngoại thương Việt Nam` |
| `q=techcom` · `q=viettel` · `q=ngan hang` | TCB · VTP/CTR/VGI · ABB/ABI/ACB… |
| Gợi ý hiện trên trình duyệt thật, chọn được bằng phím/chuột | ✅ |
| Luồng SSE đầy đủ có vé (hỏi VCB, agent gọi 3 công cụ) | ✅ trả lời hoàn chỉnh |
| `usage_events` sau lượt SSE đó | `calls=3 · tokens_in=5884 · tokens_out=759 · 61,9s · ok` |
| Log backend sau lượt SSE | 0 lỗi `different Context` |

## 4. Nhật ký lỗi phát hiện trong kiểm thử

| # | Mô tả | Mức | Nguyên nhân gốc | Xử lý | Kiểm lại |
|---|---|---|---|---|---|
| D1 | Luồng SSE ném `ValueError: Token was created in a different Context` khi kết thúc; **usage của mọi lượt hỏi qua SSE không được ghi** | **Cao** | `usage.track()` dùng `ContextVar` bọc quanh generator, nhưng Starlette gọi `next()` qua threadpool nên mỗi bước ở một ngữ cảnh khác — set ở ngữ cảnh này, reset ở ngữ cảnh kia | Tách `usage.Tracker` thành **đối tượng thường** đi theo generator; `usage.bind()` chỉ bọc quanh phần đồng bộ của từng bước | ✅ test `test_ac1_2` + thử thật ghi được `calls=3` |
| D2 | `symbols.search` bỏ sót kết quả nằm cuối bảng chữ cái | Trung bình | Vòng lặp `break` khi đủ `limit*4` ứng viên → dừng quét trước khi tới mục khớp theo tên | Quét toàn bộ danh bạ (2.051 mục sau lọc), sắp xếp rồi mới cắt | ✅ `q=ngan hang` trả về đủ |
| D3 | Gợi ý mã trả về chứng quyền (`CFPT2603`…) | Trung bình | Danh bạ nguồn có 1.535/3.586 mã là chứng quyền | Lọc theo mẫu `^C[A-Z]{3}\d{4}$` | ✅ `test_loai_chung_quyen_khoi_goi_y` |
| D4 | `q=vietcom` không ra VCB | Trung bình | Danh bạ dùng tên **pháp lý** ("Ngân hàng TMCP Ngoại thương Việt Nam"), không có chữ "Vietcombank" | Thêm bảng bí danh thương hiệu, khớp theo **tiền tố** | ✅ `test_ac5_1` |
| D5 | Hai biến cache của `symbols` dọn lệch nhau → tra trúng dữ liệu cũ | Thấp | Test dọn `_index` nhưng không dọn `_theo_ma` | Thêm `reset_cache()` dọn cả hai | ✅ toàn bộ test xanh |
| D6 | `nuxt typecheck` báo lỗi ở `playwright.config.ts` (`process` không có kiểu) | Thấp | Thiếu `@types/node` | Thêm `@types/node` vào devDependencies | ✅ 0 lỗi kiểu |
| D7 | `import mailer` lặp trong `tasks.py` | Rất thấp | Sót lại khi tách hàm `_bao_email` | Bỏ dòng thừa | ✅ |

> D1 là lý do đáng giá nhất của vòng kiểm thử này: nó **không lộ ra trong bất kỳ
> lần dùng tay nào trước đó** vì lỗi xảy ra ở cuối luồng, sau khi người dùng đã
> đọc xong câu trả lời — chỉ có số liệu là mất.

## 5. Hồi quy

- 128 test có trước S6 vẫn xanh (không sửa test cũ nào để "cho qua").
- Thử tay lại 3 luồng dễ vỡ nhất sau khi đổi `useChat`: hỏi qua widget nổi, hỏi ở trang trợ lý, và phân tích một mã.
- Test khói chạy lại sau mọi thay đổi cuối: 6/6 xanh.

## 6. Tiêu chí thoát

| Tiêu chí | Trạng thái |
|---|---|
| Mọi AC có ít nhất một test tự động hoặc bằng chứng chạy thật | ✅ 22/22 AC |
| Toàn bộ test xanh, không có test bị bỏ qua (skip) | ✅ 153 + 6 |
| Không còn lỗi mức Cao/Trung bình chưa xử lý | ✅ D1–D7 đã sửa và kiểm lại |
| Không phát sinh mục 🔴/🟠 mới trong CHECKLIST | ✅ |
| Typecheck sạch | ✅ |

## 7. Điều KHÔNG được kiểm (nói rõ để không hiểu nhầm)

- **Gửi email thật**: chưa cấu hình SMTP nên `send_alert` được giả lập trong test.
  Nội dung thư và điều kiện gửi đã kiểm; đường ống SMTP thật thì **chưa**.
- **Proof-of-work trên trình duyệt thật**: đã kiểm ở tầng API (giải bằng Python).
  Phần giải bằng WebCrypto trong trình duyệt mới chạy qua typecheck, chưa đo thời
  gian thực tế trên máy yếu.
- **Tải cao**: không có test hiệu năng. Hạn mức và cache được thiết kế cho vài
  chục người dùng đồng thời, chưa đo với số lớn hơn.
