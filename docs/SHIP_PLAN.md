# Kế hoạch đưa Phân Tích Mã ra người dùng thật (Ship Plan v2)

> Lập 2026-09-07 · bản v2 đào sâu tới mức thi công + bổ sung **khu quản trị `/admin`**.
> Mọi khẳng định đều dẫn `file:dòng` từ mã nguồn hiện tại. Bổ sung cho [`REFACTOR_PLAN.md`](REFACTOR_PLAN.md)
> (bản đó lo *chất lượng mã*, bản này lo *đủ điều kiện ship*).

**Mục lục:** [0. Chẩn đoán](#0) · [1. Rủi ro + cách sửa](#1) · [2. Kiến trúc hạn mức](#2) ·
[3. Khu quản trị /admin](#3) · [4. Tính năng người dùng](#4) · [5. Vận hành](#5) · [6. Lộ trình](#6) · [7. Cần chốt](#7)

---

<a id="0"></a>
## 0. Chẩn đoán: lỗ thủng quota nằm ở đâu?

Bạn nói "trợ lý đang mở all". Đo trên mã nguồn thì **ngược lại một nửa**, và chỗ thủng thật nguy hiểm hơn:

| | Thực tế trong mã | Kết luận |
|---|---|---|
| `/api/chat`, `/api/chat/stream` | Đã bắt đăng nhập + quota 100 lượt/user/ngày — `chat.py:108,110,154,156` | Có rào, nhưng rào yếu (H2, H4) |
| `POST /api/chat/reindex` | Bất kỳ user đăng nhập nào cũng bấm được → job nhúng toàn rổ VN30 + tin — `chat.py:314-317` | 🔴 Bom quota, chưa có vai trò quản trị |
| `GET /api/stocks/{mã}` + `/stream` | **Không đăng nhập, không giới hạn**, mỗi lần phân tích mới **tự đẩy job nhúng Gemini** — `stocks.py:60-70,94,161` | 🔴 **Lỗ chính** |

**Chuỗi tấn công đầy đủ (không cần tài khoản):**

```
GET /api/stocks/AAA?refresh=true
  └─ stocks.py:85  bỏ qua cache vì refresh=true
     └─ analyzer.analyze()      → 3–5 request tới VCI/DNSE (nguồn chặn IP ở ~20 req/phút)
        └─ stocks.py:94 ghi vào _cache  (dict KHÔNG BAO GIỜ dọn → phình RAM)
           └─ stocks.py:69 _index_analysis()
              └─ tasks.py:136 embed_texts()  → 1 lệnh nhúng Gemini, ĂN VÀO QUOTA NGÀY
```

Ba đường phá cache, chỉ một đường bị để ý:

| Đường | Vì sao lọt | Sửa |
|---|---|---|
| `?refresh=true` | Không kiểm tra ai gọi — `stocks.py:79,85` | Chỉ cho user đã đăng nhập |
| `?pe_sec=9.001` rồi `9.002`… | Khóa cache chứa số thực → mỗi giá trị là một khóa mới — `stocks.py:83` | `round(pe_sec, 2)` trước khi tạo khóa |
| Mã lạ (~1600 mã sàn) | Mỗi mã một khóa, cache không có trần | `TTLCache(maxsize=500)` + quota theo IP |

`_cache`, `_history_cache`, `_detail_cache` (`stocks.py:38,39,210`), `highlights.py:53`, `quote.py:27`
đều là dict thường, **không có `maxsize`, không có eviction** → bộ nhớ chỉ tăng, không giảm.

> Tóm tắt: khóa cửa trước (trợ lý) đã có; **cửa sau — phân tích công khai — mở toang và nối thẳng vào quota Gemini.**
>
> **Gemini đang chạy bản miễn phí nên không có hóa đơn — thiệt hại là dạng khác, và vẫn nặng:**
>
> | Cái mất | Vì sao đau |
> |---|---|
> | **Trợ lý chết cả ngày** | Ai đó đốt hết quota lúc 9h sáng → người dùng thật cả ngày còn lại chỉ thấy "trợ lý không phản hồi". Đây là **từ chối dịch vụ**, không phải tiền |
> | **IP máy chủ bị nguồn dữ liệu chặn** | VCI/DNSE chặn ở ~20 request/phút; bị chặn thì **cả web sập**, không riêng trợ lý — nặng hơn mất trợ lý nhiều |
> | **RAM container** | 5 cache dict không giới hạn → phình đến khi bị OOM kill |
> | **Khóa API bị Google hạn chế** | Lưu lượng bất thường kéo dài có thể bị siết thêm; xin lại mất thời gian |

---

<a id="1"></a>
## 1. Rủi ro bảo mật + cách sửa tới mức thi công

Mức: 🔴 chặn ship · 🟠 xong trong 2 tuần đầu · 🟡 nợ có kiểm soát.

### 🔴 H1 — Đường công khai bơm job nhúng Gemini
**Bằng chứng:** `stocks.py:60-70,94,161` · `tasks.py:116-141`
**Sửa:**
```python
# stocks.py — bỏ _index_analysis khỏi request công khai.
# Việc nạp kho RAG chuyển về 2 nguồn có kiểm soát:
#   1) beat "reindex-vn30-daily" (celery_app.py:33) — đã có sẵn
#   2) nút trong /admin cho mã lẻ (audit lại ai bấm)
key = (symbol, pos, mgmt, cat,
       round(pe_sec, 2) if pe_sec else None,      # chặn phá cache bằng số lẻ
       round(pb_fair, 2) if pb_fair else None, source)
_cache = TTLCache(maxsize=500, ttl=settings.cache_ttl_seconds)   # thay dict trần
```
`refresh: bool` → thêm `user = Depends(get_current_user_optional)`; khách gửi `refresh=true` thì **im lặng bỏ qua** (trả cache) chứ không 401 — không phá trải nghiệm.

### 🔴 H2 — Đăng ký mở, không xác minh email
**Bằng chứng:** `auth.py:37-56` · `config.py: rag_daily_quota=100` · `schemas/auth.py:12` (mật khẩu ≥6)
**Sửa:** cột `email_verified_at`; trợ lý + upload yêu cầu đã xác minh; hạ quota mặc định 100 → 20; thêm quota theo IP; mật khẩu ≥10 ký tự.

### 🔴 H3 — `reindex` mở cho mọi user
**Bằng chứng:** `chat.py:314-317`
**Sửa:** `users.role ∈ {user, admin}` + dependency:
```python
# app/api/deps.py
def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Chỉ quản trị viên dùng được chức năng này.")
    return user
```

### 🔴 H4 — Giả mạo IP vượt mọi rào tần suất
**Bằng chứng:** `ratelimit.py:_client_ip` lấy `x-forwarded-for.split(",")[0]` — phần **do client tự ghi**.
**Sửa:** chỉ tin header khi request đến từ proxy của mình, và lấy **hop cuối** (do proxy ghi), không phải hop đầu:
```python
def _client_ip(request):
    peer = request.client.host if request.client else "unknown"
    if peer not in get_settings().trusted_proxies:      # cấu hình được
        return peer                                      # gọi thẳng → dùng IP thật
    chain = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
    return chain[-get_settings().trusted_proxy_hops] if chain else peer
```

### 🔴 H5 — Backend phơi thẳng ra Internet
**Bằng chứng:** `docker-compose.yml` → `ports: "${API_PORT:-8010}:8000"`
**Sửa (prod):** bỏ `ports` của `backend`; chỉ reverse proxy ra ngoài; và
```python
app = FastAPI(..., docs_url=None if settings.env == "prod" else "/docs",
              redoc_url=None, openapi_url=None if settings.env == "prod" else "/openapi.json")
```

### 🔴 H6 — Chưa có cấu hình production
Mật khẩu Postgres `invest/invest`, `APP_COOKIE_SECURE:"false"`, không HTTPS, không security header.
**Sửa:** `docker-compose.prod.yml` + Caddy (HTTPS tự động) + middleware header:
`Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `X-Frame-Options: DENY`, CSP cơ bản.

### 🟠 H7 — `/portfolio/review` công khai, khuếch đại crawl
`portfolio.py:13` không có auth; `schemas/stock.py:533` cho tới **100 mã × 50 đợt/lượt**. → bắt đăng nhập, hạ trần còn 20 mã.

### 🟠 H8 — Upload tin `content_type` của client
`chat.py:260-279` chỉ so `file.content_type` với danh sách trắng, **không đọc byte đầu tệp**; không có hạn mức dung lượng/user.
→ kiểm magic bytes; `nosniff` + `Content-Disposition: attachment` cho PDF; trần 50 MB/user; dọn tệp mồ côi hằng tuần.

### 🟠 H9 — Token 7 ngày, đổi mật khẩu không thu hồi phiên cũ
`config.py: jwt_expire_minutes=10080` · `auth.py:86-95` → thêm `users.token_version`, ký kèm vào JWT, `decode` đối chiếu; đổi mật khẩu/khóa tài khoản → `token_version += 1`.

### 🟠 H10 — Thiếu quên mật khẩu / xóa tài khoản
→ token đặt lại mật khẩu (hạn 30 phút, dùng một lần) + xóa tài khoản theo yêu cầu (Nghị định 13/2023 về bảo vệ dữ liệu cá nhân).

### 🟡 H11 — `GET /chat/stream` là GET nhưng có tác dụng phụ
`chat.py:147-156` tạo hội thoại + trừ quota → dụ bấm link là mất quota. Sửa: `POST /chat/stream-ticket` trả vé dùng-một-lần (TTL 60s), SSE chỉ nhận vé.

### 🟡 H12 — Nhồi lệnh qua tin tức (prompt injection)
Kho RAG nạp tin ngoài (`rag/indexer.py`) rồi ghép vào prompt (`rag/agent.py`) → bọc ngữ cảnh bằng nhãn "DỮ LIỆU, KHÔNG PHẢI CHỈ THỊ", chặn tool gọi ngoài danh sách trắng (đã có `dispatch`), ghi log câu trả lời bất thường để soi ở `/admin`.

### 🟡 H13 — Không log có cấu trúc, không sao lưu
Chỉ có `print()` ra stderr → log JSON + Sentry + `pg_dump` hằng đêm **và một lần thử phục hồi thật**.

**Thuật ngữ:** *quota* = hạn mức lượt gọi · *embedding (nhúng)* = biến văn bản thành vector số để tìm theo ngữ nghĩa · *RAG* = trả lời dựa trên tài liệu tìm được · *SSE* = máy chủ đẩy dữ liệu theo luồng · *magic bytes* = vài byte đầu tệp cho biết định dạng thật · *TOTP* = mã 6 số đổi mỗi 30 giây (Google Authenticator) · *audit log* = nhật ký ai-làm-gì-lúc-nào.

---

<a id="2"></a>
## 2. Kiến trúc hạn mức — "ai được dùng gì"

### 2.1 Ba tầng

| Tầng | Được dùng | Hạn mức | Vì sao |
|---|---|---|---|
| **Khách** | Trang chủ, thị trường, phân tích mã **từ cache** | 30 phân tích/ngày · **0 lượt trợ lý** · không `refresh` · không auto-index | Người lạ thấy giá trị ngay mà không chạm ví |
| **Thành viên** (đã xác minh email) | + Theo dõi, danh mục, trợ lý, đính kèm | **5 lượt trợ lý/ngày** · 100 phân tích/ngày · 10 `refresh`/ngày · 50 MB tệp | Gemini đang chạy bản miễn phí — xem §2.5 |
| **Quản trị** | + `/admin`, reindex, cần gạt khẩn cấp | không giới hạn, **mọi thao tác ghi audit** | Việc tốn kém phải có người chịu trách nhiệm |

### 2.2 Hai van an toàn toàn cục (thiếu là mọi quota per-user đều vô nghĩa)

```
quota:gemini:global:2026-09-07   INCR mỗi lệnh gọi Gemini, chạm trần → tắt trợ lý cả hệ thống
rl:api:<ip>:<phút>               INCR mọi request /api, 120/phút
quota:rag:<user_id>:<ngày>       đã có (ratelimit.py:enforce_daily)
quota:analyze:<ip|user>:<ngày>   mới
```

**Quy tắc mở/đóng khi Redis chết — đang sai ở một chỗ:**

| Loại rào | Redis lỗi thì? | Hiện tại | Đúng |
|---|---|---|---|
| Chống dò mật khẩu | cho qua (fail-open) | ✅ `ratelimit.py:50` | giữ |
| **Quota Gemini / crawl** | **phải chặn (fail-closed)** | ❌ `ratelimit.py:78` đang cho qua | sửa: Redis chết → 503 "trợ lý tạm nghỉ". Redis chết mà vẫn cho gọi = mất trắng quota ngày trong vài phút |

Trả về chuẩn khi chạm hạn mức: HTTP 429 + `Retry-After` + header `X-Quota-Limit` / `X-Quota-Remaining`, thân JSON `{detail, limit, remaining, reset_at}` để frontend hiện "còn 12/20 lượt hôm nay".

### 2.3 Đường đi của số liệu (Redis thực thi — Postgres báo cáo)

```
request → middleware đếm Redis (nhanh, TTL 24h)
        → sự kiện ĐẮT (gọi Gemini, crawl thật) ghi thêm 1 dòng usage_events
beat "usage.flush" mỗi 5 phút: gom Redis + usage_events → usage_daily (bảng tổng hợp)
/admin đọc usage_daily  → biểu đồ nhanh, không quét bảng thô
```
Không ghi DB cho **mọi** request (sẽ thành nút thắt); chỉ ghi cho việc **ăn vào quota có hạn** (Gemini, crawl thật).

### 2.4 Chống lách hạn mức bằng dấu vân tay thiết bị (fingerprint)

**Ý tưởng:** hạn mức không đếm theo *tài khoản*, mà đếm theo **cái nhỏ nhất trong nhiều rổ** — đổi được một
rổ vẫn kẹt ở rổ khác:

```python
# Mọi rổ phải còn chỗ thì mới cho đi tiếp; rổ nào chạm trần thì 429 kèm tên rổ đó.
buckets = [
    ("user", user.id,       5),   # 5 lượt/ngày/tài khoản
    ("fp",   fp_hash,       5),   # 5 lượt/ngày/THIẾT BỊ  ← chặn "đăng ký tài khoản mới"
    ("ip",   client_ip,     8),   # 8 lượt/ngày/IP        ← chặn "đăng nhập nhiều máy"
    ("net",  ip_slash_24,  60),   # nới rộng: nhà mạng VN NAT hàng nghìn người chung IP
]
```

**Cách lấy `fp_hash`** (hai nửa, phải giả mạo được **cả hai** mới lách):

| Nửa | Nguồn | Ghi chú |
|---|---|---|
| Phía trình duyệt | **FingerprintJS v5** (đã đổi sang giấy phép **MIT**, dùng thương mại thoải mái) hoặc **ThumbmarkJS** (MIT) → `visitorId` gửi qua header `X-Device-Id` | Canvas, WebGL, phông chữ, audio, độ phân giải… |
| Phía máy chủ | Cookie `did` **httpOnly có ký** do server cấp lần đầu + `User-Agent` + `Accept-Language` + IP | Không đọc được bằng JavaScript, `curl` tự chế header sẽ thiếu chữ ký |

`fp_hash = sha256(visitorId + did + ua_family + accept_language)` — lưu vào bảng `device_fingerprints` (§3.2).
Request **không kèm** `X-Device-Id` (tắt JS, gọi bằng `curl`) → coi là thiết bị lạ, áp mức khách chặt hơn.

**Sự thật cần biết trước khi tin vào fingerprint** — nó là *ma sát*, không phải *bảo đảm*:

| Cách người dùng lách | Fingerprint bắt được? |
|---|---|
| Tab ẩn danh (incognito) | ✅ vân tay gần như không đổi |
| Xóa cookie / localStorage | ✅ |
| Đổi IP: 4G ↔ WiFi ↔ VPN | ✅ (vẫn cùng thiết bị) |
| Đăng ký email mới | ✅ (rổ `fp` vẫn đếm) |
| Đổi trình duyệt: Chrome → Firefox | ❌ vân tay khác hẳn |
| Brave / Firefox bật chống fingerprint (ngẫu nhiên hóa) | ❌ mỗi lần tải trang một vân tay |
| Trình duyệt chống phát hiện (Multilogin, Dolphin…) | ❌ |
| Máy khác / điện thoại khác | ❌ |
| Hai người **cùng đời máy, cùng iOS, cùng Safari** | ⚠️ **trùng vân tay → chặn nhầm người vô tội** |

→ Chặn được phần lớn kiểu "tiện tay lách" (ẩn danh, xóa cookie, đổi IP, đăng ký lại), **không** chặn được
người quyết tâm. Vì vậy nó **không thay thế** trần toàn cục fail-closed ở §2.2 — ghép cả hai thì kẻ quyết tâm
cũng chỉ tiêu tới đúng cái trần bạn đặt.

**Thang leo thang thay vì chặn cứng** (giảm rủi ro chặn nhầm ⚠️ ở dòng cuối bảng trên):

| Tín hiệu | Phản ứng |
|---|---|
| Vân tay mới + email dùng-một-lần | Bắt xác minh email trước khi được hỏi trợ lý |
| ≥3 tài khoản cùng một vân tay trong 24h | Hiện CAPTCHA khi đăng ký từ thiết bị đó |
| ≥5 tài khoản cùng vân tay | Chặn tạo tài khoản mới từ vân tay đó; các tài khoản cũ vẫn dùng được |
| Vân tay đã bị admin đánh dấu | Chặn thẳng, kèm lời nhắn liên hệ hỗ trợ (phòng khi chặn nhầm) |

> ⚠️ **Vân tay thiết bị là dữ liệu cá nhân** theo Nghị định 13/2023 — chính sách quyền riêng tư phải nêu rõ
> "chúng tôi thu thập đặc điểm thiết bị để chống lạm dụng hạn mức". Một câu, nhưng thiếu là sai luật.

### 2.5 Ràng buộc thật của Gemini bản miễn phí — nút thắt là RPM, không phải hạn mức người dùng

> **Không có hóa đơn ⇒ không cần theo dõi tiền.** Cả bản kế hoạch này đã bỏ mọi thứ liên quan đến chi phí
> (cột `cost_usd`, đơn giá token, trần USD). Thứ duy nhất cần canh là **quota còn lại trong ngày** — vì hết
> quota là trợ lý **im hẳn cho tất cả mọi người**, không có đường mua thêm như khi trả phí. Nghịch lý là:
> **chạy bản miễn phí khiến việc chặn lạm dụng QUAN TRỌNG HƠN, không phải ít hơn** — trả phí thì bị lạm dụng
> chỉ tốn thêm tiền, còn miễn phí thì bị lạm dụng là **mất dịch vụ**, không mua lại được.

Bản miễn phí giới hạn theo **cả hai chiều**: số request/phút (RPM) và số request/ngày (RPD). Với dòng Flash,
mức thường gặp là **~10–15 RPM** và **~1.500 RPD**, nhưng Google **không còn công bố bảng cố định** — con số
đúng là con số hiện trong AI Studio của chính dự án bạn. **Việc đầu tiên: mở AI Studio đọc quota thật rồi
điền vào `app_settings`.**

**Một "lượt hỏi" KHÔNG phải một request.** Trợ lý đang chạy vòng lặp agent với
`rag_agent_max_steps = 5` (`config.py`):

```
1 lượt hỏi = 1 lệnh nhúng câu hỏi (embed)
           + tối đa 5 vòng gọi model (mỗi vòng model chọn 1 công cụ)
           + 1 lần tổng hợp câu trả lời
           ≈ 3–7 request Gemini
```

Vậy 5 lượt/người/ngày ≈ **15–35 request/người/ngày**. Với trần ~1.500 RPD:

| Kịch bản | Sức chứa/ngày |
|---|---|
| Xấu nhất (7 request/lượt) | **~42 người** dùng hết 5 lượt |
| Trung bình (4 request/lượt) | **~75 người** |
| Nếu hạ `rag_agent_max_steps` 5 → **3** | **~100–120 người** |

**Nhưng RPM mới là thứ làm hỏng trải nghiệm trước:** một câu hỏi bắn 3–7 request liên tiếp trong ~10 giây,
nên chỉ cần **2–3 người hỏi cùng lúc** là chạm 10–15 RPM → Google trả 429 → người dùng thấy "trợ lý không
phản hồi" dù hạn mức ngày còn nguyên. Bắt buộc phải có:

1. **Hàng đợi + giới hạn đồng thời**: semaphore Redis cho phép tối đa 1–2 câu hỏi chạy cùng lúc; người thứ 3
   thấy "đang có 2 người hỏi trước bạn…" thay vì lỗi.
2. **Thử lại có giãn cách** khi Google trả 429 (1s → 2s → 4s), tối đa 3 lần.
3. **Đếm theo request Gemini thật**, không đếm theo "lượt hỏi" — biến `quota:gemini:global:<ngày>` ở §2.2 tăng
   ở **tầng `rag/gemini.py`**, nơi mọi lệnh gọi đều đi qua, chứ không tăng ở tầng route.
4. **Hạ `rag_agent_max_steps` 5 → 3** và giảm `rag_history_turns` 6 → 4 (ít lượt lịch sử = ít token = ít TPM).

**Cấu hình đổi theo quyết định này** (`core/config.py`):

| Biến | Cũ | Mới |
|---|---|---|
| `rag_daily_quota` | 100 | **5** |
| `rag_agent_max_steps` | 5 | **3** |
| `rag_history_turns` | 6 | 4 |
| *(mới)* `gemini_daily_call_cap` | — | đọc từ AI Studio, ví dụ 1.400 (chừa 100 cho job nền) |
| *(mới)* `gemini_max_concurrent` | — | 2 |

**Ba mức khi quota cạn dần** — hạ cấp mềm, không sập thẳng:

| Mức | Ngưỡng | Hành vi |
|---|---|---|
| 🟢 Bình thường | < 70% RPD | Agent đầy đủ, 3 vòng gọi công cụ |
| 🟡 Tiết kiệm | 70–90% | Tự tắt agent → lui về **RAG một nhịp** (tìm ngữ cảnh → trả lời): 1 request thay vì 3–7, rẻ hơn ~4 lần. Cờ `rag_agent_enabled` đã có sẵn (`config.py`) |
| 🔴 Cạn | > 90% | Chỉ user đã hỏi trong ngày mới được hỏi tiếp; người mới thấy "trợ lý đã hết lượt hôm nay, quay lại sau 0h" — **nói thật thay vì báo lỗi kỹ thuật** |

Việc **chừa lại quota cho job nền** rất quan trọng: lịch `reindex-vn30-daily` chạy 8h sáng (`celery_app.py:33`)
nhúng cả rổ VN30 — nếu người dùng đã đốt sạch quota từ hôm trước hoặc sáng sớm, job này chết lặng và kho RAG
đứng yên, trợ lý bắt đầu trả lời bằng dữ liệu cũ mà không ai biết. Trang **Trợ lý** trong `/admin` phải hiện
"tuổi dữ liệu" để phát hiện chuyện đó.

---

<a id="3"></a>
## 3. Khu quản trị `/admin` — đặc tả đầy đủ

### 3.1 Nền giao diện: Nuxt UI v4 (miễn phí, MIT)

Từ Nuxt UI v4, toàn bộ 125+ component (gồm phần Pro trước đây) đã **mở nguồn theo giấy phép MIT**, và
mẫu **Nuxt Dashboard Template** (sidebar thu gọn, command palette, sáng/tối, phím tắt) dùng được miễn phí
— `nuxt-ui-templates/dashboard`. Không còn chi phí bản quyền như bản Pro cũ.

**Rủi ro tích hợp cần biết trước:** app hiện tại **không dùng Tailwind** (`package.json` chỉ có
`lucide-vue-next`, `marked`), giao diện chạy trên hệ token tự viết trong `assets/css/main.css`
(`--accent/--panel/--line/--good/--bad`). Nạp `@nuxt/ui` sẽ kéo theo Tailwind v4 + `@nuxtjs/color-mode`,
mà **preflight của Tailwind reset toàn cục** → nguy cơ đè vỡ giao diện công khai (đúng kiểu va chạm class
đã gặp ở component redesign).

| Phương án | Cách làm | Ưu | Nhược |
|---|---|---|---|
| **A. Cùng app** | `/admin/*` + `layouts/admin.vue`, thêm `@nuxt/ui` | 1 lần deploy, dùng chung `useAuth` | Tailwind preflight đụng CSS công khai; build nặng thêm cho mọi trang |
| **B. App riêng** ⭐ | Thư mục `admin/` clone từ template, chạy cổng riêng, reverse proxy `admin.<domain>` | CSS cách ly hoàn toàn; **chặn được ở tầng mạng** (danh sách IP cho phép); nâng cấp độc lập | Thêm 1 đơn vị deploy; cookie phải đặt `domain=.<domain>` (thêm `APP_COOKIE_DOMAIN`) |

→ **ĐÃ CHỐT: phương án B** — app riêng tại `admin.<domain>`, cách ly CSS *và* cách ly bảo mật cùng lúc.

Việc phát sinh theo quyết định này:
- Thêm `APP_COOKIE_DOMAIN=.<domain>` để cookie đăng nhập dùng được ở cả hai tên miền con (`auth.py:_set_auth_cookie`).
- Thêm `admin.<domain>` vào `APP_CORS_ORIGINS`, và giữ `allow_credentials=True` (`main.py:57`).
- Reverse proxy: `admin.<domain>` có **danh sách IP cho phép** riêng; `<domain>` mở công cộng.
- Thêm service `admin` vào `docker-compose.prod.yml` (Nuxt riêng, không publish cổng, chỉ proxy vào).

### 3.2 Mô hình dữ liệu mới (5 migration)

`0005_admin_users` — mở rộng `users` (`models/user.py:20`):

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `role` | `varchar(16)` mặc định `user` | `user` · `admin` |
| `status` | `varchar(16)` mặc định `active` | `active` · `suspended` (khóa) · `deleted` |
| `email_verified_at` | `timestamptz null` | Chưa xác minh → không dùng trợ lý |
| `token_version` | `int` mặc định 0 | Tăng lên là mọi phiên cũ chết (H9) |
| `plan` | `varchar(16)` mặc định `free` | Chỗ móc sẵn cho gói trả phí |
| `quota_overrides` | `jsonb` | Nới/siết hạn mức cho riêng một người |
| `last_login_at`, `last_ip` | | Phục vụ điều tra lạm dụng |
| `totp_secret` | `varchar(64) null` | 2 lớp cho admin |

`0006_usage`:
- `usage_events(id, at, user_id null, ip, fp_hash, kind, ticker, provider, tokens_in, tokens_out, latency_ms, status)` — `kind ∈ analyze|chat|embed|screener|portfolio`, index `(at)`, `(user_id, at)`. **Không có cột tiền** — bản miễn phí không tính phí; token vẫn lưu vì còn trần **TPM** (token/phút).
- `usage_daily(day, kind, user_id null, count, tokens_in, tokens_out, error_count, throttled_count)` — khóa chính `(day, kind, user_id)`.

`0007_audit_settings`:
- `audit_logs(id, at, actor_user_id, actor_ip, action, target_type, target_id, before jsonb, after jsonb, reason)` — **chỉ ghi thêm, không sửa/xóa**.
- `app_settings(key, value jsonb, updated_by, updated_at)` — hạn mức + cần gạt khẩn cấp, đọc qua cache 30 giây.

`0008_provider_health`: `provider_health(at, provider, ok, latency_ms, error)` cho VCI · DNSE · CafeF · Google News · Gemini.

`0009_fingerprints` (theo §2.4):
- `device_fingerprints(fp_hash pk, first_seen, last_seen, ua, accept_language, last_ip, request_count, account_count, blocked bool, blocked_reason, note)`
- `device_accounts(fp_hash, user_id, first_seen)` — khóa chính kép, chính là bảng để **soi cụm tài khoản dùng chung một thiết bị**.

> Mức tiêu thụ Gemini hiện **chưa đo được**: `rag/gemini.py:32,59,156` không đọc `usageMetadata` trong phản hồi.
> Cần bóc `promptTokenCount`/`candidatesTokenCount` — không phải để tính tiền, mà để **biết còn cách trần TPM/RPD bao xa** và cảnh báo trước khi chạm.

### 3.3 API quản trị (`/api/admin/*`, tất cả `Depends(require_admin)` + ghi audit)

| Nhóm | Endpoint | Việc |
|---|---|---|
| Tổng quan | `GET /admin/overview` | Thẻ số + chuỗi thời gian 30 ngày |
| Người dùng | `GET /admin/users?q=&role=&status=&sort=` | Bảng có tìm/lọc/phân trang |
| | `GET /admin/users/{id}` | Hồ sơ + lịch sử dùng + thiết bị/IP |
| | `PATCH /admin/users/{id}` | Đổi `role`/`status`/`plan`/`quota_overrides` |
| | `POST /admin/users/{id}/reset-password` | Gửi link đặt lại |
| | `POST /admin/users/{id}/revoke-sessions` | `token_version += 1` |
| | `DELETE /admin/users/{id}` | Xóa theo yêu cầu (ẩn danh hóa, giữ số liệu tổng hợp) |
| Sử dụng | `GET /admin/usage?from=&to=&group_by=day|kind|user` | Nguồn của mọi biểu đồ |
| | `GET /admin/usage/top?metric=cost|count&limit=20` | Ai/mã nào tốn nhất |
| Trợ lý | `GET /admin/rag/status` · `POST /admin/rag/reindex` (chuyển từ `chat.py:314`) | Kho vector + chạy lại chỉ mục |
| | `GET /admin/rag/documents?ticker=` · `DELETE /admin/rag/documents/{id}` | Xem/dọn tài liệu rác |
| | `GET /admin/chat/stats` | Thống kê lượt hỏi, tỷ lệ lỗi, thời gian trả lời |
| Xem dữ liệu | `GET /admin/users/{id}/conversations` | Toàn bộ cuộc trò chuyện của một người |
| | `GET /admin/conversations/{id}/messages` | **Đầy đủ nội dung** câu hỏi + câu trả lời + trích dẫn |
| | `GET /admin/chat/search?q=&user_id=&from=` | Tìm toàn văn trong mọi câu hỏi/câu trả lời |
| | `GET /admin/attachments?user_id=` · `GET /admin/attachments/{id}` | Danh sách + mở tệp người dùng tải lên |
| | `GET /admin/users/{id}/watchlist` · `/portfolio` · `/notifications` | Mã theo dõi, danh mục, thông báo |
| Job | `GET /admin/jobs` · `POST /admin/jobs/{id}/retry` · `GET /admin/queue` | Celery: đang chạy, thất bại, độ dài hàng đợi |
| Nguồn dữ liệu | `GET /admin/providers` · `POST /admin/providers/{tên}/probe` | Sống/chết, độ trễ, tỷ lệ lỗi |
| Thiết bị | `GET /admin/devices?sort=account_count` | Vân tay thiết bị, số tài khoản dùng chung, lượt dùng |
| | `GET /admin/devices/{fp_hash}` | Chi tiết: các tài khoản, IP, lịch sử dùng |
| | `POST /admin/devices/{fp_hash}/block` · `/unblock` | Chặn/bỏ chặn một thiết bị |
| Cache | `GET /admin/cache` · `DELETE /admin/cache?ticker=` | Xem/xóa cache một mã khi số liệu sai |
| Thông báo | `POST /admin/broadcast` | Gửi thông báo hệ thống tới mọi user |
| Cài đặt | `GET·PUT /admin/settings` | Hạn mức từng tầng, trần RPD/RPM, cần gạt khẩn cấp |
| Nhật ký | `GET /admin/audit?actor=&action=&from=` | Ai làm gì lúc nào |

### 3.4 Các trang dashboard (12 trang)

| Trang | Thành phần chính |
|---|---|
| **`/admin` Tổng quan** | 6 thẻ số: user mới hôm nay · người dùng hoạt động (DAU) · lượt phân tích · lượt hỏi trợ lý · **request Gemini hôm nay / trần RPD** (thanh tiến độ, đỏ khi >80%) · tỷ lệ lỗi 5xx. Biểu đồ đường 30 ngày (lượt dùng theo loại), biểu đồ cột theo giờ hôm nay, bảng "5 sự cố gần nhất", đèn tín hiệu 5 nguồn dữ liệu |
| **Người dùng** | Bảng lọc/sắp xếp; hành động hàng loạt (khóa, đổi quota); trang chi tiết: biểu đồ dùng theo ngày, 20 hoạt động gần nhất, IP, nút khóa/mở/thu hồi phiên/xóa |
| **Sử dụng & hạn mức** | Chọn khoảng ngày; tách theo `kind` (phân tích/trợ lý/nhúng); **top 20 người dùng nhiều nhất**, top 20 mã được tra nhiều nhất, **tỷ lệ trúng cache** — chỉ số quan trọng nhất để kéo dài quota, và số lần bị chặn theo từng rổ hạn mức |
| **Trợ lý (RAG)** | Số tài liệu/mã trong kho vector; tuổi dữ liệu (mã lâu nhất chưa cập nhật); tỷ lệ câu trả lời "không đủ dữ liệu"; nút reindex có xác nhận; danh sách tài liệu lọc theo mã |
| **Hội thoại** | Danh sách mọi cuộc trò chuyện (lọc theo người/mã/ngày/có lỗi); mở ra xem **đầy đủ nội dung** hỏi–đáp, trích dẫn, các bước gọi công cụ và tệp đính kèm; tìm toàn văn; đánh dấu câu trả lời sai để cải thiện prompt |
| **Job & hàng đợi** | Job Celery đang chạy/thất bại (`index_jobs` — `models/rag.py:21`), độ dài hàng đợi Redis, lần chạy gần nhất của 2 lịch beat (`celery_app.py:33-42`), nút chạy lại |
| **Nguồn dữ liệu** | Bảng VCI · DNSE · CafeF · Google News · Gemini: trạng thái, độ trễ p95, tỷ lệ lỗi 24h, lần lỗi gần nhất, nút thử ngay |
| **Thiết bị & chống lạm dụng** | Bảng vân tay xếp theo *số tài khoản dùng chung* (cột này lộ ngay kẻ tạo tài khoản hàng loạt); cụm tài khoản chung thiết bị; IP bất thường; nút chặn/bỏ chặn; biểu đồ số lần chạm hạn mức theo rổ (`user`/`fp`/`ip`) — rổ nào hay chạm nhất cho biết nên siết hay nới chỗ nào |
| **Cache** | Số mục/bộ nhớ ước tính từng cache, xóa theo mã hoặc xóa hết (dùng khi nguồn trả số sai) |
| **Thông báo** | Soạn thông báo hệ thống, chọn nhóm nhận, xem trước, lịch sử đã gửi |
| **Nhật ký kiểm toán** | Dòng thời gian ai-làm-gì, lọc theo người/hành động, xem `before/after` dạng JSON |
| **Cài đặt hệ thống** | Sửa hạn mức từng tầng, trần RPD/RPM đọc từ AI Studio, và **cần gạt khẩn cấp** (§3.6) |

Template đã có sẵn sidebar, command palette (`Ctrl+K`), sáng/tối, bảng có sắp xếp/phân trang và biểu đồ —
phần việc thật là **gắn dữ liệu**, không phải dựng giao diện.

### 3.5 Bảo mật riêng cho khu quản trị

1. **Tách bề mặt**: `admin.<domain>` sau reverse proxy, có **danh sách IP cho phép** (nhà/VPN) — rào ngoài cùng, trước cả đăng nhập.
2. **Bắt buộc 2 lớp (TOTP)** cho mọi tài khoản `role=admin`; không có 2FA thì không cấp được vai trò admin.
3. **Phiên ngắn**: cookie admin sống 2 giờ (không phải 7 ngày như user thường).
4. **Xác thực lại** trước hành động nguy hiểm: xóa user, đổi quota toàn cục, reindex, broadcast.
5. **Ghi audit mọi thao tác ghi**, kèm `before/after`; bảng audit chỉ ghi thêm.
6. **Admin xem được toàn bộ dữ liệu** (quyết định của chủ sản phẩm): email đầy đủ, IP, mã theo dõi, danh mục,
   **nội dung hội thoại với trợ lý**, tệp đính kèm — không có màn che, không cần xin phép. Đổi lại, mỗi lần **đọc dữ liệu
   cá nhân của một người cụ thể** vẫn ghi một dòng `audit_logs` (`action=view_user_data`, `target_id`, thời điểm, IP admin).
   Ghi audit ở đây **không chặn thao tác** — nó là bằng chứng bảo vệ chính bạn khi có tranh chấp ("ai đã xem dữ liệu của
   tôi?"), và là thứ cơ quan quản lý hỏi đầu tiên nếu xảy ra lộ dữ liệu.

   *Hai việc phải làm kèm, không phải để hạn chế quyền mà để hợp lệ hóa nó:*
   - **Chính sách quyền riêng tư phải nói thẳng** rằng đội ngũ vận hành có thể xem nội dung hội thoại và dữ liệu tài khoản
     phục vụ vận hành/hỗ trợ/cải thiện chất lượng — Nghị định 13/2023 yêu cầu thông báo mục đích xử lý dữ liệu trước khi thu thập.
     Nói rõ trong chính sách thì việc admin đọc là hợp lệ; im lặng rồi đọc mới là vấn đề.
   - **Số tài khoản admin giữ ở mức tối thiểu** (1–2), bắt buộc 2FA và danh sách IP cho phép — vì giờ chiếm được một
     tài khoản admin là chiếm toàn bộ dữ liệu người dùng, không còn lớp che nào phía sau.
7. **Rate limit riêng** cho `/api/admin/*` và cảnh báo khi có đăng nhập admin từ IP lạ.

### 3.6 Cần gạt khẩn cấp (chốt chặn cuối khi bị lạm dụng)

Đọc từ `app_settings`, cache 30 giây, bật/tắt ngay trong `/admin` **không cần deploy lại**:

| Cần gạt | Tác dụng |
|---|---|
| `assistant_enabled=false` | Tắt trợ lý toàn hệ thống, hiện thông báo bảo trì |
| `refresh_enabled=false` | Cấm mọi `refresh=true` (ngừng crawl thật) |
| `registration_open=false` | Đóng đăng ký khi thấy bot tạo tài khoản hàng loạt |
| `gemini_daily_call_cap` | Trần **số request Gemini/ngày**, chạm là tự lui về chế độ rẻ hoặc tắt |
| `guest_analyze_limit`, `member_*_limit` | Chỉnh hạn mức tức thời |
| `maintenance_mode` | Chỉ cho phép admin truy cập |

---

<a id="4"></a>
## 4. Tính năng phía người dùng

### 4.1 Chưa rõ — phải chốt trước khi ship

| Câu hỏi | Vì sao chặn | Gợi ý |
|---|---|---|
| Sản phẩm hứa gì trong **một câu**? | 8 trang nhưng không trang nào nói rõ dùng để làm gì | "Nhập mã → biết cổ phiếu khỏe hay yếu trong 30 giây, kèm kịch bản xấu nhất bằng số" |
| Trang đích của người mới? | `/` là trang giới thiệu, `/phan-tich` mới là sản phẩm → người mới lạc | `/` = hero + ô nhập mã, gõ mã vào thẳng phân tích |
| Miễn phí hay trả phí? | Quyết định này định hình toàn bộ §2 | Ship miễn phí có hạn mức; cột `plan` đã móc sẵn |
| Redesign v3 có phải bản chốt? | 40 tệp sửa dở chưa commit | Chốt & commit **trước** khi vào S0 |

### 4.2 Còn thiếu

**Bắt buộc để ship:** quên mật khẩu · xác minh email · xóa tài khoản · trang Điều khoản + Chính sách quyền
riêng tư + miễn trừ "không phải khuyến nghị đầu tư" **hiển thị trên giao diện** (hiện chỉ nằm trong README
và mô tả API) · trang lỗi 404/500 · trạng thái rỗng · màn hình 429 tử tế · hiển thị "còn 12/20 lượt hôm nay".

**Nên có sớm:** email cho cảnh báo giá (hiện `Notification` chỉ hiện trong app — `models/user.py:66`) ·
onboarding 3 bước · trang "Cách chấm điểm" giải thích 14 tiêu chí · ô tìm mã có gợi ý tên công ty ·
phương án mobile cho bảng screener 10+ cột.

**Để sau:** xuất PDF/Excel · so sánh nhiều mã · chia sẻ link phân tích · ứng dụng di động.

---

<a id="5"></a>
## 5. Chất lượng & vận hành

| Hạng mục | Hiện trạng | Việc cần làm |
|---|---|---|
| Test backend | 654 dòng, phủ `scoring`/`screener`/`auth`/`watchlist`/`rag`/`highlights`; **trống** `analyzer`, `position`, `market`, `alerts`, `details`, `portfolio` | Ưu tiên `position._decide` (quy tắc cắt lỗ — sai là mất tiền thật) và `portfolio.review` |
| Test frontend | Không có; `typeCheck: false` (`nuxt.config.ts`) | Bật typecheck sạch + 1 test khói: nhập mã → thấy điểm |
| CI | **Không có** `.github/workflows` | 1 workflow: pytest + typecheck khi push |
| Quan sát | Chỉ `print()` ra stderr | Log JSON + Sentry + `/api/health` mở rộng (DB · Redis · Gemini · nguồn dữ liệu) |
| Sao lưu | Không có | `pg_dump` hằng đêm + **thử phục hồi một lần** trước ship |
| Bí mật | `.env` đã gitignore ✅ | `cookie_secure=true` ở prod tự kích hoạt chốt chặn `main.py:_check_secrets` |

---

<a id="6"></a>
## 6. Lộ trình

```
S0 Chặn thủng quota (2–3n) → S1 Nền tài khoản + chống lách (6–7n) → S2 Admin lõi (5–6n)
   → S3 Admin đầy đủ (5–6n) → S4 Rõ sản phẩm (5–7n) → S5 Vận hành + pháp lý (4–5n) → Beta kín → SHIP
```
Tổng ước tính **27–34 ngày công** (fingerprint +2n, trang Thiết bị +1n). S0 độc lập, làm ngay được.

**S0 — Chặn thủng quota. ✅ ĐÃ XONG (2026-09-07)** — chi tiết & kết quả nghiệm thu: [`S0_DONE.md`](S0_DONE.md).
Gỡ `_index_analysis` khỏi đường công khai · `refresh` yêu cầu đăng nhập · làm tròn
`pe_sec/pb_fair` + `TTLCache(maxsize=500)` · `require_admin` cho reindex · middleware giới hạn IP toàn `/api`
· trần Gemini toàn cục **fail-closed đặt ở `rag/gemini.py`** (đếm request thật) · semaphore `gemini_max_concurrent=2`
+ thử lại có giãn cách · sửa `_client_ip` · **quota trợ lý 100 → 5**, `rag_agent_max_steps` 5 → 3.
*Nghiệm thu:* script bắn 1000 request `?refresh=true` + 50 lần đăng ký → bị chặn, **0 lệnh gọi Gemini phát sinh**;
3 người hỏi cùng lúc → xếp hàng, không ai nhận 429 từ Google.

**S1 — Nền tài khoản + chống lách hạn mức.** Migration `0005` + `0009` · xác minh email · quên mật khẩu ·
`token_version` · mật khẩu ≥10 · xóa tài khoản · magic bytes + hạn mức tệp · **fingerprint §2.4**: plugin
FingerprintJS v5 phía Nuxt, cookie `did` có ký phía server, hạn mức đa rổ `min(user, fp, ip, net)`, thang leo thang.
*Nghiệm thu:* cùng một máy — đăng ký tài khoản thứ 2, mở tab ẩn danh, đổi 4G/WiFi → **vẫn chỉ 5 lượt/ngày**;
đổi sang trình duyệt khác thì lách được (đã biết trước — chặn nốt bằng trần toàn cục).

**S2 — Admin lõi.** Migration `0006/0007` · đo `usageMetadata` của Gemini · pipeline Redis→`usage_daily` ·
`/api/admin/overview|users|usage|settings` · dựng app `admin/` từ template · 3 trang: Tổng quan, Người dùng,
Cài đặt + cần gạt khẩn cấp · 2FA + danh sách IP cho phép.
*Nghiệm thu:* gạt `assistant_enabled=false` trong `/admin` → trợ lý tắt trong ≤30 giây, không cần deploy.

**S3 — Admin đầy đủ.** 9 trang còn lại (Sử dụng, Trợ lý, Hội thoại, Job, Nguồn dữ liệu, Thiết bị, Cache, Thông báo, Nhật ký) ·
migration `0008` · trang **Hội thoại** (xem đầy đủ nội dung, tìm toàn văn) · ghi audit `view_user_data` cho mỗi lần mở dữ liệu của một người.
*Nghiệm thu:* mọi thao tác ghi đều để lại một dòng audit đọc được.

**S4 — Rõ sản phẩm.** Chốt redesign v3 · trang đích + một câu định vị · onboarding · trang "Cách chấm điểm" ·
hiển thị hạn mức còn lại · trạng thái rỗng/lỗi/429 · rà soát mobile · gợi ý tên công ty.
*Nghiệm thu:* 3 người chưa biết dự án tự tra một mã và nói ra kết luận, không cần hỏi.

**S5 — Vận hành + pháp lý.** `docker-compose.prod.yml` (không publish cổng backend, HTTPS, mật khẩu DB ngẫu
nhiên, tắt `/docs`) · CI · test `position`/`portfolio` · Sentry + log JSON · sao lưu & thử phục hồi ·
Điều khoản · Chính sách quyền riêng tư · miễn trừ trách nhiệm.
*Nghiệm thu:* Beta kín 10–20 người 1 tuần, theo dõi **số request Gemini/ngày so với trần** và tỷ lệ 5xx trên `/admin` trước khi mở công khai.

---

<a id="7"></a>
## 7. Cần bạn chốt

✅ **Đã chốt:**
- Admin = **app riêng `admin.<domain>`** (phương án B, §3.1).
- Gemini dùng **bản miễn phí** → trợ lý **5 lượt/người/ngày**, khách 0 lượt; **không theo dõi chi phí, chỉ theo dõi quota** (§2.1, §2.5).
- Chống lách hạn mức bằng **vân tay thiết bị + hạn mức đa rổ** (§2.4).

❓ **Còn lại:**
1. **Mô hình truy cập**: 3 tầng như §2.1, hay bắt đăng nhập cho mọi thứ? — *gợi ý: 3 tầng*
2. **Phạm vi admin bản đầu**: 3 trang lõi (S2) đủ ship, hay làm hết 12 trang rồi mới ship? — *gợi ý: ship sau S2, S3 làm song song beta*
3. **Quota thật của dự án Gemini**: mở AI Studio đọc RPM/RPD hiện tại rồi điền vào `app_settings` — con số này quyết định `gemini_daily_call_cap` (§2.5).
4. **Hạ tầng đích**: VPS tự dựng (Caddy + sao lưu tự làm) hay nền tảng có sẵn (Railway/Fly.io)? Lưu ý: `admin.<domain>` cần thêm bản ghi DNS + chứng chỉ.
5. **Redesign v3**: chốt & commit hay revert trước khi vào S0?
6. **Ngưỡng hạ cấp mềm** (§2.5): 70% quota là tắt agent, 90% là khóa người mới — con số này bạn thấy hợp lý chưa?
