// options.js — đặt URL InvestStudio + (với domain tuỳ chỉnh) xin quyền và đăng ký
// content script tự lấy token trên trang đó.
const CFG = "tcb_config";
const urlEl = document.getElementById("url");
const statusEl = document.getElementById("status");
const tokDot = document.getElementById("tokdot");
const tokInfo = document.getElementById("tokinfo");

const isLocal = (origin) => /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/i.test(origin);

function setStatus(msg, ok) {
  statusEl.textContent = msg;
  statusEl.style.color = ok ? "#16a34a" : "#ef4444";
}

async function load() {
  const cfg = (await chrome.storage.local.get(CFG))[CFG] || {};
  urlEl.value = cfg.apiBase || "http://localhost:3010";
  const has = !!cfg.investToken;
  tokDot.classList.toggle("on", has);
  if (has) {
    const who = cfg.linkedEmail ? `${cfg.linkedEmail}${cfg.linkedName ? " (" + cfg.linkedName + ")" : ""}` : "(không rõ)";
    const when = cfg.tokenAt ? new Date(cfg.tokenAt).toLocaleString("vi-VN") : "";
    tokInfo.textContent = `✓ Đang đồng bộ vào: ${who} · lấy lúc ${when}`;
  } else {
    tokInfo.textContent = "Chưa liên kết tài khoản nào";
  }
  document.getElementById("link").hidden = has;
  document.getElementById("switch").hidden = !has;
  document.getElementById("unlink").hidden = !has;
  const side = document.getElementById("side-link");
  if (side) side.textContent = has ? (cfg.linkedEmail || "Đã liên kết") : "Chưa liên kết";
}

// ── Chuyển mục sidebar ───────────────────────────────────────────────────────
document.querySelectorAll(".nav-item").forEach((btn) => {
  btn.addEventListener("click", () => {
    const sec = btn.getAttribute("data-sec");
    document.querySelectorAll(".nav-item").forEach((b) => b.classList.toggle("on", b === btn));
    document.querySelectorAll("[data-panel]").forEach((p) => { p.hidden = p.getAttribute("data-panel") !== sec; });
  });
});

async function save() {
  let base;
  try {
    base = new URL(urlEl.value.trim()).origin;
  } catch {
    return setStatus("URL không hợp lệ. Ví dụ: http://localhost:3010", false);
  }
  const cfg = (await chrome.storage.local.get(CFG))[CFG] || {};
  cfg.apiBase = base;
  await chrome.storage.local.set({ [CFG]: cfg });

  if (isLocal(base)) {
    //  localhost/127.0.0.1 đã khai trong manifest → content script tự chạy sẵn.
    setStatus("Đã lưu URL. Bấm 'Liên kết tài khoản InvestStudio' bên dưới để liên kết.", true);
    return;
  }

  //  Domain tuỳ chỉnh: xin quyền host + đăng ký content script tự lấy token.
  const pattern = base + "/*";
  let granted = false;
  try {
    granted = await chrome.permissions.request({ origins: [pattern] });
  } catch (e) {
    return setStatus("Không xin được quyền: " + e.message, false);
  }
  if (!granted) return setStatus("Bạn đã từ chối cấp quyền cho " + base, false);

  try {
    await chrome.scripting.unregisterContentScripts({ ids: ["instudio-dyn"] }).catch(() => {});
    await chrome.scripting.registerContentScripts([{
      id: "instudio-dyn",
      matches: [pattern],
      js: ["instudio.js"],
      runAt: "document_idle",
    }]);
  } catch (e) {
    return setStatus("Lưu URL xong nhưng đăng ký script lỗi: " + e.message, false);
  }
  setStatus("Đã lưu + cấp quyền. Mở " + base + " (đã đăng nhập) để token tự lấy.", true);
}

// ── Logs ─────────────────────────────────────────────────────────────────────
const LOGS = "tcb_logs";
const logsEl = document.getElementById("logs");

function fmtLog(e) {
  const t = new Date(e.t || Date.now()).toLocaleTimeString("vi-VN");
  const parts = [t, (e.event || "?").toUpperCase(), e.ok ? "OK" : "LỖI"];
  if (e.status != null) parts.push("HTTP " + e.status);
  if (e.email) parts.push("acc=" + e.email);
  if (e.origin) parts.push(e.origin);
  if (e.url) parts.push(e.url);
  if (e.custody) parts.push("custody=" + e.custody);
  if (e.account) parts.push("acct=" + e.account);
  if (e.holdings != null) parts.push("holdings=" + e.holdings);
  if (e.realized != null) parts.push("realized=" + e.realized);
  if (e.hasToken != null) parts.push("token=" + (e.hasToken ? "có" : "KHÔNG"));
  if (e.note) parts.push("· " + e.note);
  if (e.error) parts.push("· " + e.error);
  let line = parts.join("  ");
  if (e.resp) line += "\n    ↳ " + e.resp;
  return line;
}

async function renderLogs() {
  const logs = (await chrome.storage.local.get(LOGS))[LOGS] || [];
  logsEl.textContent = logs.length ? logs.map(fmtLog).join("\n") : "(chưa có log nào)";
}

document.getElementById("reloadLogs").addEventListener("click", renderLogs);
document.getElementById("clearLogs").addEventListener("click", async () => {
  await chrome.storage.local.set({ [LOGS]: [] });
  renderLogs();
});
document.getElementById("copyLogs").addEventListener("click", async () => {
  const logs = (await chrome.storage.local.get(LOGS))[LOGS] || [];
  await navigator.clipboard.writeText(logs.map(fmtLog).join("\n"));
  setStatus("Đã copy logs.", true);
});

// ── Liên kết tài khoản ───────────────────────────────────────────────────────
function openInvest(path) {
  let base;
  try { base = new URL(urlEl.value.trim()).origin; } catch { base = "http://localhost:3010"; }
  chrome.tabs.create({ url: base + (path || "") });
  return base;
}

async function clearLink() {
  const cfg = (await chrome.storage.local.get(CFG))[CFG] || {};
  delete cfg.investToken; delete cfg.linkedEmail; delete cfg.linkedName; delete cfg.tokenAt;
  await chrome.storage.local.set({ [CFG]: cfg });
}

document.getElementById("link").addEventListener("click", () => {
  const base = openInvest();
  setStatus(`Đã mở ${base}. Đăng nhập → token tự lấy, rồi quay lại đây kiểm tra.`, true);
});

document.getElementById("switch").addEventListener("click", async () => {
  await clearLink();
  const base = openInvest("/login");
  await load();
  setStatus(`Đã bỏ liên kết cũ. Trên tab ${base} vừa mở: ĐĂNG XUẤT rồi đăng nhập tài khoản MỚI.`, true);
});

document.getElementById("unlink").addEventListener("click", async () => {
  await clearLink();
  await load();
  setStatus("Đã huỷ liên kết. Extension sẽ không đồng bộ cho tới khi liên kết lại.", true);
});

document.getElementById("save").addEventListener("click", save);
chrome.storage.onChanged.addListener((ch, area) => {
  if (area !== "local") return;
  if (ch[CFG]) load();
  if (ch[LOGS]) renderLogs();
});
load();
renderLogs();
