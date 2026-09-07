/**
 * Vân tay thiết bị — để hạn mức trợ lý không bị vô hiệu bằng cách đăng ký email mới.
 *
 * Chạy MỘT LẦN lúc tải trang: tính `visitorId` (canvas, WebGL, phông chữ, âm
 * thanh…) rồi ghi vào cookie `fpjs`. Dùng cookie chứ không phải header vì
 * trình duyệt tự đính cookie vào MỌI request cùng origin — không phải sửa từng
 * lời gọi API trong các composable, và luồng SSE (EventSource, không đặt được
 * header) cũng có vân tay.
 *
 * Backend ghép cookie này với cookie `did` (httpOnly, có ký ở máy chủ) rồi băm
 * ra `fp_hash` — xem backend/app/core/fingerprint.py.
 *
 * ⚠️ Không phải bí mật, chỉ là mã nhận dạng: cookie này KHÔNG httpOnly (phía
 * trình duyệt phải ghi được). Nửa chống giả mạo nằm ở cookie `did` có chữ ký.
 * ⚠️ Đây là dữ liệu cá nhân theo Nghị định 13/2023 — chính sách quyền riêng tư
 * phải nêu rõ việc thu thập đặc điểm thiết bị để chống lạm dụng hạn mức.
 */
const COOKIE = 'fpjs'
const ONE_YEAR = 60 * 60 * 24 * 365

function readCookie(name: string): string {
  const hit = document.cookie.split('; ').find((row) => row.startsWith(`${name}=`))
  return hit ? decodeURIComponent(hit.slice(name.length + 1)) : ''
}

export default defineNuxtPlugin(() => {
  //  Đã có rồi thì thôi — tính lại mỗi lần tải trang vừa tốn CPU vừa vô ích.
  if (readCookie(COOKIE)) return

  //  Nạp LƯỜI sau khi trang đã hiển thị: đây là việc nền, không được làm chậm
  //  lần vẽ đầu tiên.
  const run = async () => {
    try {
      const FingerprintJS = await import('@fingerprintjs/fingerprintjs')
      const agent = await FingerprintJS.load()
      const { visitorId } = await agent.get()
      const secure = location.protocol === 'https:' ? '; Secure' : ''
      document.cookie = `${COOKIE}=${visitorId}; Max-Age=${ONE_YEAR}; Path=/; SameSite=Lax${secure}`
    } catch {
      //  Chặn quảng cáo / trình duyệt chống fingerprint có thể chặn thư viện.
      //  Không sao: backend vẫn còn cookie `did` + IP để đếm, chỉ kém chặt hơn.
    }
  }

  if (typeof requestIdleCallback === 'function') requestIdleCallback(() => void run())
  else setTimeout(() => void run(), 1200)
})
