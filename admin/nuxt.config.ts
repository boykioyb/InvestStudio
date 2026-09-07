// Khu QUẢN TRỊ — app Nuxt RIÊNG, không dùng chung với trang công khai.
//
// Vì sao tách hẳn:
//  1. Nuxt UI kéo theo Tailwind, mà preflight của Tailwind reset CSS toàn cục —
//     nhét chung sẽ đè vỡ hệ thiết kế tự viết của trang công khai.
//  2. Tách được ở TẦNG MẠNG: admin.<domain> đặt sau danh sách IP cho phép, còn
//     trang công khai vẫn mở. Khu quản trị đọc được dữ liệu của mọi người dùng
//     nên không nên nằm chung bề mặt tấn công.
export default defineNuxtConfig({
  compatibilityDate: '2025-01-01',
  devtools: { enabled: false },

  //  Chạy như SPA (không render phía máy chủ). Lý do: mọi lời gọi API quản trị
  //  đều dựa vào cookie đăng nhập của TRÌNH DUYỆT — render phía máy chủ sẽ gọi
  //  API mà không có cookie đó và luôn nhận 401. Trang quản trị cũng chẳng cần
  //  SEO hay first-paint nhanh, nên SSR chỉ có hại ở đây.
  ssr: false,
  modules: ['@nuxt/ui'],
  css: ['~/assets/css/main.css'],

  runtimeConfig: {
    // Proxy phía máy chủ sang FastAPI (không lộ ra trình duyệt).
    apiProxyTarget: 'http://localhost:8010'
  },

  devServer: { port: 3020, host: '0.0.0.0' },

  app: {
    head: {
      htmlAttrs: { lang: 'vi' },
      title: 'Quản trị — InvestStudio',
      // Khu quản trị KHÔNG được lập chỉ mục tìm kiếm.
      meta: [{ name: 'robots', content: 'noindex, nofollow' }]
    }
  }
})
