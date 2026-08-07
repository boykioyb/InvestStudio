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

  devServer: {
    port: 3010,
    host: '0.0.0.0'
  },

  app: {
    head: {
      htmlAttrs: { lang: 'vi' },
      title: 'Phân tích mã cổ phiếu — InvestStudio',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        {
          name: 'description',
          content:
            'Công cụ hỗ trợ tư duy đầu tư: nhập mã cổ phiếu, xem sức khỏe tài chính, định giá, kỹ thuật và điểm tổng hợp.'
        }
      ]
    }
  },

  typescript: {
    strict: true,
    typeCheck: false
  }
})
