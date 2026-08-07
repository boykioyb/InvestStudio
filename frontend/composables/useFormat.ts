/**
 * Định dạng số/chuỗi để hiển thị. Thuần trình bày — không suy luận gì thêm.
 */
export function useFormat() {
  /** Số thập phân theo chuẩn Việt Nam (dấu phẩy thập phân). */
  const num = (value: unknown, digits = 2): string => {
    if (typeof value !== 'number' || !Number.isFinite(value)) return '—'
    return value.toLocaleString('vi-VN', {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits
    })
  }

  /** Giá cổ phiếu (đơn vị nghìn đồng như nguồn dữ liệu VN). */
  const price = (value: unknown): string => num(value, 2)

  /** Chuỗi ngày ISO -> dd/mm/yyyy; giữ nguyên nếu không parse được. */
  const date = (value: unknown): string => {
    if (typeof value !== 'string' || !value) return '—'
    const m = value.match(/^(\d{4})-(\d{2})-(\d{2})/)
    return m ? `${m[3]}/${m[2]}/${m[1]}` : value
  }

  return { num, price, date }
}
