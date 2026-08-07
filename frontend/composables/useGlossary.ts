/**
 * Từ điển giải nghĩa cho người mới.
 * Chỉ là chú thích giáo dục hiển thị dạng tooltip — không tham gia chấm điểm.
 * Khớp theo chuỗi con trong nhãn mà API trả về.
 */

interface GlossEntry {
  /** Các cách viết có thể gặp trong nhãn. */
  match: string[]
  /** Câu giải thích tiếng Việt dễ hiểu. */
  gloss: string
}

const GLOSSARY: GlossEntry[] = [
  {
    match: ['roe'],
    gloss:
      'ROE (tỷ suất lợi nhuận trên vốn chủ sở hữu): mỗi 100 đồng vốn của cổ đông tạo ra bao nhiêu đồng lãi mỗi năm.'
  },
  {
    match: ['roa'],
    gloss:
      'ROA (tỷ suất lợi nhuận trên tổng tài sản): mỗi 100 đồng tài sản tạo ra bao nhiêu đồng lãi.'
  },
  {
    match: ['p/e', 'pe '],
    gloss:
      'P/E (giá trên lợi nhuận mỗi cổ phiếu): bạn trả bao nhiêu đồng để mua 1 đồng lợi nhuận một năm. Thường so với trung bình ngành.'
  },
  {
    match: ['p/b', 'pb '],
    gloss:
      'P/B (giá trên giá trị sổ sách): bạn trả bao nhiêu đồng cho 1 đồng tài sản ròng ghi trên sổ sách.'
  },
  {
    match: ['d/e', 'nợ vay', 'đòn bẩy'],
    gloss:
      'D/E (nợ trên vốn chủ sở hữu): vay bao nhiêu đồng trên mỗi đồng vốn tự có. Càng cao càng rủi ro khi lãi suất tăng.'
  },
  {
    match: ['rsi', 'động lượng'],
    gloss:
      'RSI (chỉ báo sức mạnh tương đối, thang 0–100): đo mức độ tăng/giảm gần đây. Quy ước phổ biến: trên 70 là "quá mua", dưới 30 là "quá bán".'
  },
  {
    match: ['ocf', 'dòng tiền'],
    gloss:
      'OCF / dòng tiền kinh doanh: tiền mặt thật thu về từ hoạt động bán hàng. Lãi trên giấy mà không có tiền về là dấu hiệu đáng ngại.'
  },
  {
    match: ['biên ln', 'biên lợi nhuận', 'margin'],
    gloss: 'Biên lợi nhuận: trong 100 đồng doanh thu thì giữ lại được bao nhiêu đồng lãi.'
  },
  {
    match: ['tăng trưởng'],
    gloss:
      'Tăng trưởng lợi nhuận (YoY = so với cùng kỳ năm trước): lợi nhuận năm nay hơn/kém năm ngoái bao nhiêu phần trăm.'
  },
  {
    match: ['cổ tức'],
    gloss:
      'Cổ tức: phần lợi nhuận doanh nghiệp chia lại cho cổ đông, thường tính theo % trên thị giá.'
  },
  {
    match: ['xu hướng', 'trend'],
    gloss:
      'Xu hướng giá: giá đang đi lên, đi ngang hay đi xuống khi so với đường trung bình các phiên gần đây.'
  },
  {
    match: ['biến động', 'vol'],
    gloss:
      'Biến động: giá dao động mạnh hay nhẹ. Biến động càng lớn thì lãi/lỗ ngắn hạn càng dữ dội.'
  },
  {
    match: ['thanh khoản', 'klgd', 'khối lượng'],
    gloss:
      'Thanh khoản (khối lượng giao dịch): mã có dễ mua/bán không. Thanh khoản thấp thì khó thoát hàng khi cần.'
  },
  {
    match: ['vị thế', 'lợi thế'],
    gloss:
      'Vị thế cạnh tranh: doanh nghiệp có lợi thế bền vững nào (thương hiệu, quy mô, chi phí thấp...) khiến đối thủ khó chiếm chỗ.'
  },
  {
    match: ['lãnh đạo', 'quản trị'],
    gloss:
      'Ban lãnh đạo / quản trị: đội ngũ điều hành có minh bạch, giữ lời hứa với cổ đông và không pha loãng cổ phiếu vô tội vạ không.'
  },
  {
    match: ['xúc tác', 'câu chuyện', 'triển vọng'],
    gloss:
      'Chất xúc tác: sự kiện sắp tới có thể làm giá tăng (nhà máy mới, hợp đồng lớn, chính sách hỗ trợ...).'
  },
  {
    match: ['định giá'],
    gloss: 'Định giá: cổ phiếu đang đắt hay rẻ so với lợi nhuận, tài sản và so với các mã cùng ngành.'
  }
]

export function useGlossary() {
  /** Trả về lời giải nghĩa cho một nhãn, hoặc chuỗi rỗng nếu không có. */
  const glossFor = (label?: string | null): string => {
    if (!label) return ''
    const l = ` ${label.toLowerCase()} `
    const hits = GLOSSARY.filter((e) => e.match.some((m) => l.includes(m)))
    return hits.slice(0, 2).map((e) => e.gloss).join(' ')
  }

  return { glossFor }
}
