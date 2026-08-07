import type { ScreenerColumn, ScreenerList, SortOrder } from '~/types/stock'

/**
 * Tải danh sách mã theo rổ.
 *
 * Sắp xếp do MÁY CHỦ làm — bấm đổi cột là gọi lại API. Máy chủ giữ cache theo
 * rổ nên thao tác này KHÔNG đi ra nguồn dữ liệu bên ngoài (hạn mức chỉ 20
 * request/phút). Cố ý không tự sắp xếp ở đây: hai bản cài đặt sắp xếp ở hai
 * ngôn ngữ sớm muộn cũng lệch nhau, đúng vết xe đổ của hàm làm tròn ngày trước.
 */
export function useScreener() {
  const config = useRuntimeConfig()
  const apiBase = String(config.public.apiBase || '').replace(/\/+$/, '')

  const data = ref<ScreenerList | null>(null)
  const pending = ref(false)
  const error = ref('')

  const group = ref('VN30')
  //  Vốn hóa là cột duy nhất luôn có số liệu kể cả ngoài phiên → làm mặc định.
  const sort = ref('market_cap')
  const order = ref<SortOrder>('desc')

  function messageOf(err: unknown): string {
    const detail = (err as { data?: { detail?: string } })?.data?.detail
    return detail || 'Không tải được danh sách. Kiểm tra máy chủ và thử lại.'
  }

  async function load(): Promise<void> {
    pending.value = true
    error.value = ''
    try {
      data.value = await $fetch<ScreenerList>(`${apiBase}/api/screener`, {
        query: { group: group.value, sort: sort.value, order: order.value }
      })
    } catch (err) {
      data.value = null
      error.value = messageOf(err)
    } finally {
      pending.value = false
    }
  }

  function selectGroup(key: string): void {
    if (group.value === key) return
    group.value = key
    void load()
  }

  /**
   * Bấm vào tiêu đề cột: cùng cột thì đảo chiều, khác cột thì sang cột mới.
   * Cột số mặc định giảm dần (lớn nhất lên trước — thứ người ta muốn thấy),
   * cột chữ mặc định tăng dần (A→Z). Đây là thói quen dùng bảng, không phải
   * quy tắc nghiệp vụ.
   */
  function toggleSort(column: ScreenerColumn): void {
    if (sort.value === column.key) {
      order.value = order.value === 'desc' ? 'asc' : 'desc'
    } else {
      sort.value = column.key
      order.value = column.type === 'text' ? 'asc' : 'desc'
    }
    void load()
  }

  return { data, pending, error, group, sort, order, load, selectGroup, toggleSort }
}
