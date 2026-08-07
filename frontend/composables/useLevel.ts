import type { ItemLevel, Level } from '~/types/stock'

/**
 * NƠI DUY NHẤT ánh xạ `level` (do API cung cấp) sang class màu.
 * Đây là logic trình bày thuần túy — không suy ra kết luận, không so ngưỡng điểm.
 */

const TEXT_CLASS: Record<Level, string> = {
  good: 'lv-good',
  warn: 'lv-warn',
  bad: 'lv-bad'
}

const FILL_CLASS: Record<Level, string> = {
  good: 'bg-good',
  warn: 'bg-warn',
  bad: 'bg-bad'
}

/** API trả level tiêu chí dạng số: 0 = kém, 1 = trung bình, 2 = tốt. */
const ITEM_LEVEL_TO_LEVEL: Record<ItemLevel, Level> = {
  0: 'bad',
  1: 'warn',
  2: 'good'
}

export function useLevel() {
  /** Class màu chữ cho level dạng chuỗi. */
  const textClass = (level?: Level | null): string =>
    level && TEXT_CLASS[level] ? TEXT_CLASS[level] : 'lv-na'

  /** Class màu nền (thanh bar, chấm...) cho level dạng chuỗi. */
  const fillClass = (level?: Level | null): string =>
    level && FILL_CLASS[level] ? FILL_CLASS[level] : 'bg-na'

  /** Đổi level dạng số (0|1|2) của tiêu chí sang level dạng chuỗi. */
  const fromItemLevel = (level?: ItemLevel | number | null): Level | null => {
    if (level === 0 || level === 1 || level === 2) return ITEM_LEVEL_TO_LEVEL[level]
    return null
  }

  /**
   * Class màu chữ cho một tiêu chí.
   * `available = false` (không crawl được) luôn hiển thị màu "thiếu dữ liệu".
   */
  const itemTextClass = (level?: ItemLevel | number | null, available = true): string =>
    available ? textClass(fromItemLevel(level)) : 'lv-na'

  const itemFillClass = (level?: ItemLevel | number | null, available = true): string =>
    available ? fillClass(fromItemLevel(level)) : 'bg-na'

  return { textClass, fillClass, fromItemLevel, itemTextClass, itemFillClass }
}
