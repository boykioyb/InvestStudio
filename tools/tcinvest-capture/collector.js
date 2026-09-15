// collector.js — chạy trong "ISOLATED world" (có quyền chrome.*).
// Nhận record + token từ interceptor, che token, gom endpoint, vẽ panel nổi,
// và ĐỒNG BỘ danh mục về InvestStudio (qua background.js).
(() => {
  const TAG = "__TCB_CAP__";
  const KEY = "tcb_captures";
  const CFG = "tcb_config"; // { apiBase, investToken }
  const IDS = "tcb_ids";    // { custody, account } — không nhạy cảm, lưu để tái dùng

  let captures = [];
  //  URL WEB InvestStudio (nơi đăng nhập) — mặc định frontend 3010, KHÔNG phải
  //  backend 8010. Extension gọi /api qua proxy của web là tới backend.
  let cfg = { apiBase: "http://localhost:3010", investToken: "" };
  let ids = { custody: "", account: "" };
  let token = ""; // token TCBS — CHỈ giữ trong bộ nhớ trang, không lưu, không hiển thị

  // --- che thông tin nhạy cảm trước khi lưu/hiển thị ---
  const redact = (s) => {
    if (!s) return s;
    return String(s)
      .replace(/eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{6,}/g, "«TOKEN_ĐÃ_CHE»")
      .replace(/("(?:access_?token|refresh_?token|id_?token|token|otp|password|secret)"\s*:\s*")[^"]*(")/gi, '$1«ĐÃ_CHE»$2');
  };

  const pathOf = (url) => {
    try { return new URL(url, location.origin).pathname; }
    catch (_) { return (url || "").split("?")[0]; }
  };
  const keyOf = (rec) => rec.method + " " + pathOf(rec.url);

  // rút custodyID (VD 105C708320) + accountNo (VD 0001M18951) từ URL quan sát được
  const learnIds = (url) => {
    if (!url) return;
    let m;
    if ((m = url.match(/\/customers\/([0-9A-Za-z]+)\//))) ids.custody = m[1];
    else if ((m = url.match(/[?&]custodyId=([0-9A-Za-z]+)/i))) ids.custody = m[1];
    if ((m = url.match(/\/accounts\/([0-9A-Za-z]+)\//))) ids.account = m[1];
    else if ((m = url.match(/[?&]accountNo=([0-9A-Za-z]+)/i))) ids.account = m[1];
    if (ids.custody || ids.account) chrome.storage.local.set({ [IDS]: ids });
  };

  // --- nạp dữ liệu đã lưu ---
  chrome.storage.local.get([KEY, CFG, IDS], (r) => {
    captures = r[KEY] || [];
    if (r[CFG]) cfg = Object.assign(cfg, r[CFG]);
    if (r[IDS]) ids = Object.assign(ids, r[IDS]);
    render();
  });

  //  Token đồng bộ do instudio.js ghi từ tab InvestStudio → cập nhật chấm xanh ngay.
  chrome.storage.onChanged.addListener((ch, area) => {
    if (area !== "local" || !ch[CFG]) return;
    cfg = Object.assign(cfg, ch[CFG].newValue || {});
    refreshBadges();
  });

  // --- nhận message từ interceptor ---
  window.addEventListener("message", (e) => {
    if (e.source !== window) return;
    const d = e.data;
    if (!d || d.source !== TAG) return;

    if (d.token) { token = d.token; refreshBadges(); return; }

    if (d.rec) {
      const rec = d.rec;
      learnIds(rec.url);
      rec.body = redact(rec.body);
      const k = keyOf(rec);
      const i = captures.findIndex((c) => keyOf(c) === k);
      rec.count = (i >= 0 ? captures[i].count || 1 : 0) + 1;
      if (i >= 0) captures[i] = rec; else captures.push(rec);
      chrome.storage.local.set({ [KEY]: captures });
      render();
    }
  });

  // ---------- UI ----------
  let panel, listEl, filterEl, badge, statusEl, tokenDot, idsLine, instDot, urlLine, linkLine;

  const css = `
  #tcbcap-btn{position:fixed;z-index:2147483647;right:16px;bottom:16px;background:#111827;color:#fff;
    border:1px solid #374151;border-radius:999px;padding:10px 14px;font:600 13px system-ui;cursor:pointer;
    box-shadow:0 6px 20px rgba(0,0,0,.35)}
  #tcbcap-btn b{background:#16a34a;color:#fff;border-radius:999px;padding:1px 7px;margin-left:6px;font-size:12px}
  #tcbcap-panel{position:fixed;z-index:2147483647;right:16px;bottom:64px;width:540px;max-width:calc(100vw - 32px);
    height:min(74vh,680px);background:#0b1220;color:#e5e7eb;border:1px solid #334155;border-radius:12px;
    display:none;flex-direction:column;font:13px/1.45 system-ui;box-shadow:0 12px 40px rgba(0,0,0,.5);overflow:hidden}
  #tcbcap-panel.open{display:flex}
  .tcbcap-sync{padding:10px;border-bottom:1px solid #1f2937;background:#0f172a}
  .tcbcap-sync .row{display:flex;gap:8px;align-items:center;margin-bottom:6px}
  .tcbcap-sync input{flex:1;background:#111827;border:1px solid #374151;color:#e5e7eb;border-radius:8px;padding:7px 10px;font:12px system-ui}
  .tcbcap-sync label{width:96px;font:12px system-ui;color:#94a3b8}
  #tcbcap-do{background:#16a34a;border:1px solid #16a34a;color:#fff;border-radius:8px;padding:8px 12px;cursor:pointer;font:600 13px system-ui;white-space:nowrap}
  #tcbcap-do:disabled{opacity:.5;cursor:not-allowed}
  #tcbcap-opts{background:#1f2937;border:1px solid #374151;color:#e5e7eb;border-radius:8px;padding:8px 12px;cursor:pointer;font:600 13px system-ui;white-space:nowrap}
  #tcbcap-url{font:11px ui-monospace,monospace;color:#94a3b8;word-break:break-all}
  .tcbcap-meta{display:flex;gap:14px;font:11px system-ui;color:#64748b;flex-wrap:wrap;align-items:center}
  .tcbcap-meta .dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:#ef4444;margin-right:4px;vertical-align:middle}
  .tcbcap-meta .dot.on{background:#22c55e}
  #tcbcap-status{font:12px system-ui;margin-top:6px;min-height:16px}
  #tcbcap-head{display:flex;gap:8px;align-items:center;padding:10px;border-bottom:1px solid #1f2937}
  #tcbcap-head input{flex:1;background:#111827;border:1px solid #374151;color:#e5e7eb;border-radius:8px;padding:7px 10px;font:13px system-ui}
  #tcbcap-head button{background:#1f2937;border:1px solid #374151;color:#e5e7eb;border-radius:8px;padding:7px 10px;cursor:pointer;font:12px system-ui;white-space:nowrap}
  #tcbcap-list{overflow:auto;padding:8px;flex:1}
  .tcbcap-row{border:1px solid #1f2937;border-radius:8px;margin-bottom:8px;overflow:hidden}
  .tcbcap-row>summary{list-style:none;cursor:pointer;padding:8px 10px;display:flex;gap:8px;align-items:center}
  .tcbcap-row>summary::-webkit-details-marker{display:none}
  .tcbcap-m{font:700 11px ui-monospace,monospace;padding:1px 6px;border-radius:5px;background:#1e293b}
  .tcbcap-m.GET{color:#38bdf8}.tcbcap-m.POST{color:#f59e0b}
  .tcbcap-p{font:12px ui-monospace,monospace;color:#cbd5e1;word-break:break-all;flex:1}
  .tcbcap-n{font:11px system-ui;color:#64748b}
  .tcbcap-row pre{margin:0;padding:10px;background:#020617;color:#a7f3d0;font:11px/1.5 ui-monospace,monospace;
    white-space:pre-wrap;word-break:break-all;max-height:240px;overflow:auto;border-top:1px solid #1f2937}
  .tcbcap-copy{margin:6px 10px;background:#1f2937;border:1px solid #374151;color:#e5e7eb;border-radius:6px;padding:4px 8px;cursor:pointer;font:11px system-ui}
  #tcbcap-empty{color:#64748b;text-align:center;padding:20px}
  `;

  const ensureUI = () => {
    if (panel) return;
    const style = document.createElement("style");
    style.textContent = css;
    document.documentElement.appendChild(style);

    const btn = document.createElement("button");
    btn.id = "tcbcap-btn";
    btn.innerHTML = 'TCBS <b id="tcbcap-badge">0</b>';
    btn.onclick = () => panel.classList.toggle("open");
    document.documentElement.appendChild(btn);
    badge = btn.querySelector("#tcbcap-badge");

    panel = document.createElement("div");
    panel.id = "tcbcap-panel";
    panel.innerHTML = `
      <div class="tcbcap-sync">
        <div class="tcbcap-meta">
          <span><span id="tcbcap-tokdot" class="dot"></span>token TCBS</span>
          <span><span id="tcbcap-instdot" class="dot"></span>token đồng bộ</span>
          <span id="tcbcap-ids">lưu ký: — · tiểu khoản: —</span>
        </div>
        <div class="tcbcap-meta"><span id="tcbcap-link">Liên kết: (chưa có)</span></div>
        <div class="tcbcap-meta"><span id="tcbcap-url">InvestStudio: (chưa đặt)</span></div>
        <div class="row" style="display:flex;gap:8px;margin-top:8px">
          <button id="tcbcap-do">Đồng bộ danh mục</button>
          <button id="tcbcap-opts">Cài đặt</button>
        </div>
        <div id="tcbcap-status"></div>
      </div>
      <div id="tcbcap-head">
        <input id="tcbcap-filter" placeholder="lọc endpoint: se, portfolio, asset…">
        <button id="tcbcap-copy">Copy tất cả</button>
        <button id="tcbcap-clear">Xoá</button>
      </div>
      <div id="tcbcap-list"></div>`;
    document.documentElement.appendChild(panel);

    listEl = panel.querySelector("#tcbcap-list");
    filterEl = panel.querySelector("#tcbcap-filter");
    statusEl = panel.querySelector("#tcbcap-status");
    tokenDot = panel.querySelector("#tcbcap-tokdot");
    idsLine = panel.querySelector("#tcbcap-ids");
    instDot = panel.querySelector("#tcbcap-instdot");
    urlLine = panel.querySelector("#tcbcap-url");
    linkLine = panel.querySelector("#tcbcap-link");

    panel.querySelector("#tcbcap-opts").onclick = () => chrome.runtime.sendMessage({ type: "open-options" });

    filterEl.oninput = render;
    panel.querySelector("#tcbcap-clear").onclick = () => {
      captures = [];
      chrome.storage.local.set({ [KEY]: captures });
      render();
    };
    panel.querySelector("#tcbcap-copy").onclick = (ev) => {
      const dump = filtered().map((c) => ({ method: c.method, url: c.url, status: c.status, calls: c.count, body: c.body }));
      navigator.clipboard.writeText(JSON.stringify(dump, null, 2)).then(() => {
        ev.target.textContent = "Đã copy ✓";
        setTimeout(() => (ev.target.textContent = "Copy tất cả"), 1500);
      });
    };
    panel.querySelector("#tcbcap-do").onclick = doSync;
    refreshBadges();
  };

  const refreshBadges = () => {
    if (!panel) return;
    tokenDot.classList.toggle("on", !!token);
    instDot.classList.toggle("on", !!cfg.investToken);
    idsLine.textContent = `lưu ký: ${ids.custody || "—"} · tiểu khoản: ${ids.account || "—"}`;
    urlLine.textContent = "InvestStudio: " + (cfg.apiBase || "(chưa đặt — bấm Cài đặt)");
    linkLine.textContent = "Liên kết: " + (cfg.linkedEmail || "(chưa — bấm Cài đặt để liên kết)");
  };

  const setStatus = (msg, color) => {
    if (statusEl) { statusEl.textContent = msg; statusEl.style.color = color || "#94a3b8"; }
  };

  async function doSync() {
    const btn = panel.querySelector("#tcbcap-do");
    //  Đọc cấu hình mới nhất (token đồng bộ do instudio.js ghi từ tab InvestStudio).
    cfg = Object.assign(cfg, (await chrome.storage.local.get(CFG))[CFG] || {});
    refreshBadges();
    if (!token) return setStatus("Chưa bắt được token TCBS — bấm quanh trang (mở Tài sản) rồi thử lại.", "#f59e0b");
    if (!ids.custody) return setStatus("Chưa thấy số lưu ký — mở trang Tài sản để trang tự gọi API.", "#f59e0b");
    if (!cfg.apiBase) return setStatus("Chưa đặt URL InvestStudio — bấm Cài đặt.", "#f59e0b");
    if (!cfg.investToken) return setStatus("Chưa liên kết tài khoản — bấm Cài đặt → Liên kết tài khoản InvestStudio.", "#f59e0b");
    btn.disabled = true;
    setStatus("Đang lấy danh mục & đồng bộ…", "#38bdf8");
    chrome.runtime.sendMessage(
      { type: "tcb-sync", token, custody: ids.custody, account: ids.account, apiBase: cfg.apiBase, investToken: cfg.investToken },
      (res) => {
        btn.disabled = false;
        if (!res) return setStatus("Không nhận được phản hồi từ background.", "#ef4444");
        if (!res.ok) return setStatus("Lỗi: " + (res.error || res.status || "không rõ"), "#ef4444");
        const n = (res.holdings || []).length;
        const lotsTxt = res.lots ? ` · ${res.lots} đợt khớp` : "";
        if (res.imported) setStatus(`✓ Đã đồng bộ ${n} mã${lotsTxt} về InvestStudio.`, "#22c55e");
        else setStatus(`Lấy được ${n} mã. ${res.note || "Chưa cấu hình URL InvestStudio."}`, "#f59e0b");
      }
    );
  }

  const filtered = () => {
    const q = (filterEl && filterEl.value || "").trim().toLowerCase();
    const arr = q ? captures.filter((c) => (c.url + c.body).toLowerCase().includes(q)) : captures.slice();
    return arr.sort((a, b) => b.ts - a.ts);
  };

  const render = () => {
    ensureUI();
    refreshBadges();
    if (badge) badge.textContent = String(captures.length);
    const rows = filtered();
    if (!rows.length) {
      listEl.innerHTML = '<div id="tcbcap-empty">Chưa bắt được gì. Lướt sang trang Tài sản / Danh mục để nó tự ghi.</div>';
      return;
    }
    listEl.innerHTML = "";
    for (const c of rows) {
      const det = document.createElement("details");
      det.className = "tcbcap-row";
      const sum = document.createElement("summary");
      sum.innerHTML =
        `<span class="tcbcap-m ${c.method}">${c.method}</span>` +
        `<span class="tcbcap-p">${pathOf(c.url)}</span>` +
        `<span class="tcbcap-n">×${c.count} · ${c.status}</span>`;
      det.appendChild(sum);

      const copyOne = document.createElement("button");
      copyOne.className = "tcbcap-copy";
      copyOne.textContent = "Copy URL + body";
      copyOne.onclick = () => {
        navigator.clipboard.writeText(`${c.method} ${c.url}\nstatus: ${c.status}\n\n${c.body}`).then(() => {
          copyOne.textContent = "Đã copy ✓"; setTimeout(() => copyOne.textContent = "Copy URL + body", 1500);
        });
      };
      det.appendChild(copyOne);

      const pre = document.createElement("pre");
      let pretty = c.body;
      try { pretty = JSON.stringify(JSON.parse(c.body), null, 2); } catch (_) {}
      pre.textContent = pretty;
      det.appendChild(pre);
      listEl.appendChild(det);
    }
  };
})();
