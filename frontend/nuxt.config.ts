// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-01-01',
  devtools: { enabled: false },

  css: ['~/assets/css/main.css'],

  runtimeConfig: {
    // Đích proxy phía máy chủ (không lộ ra trình duyệt).
    // Ghi đè bằng NUXT_API_PROXY_TARGET — trong Docker là http://backend:8000
    apiProxyTarget: 'http://localhost:8010',

    public: {
      // Rỗng = gọi cùng origin qua proxy /api của Nuxt.
      // Nhờ vậy mở từ điện thoại/máy khác trong LAN vẫn chạy và không dính CORS.
      // Chỉ đặt NUXT_PUBLIC_API_BASE khi muốn trỏ thẳng tới backend ở nơi khác.
      apiBase: ''
    }
  },

  //  Đường dẫn cũ (tiếng Việt) → đường dẫn mới (tiếng Anh). Chỉ để tab và
  //  bookmark đang mở không gãy trong lúc chuyển đổi — sản phẩm chưa phát hành
  //  nên xóa khối này sau vài tuần là được.
  routeRules: {
    '/dang-nhap': { redirect: { to: '/login', statusCode: 301 } },
    '/dang-ky': { redirect: { to: '/register', statusCode: 301 } },
    '/phan-tich': { redirect: { to: '/analysis', statusCode: 301 } },
    '/danh-sach': { redirect: { to: '/screener', statusCode: 301 } },
    '/theo-doi': { redirect: { to: '/watchlist', statusCode: 301 } },
    '/danh-muc': { redirect: { to: '/portfolio', statusCode: 301 } },
    '/tro-ly': { redirect: { to: '/assistant', statusCode: 301 } }
  },

  devServer: {
    port: 3010,
    host: '0.0.0.0'
  },

  app: {
    head: {
      //  Sơn nền tối ngay trên thẻ <html> → paint đầu tiên đã tối, không lóe
      //  trắng trong lúc CSS ngoài đang tải (rõ nhất ở dev, nơi CSS tách nhiều file).
      htmlAttrs: { lang: 'vi', style: 'background:#070b16' },
      title: 'Phân Tích Mã — công cụ phân tích cổ phiếu Việt Nam',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        //  Báo trình duyệt dùng bảng màu tối ngay từ đầu (nền UA, thanh cuộn,
        //  ô nhập mặc định) — thêm một lớp chống lóe trắng.
        { name: 'color-scheme', content: 'dark' },
        { name: 'theme-color', content: '#070b16' },
        {
          name: 'description',
          content:
            'Công cụ hỗ trợ tư duy đầu tư: nhập mã cổ phiếu, xem sức khỏe tài chính, định giá, kỹ thuật và điểm tổng hợp.'
        }
      ],
      //  CSS tối thiểu chèn thẳng vào <head>, đứng TRƯỚC mọi stylesheet ngoài.
      style: [
        { innerHTML: 'html{background:#070b16;color-scheme:dark}body{margin:0;background:#070b16;color:#eef3ff}' }
      ]
    }
  },

  typescript: {
    strict: true,
    //  Tắt lúc dev cho nhanh (vue-tsc chạy mỗi lần đổi file rất nặng); CI chạy
    //  `npm run typecheck` mỗi lần push nên vẫn không lọt lỗi kiểu ra nhánh chính.
    typeCheck: false
  }
})
