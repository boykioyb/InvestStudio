<script setup lang="ts">
/**
 * Điều khoản sử dụng.
 *
 * ⚠️ Đây là BẢN NHÁP do đội phát triển soạn, chưa qua luật sư. Nội dung mô tả
 * đúng cách hệ thống đang hoạt động (hạn mức, quyền khóa tài khoản, giới hạn dữ
 * liệu) nên dùng được cho giai đoạn beta, nhưng phải nhờ người có chuyên môn
 * pháp lý rà trước khi mở rộng.
 */
useHead({ title: 'Điều khoản sử dụng — Phân Tích Mã' })

const CAP_NHAT = '08/09/2026'
</script>

<template>
  <div class="wrap phap-ly">
    <AppHeader />

    <article class="card">
      <h1>Điều khoản sử dụng</h1>
      <p class="note">Cập nhật lần cuối: {{ CAP_NHAT }}</p>

      <h2>1. Dịch vụ này là gì</h2>
      <p>
        Phân Tích Mã là công cụ tổng hợp dữ liệu công khai về cổ phiếu niêm yết tại Việt Nam,
        chấm điểm theo một mô hình 14 tiêu chí và trình bày kết quả để bạn tự cân nhắc.
      </p>

      <h2>2. KHÔNG phải tư vấn đầu tư</h2>
      <p>
        Điểm số, xếp loại, các chữ như "mua thêm", "giữ", "cắt lỗ" và mọi nội dung do trợ lý
        sinh ra <b>không phải là khuyến nghị đầu tư, không phải tư vấn tài chính</b> và không
        được xem là cơ sở duy nhất cho bất kỳ quyết định mua bán nào. Chúng tôi không phải
        công ty chứng khoán, không nhận ủy thác và không quản lý tài sản cho bạn.
      </p>
      <p>
        <b>Mọi quyết định đầu tư và mọi khoản lãi/lỗ phát sinh là của riêng bạn.</b>
      </p>

      <h2>3. Giới hạn của dữ liệu</h2>
      <ul>
        <li>Dữ liệu lấy từ nguồn công khai của bên thứ ba, có thể <b>trễ, thiếu hoặc sai</b>.</li>
        <li>Thiếu dữ liệu thì tiêu chí đó bị chấm 0 điểm — điểm thấp có thể do thiếu số liệu
          chứ không phải vì doanh nghiệp kém.</li>
        <li>Khuyến nghị và giá mục tiêu hiển thị trong phần Hồ sơ là <b>của bên thứ ba</b>,
          không phải quan điểm của chúng tôi.</li>
        <li>Trợ lý dùng mô hình ngôn ngữ và <b>có thể trả lời sai</b>. Luôn đối chiếu với
          nguồn được trích dẫn.</li>
      </ul>

      <h2>4. Tài khoản và hạn mức</h2>
      <ul>
        <li>Bạn chịu trách nhiệm giữ bí mật mật khẩu và mọi hoạt động dưới tài khoản của mình.</li>
        <li>Một người chỉ nên dùng một tài khoản. Số lượt hỏi trợ lý và số lượt phân tích
          bị giới hạn theo ngày, tính theo cả tài khoản, thiết bị và địa chỉ mạng.</li>
        <li>Chúng tôi có quyền <b>hạ hạn mức, tạm khóa hoặc xóa</b> tài khoản có dấu hiệu
          lạm dụng: tạo tài khoản hàng loạt, tự động hóa truy cập, hoặc gây quá tải hệ thống.</li>
        <li>Dịch vụ đang trong giai đoạn thử nghiệm, cung cấp "nguyên trạng", có thể gián
          đoạn hoặc thay đổi tính năng mà không báo trước.</li>
      </ul>

      <h2>5. Bạn không được</h2>
      <ul>
        <li>Thu thập dữ liệu tự động (crawl, scrape) hoặc bán lại dữ liệu lấy từ dịch vụ.</li>
        <li>Tìm cách vượt hạn mức, dò lỗ hổng, hoặc can thiệp vào hạ tầng.</li>
        <li>Dùng dịch vụ để tư vấn đầu tư cho người khác dưới danh nghĩa chuyên nghiệp.</li>
      </ul>

      <h2>6. Thay đổi điều khoản</h2>
      <p>
        Khi có thay đổi đáng kể, chúng tôi sẽ thông báo trong ứng dụng. Tiếp tục sử dụng sau
        thông báo được hiểu là bạn đồng ý với bản mới.
      </p>

      <p class="lien-quan">
        Xem thêm: <NuxtLink to="/privacy">Chính sách quyền riêng tư</NuxtLink> ·
        <NuxtLink to="/scoring">Cách chấm điểm</NuxtLink>
      </p>
    </article>
  </div>
</template>

<style scoped>
.phap-ly { max-width: 760px; }
h1 { margin: 18px 0 4px; font-size: 26px; }
h2 { margin: 22px 0 8px; font-size: 16px; }
p, li { font-size: 14px; line-height: 1.65; color: var(--text-2); }
p { margin: 0 0 10px; }
ul { margin: 0 0 10px; padding-left: 20px; }
li { margin-bottom: 6px; }
b { color: var(--text); }
.lien-quan { margin-top: 26px; padding-top: 14px; border-top: 1px solid var(--line); font-size: 13px; }
</style>
