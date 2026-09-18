# North Star Metric (NSM) — đo lường & cách xem lại

> Gắn với `backlog-refinement.md` › ISSUE-03. Mục tiêu: thay "vanity metrics" (lượt
> xem, đăng ký) bằng **bằng chứng thật** về giá trị cốt lõi, và mở khoá thước đo cho
> ISSUE-01 ("vì sao điểm này").

## Chốt phương án

Đo song song **cả 3** phương án ứng viên trên cùng một luồng sự kiện, để có dữ liệu
thật rồi mới chốt 1 chỉ số chính:

| Mã | Phương án | Ý nghĩa |
|----|-----------|---------|
| **NSM-A** | Số mã user thực sự phân tích / tuần | Hành vi giá trị cốt lõi: mở & xem phân tích một mã |
| **NSM-B** | Tỉ lệ user hoạt động có tương tác trợ lý | Mức dùng trợ lý agentic — điểm khác biệt sản phẩm |
| **NSM-C** | % người xem điểm mở "vì sao điểm", rồi % trong số đó có hành động | Kiểm chứng **giả định nguy hiểm nhất**: "user có tin điểm máy chấm không" |

## Instrument (event cần log, nơi log)

Một bảng chuyên trách: **`product_events`** (`backend/app/models/analytics.py`) — TÁCH
khỏi `usage_events` (bảng đó đo chi phí/quota). Ghi qua `services/analytics.log_event`.

| event | Sinh ở đâu | Ghi bởi | Danh tính |
|-------|-----------|---------|-----------|
| `analyze` | Người dùng nhận một điểm số (mới hoặc từ cache) | Máy chủ — `routes/stocks.py` (cả `/{ticker}` và `/{ticker}/stream`) | user_id, hoặc fp_hash nếu là khách |
| `assistant` | Một lượt hỏi–đáp trợ lý hoàn tất | Máy chủ — `routes/chat.py` (`ask` và `ask_stream`) | user_id |
| `why_open` | Mở phần "vì sao điểm này" | Frontend → `POST /api/metrics/event` | user_id / fp_hash |
| `score_action` | Hành động sau khi xem điểm (VD theo dõi mã) | Frontend → `POST /api/metrics/event` | user_id / fp_hash |

`analyze`/`assistant` do **máy chủ** tự ghi tại nơi việc thật xảy ra → không giả mạo
số đếm được. `why_open`/`score_action` là sự kiện giao diện nên frontend báo về; endpoint
chỉ nhận đúng hai loại này và có rào chống spam.

Danh tính để đếm "người dùng riêng biệt": ưu tiên `user_id`; khách rơi về `fp_hash`
(vân tay thiết bị **đã có sẵn** cho hạn mức — không thêm bề mặt thu thập dữ liệu mới).

## Cách xem lại (bằng chứng thật)

- **Nhanh:** `GET /api/admin/nsm?days=7` (chỉ quản trị viên). Trả số liệu thô + tỉ lệ đã
  tính cho cả 3 NSM. Cài đặt trong `services/analytics.nsm_summary`.
- **SQL tương đương** (khi khối lượng lớn, thay cho tính trong Python). Danh tính =
  `COALESCE('u' || user_id, fp_hash)`; cửa sổ 7 ngày:

```sql
-- NSM-A · trung bình số mã riêng biệt mỗi người phân tích / tuần
WITH a AS (
  SELECT COALESCE('u'||user_id, NULLIF(fp_hash,'')) AS ident, ticker
  FROM product_events
  WHERE event='analyze' AND at >= now() - interval '7 days'
    AND COALESCE('u'||user_id, NULLIF(fp_hash,'')) IS NOT NULL
)
SELECT COUNT(DISTINCT (ident, ticker))::float / NULLIF(COUNT(DISTINCT ident),0)
FROM a;

-- NSM-B · tỉ lệ user hoạt động có tương tác trợ lý
WITH ev AS (
  SELECT event, COALESCE('u'||user_id, NULLIF(fp_hash,'')) AS ident
  FROM product_events
  WHERE at >= now() - interval '7 days'
    AND COALESCE('u'||user_id, NULLIF(fp_hash,'')) IS NOT NULL
)
SELECT COUNT(DISTINCT ident) FILTER (WHERE event='assistant')::float
       / NULLIF(COUNT(DISTINCT ident),0)
FROM ev;

-- NSM-C · % người xem điểm mở "vì sao"; và % trong số mở đó có hành động
WITH ev AS (
  SELECT event, COALESCE('u'||user_id, NULLIF(fp_hash,'')) AS ident
  FROM product_events
  WHERE at >= now() - interval '7 days'
    AND COALESCE('u'||user_id, NULLIF(fp_hash,'')) IS NOT NULL
),
who AS (
  SELECT
    ARRAY(SELECT DISTINCT ident FROM ev WHERE event='analyze')      AS saw,
    ARRAY(SELECT DISTINCT ident FROM ev WHERE event='why_open')     AS opened,
    ARRAY(SELECT DISTINCT ident FROM ev WHERE event='score_action') AS acted
)
SELECT
  cardinality(ARRAY(SELECT unnest(opened) INTERSECT SELECT unnest(saw)))::float
    / NULLIF(cardinality(saw),0)                             AS why_open_rate,
  cardinality(ARRAY(SELECT unnest(opened) INTERSECT SELECT unnest(acted)))::float
    / NULLIF(cardinality(opened),0)                          AS act_after_why_rate
FROM who;
```

## Vòng lặp

Build → Measure → Learn: chạy 1–2 tuần, đọc `GET /api/admin/nsm`, rồi chốt 1 NSM chính
và cập nhật `backlog-refinement.md`.
