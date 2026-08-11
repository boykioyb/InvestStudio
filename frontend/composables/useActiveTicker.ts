/**
 * Mã cổ phiếu ĐANG XEM — chia sẻ toàn app để trợ lý nổi (ChatWidget) biết đang
 * ở mã nào mà hỏi đúng ngữ cảnh. Trang phân tích ghi vào đây; widget đọc ra.
 */
export function useActiveTicker() {
  return useState<string>('active-ticker', () => '')
}
