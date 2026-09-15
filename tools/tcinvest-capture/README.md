# TCInvest Capture → InvestStudio

Extension Chrome (Manifest V3) làm 2 việc trên [tcinvest.tcbs.com.vn](https://tcinvest.tcbs.com.vn/):

1. **Bắt API** — ghi lại mọi response JSON để dò endpoint (panel + ô lọc + copy).
2. **Đồng bộ danh mục** — lấy cổ phiếu đang giữ (số lượng, giá vốn) và đẩy về
   InvestStudio để chấm điểm — bằng cách **mượn token của trang** rồi tự gọi API.

Chỉ dùng cho **tài khoản của chính bạn**. Token TCBS chỉ nằm trong bộ nhớ trang,
**không lưu ra đĩa, không hiển thị, không gửi đi đâu** ngoài chính API TCBS.

## Cài đặt (1 phút)

1. Chrome → `chrome://extensions` → bật **Developer mode**.
2. **Load unpacked** → chọn thư mục `tools/tcinvest-capture/`.
3. (Chạy được cả Edge, Brave, Cốc Cốc.)

## Đồng bộ danh mục về InvestStudio

**Token đồng bộ tự lấy — không phải copy/dán.**

```
Mở InvestStudio (đã đăng nhập)  ──▶ extension TỰ lấy token đồng bộ
Mở TCInvest ▸ Tài sản           ──▶ bấm "Đồng bộ danh mục"
```

Chi tiết:

1. **Cài đặt URL + liên kết tài khoản một lần**: chuột phải icon extension → *Options*
   (hoặc nút **Cài đặt** trong panel TCBS). Nhập **URL InvestStudio** (mặc định
   `http://localhost:3010`) → **Lưu URL**. Với domain khác `localhost`, sẽ hỏi cấp quyền.
2. Bấm **Liên kết tài khoản InvestStudio** → tab InvestStudio mở ra → **đăng nhập** →
   extension tự lấy token (mục "Tài khoản liên kết" hiện `✓ Đang đồng bộ vào: <email>`).
   - **Đổi tài khoản**: bấm *Đổi tài khoản* → đăng xuất & đăng nhập tài khoản khác.
   - **Huỷ liên kết**: dừng đồng bộ cho tới khi liên kết lại.
3. **Trên TCInvest**: đăng nhập, mở **Tài sản** một lần để extension bắt được
   **token TCBS** + **số lưu ký** (2 chấm xanh + dòng URL báo sẵn sàng).
4. Bấm nút **`TCBS`** góc dưới phải → **Đồng bộ danh mục**. Xong.

> Token đồng bộ tự làm mới mỗi ngày khi bạn mở InvestStudio; sống 30 ngày, đổi mật
> khẩu InvestStudio là hết hiệu lực.

## An toàn

- **Token TCBS**: chỉ giữ trong RAM của tab, hết khi đóng tab. Không lưu, không log.
- **Token đồng bộ InvestStudio**: chỉ dùng được cho đúng `POST /api/portfolio/import`
  (không đăng nhập web, không đọc dữ liệu khác được), hết hạn sau 30 ngày, và mất
  hiệu lực ngay khi bạn đổi mật khẩu InvestStudio.
- Extension chỉ **đọc** danh mục, **không đặt lệnh**, không ghi gì lên tài khoản TCBS.

## Cấu trúc

| File | Vai trò |
|---|---|
| `manifest.json` | Khai báo extension, quyền, background + 2 content script |
| `interceptor.js` | MAIN world (tcbs): vá `fetch`/`XHR`, nghe response JSON + bắt Bearer token |
| `collector.js` | ISOLATED world (tcbs): che token, gom endpoint, panel, nút Đồng bộ |
| `background.js` | Gọi `/se` + `portfolio_gainloss` bằng token, map, POST về InvestStudio |
| `instudio.js` | Chạy trên trang InvestStudio: TỰ lấy token đồng bộ (cookie same-origin) |
| `options.html/.js` | Trang Cài đặt URL InvestStudio (+ cấp quyền cho domain tuỳ chỉnh) |

## Endpoint TCBS đang dùng

```
# Cổ phiếu đang giữ (lãi/lỗ chưa thực hiện = currentPrice − costPrice)
GET https://apiext.tcbs.com.vn/hft-krema/v1/customers/{custodyID}/se?secTypeName=STOCK
→ { stock: [ { symbol, totalQtty, availableTrading, costPrice, currentPrice, ... } ] }

# Lãi/lỗ ĐÃ THỰC HIỆN (đã bán) — gộp cả danh mục
GET https://apiextaws.tcbs.com.vn/tcbs-hfc-data/v2/pngin/portfolio_gainloss?acctno=ALL&fromDate=2000-01-01&toDate={today}
→ { response: { data: [ { symbol, actualPnl, buyQtty, sellQtty, buyFee, sellTax, ... } ] } }

# Từng ĐỢT KHỚP (mua/bán) — theo tiểu khoản + mã, để dựng 'Vị thế của tôi'
GET https://apiextaws.tcbs.com.vn/tcbs-hfc-data/v1/trans-hist/{accountNo}/orderHistories
    ?txdate=gte:DD-MM-YYYY and lte:DD-MM-YYYY&orStatus=4,7&symbol=X&execType=eq:NB or eq:NS or ...&pageSize=100&pageIndex=1
→ { data: [ { execType(NB=mua/NS=bán), execQtty, matchPrice, feeAcr, taxSellAmout, txdate, orderID } ] }
```

Extension gửi `holdings[]` + `realized[]` về `/api/portfolio/import`, và `lots[]` về
`/api/portfolio/import-lots`. Trên trang Danh mục có nút **Nhập đợt mua vào Vị thế của tôi**.
