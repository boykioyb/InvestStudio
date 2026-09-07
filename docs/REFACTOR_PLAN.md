# Kế hoạch Refactor toàn diện — Phân Tích Mã (BE + FE)

> Trạng thái: **CHỜ DUYỆT SCOPE** — chưa bắt đầu code.
> Ngày lập: 2026-08-24. Nguồn: khảo sát code có bằng chứng (file:line) toàn bộ `backend/app/` và `frontend/`.

---

## 0. Nguyên tắc & bất biến phải giữ

- **Single-source-of-truth chấm điểm**: mọi logic 14 tiêu chí chỉ nằm trong `backend/app/services/scoring.py` + `criteria.py`. Không được nhân bản ra nơi khác.
- **Frontend không chứa logic nghiệp vụ**: FE chỉ hiển thị + gọi API. Formatter/level dùng chung (`useFormat`, `useLevel`).
- **Xử lý thiếu dữ liệu bảo thủ**: `None → 0 điểm + available=False`, không bịa số.
- **Đơn vị tiền**: nguồn dùng "nghìn đồng" (千円) cho giá/cp; tiền tổng hiển thị VND thật cho người dùng.
- Sau **mỗi pha**: chạy `pytest` (BE) + `nuxt typecheck` (FE), commit riêng từng pha.

---

## ⚠️ Lưới an toàn (tình trạng hiện tại)

| | Test | Lint | CI |
|---|---|---|---|
| Backend | Có nhưng lệch: `scoring` kỹ; `position.py`, `analyzer.py`, `market.py`, `alerts.py`, `details.py` **0 test** | — | ❌ |
| Frontend | ❌ không | ❌ không eslint | ❌ |

→ Refactor lớn cần lưới an toàn ⇒ **Phase 0** bắt buộc.

---

## Bản đồ phát hiện — BACKEND

| # | Vấn đề | Bằng chứng | Đề xuất |
|---|---|---|---|
| R1 | Không có primitive fan-out; I/O sync; "batch" chỉ là vòng lặp tuần tự | `rag/tasks.py:82-86`, `vci_direct.py:45`, `cafef.py:45` | `services/batch.py` dùng `ThreadPoolExecutor` (4–6 worker, tôn trọng rate limit ~20 req/phút) |
| R2 | `position.review` luôn gọi `analyzer.analyze` nặng (3+ round-trip), không có đường lấy giá rẻ | `position.py:40-43`, `analyzer.py:136-142`, `market.py:52` | Tách `price_review` (rẻ, chỉ giá+P&L+stop) vs `action` (cần điểm). Batch mặc định dùng đường rẻ, `deep=true` mới chấm điểm |
| R3 | Helper số/parse + quy đổi `/1000` lặp ~6 nơi | `market.py:35/45`, `screener.py:123/139`, `details.py:165/194`, `alerts.py:153` | `services/units.py`: `to_float`, `clean_text`, `dong_to_nghin`, `to_billion/million`, `percent` |
| R4 | `try/except VciError→ProviderError` copy ~10 lần | `vci_adapter.py:29-31/45-48/72-75`, `details.py:147-152/233-236`, `feed.py:156-159`, `screener.py:238-250` | Decorator `@wrap_vci_errors("...{ticker}")` trong `providers/base.py`; bỏ import lười |
| R5 | `schemas/stock.py` 556 LOC / 50 model hổ lốn | `schemas/stock.py` | Tách package `schemas/`: `scoring/market/company/feed/position/screener` + shim re-export |
| R6 | File đa trách nhiệm lớn | `rag/agent.py:501`, `vci_direct.py:423`, `details.py:320` | `agent_tools.py`; tách `vci_price/financials/company`; `ratio_maps.py` |
| R7 | Gọi private `scoring._size_bracket` xuyên module | `position.py:72`, `scoring.py:260` | Public hóa `size_bracket` |
| R8 | Validate/cache route không nhất quán | `stocks.py:79/122/191` (isalnum lặp), `stocks.py:38/39/210` (3 cache) | Dùng `_symbol()` + `_cached()` đồng bộ |

**Điểm mạnh giữ nguyên:** single-source scoring; funnel lỗi `ProviderError→502`; cache TTL theo tham số; asymmetry của `position._decide` (kỷ luật cắt lỗ trước cơ hội mua thêm).

**Concurrency:** tất cả sync I/O; `httpx.Client` dùng chung là thread-safe ⇒ dùng threadpool (không phải asyncio). Batch phải: tôn trọng rate limit, tái dùng cache `stocks.py:_cache`, trả **lỗi từng mã riêng** (không all-or-nothing).

---

## Bản đồ phát hiện — FRONTEND

| # | Vấn đề | Bằng chứng | Đề xuất |
|---|---|---|---|
| A | **Không có layout chung** — 4 trang tự dựng header/nav, markup + CSS khác nhau, link không đồng bộ (còn là bug UX) | `index.vue:117-164`, `danh-sach.vue:62-81`, `theo-doi.vue:85-92`, `tro-ly.vue:115-121` | `layouts/default.vue` + `components/AppHeader.vue` (slot cho search/action riêng trang) |
| B | **Đơn vị tiền loạn**: cùng màn `PositionTab` có chỗ nghìn đ (dòng lot), chỗ VND thật (bảng review); 7 component tự khai `num` | `PositionTab.vue:85` vs `133/192`, `theo-doi.vue:78-79`, `ForeignFlowCard/TradingTab/CapitalTab/MoneyFlowTab` | Đưa `money()` + biến thể triệu-cp vào `useFormat`; thay hết bản sao |
| C | 2 trang quá lớn | `tro-ly.vue:788`, `index.vue:773` | Tách `ChatSidebar/ChatThread/ChatComposer`; `AnalyzeOptionsPanel/AnalyzeProgress` |
| D | apiBase + bóc lỗi + pending/error lặp ở 9 composable | `useScreener:13/24-27`, `useWatchlist:18-22`, `useStockDetails:25/37-40`… | `useApi()` base (apiBase + `extractDetail` + wrapper request) |
| E | Logic trình bày rò vào component | `PositionTab.vue:20-34` (`num/money/viDate/signClass`), `tro-ly.vue:40-47` | Dồn về `useFormat`/`useLevel` |
| F | `.chip` khai lại 3 nơi (có va chạm tên), CSS header lặp | `index.vue:367`, `danh-sach.vue:177`, `tro-ly.vue:702` | `.chip` global hóa; audit scoped-vs-global |
| G | A11y/responsive lệch; `window.prompt/confirm` | `tro-ly.vue:99/104` | Chuẩn hóa qua `AppHeader`; thay prompt/confirm bằng modal |

**Điểm mạnh giữ nguyên:** `useFormat`/`useLevel`; bảng screener 100% từ metadata server; design tokens `main.css` (`--accent/--panel/--line/--good/--bad/--muted`…); lazy tab load + ARIA của `StockTabs`.

**State vị thế (cho trang tổng quan):** localStorage key `investstudio.positions.v1`, shape `{ [TICKER]: { lots: PositionLot[], account?: string } }` (`usePositionBook.ts:3,33-47`). Đã chứa **tất cả mã** trong 1 blob ⇒ chỉ cần thêm export `listAll()` là dựng được overview.

---

## Kế hoạch theo pha

### Phase 0 — Lưới an toàn *(bắt buộc, làm trước)*
- BE: test hàm thuần cho `position._decide`, `market` (MFI/OBV/stats), `alerts._adjustment`, `analyzer._first_success`.
- FE: bật `nuxt typecheck` sạch; thêm eslint config tối thiểu.
- CI: 1 workflow chạy `pytest` + `typecheck` khi push/PR.

### Phase 1 — Nền dùng chung *(điều kiện tiên quyết cho IA overview-first)*
- FE: `useFormat.money()` (gộp helper vừa thêm ở PositionTab), sửa lệch đơn vị PositionTab, `useApi()` base, gom parser số về `utils/`.
- FE: `layouts/default.vue` + `AppHeader.vue`, áp cho cả 4 trang, thống nhất link nav.
- BE: `services/units.py` (R3), public `size_bracket` (R7).

### Phase 2 — Tính năng Danh mục (overview-first) *(giá trị chính bạn muốn)*
- BE: `services/batch.py` (R1) + tách `price_review` (R2) + `POST /api/portfolio/review` (chạy song song, lỗi từng mã riêng, trả `{holdings, totals, errors}`).
- FE: `usePositionBook().listAll()`, `usePortfolio()` + trang `/danh-muc`: thẻ tổng (Tổng vốn · Giá trị TT · **Lãi/lỗ đ + %** · số mã lãi/lỗ) + bảng mỗi mã → bấm vào `/?ma=`. Tiền hiển thị VND thật.
- IA: `/danh-muc` là trang mặc định khi đã đăng nhập & có vị thế; `/` vẫn là màn chi tiết mã.

### Phase 3 — Cấu trúc (tách file lớn)
- BE: tách `schemas/` package (R5), `agent_tools.py` + tách `vci_direct` theo nhóm, `ratio_maps.py` (R6).
- FE: tách `index.vue` và `tro-ly.vue` thành sub-component (C).

### Phase 4 — Dọn boilerplate
- BE: `@wrap_vci_errors` (R4), gộp cache + `_symbol()` route (R8).
- FE: `.chip` global + audit CSS va chạm (F), thay `window.prompt/confirm` (G).

```
P0 (an toàn) → P1 (nền chung) → P2 (Danh mục) → P3 (tách file) → P4 (dọn)
```

---

## Quyết định cần chốt

1. Làm **Phase 0** trước? — *gợi ý: có*
2. Phạm vi: **P0→P4 hết** hay **P0→P2 trước** rồi tính tiếp? — *gợi ý: P0→P2*
3. Trang tổng quan: **B‑lite** (nhanh, chỉ lãi/lỗ) hay **B‑full** (kèm điểm/khuyến nghị)? `/danh-muc` mặc định khi đã đăng nhập? Nav gom layout chung? — *gợi ý: B‑lite · có · có*

---

## Đã hoàn thành ngoài kế hoạch
- Sửa hiển thị Lãi/Lỗ ra VND thật trong `frontend/components/tabs/PositionTab.vue` (thêm `money()`, nhãn `(đ)`). Sẽ được gộp vào `useFormat` ở Phase 1.
