// background.js — service worker (MV3).
// Nhận yêu cầu "đồng bộ" từ collector.js, gọi API danh mục TCBS bằng token đã bắt,
// map về shape gọn, rồi POST sang InvestStudio. Chạy ở background nên tránh được
// vướng CORS khi gọi sang localhost/domain InvestStudio (đã khai trong host_permissions).

const LOGS = "tcb_logs";

//  Nhật ký vòng (giữ 50 dòng gần nhất) để dev theo dõi trong trang Cài đặt.
async function logEvent(entry) {
  try {
    const cur = (await chrome.storage.local.get(LOGS))[LOGS] || [];
    cur.unshift(Object.assign({ t: Date.now() }, entry));
    await chrome.storage.local.set({ [LOGS]: cur.slice(0, 50) });
  } catch (_) {}
}

const TCBS_SE = (custody, account) =>
  `https://apiext.tcbs.com.vn/hft-krema/v1/customers/${encodeURIComponent(custody)}/se?secTypeName=STOCK` +
  (account ? `&accountNo=${encodeURIComponent(account)}` : "");

//  Lãi/lỗ ĐÃ THỰC HIỆN cả danh mục (acctno=ALL). Lấy khoảng rộng để gộp trọn đời.
const TCBS_GAINLOSS = () => {
  const today = new Date().toISOString().slice(0, 10);
  return `https://apiextaws.tcbs.com.vn/tcbs-hfc-data/v2/pngin/portfolio_gainloss` +
    `?acctno=ALL&fromDate=2000-01-01&toDate=${today}`;
};

//  Lịch sử khớp lệnh (từng đợt) theo mã. txdate dạng DD-MM-YYYY, cú pháp lọc lạ
//  của TCBS: "gte:.. and lte:..".
const dmy = (d) => `${String(d.getDate()).padStart(2, "0")}-${String(d.getMonth() + 1).padStart(2, "0")}-${d.getFullYear()}`;
const TCBS_ORDERHIST = (account, symbol, fromD, toD, page) => {
  const tx = encodeURIComponent(`gte:${fromD} and lte:${toD}`);
  const ex = encodeURIComponent("eq:NB or eq:NS or eq:SS or eq:BC or eq:MS");
  return `https://apiextaws.tcbs.com.vn/tcbs-hfc-data/v1/trans-hist/${encodeURIComponent(account)}/orderHistories` +
    `?txdate=${tx}&orStatus=4,7&symbol=${encodeURIComponent(symbol)}&execType=${ex}&pageSize=100&pageIndex=${page}`;
};

//  Lấy từng đợt khớp cho các mã đang giữ (3 năm gần nhất). Lỗi 1 mã không chặn cả.
async function fetchLots({ token, account, tickers }) {
  if (!account || !tickers || !tickers.length) return [];
  const now = new Date();
  const from = new Date(now); from.setFullYear(from.getFullYear() - 3);
  const fromD = dmy(from), toD = dmy(now);
  const out = [];
  for (const t of tickers) {
    for (let page = 1; page <= 5; page++) {
      let res;
      try { res = await fetch(TCBS_ORDERHIST(account, t, fromD, toD, page), { headers: { Authorization: token } }); }
      catch (_) { break; }
      if (!res.ok) break;
      const data = await res.json();
      const rows = (data && data.data) || [];
      for (const r of rows) {
        const qty = Number(r.execQtty) || 0, price = Number(r.matchPrice) || 0;
        if (qty <= 0 || price <= 0) continue;
        const ex = String(r.execType || "");
        const isSell = ex.slice(-1) === "S" || Number(r.taxSellAmout) > 0;
        out.push({
          ticker: r.symbol, side: isSell ? "sell" : "buy", qty, price,
          fee: Number(r.feeAcr) || 0, tax: Number(r.taxSellAmout) || 0,
          txdate: String(r.txdate || "").slice(0, 10), orderId: String(r.orderID || ""),
        });
      }
      if (rows.length < 100) break;
    }
  }
  return out;
}

// map 1 dòng chứng khoán TCBS -> holding gọn cho InvestStudio
const toHolding = (s) => ({
  ticker: s.symbol,
  qty: s.totalQtty,               // tổng số lượng đang giữ
  available: s.availableTrading,  // số bán được ngay
  avgPrice: s.costPrice,          // giá vốn bình quân
  marketPrice: s.currentPrice,    // giá thị trường hiện tại
});

async function fetchHoldings({ token, custody, account }) {
  if (!token) throw new Error("Chưa bắt được token TCBS. Hãy bấm quanh trang TCInvest (mở Tài sản) rồi thử lại.");
  if (!custody) throw new Error("Chưa xác định được số lưu ký. Mở trang Tài sản để trang tự gọi API.");
  const res = await fetch(TCBS_SE(custody, account), { headers: { Authorization: token } });
  if (!res.ok) throw new Error(`TCBS trả HTTP ${res.status} (token có thể đã hết hạn — thao tác lại trên TCInvest).`);
  const data = await res.json();
  return (data.stock || []).map(toHolding);
}

//  Lãi/lỗ đã thực hiện — không chặn đồng bộ nếu lỗi (chỉ là dữ liệu bổ sung).
async function fetchRealized({ token }) {
  try {
    const res = await fetch(TCBS_GAINLOSS(), { headers: { Authorization: token } });
    if (!res.ok) return [];
    const data = await res.json();
    const rows = (data && data.response && data.response.data) || [];
    return rows.map((r) => ({
      ticker: r.symbol,
      actualPnl: r.actualPnl,
      sellQtty: r.sellQtty,
      buyQtty: r.buyQtty,
    })).filter((r) => r.ticker);
  } catch (_) {
    return [];
  }
}

async function importToInvestStudio({ apiBase, investToken, account, holdings, realized }) {
  const base = String(apiBase || "").replace(/\/+$/, "");
  const headers = { "Content-Type": "application/json" };
  if (investToken) headers["Authorization"] = /^Bearer/i.test(investToken) ? investToken : `Bearer ${investToken}`;
  const res = await fetch(`${base}/api/portfolio/import`, {
    method: "POST",
    headers,
    body: JSON.stringify({ source: "TCBS", account, holdings, realized: realized || [] }),
  });
  const text = await res.text();
  return { ok: res.ok, status: res.status, body: text.slice(0, 800) };
}

async function importLotsToInvestStudio({ apiBase, investToken, account, lots }) {
  const base = String(apiBase || "").replace(/\/+$/, "");
  const headers = { "Content-Type": "application/json" };
  if (investToken) headers["Authorization"] = /^Bearer/i.test(investToken) ? investToken : `Bearer ${investToken}`;
  const res = await fetch(`${base}/api/portfolio/import-lots`, {
    method: "POST",
    headers,
    body: JSON.stringify({ source: "TCBS", account, lots: lots || [] }),
  });
  const text = await res.text();
  return { ok: res.ok, status: res.status, body: text.slice(0, 400) };
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  //  Content script không gọi được openOptionsPage → nhờ background mở giúp.
  if (msg && msg.type === "open-options") {
    if (chrome.runtime.openOptionsPage) chrome.runtime.openOptionsPage();
    else chrome.tabs.create({ url: chrome.runtime.getURL("options.html") });
    return;
  }
  if (!msg || msg.type !== "tcb-sync") return;
  (async () => {
    const base = String(msg.apiBase || "").replace(/\/+$/, "");
    try {
      const holdings = await fetchHoldings(msg);
      const realized = await fetchRealized(msg);
      if (!base) {
        await logEvent({ event: "sync", ok: false, note: "chưa đặt URL InvestStudio",
          custody: msg.custody, account: msg.account, holdings: holdings.length, realized: realized.length });
        sendResponse({ ok: true, imported: false, holdings, realized, note: "Chưa cấu hình URL InvestStudio — chỉ lấy danh mục để xem." });
        return;
      }
      const imp = await importToInvestStudio({ ...msg, holdings, realized });
      await logEvent({
        event: "sync", ok: imp.ok, url: `${base}/api/portfolio/import`,
        status: imp.status, custody: msg.custody, account: msg.account,
        holdings: holdings.length, realized: realized.length,
        hasToken: !!msg.investToken, resp: imp.body,
      });

      //  Đồng bộ thêm TỪNG ĐỢT KHỚP (cho 'Vị thế của tôi') — không chặn nếu lỗi.
      let lots = [];
      let lotsRes = null;
      try {
        const tickers = [...new Set(holdings.map((h) => h.ticker))];
        lots = await fetchLots({ token: msg.token, account: msg.account, tickers });
        if (lots.length) lotsRes = await importLotsToInvestStudio({ ...msg, lots });
        await logEvent({
          event: "lots", ok: lotsRes ? lotsRes.ok : true, url: `${base}/api/portfolio/import-lots`,
          status: lotsRes ? lotsRes.status : null, account: msg.account, count: lots.length,
          resp: lotsRes ? lotsRes.body : "(không có đợt khớp)",
        });
      } catch (le) {
        await logEvent({ event: "lots", ok: false, error: String(le && le.message ? le.message : le) });
      }

      sendResponse({
        ok: imp.ok, imported: imp.ok, status: imp.status, holdings, realized,
        lots: lots.length, lotsOk: lotsRes ? lotsRes.ok : null, resp: imp.body,
      });
    } catch (e) {
      const err = String(e && e.message ? e.message : e);
      await logEvent({ event: "sync", ok: false, url: base ? `${base}/api/portfolio/import` : "", error: err });
      sendResponse({ ok: false, error: err });
    }
  })();
  return true; // giữ kênh mở cho phản hồi bất đồng bộ
});
