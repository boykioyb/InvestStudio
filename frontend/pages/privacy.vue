<script setup lang="ts">
/**
 * Chính sách quyền riêng tư.
 *
 * ⚠️ BẢN NHÁP, chưa qua luật sư — nhưng nội dung mô tả ĐÚNG những gì hệ thống
 * đang làm thật. Hai điều bắt buộc phải nói thẳng theo Nghị định 13/2023:
 *   1. đội vận hành xem được nội dung hội thoại với trợ lý;
 *   2. hệ thống thu thập đặc điểm thiết bị (vân tay) để chống lạm dụng hạn mức.
 * Im lặng rồi vẫn làm hai việc đó mới là vi phạm.
 */
useHead({ title: 'Chính sách quyền riêng tư — Phân Tích Mã' })

const CAP_NHAT = '08/09/2026'
</script>

<template>
  <div class="wrap phap-ly">
    <AppHeader />

    <article class="card">
      <h1>Chính sách quyền riêng tư</h1>
      <p class="note">Cập nhật lần cuối: {{ CAP_NHAT }} · Áp dụng theo Nghị định 13/2023/NĐ-CP
        về bảo vệ dữ liệu cá nhân.</p>

      <h2>1. Chúng tôi thu thập gì</h2>
      <table class="bang">
        <thead>
          <tr><th>Dữ liệu</th><th>Vì sao cần</th></tr>
        </thead>
        <tbody>
          <tr>
            <td>Email, tên hiển thị</td>
            <td>Định danh tài khoản, gửi thư xác minh và đặt lại mật khẩu</td>
          </tr>
          <tr>
            <td>Mật khẩu (lưu dạng <b>băm bcrypt</b>, không lưu bản thô)</td>
            <td>Đăng nhập</td>
          </tr>
          <tr>
            <td>Mã theo dõi, ngưỡng cảnh báo, ghi chú</td>
            <td>Tính năng theo dõi và báo khi chạm ngưỡng</td>
          </tr>
          <tr>
            <td><b>Nội dung hội thoại với trợ lý</b> và tệp bạn đính kèm</td>
            <td>Trả lời câu hỏi, giữ lịch sử trò chuyện cho chính bạn xem lại</td>
          </tr>
          <tr>
            <td>Địa chỉ IP, thời điểm đăng nhập</td>
            <td>Bảo mật tài khoản, điều tra khi có lạm dụng</td>
          </tr>
          <tr>
            <td><b>Đặc điểm thiết bị</b> (loại trình duyệt, ngôn ngữ, các đặc trưng kỹ thuật
              được băm thành một mã định danh)</td>
            <td>Chống lạm dụng hạn mức — xem mục 3</td>
          </tr>
          <tr>
            <td>Số lượt dùng tính năng</td>
            <td>Áp hạn mức và theo dõi tình trạng hệ thống</td>
          </tr>
        </tbody>
      </table>

      <p class="ghi-chu">
        <b>Sổ mua nhiều đợt của bạn KHÔNG được gửi lên máy chủ để lưu.</b> Nó nằm trong
        trình duyệt của chính bạn (localStorage). Máy chủ chỉ nhận số liệu để tính rồi trả
        kết quả, không giữ lại. Xóa dữ liệu duyệt web là mất — đó là chủ ý: số tiền bạn đầu
        tư là chuyện riêng.
      </p>

      <h2>2. Ai xem được dữ liệu của bạn</h2>
      <p>
        <b>Đội vận hành có thể xem toàn bộ dữ liệu tài khoản, bao gồm nội dung hội thoại với
        trợ lý và tệp đính kèm</b>, phục vụ vận hành hệ thống, hỗ trợ người dùng, xử lý lạm
        dụng và cải thiện chất lượng trả lời. Chúng tôi nói thẳng điều này thay vì để bạn tự
        đoán.
      </p>
      <p>
        Mỗi lần một quản trị viên mở dữ liệu của một người dùng cụ thể, hệ thống ghi lại một
        dòng nhật ký kiểm toán (ai xem, xem của ai, lúc nào). Số tài khoản quản trị được giữ
        ở mức tối thiểu và bắt buộc xác thực hai lớp.
      </p>
      <p>
        Chúng tôi <b>không bán, không trao đổi</b> dữ liệu cá nhân của bạn. Bên thứ ba duy
        nhất nhận nội dung câu hỏi là <b>Google (Gemini API)</b> để sinh câu trả lời cho trợ lý.
      </p>

      <h2>3. Vì sao thu thập đặc điểm thiết bị</h2>
      <p>
        Trợ lý chạy trên hạn mức có giới hạn. Nếu chỉ đếm theo tài khoản thì chỉ cần đăng ký
        thêm email là nhân hạn mức lên nhiều lần, và một người có thể làm cạn phần của tất cả
        những người còn lại. Vì vậy hệ thống tính thêm một mã định danh thiết bị (băm từ các
        đặc trưng kỹ thuật của trình duyệt) để đếm hạn mức theo thiết bị. Mã này
        <b>không cho phép chúng tôi biết bạn là ai ngoài dịch vụ</b> và không dùng cho quảng cáo.
      </p>

      <h2>4. Giữ trong bao lâu</h2>
      <ul>
        <li>Dữ liệu tài khoản: cho tới khi bạn xóa tài khoản.</li>
        <li>Nhật ký sử dụng và nhật ký kiểm toán: giữ để phục vụ điều tra sự cố và bảo mật.</li>
        <li>Bản sao lưu cơ sở dữ liệu: giữ tối đa 14 ngày rồi tự xóa.</li>
      </ul>

      <h2>5. Quyền của bạn</h2>
      <ul>
        <li><b>Xem và sửa</b> thông tin tài khoản tại trang
          <NuxtLink to="/account">Tài khoản</NuxtLink>.</li>
        <li><b>Xóa toàn bộ dữ liệu</b>: nút "Xóa tài khoản" ở cùng trang. Thao tác xóa thật —
          mã theo dõi, hội thoại và tệp đính kèm bị xóa theo, không hoàn tác được.</li>
        <li><b>Rút lại sự đồng ý</b> bằng cách ngừng sử dụng và xóa tài khoản.</li>
      </ul>

      <h2>6. Bảo mật</h2>
      <ul>
        <li>Mật khẩu lưu dạng băm bcrypt.</li>
        <li>Token đăng nhập nằm trong cookie <b>httpOnly</b> — JavaScript không đọc được.</li>
        <li>Đổi mật khẩu sẽ đăng xuất mọi thiết bị khác.</li>
        <li>Kết nối qua HTTPS ở môi trường thật.</li>
      </ul>
      <p>
        Không hệ thống nào an toàn tuyệt đối. Đừng gửi cho trợ lý những thông tin bạn không
        muốn người khác đọc — số tài khoản ngân hàng, giấy tờ tùy thân, mật khẩu.
      </p>

      <p class="lien-quan">
        Xem thêm: <NuxtLink to="/terms">Điều khoản sử dụng</NuxtLink>
      </p>
    </article>
  </div>
</template>

<style scoped>
.phap-ly { max-width: 760px; }
h1 { margin: 18px 0 4px; font-size: 26px; }
h2 { margin: 22px 0 8px; font-size: 16px; }
p, li, td, th { font-size: 14px; line-height: 1.65; color: var(--text-2); }
p { margin: 0 0 10px; }
ul { margin: 0 0 10px; padding-left: 20px; }
li { margin-bottom: 6px; }
b { color: var(--text); }

.bang { width: 100%; border-collapse: collapse; margin: 10px 0 14px; }
.bang th { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--line-hi, var(--line)); color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.4px; }
.bang td { padding: 8px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
.bang td:first-child { width: 42%; }

.ghi-chu { padding: 12px 14px; border-left: 2px solid var(--accent); background: var(--panel2); border-radius: 0 8px 8px 0; }
.lien-quan { margin-top: 26px; padding-top: 14px; border-top: 1px solid var(--line); font-size: 13px; }

@media (max-width: 620px) {
  .bang, .bang tbody, .bang tr, .bang td { display: block; width: auto; }
  .bang thead { display: none; }
  .bang tr { padding: 8px 0; border-bottom: 1px solid var(--line); }
  .bang td { border: 0; padding: 2px 0; }
  .bang td:first-child { width: auto; font-weight: 600; color: var(--text); }
}
</style>
