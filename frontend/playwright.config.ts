import { defineConfig, devices } from '@playwright/test'

/**
 * Test khói cho luồng chính của giao diện.
 *
 * Chạy trên server ĐANG CHẠY (dev hoặc preview) chứ không tự dựng: bộ test này
 * kiểm cả đường đi thật tới backend và nguồn dữ liệu, nên phải chạy trên đúng
 * ngăn xếp đầy đủ. Đổi đích bằng biến môi trường BASE_URL.
 */
export default defineConfig({
  testDir: './tests',
  //  Phân tích một mã có thể mất vài giây vì crawl thật.
  timeout: 90_000,
  expect: { timeout: 20_000 },
  reporter: process.env.CI ? 'github' : 'list',
  retries: process.env.CI ? 1 : 0,
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3010',
    trace: 'retain-on-failure'
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }]
})
