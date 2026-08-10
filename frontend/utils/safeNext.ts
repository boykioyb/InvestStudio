/**
 * Lọc tham số `?next=` để chống open redirect (chuyển hướng ra site ngoài).
 *
 * Chỉ chấp nhận đường dẫn NỘI BỘ: bắt đầu bằng một dấu `/` DUY NHẤT, không phải
 * `//host` hay `/\host` (cả hai vẫn khởi đầu bằng `/` nhưng trình duyệt hiểu là
 * host ngoài). Không hợp lệ → về trang chủ.
 */
export function isSafeNext(next: string): string {
  if (!next.startsWith('/')) return '/'
  if (next.startsWith('//') || next.startsWith('/\\')) return '/'
  return next
}
