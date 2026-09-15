// interceptor.js — chạy trong "MAIN world" (cùng ngữ cảnh với trang TCInvest).
// Nhiệm vụ:
//  1) Nghe mọi response JSON để tìm endpoint (postMessage rec).
//  2) Bắt header Authorization: Bearer ... để đồng bộ danh mục (postMessage token).
// Token chỉ được chuyển sang collector.js (cùng máy), KHÔNG gửi ra ngoài.
(() => {
  const TAG = "__TCB_CAP__";
  const MAX = 30000;

  const post = (payload) => {
    try { window.postMessage(Object.assign({ source: TAG }, payload), "*"); } catch (_) {}
  };

  // đọc Authorization từ nhiều kiểu headers khác nhau
  const readAuth = (h) => {
    if (!h) return null;
    try {
      if (typeof Headers !== "undefined" && h instanceof Headers) return h.get("Authorization") || h.get("authorization");
      if (Array.isArray(h)) {
        for (const pair of h) if (String(pair[0]).toLowerCase() === "authorization") return pair[1];
        return null;
      }
      for (const k in h) if (k.toLowerCase() === "authorization") return h[k];
    } catch (_) {}
    return null;
  };

  const maybeToken = (auth, url) => {
    if (!auth || typeof auth !== "string") return;
    if (!/^Bearer\s+/i.test(auth)) return;
    if (!/tcbs\.com\.vn/i.test(url || "")) return;
    post({ token: auth });
  };

  // --- vá fetch ---
  const origFetch = window.fetch;
  if (typeof origFetch === "function") {
    window.fetch = async function (...args) {
      const req = args[0];
      const url = typeof req === "string" ? req : (req && req.url) || "";
      try {
        let auth = readAuth(args[1] && args[1].headers);
        if (!auth && req && typeof req === "object" && req.headers) auth = readAuth(req.headers);
        maybeToken(auth, url);
      } catch (_) {}

      const res = await origFetch.apply(this, args);
      try {
        const method = (args[1] && args[1].method) || (req && req.method) || "GET";
        const ct = (res.headers && res.headers.get("content-type")) || "";
        if (ct.includes("json")) {
          res.clone().text().then((body) =>
            post({ rec: { kind: "fetch", url, method: String(method).toUpperCase(), status: res.status, body: (body || "").slice(0, MAX), ts: Date.now() } })
          ).catch(() => {});
        }
      } catch (_) {}
      return res;
    };
  }

  // --- vá XMLHttpRequest ---
  const origOpen = XMLHttpRequest.prototype.open;
  const origSend = XMLHttpRequest.prototype.send;
  const origSetHeader = XMLHttpRequest.prototype.setRequestHeader;

  XMLHttpRequest.prototype.open = function (method, url) {
    this.__cap = { method: String(method || "GET").toUpperCase(), url: url || "" };
    return origOpen.apply(this, arguments);
  };
  XMLHttpRequest.prototype.setRequestHeader = function (name, value) {
    try {
      if (String(name).toLowerCase() === "authorization") maybeToken(value, this.__cap && this.__cap.url);
    } catch (_) {}
    return origSetHeader.apply(this, arguments);
  };
  XMLHttpRequest.prototype.send = function () {
    this.addEventListener("load", () => {
      try {
        const ct = this.getResponseHeader("content-type") || "";
        if (ct.includes("json") && this.__cap) {
          post({ rec: { kind: "xhr", url: this.__cap.url, method: this.__cap.method, status: this.status, body: (this.responseText || "").slice(0, MAX), ts: Date.now() } });
        }
      } catch (_) {}
    });
    return origSend.apply(this, arguments);
  };

  console.log("%c[TCInvest Capture] interceptor đã bật", "color:#16a34a;font-weight:bold");
})();
