/**
 * Nội dung MINH HOẠ cho trang chủ (thẻ kết quả mẫu FPT) + tiện ích vẽ sparkline.
 *
 * QUAN TRỌNG: đây là dữ liệu trình bày cố định để giới thiệu sản phẩm — KHÔNG
 * phải số liệu live và KHÔNG chứa logic chấm điểm. Mọi điểm số thật đều do máy
 * chủ trả về. Hai hàm `series`/`paths` chỉ là toán vẽ đường SVG.
 */

/** Mức tín hiệu của một tiêu chí → lớp CSS lv-good / lv-warn / lv-bad. */
export type DemoLevel = 'good' | 'warn' | 'bad'

export interface DemoCriterion {
  label: string
  raw: string
  points: number
  max: number
  level: DemoLevel
}

export interface DemoGroup {
  name: string
  sum: number
  max: number
  /** Tông màu của nhóm — ghi thẳng trong dữ liệu mẫu, client không tự chấm. */
  level: DemoLevel
  note: string
  items: DemoCriterion[]
}

export interface DemoHorizon {
  label: string
  value: number
  best: boolean
}

export interface DemoRange {
  key: string
  label: string
  /** số phiên trong khung */
  n: number
  lo: number
  hi: number
  chg: string
}

export interface DemoRule {
  icon: string
  /** tông màu ô icon */
  tone: 'bad' | 'na' | 'alt'
  title: string
  body: string
}

/** Đường vẽ sparkline đã tính sẵn theo hệ toạ độ 600×140. */
export interface SparkPaths {
  line: string
  area: string
  lastX: string
  lastY: string
}

const GROUPS: DemoGroup[] = [
  {
    name: 'Nền tảng & tài chính',
    level: 'good',
    sum: 39,
    max: 45,
    note: 'Nhóm nặng nhất (45 điểm): doanh nghiệp có kiếm ra tiền thật và có nợ nhiều không. FPT mất điểm duy nhất ở tăng trưởng lợi nhuận 19,1% — tốt nhưng chưa tới mốc điểm tối đa.',
    items: [
      { label: 'Tăng trưởng LN', raw: '19.1% YoY', points: 6, max: 12, level: 'warn' },
      { label: 'ROE', raw: '28.3%', points: 10, max: 10, level: 'good' },
      { label: 'Biên lợi nhuận', raw: '16.0%', points: 8, max: 8, level: 'good' },
      { label: 'Nợ vay D/E', raw: '0.48', points: 8, max: 8, level: 'good' },
      { label: 'Dòng tiền KD', raw: 'Dương bền', points: 7, max: 7, level: 'good' }
    ]
  },
  {
    name: 'Định giá',
    level: 'good',
    sum: 18,
    max: 20,
    note: 'Giá đang trả có đắt so với ngành không. P/E ngành là ước lượng theo bảng benchmark — ngân hàng nên dùng P/E ngành 9.',
    items: [
      { label: 'P/E vs ngành', raw: '12.2 / ngành 18.0', points: 10, max: 10, level: 'good' },
      { label: 'P/B', raw: '3.06 / hợp lý 3.5', points: 5, max: 5, level: 'good' },
      { label: 'Cổ tức', raw: '2.8%', points: 3, max: 5, level: 'warn' }
    ]
  },
  {
    name: 'Kỹ thuật & xu hướng',
    level: 'good',
    sum: 16,
    max: 20,
    note: 'Luôn đo trên cửa sổ 180 ngày cố định để mọi mã cùng một thước. Biểu đồ nhiều khung chỉ để xem, không đổi điểm.',
    items: [
      { label: 'Xu hướng giá', raw: 'Đi ngang', points: 4, max: 8, level: 'warn' },
      { label: 'Thanh khoản', raw: '5.99 tr cp/phiên', points: 6, max: 6, level: 'good' },
      { label: 'Động lượng RSI', raw: 'RSI 58', points: 6, max: 6, level: 'good' }
    ]
  },
  {
    name: 'Định tính & vĩ mô',
    level: 'warn',
    sum: 8,
    max: 15,
    note: 'Ba tiêu chí này máy không crawl được — mặc định "trung bình", bạn tự chỉnh khi mở phân tích đầy đủ. 15 điểm này là phần bạn góp ý kiến của mình.',
    items: [
      { label: 'Vị thế ngành', raw: 'Trung bình', points: 3, max: 6, level: 'warn' },
      { label: 'Ban lãnh đạo & cổ đông', raw: 'Ổn', points: 3, max: 5, level: 'warn' },
      { label: 'Catalyst', raw: 'Tiềm năng', points: 2, max: 4, level: 'warn' }
    ]
  }
]

const HORIZONS: DemoHorizon[] = [
  { label: 'Ngắn hạn (ngày–tuần)', value: 76, best: false },
  { label: 'Trung hạn (tháng–1 năm)', value: 80, best: true },
  { label: 'Dài hạn (nhiều năm)', value: 79, best: false }
]

const RANGES: DemoRange[] = [
  { key: '1T', label: '1 tháng', n: 22, lo: 68.1, hi: 76.5, chg: '-1.52%' },
  { key: '1Q', label: 'Một quý', n: 66, lo: 62.2, hi: 76.5, chg: '-1.52%' },
  { key: '1N', label: '1 năm', n: 248, lo: 58.4, hi: 81.9, chg: '+9.8%' },
  { key: '3N', label: '3 năm', n: 744, lo: 31.2, hi: 81.9, chg: '+118%' }
]

const RULES: DemoRule[] = [
  {
    icon: '−8%',
    tone: 'bad',
    title: 'Kịch bản xấu nhất bằng con số',
    body: 'Mỗi mã có giá cắt lỗ cụ thể và thiệt hại ước tính trên tổng tài khoản. Rủi ro liệt kê là các tiêu chí đang bị 0 điểm của chính mã đó.'
  },
  {
    icon: 'N/A',
    tone: 'na',
    title: 'Thiếu số liệu thì 0 điểm, không bịa',
    body: 'Chỉ số không lấy được sẽ hiện N/A và kéo điểm xuống. Công cụ nói rõ điểm thấp là do thiếu dữ liệu.'
  },
  {
    icon: '≠',
    tone: 'alt',
    title: 'Sổ mua nhiều đợt cố ý bất đối xứng',
    body: 'Thủng cắt lỗ là cắt lỗ, bất kể điểm bao nhiêu. Khi đang lỗ, "bình quân giá xuống" luôn kèm cảnh báo: tiền chịu rủi ro tăng lên.'
  }
]

export function useHomeDemo() {
  /**
   * Sinh dãy giá giả lập tất định (cùng đầu vào → cùng kết quả, nên máy chủ và
   * trình duyệt vẽ giống nhau, không lệch hydrate).
   */
  function series(n: number, lo: number, hi: number, last: number): number[] {
    let s = 7 + n
    const rand = (): number => (s = (s * 16807) % 2147483647) / 2147483647
    const pts: number[] = []
    let v = lo + (hi - lo) * 0.55
    for (let i = 0; i < n; i++) {
      v += (rand() - 0.5) * (hi - lo) * 0.14 + (last - v) * 0.02
      v = Math.max(lo, Math.min(hi, v))
      pts.push(v)
    }
    pts[Math.floor(n * 0.62)] = lo
    pts[Math.floor(n * 0.25)] = hi
    pts[n - 1] = last
    return pts
  }

  /** Quy dãy số về đường `path` SVG trong khung 600×140. */
  function paths(pts: number[]): SparkPaths {
    const W = 600
    const H = 140
    const px = 10
    const py = 14
    const min = Math.min(...pts)
    const max = Math.max(...pts)
    const span = max - min || 1
    const P = pts.map((v, i): [number, number] => [
      px + ((W - 2 * px) * i) / (pts.length - 1),
      py + (H - 2 * py) * (1 - (v - min) / span)
    ])
    const line = P.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(' ')
    const l = P[P.length - 1]
    return {
      line,
      area: `${line} L${l[0].toFixed(1)} ${H - py} L${P[0][0].toFixed(1)} ${H - py} Z`,
      lastX: l[0].toFixed(1),
      lastY: l[1].toFixed(1)
    }
  }

  return { GROUPS, HORIZONS, RANGES, RULES, series, paths }
}
