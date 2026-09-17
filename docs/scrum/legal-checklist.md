# Legal Checklist — InvestStudio

> Ngày lập: 2026-09-17
> Mục đích: bản đồ rủi ro pháp lý + checklist tuân thủ trước khi go-live (mở công khai / thu phí).
>
> ⚠️ **Miễn trừ:** Tài liệu này do AI soạn, **KHÔNG phải tư vấn pháp lý**. Nó giúp xác định *cần hỏi luật sư cái gì*. Trước khi go-live phải có **luật sư chứng khoán + luật sư dữ liệu** rà soát chính thức.

---

## Cách đọc

- **Mức rủi ro:** 🔴 Cao (chặn go-live) · 🟡 Trung bình · 🟢 Thấp.
- **Trạng thái:** `TODO` · `DOING` · `DONE` · `BLOCKED` · `N/A`.
- Thuật ngữ: **UBCKNN** = Ủy ban Chứng khoán Nhà nước · **PDPD** = Personal Data Protection Decree (Nghị định 13/2023/NĐ-CP về bảo vệ dữ liệu cá nhân) · **ToS** = Terms of Service (điều khoản sử dụng) · **ĐT** = đầu tư.

---

## L1 · Tư vấn đầu tư chứng khoán — cần giấy phép? 🔴

**Rủi ro:** "Chấm điểm cổ phiếu" + trợ lý gợi ý có thể bị xem là *tư vấn đầu tư chứng khoán* — hoạt động có điều kiện, **cần giấy phép UBCKNN** theo Luật Chứng khoán 2019.

- [ ] Rà soát với luật sư: sản phẩm hiện tại có rơi vào định nghĩa "tư vấn đầu tư" không? — **TODO**
- [ ] Định vị lại là **công cụ thông tin / giáo dục**, không đưa khuyến nghị mua/bán cụ thể. — **TODO**
- [ ] Rà soát ngôn từ toàn hệ thống: loại bỏ "nên mua", "khuyến nghị", "chắc chắn tăng"... — **TODO**
- [ ] Thêm **disclaimer** cạnh MỖI điểm số: *"Đây là thông tin tham khảo, không phải khuyến nghị đầu tư."* — **TODO**

---

## L2 · Bản quyền & Điều khoản sử dụng dữ liệu 🔴

**Rủi ro:** Crawl trực tiếp API VCI/Vietcap/DNSE (đang làm để né rate-limit) có thể **vi phạm ToS** và quyền của nhà cung cấp đối với dữ liệu.

- [ ] Đọc & lưu lại ToS của từng nguồn: VCI/Vietcap, DNSE. — **TODO**
- [ ] Xác định dữ liệu nào được phép dùng lại / hiển thị / thương mại hoá. — **TODO**
- [ ] Ưu tiên nguồn có **API chính thức hoặc hợp đồng cấp phép dữ liệu**. — **TODO**
- [ ] Có phương án dự phòng nếu một nguồn bị chặn hoặc gửi khiếu nại. — **TODO**

---

## L3 · Bảo vệ dữ liệu cá nhân (PDPD — NĐ 13/2023/NĐ-CP) 🔴

**Rủi ro:** Thu thập tài khoản Google (OAuth), lưu danh mục đầu tư của user → cần **cơ sở pháp lý + sự đồng ý** hợp lệ.

- [ ] Soạn **Privacy Policy** (chính sách quyền riêng tư) công khai. — **TODO**
- [ ] Màn hình **xin đồng ý** trước khi thu thập dữ liệu cá nhân. — **TODO**
- [ ] Ghi rõ: thu thập gì, mục đích, lưu ở đâu, lưu bao lâu, chia sẻ với ai. — **TODO**
- [ ] Cho phép user **xem / xuất / xoá** dữ liệu của mình. — **TODO**
- [ ] Xác định vai trò: bên kiểm soát dữ liệu / bên xử lý dữ liệu. — **TODO**

---

## L4 · Token TCInvest (extension TCBS) 🔴

**Rủi ro:** Extension bắt token phiên môi giới của user để đồng bộ danh mục. Nếu lộ → tài khoản chứng khoán user bị xâm phạm → **trách nhiệm pháp lý nặng**; có thể vi phạm ToS của TCBS.

- [ ] Rà soát ToS của TCBS/TCInvest về việc dùng token phiên bởi bên thứ ba. — **TODO**
- [ ] Màn hình đồng ý minh bạch: token dùng làm gì, lưu ở đâu, bao lâu, ai truy cập. — **TODO**
- [ ] Mã hoá token khi lưu trữ & khi truyền; scope tối thiểu; tự hết hạn. — **TODO**
- [ ] Đánh giá: có nên **bỏ tính năng** nếu không có cơ sở pháp lý vững? — **TODO**
- [ ] Quy trình xử lý sự cố nếu token bị lộ (thông báo user, thu hồi). — **TODO**

---

## L5 · Miễn trừ trách nhiệm & tổn thất đầu tư 🟡

**Rủi ro:** User thua lỗ khi hành động theo điểm số → có thể quy trách nhiệm cho sản phẩm.

- [ ] Soạn **Terms of Service** có điều khoản **giới hạn trách nhiệm**. — **TODO**
- [ ] Disclaimer rõ: *"Quyết định đầu tư và rủi ro là của bạn."* — **TODO**
- [ ] Buộc user chấp nhận ToS trước khi dùng tính năng phân tích. — **TODO**

---

## L6 · Đăng ký kinh doanh & mô hình pháp nhân 🟡

**Rủi ro:** Nếu thu phí, cần **đăng ký ngành nghề** phù hợp; fintech/chứng khoán là ngành có điều kiện.

- [ ] Xác định pháp nhân vận hành (cá nhân / công ty). — **TODO**
- [ ] Đăng ký ngành nghề kinh doanh phù hợp trước khi thu tiền. — **TODO**
- [ ] Xác định nghĩa vụ thuế / hoá đơn cho doanh thu. — **TODO**

---

## Cổng chặn go-live (BLOCKER)

Không mở công khai / không thu phí cho tới khi các mục 🔴 sau đạt tối thiểu:

- [ ] **L1** — có disclaimer "không phải khuyến nghị ĐT" + luật sư xác nhận không cần giấy phép (hoặc đã xin). — **BLOCKED**
- [ ] **L2** — đã rà ToS nguồn dữ liệu, không dùng nguồn vi phạm. — **BLOCKED**
- [ ] **L3** — có Privacy Policy + màn hình đồng ý theo NĐ 13/2023. — **BLOCKED**
- [ ] **L4** — token TCBS có cơ sở pháp lý + đồng ý minh bạch, hoặc đã tắt. — **BLOCKED**

---

## Ưu tiên xử lý

Hai điểm dễ "chết" nhất, xử lý sớm nhất (tương tự *riskiest assumption* của phần đánh giá sản phẩm):

1. **L1** — định vị "công cụ thông tin, không tư vấn" (quyết định cả hướng sản phẩm).
2. **L4** — token TCBS (rủi ro bảo mật + trách nhiệm cao nhất).

> Liên kết: xem thêm [`backlog-refinement.md`](./backlog-refinement.md) cho backlog tính năng.
