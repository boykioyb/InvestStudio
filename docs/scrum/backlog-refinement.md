# Backlog Refinement — InvestStudio

> Ngày refine: 2026-09-17
> Mục đích: ghi lại những vấn đề cần sửa, phát hiện từ khung **Đánh giá → Chẩn đoán → Cải thiện** (Evaluate → Diagnose → Improve).
> Nguyên tắc: chữa **cái yếu nhất trước**, ưu tiên theo ICE, và luôn ưu tiên *Riskiest Assumption* (giả định nguy hiểm nhất).

---

## 0. Cách đọc file này

- **Loại (Type):** `Iterate` (tinh chỉnh) · `Pivot` (xoay trục) · `Kill` (dừng).
- **ICE = (Impact × Confidence) / Effort** — thang mỗi yếu tố 1–10, ICE cao làm trước.
  - *Impact:* sửa xong lợi bao nhiêu. *Confidence:* chắc là hiệu quả không. *Effort:* tốn bao nhiêu công.
- **Trạng thái:** `TODO` · `DOING` · `DONE` · `BLOCKED`.
- Thuật ngữ: **ICP** = Ideal Customer Profile (chân dung khách lý tưởng); **NSM** = North Star Metric (chỉ số Bắc Đẩu); **MVP** = Minimum Viable Product.

---

## 1. Vấn đề ưu tiên cao — sửa ngay

### ISSUE-01 · Riskiest Assumption chưa được kiểm chứng: "user có tin điểm số máy chấm không?"
- **Bước đánh giá liên quan:** Validation / Solution
- **Triệu chứng:** Toàn bộ sản phẩm dựa trên giả định người dùng tin vào điểm số do hệ thống chấm. Nếu họ không tin → sản phẩm vô nghĩa. Đây là giả định nguy hiểm nhất và hiện **chưa có bằng chứng**.
- **Cách cải thiện:** Thêm phần **"Vì sao điểm này"** (giải thích minh bạch từng yếu tố cấu thành điểm) ngay cạnh mỗi điểm số. Đo tỉ lệ user click mở phần giải thích.
- **Loại:** Iterate · **ICE:** I=9, C=7, E=4 → **~15.8** · **Trạng thái:** TODO
- **Cách đo (bằng chứng thật):** % user mở "vì sao điểm này"; tỉ lệ user hành động sau khi xem điểm.

### ISSUE-02 · News feed toàn tin cũ (feed đứng yên từ ~2025-08)
- **Bước đánh giá liên quan:** Solution (chất lượng dữ liệu)
- **Triệu chứng:** "Tin toàn tin cũ" — nguyên nhân là **phía nguồn**: feed Vietcap bị đóng băng, KHÔNG phải bug cache/code.
- **Cách cải thiện:** Đây là *pivot nhỏ về nguồn dữ liệu* — thêm **nguồn tin thứ 2** (endpoint tin tức DNSE đã sẵn sàng). Không cố sửa cache vì không phải nguyên nhân.
- **Loại:** Pivot (nguồn) · **ICE:** I=8, C=8, E=5 → **~12.8** · **Trạng thái:** TODO
- **Cách đo:** độ tươi của tin (ngày đăng gần nhất < 48h); số tin mới/ngày.

### ISSUE-03 · Chưa có North Star Metric (NSM)
- **Bước đánh giá liên quan:** Validation
- **Triệu chứng:** Đang đo mơ hồ, dễ rơi vào "vanity metrics" (số liệu ảo: lượt xem, đăng ký) thay vì giá trị thật.
- **Cách cải thiện:** Chốt **1 chỉ số** đại diện giá trị cốt lõi. Đề xuất: *"số cổ phiếu user thực sự phân tích / tuần"* hoặc *"số phiên có tương tác trợ lý / user hoạt động"*.
- **Loại:** Iterate · **ICE:** I=7, C=6, E=2 → **~21** · **Trạng thái:** TODO
- **Ghi chú:** ICE cao vì rẻ + mở khoá mọi quyết định đo lường sau này. Nên làm đầu tiên dù Impact vừa.

---

## 1B. Vấn đề pháp lý — BLOCKER (chặn go-live)

> Các issue này **chặn mở công khai / thu phí** cho tới khi đạt. Chi tiết đầy đủ: [`legal-checklist.md`](./legal-checklist.md).
> Ghi chú: đây là rủi ro tuân thủ, không ưu tiên bằng ICE mà bằng nguyên tắc "không có = không go-live".

### ISSUE-L1 · Tư vấn đầu tư — cần giấy phép UBCKNN? 🔴
- **Bước đánh giá liên quan:** Business Model / Pháp lý
- **Triệu chứng:** "Chấm điểm cổ phiếu" + trợ lý gợi ý có thể bị xem là *tư vấn đầu tư chứng khoán* — hoạt động có điều kiện, cần giấy phép theo Luật Chứng khoán 2019.
- **Cách cải thiện:** Định vị là **công cụ thông tin/giáo dục**, bỏ ngôn từ khuyến nghị ("nên mua"...), thêm **disclaimer** cạnh mỗi điểm số; luật sư xác nhận không cần giấy phép (hoặc xin).
- **Loại:** BLOCKER · **Trạng thái:** BLOCKED · ref: legal L1

### ISSUE-L4 · Token TCInvest (extension TCBS) 🔴
- **Bước đánh giá liên quan:** Solution / Bảo mật / Pháp lý
- **Triệu chứng:** Extension bắt token phiên môi giới của user; nếu lộ → tài khoản chứng khoán bị xâm phạm, trách nhiệm pháp lý nặng, có thể vi phạm ToS TCBS.
- **Cách cải thiện:** Đồng ý minh bạch (token dùng gì/lưu đâu/bao lâu), mã hoá, scope tối thiểu, tự hết hạn; cân nhắc **tắt** nếu không có cơ sở pháp lý vững.
- **Loại:** BLOCKER · **Trạng thái:** BLOCKED · ref: legal L4

### ISSUE-L3 · Bảo vệ dữ liệu cá nhân (NĐ 13/2023/NĐ-CP) 🔴
- **Bước đánh giá liên quan:** Pháp lý
- **Triệu chứng:** Thu tài khoản Google (OAuth) + lưu danh mục đầu tư → cần cơ sở pháp lý + sự đồng ý.
- **Cách cải thiện:** Privacy Policy + màn hình xin đồng ý; cho user xem/xuất/xoá dữ liệu; ghi rõ mục đích & thời hạn lưu.
- **Loại:** BLOCKER · **Trạng thái:** BLOCKED · ref: legal L3

### ISSUE-L2 · Bản quyền & ToS nguồn dữ liệu (VCI/Vietcap/DNSE) 🔴
- **Bước đánh giá liên quan:** Solution (dữ liệu) / Pháp lý
- **Triệu chứng:** Crawl trực tiếp API để né rate-limit có thể vi phạm ToS và quyền dữ liệu của nhà cung cấp.
- **Cách cải thiện:** Rà ToS từng nguồn; ưu tiên nguồn có API chính thức/hợp đồng; có phương án dự phòng nếu bị chặn/khiếu nại.
- **Loại:** BLOCKER · **Trạng thái:** BLOCKED · ref: legal L2

---

## 2. Vấn đề cần làm rõ trước khi ưu tiên (thiếu dữ kiện đánh giá)

Khung đánh giá lộ ra 4 mảng chưa được trả lời — **cần điều tra khách hàng/thị trường**, không phải sửa code:

### ISSUE-04 · Problem/Customer: vấn đề có đủ "đau" không, và ICP là ai?
- **Triệu chứng:** Chưa xác nhận NĐT cá nhân VN thực sự đau vì thiếu công cụ chấm điểm, hay đã quen bảng giá + group Zalo.
- **Cách cải thiện:** Phỏng vấn 20–30 khách theo **câu hỏi quá khứ** ("lần cuối bạn gặp vấn đề này là khi nào, đã làm gì?"). Thu hẹp về **1 ICP** cụ thể (VD: NĐT F0 vốn 50–200tr, đang dùng app TCBS).
- **Loại:** cần validate trước khi quyết Iterate/Pivot · **Trạng thái:** TODO

### ISSUE-05 · Competition: điểm khác biệt sắc là gì?
- **Triệu chứng:** So với TCBS, SSI iBoard, Fireant — cần 1 khác biệt đối thủ khó copy.
- **Giả thuyết khác biệt hiện tại:** *scoring 1 nguồn dữ liệu duy nhất + trợ lý agentic*. Cần kiểm chứng đây có phải lý do user chọn không.
- **Trạng thái:** TODO

### ISSUE-06 · Distribution: kênh tiếp cận khách là gì?
- **Triệu chứng:** Sản phẩm tốt mà không có kênh phân phối vẫn chết. Chưa chốt kênh.
- **Ứng viên:** SEO theo mã cổ phiếu · cộng đồng F0 · tích hợp extension TCInvest (đã có sẵn) làm phễu.
- **Trạng thái:** TODO

### ISSUE-07 · Business Model: ai trả tiền, trả bao nhiêu?
- **Triệu chứng:** Chưa xác nhận có người chịu trả cho điểm số + trợ lý.
- **Cách cải thiện:** Thử pricing (freemium / usage-based), test bằng "đặt cọc / trả trước".
- **Trạng thái:** TODO

---

## 3. Bảng ưu tiên tổng hợp (sắp theo ICE)

| # | Vấn đề | Loại | ICE | Trạng thái |
|---|--------|------|-----|-----------|
| ISSUE-03 | Chốt North Star Metric | Iterate | ~21 | TODO |
| ISSUE-01 | "Vì sao điểm này" (riskiest assumption) | Iterate | ~15.8 | TODO |
| ISSUE-02 | Thêm nguồn tin thứ 2 (DNSE) | Pivot | ~12.8 | TODO |
| ISSUE-04 | Validate Problem + ICP | Investigate | cần data | TODO |
| ISSUE-05 | Làm rõ khác biệt cạnh tranh | Investigate | cần data | TODO |
| ISSUE-06 | Chốt kênh phân phối | Investigate | cần data | TODO |
| ISSUE-07 | Test business model / pricing | Investigate | cần data | TODO |

---

## 4. Definition of Done cho vòng refine này

- [ ] Mỗi issue ưu tiên cao (01–03) có **1 chỉ số đo** rõ ràng và cách thu thập bằng chứng.
- [ ] ISSUE-04..07 có kế hoạch điều tra (số buổi phỏng vấn, đối tượng, câu hỏi).
- [ ] Sau khi sửa → **đánh giá lại** bước tương ứng, cập nhật trạng thái + ICE trong file này.

> Vòng lặp: **Build → Measure → Learn** rẻ & nhanh trên cái ICE cao nhất, rồi refine lại backlog này.
