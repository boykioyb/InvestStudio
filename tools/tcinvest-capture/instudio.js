// instudio.js — chạy trên CHÍNH trang InvestStudio (localhost hoặc domain đã cấu hình).
// Khi bạn đang đăng nhập, tự gọi /api/portfolio/import-token bằng cookie same-origin
// (cookie httpOnly chỉ đi được khi cùng origin) rồi lưu token vào extension. Nhờ vậy
// bên TCBS không phải dán token thủ công.
(async () => {
  const CFG = "tcb_config";
  const LOGS = "tcb_logs";
  const log = async (entry) => {
    try {
      const cur = (await chrome.storage.local.get(LOGS))[LOGS] || [];
      cur.unshift(Object.assign({ t: Date.now() }, entry));
      await chrome.storage.local.set({ [LOGS]: cur.slice(0, 50) });
    } catch (_) {}
  };
  //  Lấy lại nếu token cũ hơn 5 phút — đủ để đổi tài khoản InvestStudio là token
  //  cập nhật ngay sang tài khoản mới, mà không gọi API mỗi lần điều hướng.
  const REFRESH = 5 * 60 * 1000;

  try {
    const cur = (await chrome.storage.local.get(CFG))[CFG] || {};
    const fresh = cur.investToken && cur.tokenAt && (Date.now() - cur.tokenAt < REFRESH)
      && cur.apiBase === location.origin;
    if (fresh) return;

    const res = await fetch(`${location.origin}/api/portfolio/import-token`, {
      method: "POST",
      credentials: "include",
    });
    if (!res.ok) {
      await log({ event: "token", ok: false, origin: location.origin, status: res.status });
      return; // chưa đăng nhập / chưa build backend → im lặng bỏ qua
    }
    const data = await res.json();
    if (!data || !data.token) return;
    await log({ event: "token", ok: true, origin: location.origin, email: data.email || "" });

    await chrome.storage.local.set({
      [CFG]: Object.assign(cur, {
        apiBase: location.origin,
        investToken: data.token,
        tokenAt: Date.now(),
        linkedEmail: data.email || "",
        linkedName: data.name || "",
      }),
    });
    console.log("%c[InvestStudio Sync] đã liên kết " + (data.email || ""), "color:#16a34a;font-weight:bold");
  } catch (_) {
    /* im lặng: đây chỉ là bước tiện lợi, không được làm phiền trang InvestStudio */
  }
})();
