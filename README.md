# InvestStudio

Công cụ phân tích cổ phiếu Việt Nam: **nhập mã → crawl dữ liệu công khai → chấm điểm 100 điểm → kết luận** (sức khỏe tài chính · tầm nhìn · điểm số · quyết định).

> ⚠️ Công cụ hỗ trợ tư duy, **không phải khuyến nghị đầu tư**. Dữ liệu lấy từ nguồn công khai, có thể trễ hoặc sai lệch — hãy tự kiểm chứng trước khi ra quyết định tiền bạc.

## Kiến trúc — một nguồn sự thật

```
┌──────────────┐   HTTP/JSON    ┌─────────────────────────────┐
│  Nuxt 3      │ ─────────────► │  FastAPI                    │
│  (chỉ render)│ ◄───────────── │  crawl + CHẤM ĐIỂM          │
└──────────────┘                └──────────┬──────────────────┘
                                           │
                              ┌────────────┴────────────┐
                              │ CafeF (giá/kỹ thuật)    │
                              │ vnstock/VCI (cơ bản)    │
                              └─────────────────────────┘
```

**Quy tắc bất di bất dịch:** toàn bộ logic chấm điểm nằm DUY NHẤT ở
[`backend/app/services/scoring.py`](backend/app/services/scoring.py).
Frontend không được chứa ngưỡng, công thức hay chữ verdict — nó chỉ hiển thị
những gì API đã tính sẵn. Đây là bài học rút ra từ bản cũ: khi logic bị nhân
bản ở cả JS lẫn Python, hai bên lệch nhau 2 điểm chỉ vì `Math.round(2.5)=3`
còn `round(2.5)=2`.

## Chạy

```bash
cp .env.example .env               # điền GEMINI_API_KEY nếu muốn dùng trợ lý RAG
docker compose up --build          # Web :3010 · API :8010 · Postgres (nội bộ)
```

- Kèm sẵn **PostgreSQL + pgvector** (lưu tài khoản, mã yêu thích, kho vector RAG) —
  tự khởi tạo bảng lúc backend chạy, không cần thao tác gì thêm.
- Trợ lý RAG cần `GEMINI_API_KEY` trong `.env`; các phần khác chạy được mà không cần key.
- Giao diện: <http://localhost:3010> — mở được từ **điện thoại/máy khác trong LAN**
  bằng `http://<IP-máy-chủ>:3010` (trình duyệt gọi `/api` cùng origin, Nuxt proxy
  sang backend qua mạng nội bộ Docker nên không dính CORS và không phụ thuộc `localhost`)
- Tài liệu API (Swagger): <http://localhost:8010/docs>
- Đổi cổng nếu bị trùng: `WEB_PORT=4000 API_PORT=9000 docker compose up`

## API

| Endpoint | Mô tả |
|---|---|
| `GET /api/health` | Kiểm tra sống |
| `GET /api/stocks/{ticker}` | Phân tích một mã (một phát, chờ tới khi xong) |
| `GET /api/stocks/{ticker}/stream` | Như trên nhưng phát **tiến độ thật** qua SSE |
| `GET /api/stocks/{ticker}/history?range=` | Nến ngày theo khung `1m` · `3m` · `1y` · `3y` |
| `GET /api/stocks/{ticker}/profile` | Hồ sơ: tổng quan, lãnh đạo, cổ đông, công ty con/liên kết |
| `GET /api/stocks/{ticker}/financials?statement=` | Báo cáo `income` · `balance` · `cashflow` (4 kỳ, tỷ đồng) |
| `GET /api/stocks/{ticker}/ratios` | 54 chỉ số kỳ gần nhất, gom nhóm |
| `GET /api/stocks/{ticker}/board` | Bảng giá phiên hiện tại + sổ lệnh 3 mức + khối ngoại |
| `GET /api/stocks/{ticker}/money-flow?range=` | MFI, OBV, KL phiên tăng/giảm theo ngày |
| `GET /api/stocks/{ticker}/stats?range=` | Biên độ, biến động, nhịp giao dịch (tự tính) |
| `GET /api/stocks/{ticker}/news` | Tin công bố + sự kiện doanh nghiệp |
| `GET /api/stocks/{ticker}/corporate-actions` | Cổ tức, phát hành thêm, giao dịch nội bộ |
| `POST /api/stocks/{ticker}/position` | Sổ mua nhiều đợt → nên mua thêm, giữ, hay cắt lỗ |
| `GET /api/screener?group=&sort=&order=` | Danh sách mã theo rổ, sắp xếp theo cột bất kỳ |

Luồng SSE gửi các sự kiện `progress` khi mỗi bước THẬT bắt đầu chạy
(`technical` 10% → `company` 45% → `fundamentals` 55% → `scoring` 90% → `done` 100%),
rồi `result` (hoặc `error`). Phần trăm gắn với bước thật, **không phải đồng hồ đếm giả**.

Tham số của `/api/stocks/{ticker}`:

| Tham số | Mặc định | Ý nghĩa |
|---|---|---|
| `pos`, `mgmt`, `cat` | `1` | 3 tiêu chí **định tính** (0=yếu, 1=trung bình, 2=tốt) — không crawl được, người dùng tự đánh giá |
| `pe_sec`, `pb_fair` | theo ngành | Ghi đè P/E ngành và P/B hợp lý (mặc định là **ước lượng** benchmark) |
| `source` | `auto` | `auto` (CafeF→vnstock) · `vnstock` · `cafef` (chỉ kỹ thuật) |
| `refresh` | `false` | Bỏ qua cache, crawl lại |

```bash
curl "http://localhost:8010/api/stocks/FPT"
curl "http://localhost:8010/api/stocks/VPB?pe_sec=9&pos=2"   # ngân hàng
```

## Tài khoản · Mã theo dõi · Trợ lý RAG

Đăng nhập để **lưu mã yêu thích** và dùng **trợ lý hỏi–đáp** (RAG). Token là
cookie **httpOnly** (JavaScript không đọc được → an toàn hơn trước XSS); mật khẩu
lưu dạng băm **bcrypt**, không bao giờ lưu bản thô.

| Endpoint | Mô tả |
|---|---|
| `POST /api/auth/register` · `login` · `logout` | Đăng ký / đăng nhập / đăng xuất (đặt cookie) |
| `GET /api/auth/me` | Thông tin tài khoản đang đăng nhập |
| `GET · POST /api/watchlist` | Liệt kê / thêm mã theo dõi |
| `PATCH · DELETE /api/watchlist/{id}` | Sửa ghi chú·ngưỡng / bỏ theo dõi |
| `POST /api/chat` | Hỏi trợ lý một câu (RAG) |
| `POST /api/chat/reindex` · `GET /api/chat/status` | Lập chỉ mục lại VN30 + tin / xem trạng thái |

Trang web tương ứng: <http://localhost:3010/dang-nhap> · `/theo-doi` (⭐ mã theo dõi)
· `/tro-ly` (💬 trợ lý). Nút ⭐ nằm ngay trong màn hình phân tích của mỗi mã.

**RAG hoạt động thế nào** (một nguồn sự thật vẫn ở backend):

1. **Lập chỉ mục** — tổng quan rổ VN30 (từ **một** request `price_board`) + tin tức
   từng mã → nhúng bằng Gemini `gemini-embedding-001` (ép 768 chiều) → lưu vào cột
   `vector` của pgvector. Vì nguồn giới hạn **20 request/phút**, luồng mặc định KHÔNG
   gọi `analyze()` cho từng mã (mỗi analyze bắn nhiều request); thêm cờ `--deep` nếu
   muốn kèm điểm số/ROE (chậm hơn, có tự nghỉ khi chạm giới hạn).
2. **Hỏi** — câu hỏi được nhúng → tìm `k` đoạn gần nghĩa nhất (khoảng cách cosine,
   chỉ mục HNSW) → Gemini `gemini-3.6-flash` tổng hợp **chỉ từ ngữ cảnh đó**, kèm
   nguồn để kiểm chứng. Không đủ dữ liệu thì nói thẳng, **không bịa số, không khuyến nghị mua bán**.

**Lập chỉ mục chạy như một JOB NỀN qua Celery** (service `worker` + `redis`), tách
khỏi web process nên không chặn request và sống sót qua restart. Tiến độ ghi vào
bảng `index_jobs`, đọc qua `GET /api/chat/status`. Kích hoạt lần đầu (cần
`GEMINI_API_KEY`) bằng nút trên trang `/tro-ly`, hoặc bằng dòng lệnh:

```bash
docker compose exec backend python -m scripts.reindex          # đẩy job: cả VN30 + tin
docker compose exec backend python -m scripts.reindex FPT VCB  # đẩy job: vài mã cụ thể
docker compose exec backend python -m scripts.reindex --deep   # kèm điểm số/ROE (chậm)
docker compose exec backend python -m scripts.reindex --inline # chạy ngay, không cần worker
docker compose logs -f worker                                   # xem worker xử lý
```

## Danh sách mã — sắp xếp ở MÁY CHỦ

Trang <http://localhost:3010/danh-sach>: chọn rổ (VN30 · VN100 · HNX30 · toàn HOSE),
bấm tiêu đề cột để sắp xếp, bấm một dòng là mở thẳng màn hình phân tích của mã đó.

Sắp xếp chạy ở backend chứ không ở frontend — cùng lý do với mô hình chấm điểm:
hai bản cài đặt ở hai ngôn ngữ sớm muộn cũng lệch nhau. Bấm đổi cột KHÔNG gọi ra
nguồn dữ liệu (cache theo rổ), vì hạn mức tài khoản khách chỉ **20 request/phút**.

Nhãn cột, đơn vị và lời giải thích đều do máy chủ khai báo trong
[`screener.py`](backend/app/services/screener.py); frontend chỉ dựng bảng theo mô tả.

Vài quy tắc trung thực của bảng:

| Tình huống | Cách xử lý |
|---|---|
| Nguồn trả `0` nghĩa là "chưa có số liệu" | Hiện **—**, không hiện `0` |
| Ô trống khi sắp xếp | Luôn xuống cuối bảng, dù tăng hay giảm |
| Phiên chưa khớp lệnh | Cột Giá là **giá tham chiếu**, và lời giải thích của cột nói đúng như vậy |
| Khối ngoại lớn hơn tổng giá trị đã khớp | Bất khả thi ⇒ là số phiên trước → in nghiêng, xám, có dấu `*` |

## Mô hình chấm điểm (100đ · 14 tiêu chí / 4 nhóm)

| Nhóm | Điểm | Tiêu chí |
|---|---|---|
| Nền tảng & tài chính | 45 | Tăng trưởng LN 12 · ROE 10 · Biên LN 8 · D/E 8 · Dòng tiền KD 7 |
| Định giá | 20 | P/E vs ngành 10 · P/B 5 · Cổ tức 5 |
| Kỹ thuật & xu hướng | 20 | Xu hướng giá 8 · Thanh khoản 6 · RSI 6 |
| Định tính & vĩ mô | 15 | Vị thế ngành 6 · Ban lãnh đạo 5 · Catalyst 4 |

Xếp loại: **≥80** xuất sắc · **65–79** tốt · **50–64** trung bình · **<50** yếu.

## Kịch bản xấu nhất — nói thẳng con số

Thay vì nhắc "hãy tự hỏi kịch bản xấu nhất", API tính sẵn và trả về trong
`score.decision.worst_case`:

| Trường | Ý nghĩa |
|---|---|
| `stop_price` | Giá cụ thể khi chạm cắt lỗ −8% (VD: mua 22.55 → cắt tại **20.75**) |
| `account_loss` | Thiệt hại ước tính trên **tổng tài khoản** = quy mô vị thế tối đa × 8% |
| `narrative` | Diễn giải kịch bản kèm số, và cảnh báo lỗi phổ biến (không cắt, bình quân giá xuống) |
| `risks[]` | Tối đa 3 tiêu chí **đang bị 0đ của chính mã đó** + cảnh báo nếu thiếu dữ liệu |

Danh sách rủi ro suy ra từ số liệu thật, không phải lời khuyên chung — ví dụ D/E cao
sẽ nói rõ "lãi suất tăng là chi phí tài chính ăn hết lợi nhuận", thanh khoản mỏng
sẽ nói "khi cần bán gấp có thể không có người mua".

## Sổ mua nhiều đợt — quy tắc cố ý BẤT ĐỐI XỨNG

"Bình quân giá xuống" là hành vi làm cháy tài khoản phổ biến nhất của nhà đầu tư mới.
Một máy tính giá vốn bình quân rất dễ trở thành cái nút hợp thức hóa việc gồng lỗ.
Vì vậy [`position.py`](backend/app/services/position.py) kiểm tra theo thứ tự:

| Điều kiện | Kết luận |
|---|---|
| Giá thủng ngưỡng cắt lỗ (−8% từ **giá vốn bình quân**) | **Cắt lỗ** — bất kể điểm số bao nhiêu |
| Điểm < 50 | **Thoát dần** — luận điểm đầu tư đã sai |
| Điểm ≥ 65 · chưa thủng cắt lỗ · tỷ trọng dưới trần | Được cân nhắc mua thêm, kèm trần tỷ trọng |
| Còn lại | **Giữ nguyên, không mua thêm** |

Khi đang lỗ, công cụ luôn cảnh báo rằng mua thêm **tăng số tiền đang chịu rủi ro** —
giá vốn bình quân giảm chỉ là con số kế toán. Các đợt mua lưu trong **localStorage của
trình duyệt**, máy chủ chỉ nhận để tính rồi trả kết quả, không lưu.

## Giới hạn trung thực

- **Biểu đồ nhiều khung chỉ để xem**, không đổi điểm số: bộ chấm luôn dùng cửa sổ 180 ngày cố định để mọi mã được đo bằng cùng một thước.
- **Bảng chỉ số chỉ có kỳ gần nhất (TTM)**: nguồn trả nhiều kỳ nhưng nhãn năm bị trùng lặp, không thể gán năm chắc chắn — thà một kỳ đúng còn hơn bốn kỳ sai năm.
- **Khuyến nghị & giá mục tiêu trong tab Hồ sơ là của Vietcap (VCI)**, không phải quan điểm của công cụ này. Luôn hiển thị kèm nguồn.
- **Báo cáo tài chính giới hạn 4 kỳ** (giới hạn của bản miễn phí).
- **Không có nguồn cho file PDF báo cáo tài chính** — công cụ hiển thị số liệu có cấu trúc thay thế.
- **Không có dữ liệu áp lực mua/bán cả phiên**: nguồn chỉ trả 100 lệnh khớp cuối (~10 giây), nên tab Dòng tiền dùng chỉ báo theo ngày (MFI/OBV) cộng khối ngoại của **một phiên** — không phải xu hướng nhiều ngày.
- **Tin tức không có URL bài gốc.** Giới hạn nằm ở API gốc của Vietcap, không phải do vnstock: endpoint `iq.vietcap.com.vn/.../v1/news` chỉ trả `newsId`, `newsTitle`, `newsImageUrl`, `publicDate`; endpoint chi tiết theo `newsId` trả `data: null`. Vì vậy mỗi tin kèm link **TÌM KIẾM** theo đúng tiêu đề (CafeF, Google) và mỗi mã kèm link trang **công bố thông tin chính thức** (HOSE) — gắn nhãn rõ là "tìm", không trình bày như bài gốc.
- **3 tiêu chí định tính (15đ) không crawl được** — mặc định "trung bình", chỉnh qua `pos/mgmt/cat`.
- **P/E ngành & P/B hợp lý là ƯỚC LƯỢNG** theo bảng benchmark, không phải số crawl. Ngân hàng nên truyền `pe_sec=9`.
- **Chỉ số không lấy được → 0đ + đánh dấu `available=false`**, hiển thị "N/A". Cố ý bảo thủ: thà chấm thấp còn hơn bịa số. Điểm tổng khi đó sẽ thấp bất thường — đó là do thiếu dữ liệu, không phải cổ phiếu xấu.
- **Không có nguồn lấy lịch sử giá theo LÔ nhiều mã.** `Trading.price_history` có trong vnstock và docstring ghi đúng "for a list of symbols", nhưng cả `VCI` lẫn `KBS` đều ném `NotImplementedError`. Vì vậy danh sách mã dựng từ `price_board` (một request cho cả rổ, 427 mã HOSE hết 0,4 giây) và chỉ có số liệu khớp lệnh khi đang trong phiên.
- **Nguồn TRỘN ĐƠN VỊ trong cùng một bảng giá**: `accumulated_value` là **triệu đồng**, còn `foreign_buy_value`/`foreign_sell_value` là **đồng**. Đã đối chiếu bằng `KL × giá`. Chia nhầm là cả cột hiện `0,0`.
- **Số khối ngoại KHÔNG được nguồn xóa khi mở phiên mới**: đo lúc 08:51 và 09:02 (phiên mới, chưa khớp lệnh) vẫn thấy y nguyên 172,6 tỷ của phiên trước; tới 09:23 mới reset về số thật của hôm nay. Công cụ phát hiện bằng phép thử số học — khối ngoại không thể lớn hơn tổng giá trị đã khớp của chính mã đó — rồi đánh dấu ô đó là số phiên cũ.
- **CafeF chỉ còn endpoint giá** (`pricehistory.ashx`); các endpoint cơ bản đã chết 404 → cơ bản phụ thuộc vnstock.
- Biểu đồ giá vẽ từ **giá thật** (24–784 phiên tùy khung). Không có dữ liệu thì không vẽ — không bịa đường giả.

## Cấu trúc

```
backend/           FastAPI
  app/
    api/routes/    endpoint (stocks · screener · auth · watchlist · chat)
    api/deps.py    lấy người dùng đang đăng nhập
    core/          config · security (bcrypt + JWT)
    db/            engine · session · init_db (tạo pgvector + bảng)
    models/        ORM: user · watchlist · rag_document
    schemas/       DTO (Pydantic)
    services/
      scoring.py   ★ NGUỒN SỰ THẬT của mô hình chấm điểm
      analyzer.py  orchestrator gộp nguồn
      screener.py  danh sách mã + sắp xếp
      providers/   cafef.py · vnstock_source.py
      rag/         gemini · store (pgvector) · indexer · chat
  scripts/         reindex.py — lập chỉ mục RAG từ dòng lệnh
  tests/           khóa hành vi mô hình chấm điểm
frontend/          Nuxt 3 (chỉ render)
  composables/     useAuth · useWatchlist · useChat (chỉ gọi API, không logic)
  pages/           index · danh-sach · dang-nhap · dang-ky · theo-doi · tro-ly
legacy/            bản cũ (HTML tĩnh + CLI Python) — giữ để tham khảo
```

## Phát triển

```bash
docker compose run --rm backend pytest tests -q    # chạy test mô hình
docker compose logs -f backend                     # xem log
```

Khi sửa mô hình chấm điểm: sửa `scoring.py`, cập nhật mốc chuẩn trong
`tests/test_scoring.py`, **không** đụng tới frontend.
