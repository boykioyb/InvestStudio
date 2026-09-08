/**
 * Giải câu đố proof-of-work của bước đăng ký (xem backend/app/core/challenge.py).
 *
 * Tìm `answer` sao cho sha256(nonce + answer) bắt đầu bằng N số 0 (hex). Chạy
 * bằng WebCrypto ngay trên trình duyệt; độ khó 4 mất khoảng dưới một giây.
 *
 * Nhường luồng chính sau mỗi 500 lần thử để trang không bị "đơ" — người dùng
 * vẫn gõ được vào form trong lúc máy đang giải.
 */
async function sha256Hex(text: string): Promise<string> {
  const bytes = new TextEncoder().encode(text)
  const digest = await crypto.subtle.digest('SHA-256', bytes)
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('')
}

export async function solveProofOfWork(
  nonce: string,
  difficulty: number,
  maxTries = 5_000_000
): Promise<string> {
  const target = '0'.repeat(difficulty)
  for (let i = 0; i < maxTries; i++) {
    const answer = i.toString(36)
    if ((await sha256Hex(nonce + answer)).startsWith(target)) return answer
    if (i % 500 === 499) await new Promise((r) => setTimeout(r, 0))
  }
  //  Không giải nổi (độ khó bị đặt quá cao) → trả rỗng, backend sẽ từ chối và
  //  người dùng thấy thông báo rõ ràng thay vì trang treo vô hạn.
  return ''
}
