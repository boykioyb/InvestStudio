import type {
  AlertFeed,
  CompanyProfile,
  CorporateActions,
  FinancialStatement,
  MoneyFlow,
  NewsFeed,
  RangeKey,
  RatioTable,
  StatementKey,
  StockStats,
  TradingBoard
} from '~/types/stock'

/**
 * Tải dữ liệu chi tiết cho các tab (hồ sơ · tài chính · chỉ số).
 *
 * Chỉ lấy dữ liệu. Mọi con số đã được máy chủ làm tròn và quy đổi đơn vị sẵn —
 * frontend KHÔNG tính toán lại (xem quy tắc một nguồn sự thật trong README).
 *
 * Có cache theo mã: mở lại tab cũ không gọi mạng thêm lần nữa.
 */
export function useStockDetails() {
  const config = useRuntimeConfig()
  const apiBase = String(config.public.apiBase || '').replace(/\/+$/, '')

  const profile = ref<CompanyProfile | null>(null)
  const statement = ref<FinancialStatement | null>(null)
  const ratios = ref<RatioTable | null>(null)

  const loading = ref<Record<string, boolean>>({})
  const errors = ref<Record<string, string | null>>({})

  /** Bộ nhớ đệm theo khóa "mã:loại" để không gọi lại khi quay về tab cũ. */
  const cache = new Map<string, unknown>()

  function messageOf(err: unknown): string {
    const detail = (err as { data?: { detail?: string } })?.data?.detail
    return detail || 'Không tải được dữ liệu. Kiểm tra máy chủ và thử lại.'
  }

  async function get<T>(key: string, path: string, query: Record<string, string> = {}): Promise<T | null> {
    if (cache.has(key)) return cache.get(key) as T

    loading.value = { ...loading.value, [key]: true }
    errors.value = { ...errors.value, [key]: null }
    try {
      const result = await $fetch<T>(path, { baseURL: apiBase, query, timeout: 60_000 })
      cache.set(key, result)
      return result
    } catch (err) {
      errors.value = { ...errors.value, [key]: messageOf(err) }
      return null
    } finally {
      loading.value = { ...loading.value, [key]: false }
    }
  }

  const encode = (ticker: string) => encodeURIComponent(ticker.trim().toUpperCase())

  async function loadProfile(ticker: string): Promise<void> {
    const code = ticker.trim().toUpperCase()
    profile.value = await get<CompanyProfile>(`${code}:profile`, `/api/stocks/${encode(code)}/profile`)
  }

  async function loadStatement(ticker: string, kind: StatementKey): Promise<void> {
    const code = ticker.trim().toUpperCase()
    statement.value = await get<FinancialStatement>(
      `${code}:fin:${kind}`,
      `/api/stocks/${encode(code)}/financials`,
      { statement: kind }
    )
  }

  async function loadRatios(ticker: string): Promise<void> {
    const code = ticker.trim().toUpperCase()
    ratios.value = await get<RatioTable>(`${code}:ratios`, `/api/stocks/${encode(code)}/ratios`)
  }

  const alerts = ref<AlertFeed | null>(null)
  const board = ref<TradingBoard | null>(null)
  const flow = ref<MoneyFlow | null>(null)
  const stats = ref<StockStats | null>(null)
  const news = ref<NewsFeed | null>(null)
  const actions = ref<CorporateActions | null>(null)

  async function loadAlerts(ticker: string): Promise<void> {
    const code = ticker.trim().toUpperCase()
    alerts.value = await get<AlertFeed>(`${code}:alerts`, `/api/stocks/${encode(code)}/alerts`)
  }

  async function loadBoard(ticker: string): Promise<void> {
    const code = ticker.trim().toUpperCase()
    board.value = await get<TradingBoard>(`${code}:board`, `/api/stocks/${encode(code)}/board`)
  }

  async function loadFlow(ticker: string, range: RangeKey): Promise<void> {
    const code = ticker.trim().toUpperCase()
    flow.value = await get<MoneyFlow>(
      `${code}:flow:${range}`, `/api/stocks/${encode(code)}/money-flow`, { range }
    )
  }

  async function loadStats(ticker: string, range: RangeKey): Promise<void> {
    const code = ticker.trim().toUpperCase()
    stats.value = await get<StockStats>(
      `${code}:stats:${range}`, `/api/stocks/${encode(code)}/stats`, { range }
    )
  }

  async function loadNews(ticker: string): Promise<void> {
    const code = ticker.trim().toUpperCase()
    news.value = await get<NewsFeed>(`${code}:news`, `/api/stocks/${encode(code)}/news`)
  }

  async function loadActions(ticker: string): Promise<void> {
    const code = ticker.trim().toUpperCase()
    actions.value = await get<CorporateActions>(
      `${code}:actions`, `/api/stocks/${encode(code)}/corporate-actions`
    )
  }

  /** Đổi mã → bỏ hết cache cũ để không hiển thị nhầm dữ liệu mã trước. */
  function reset(): void {
    cache.clear()
    profile.value = null
    statement.value = null
    ratios.value = null
    alerts.value = null
    board.value = null
    flow.value = null
    stats.value = null
    news.value = null
    actions.value = null
    loading.value = {}
    errors.value = {}
  }

  const isLoading = (key: string) => Boolean(loading.value[key])
  const errorOf = (key: string) => errors.value[key] || null

  return {
    profile,
    statement,
    ratios,
    alerts,
    board,
    flow,
    stats,
    news,
    actions,
    isLoading,
    errorOf,
    loadProfile,
    loadStatement,
    loadRatios,
    loadAlerts,
    loadBoard,
    loadFlow,
    loadStats,
    loadNews,
    loadActions,
    reset
  }
}
