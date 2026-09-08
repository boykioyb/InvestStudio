import { expect, test } from '@playwright/test'

/**
 * Luồng chính: mở trang chủ → nhập mã → thấy điểm.
 *
 * Đây là thứ mà nếu hỏng thì sản phẩm coi như chết, nhưng lại không có test nào
 * bắt được — mọi test khác đều ở tầng backend.
 */

//  Bỏ qua hướng dẫn 3 bước để nó không che ô nhập mã.
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('phantichma.onboarding.v1', 'test')
  })
})

test('trang chủ hiện câu định vị và ô nhập mã', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveTitle(/Phân Tích Mã/)
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  await expect(page.getByLabel('Mã cổ phiếu').first()).toBeVisible()
})

test('nhập mã → ra trang phân tích và thấy điểm tổng', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('Mã cổ phiếu').first().fill('FPT')
  await page.getByRole('button', { name: /Chấm điểm/ }).first().click()

  await expect(page).toHaveURL(/\/analysis\?symbol=FPT/)
  //  Điểm tổng là con số 0–100; chờ lâu vì lần đầu có thể crawl thật.
  await expect(page.getByText(/\/100/).first()).toBeVisible({ timeout: 60_000 })
})

test('ô tìm mã gợi ý theo tên công ty', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('Mã cổ phiếu').first().fill('vietcom')
  await expect(page.getByRole('option').first()).toContainText('VCB')
})

test('trang cách chấm điểm dựng từ mô hình của backend', async ({ page }) => {
  await page.goto('/scoring')
  await expect(page.getByRole('heading', { name: 'Cách chấm điểm' })).toBeVisible()
  //  14 tiêu chí — con số này do backend trả về, không phải hằng số ở frontend.
  await expect(page.locator('.tieu-chi > li')).toHaveCount(14)
})

test('đường dẫn không tồn tại cho lối đi tiếp thay vì ngõ cụt', async ({ page }) => {
  await page.goto('/khong-co-trang-nay')
  await expect(page.getByText('Không có trang này')).toBeVisible()
  await expect(page.getByLabel('Mã cổ phiếu')).toBeVisible()
})

test('trang pháp lý có ở chân mọi trang', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('link', { name: 'Chính sách quyền riêng tư' }).click()
  await expect(page.getByRole('heading', { name: 'Chính sách quyền riêng tư' })).toBeVisible()
  //  Hai điều Nghị định 13/2023 bắt buộc thông báo.
  await expect(page.getByText(/nội dung hội thoại với trợ lý/i).first()).toBeVisible()
  await expect(page.getByText(/đặc điểm thiết bị/i).first()).toBeVisible()
})
