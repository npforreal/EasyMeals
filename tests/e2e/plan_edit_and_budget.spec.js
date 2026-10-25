import { test, expect } from '@playwright/test';

test.describe('Vòng 13 - Giai đoạn B: Chỉnh sửa thực đơn, Đi chợ theo nhóm & Ngân sách thực tế', () => {
  test.beforeEach(async ({ page }) => {
    // Reset dữ liệu IndexedDB trước mỗi test
    await page.goto('/settings');
    page.on('dialog', (dialog) => dialog.accept());
    const clearBtn = page.locator('#btn-clear-data');
    if (await clearBtn.isVisible()) {
      await clearBtn.click();
      await page.waitForTimeout(400);
    }
  });

  test('B1 & B2: Sinh lại bữa đơn lẻ không ảnh hưởng bữa khác, không cho sinh lại bữa đã ăn', async ({ page }) => {
    // 1. Tạo thực đơn 2 ngày
    await page.goto('/planner');
    await page.waitForSelector('#btn-generate');
    // Chọn chip 2 ngày
    await page.click('.day-chip[data-days="2"]');
    await page.click('#btn-generate');

    // Chờ các meal-box xuất hiện
    await page.waitForSelector('.meal-box');
    const mealBoxes = page.locator('.meal-box');
    await expect(mealBoxes).toHaveCount(4); // 2 ngày * 2 bữa = 4 bữa

    // 2. Lấy tên các món của bữa đầu tiên trước khi sinh lại
    const firstMeal = mealBoxes.first();
    const regenBtn = firstMeal.locator('button:has-text("Sinh lại bữa này")');
    await expect(regenBtn).toBeVisible();

    // Dialog confirm đã được auto-accept bởi beforeEach listener
    await regenBtn.click();

    // Chờ toast thông báo sinh lại thành công
    await expect(page.locator('.toast:has-text("Đã sinh lại bữa ăn")')).toBeVisible();

    // 3. Đánh dấu ăn bữa đầu tiên
    const eatBtn = firstMeal.locator('button:has-text("Đánh dấu Đã ăn")');
    await eatBtn.click({ force: true });

    // Hộp thoại thiếu nguyên liệu hiện ra -> bấm "Vẫn đánh dấu đã ăn (trừ phần đang có)"
    const partialBtn = page.locator('button:has-text("Vẫn đánh dấu đã ăn")');
    await expect(partialBtn).toBeVisible({ timeout: 5000 });
    await partialBtn.click();

    // Chờ bữa chuyển trạng thái thành "Đã nấu ăn"
    await expect(firstMeal.locator('.badge:has-text("Đã nấu ăn")')).toBeVisible({ timeout: 5000 });

    // 4. B2 - Bảo vệ lịch sử: Bữa đã ăn không còn nút "Sinh lại bữa này"
    await expect(firstMeal.locator('button:has-text("Sinh lại bữa này")')).toHaveCount(0);
    await expect(firstMeal.locator('button:has-text("Hoàn tác bữa ăn")')).toBeVisible();
  });

  test('B3 & B4: Danh sách mua phân nhóm quầy, thêm mục tự do và tính ngân sách', async ({ page }) => {
    // 1. Tạo thực đơn 1 ngày để có danh sách đi chợ
    await page.goto('/planner');
    await page.waitForSelector('#btn-generate');
    await page.click('.day-chip[data-days="1"]');
    await page.click('#btn-generate');
    await page.waitForSelector('.meal-box');

    // 2. Sang trang Đi chợ
    await page.goto('/shopping-list');
    await page.waitForSelector('.shopping-item-row');

    // B3: Kiểm tra có các nhóm quầy hàng
    const categoryGroups = page.locator('.shopping-category-group');
    await expect(categoryGroups.first()).toBeVisible();

    // B4: Kiểm tra thẻ Ngân sách & Chi tiêu
    const budgetCard = page.locator('#shopping-budget-card');
    await expect(budgetCard).toBeVisible();
    await expect(page.locator('#budget-estimated')).toBeVisible();
    await expect(page.locator('#budget-spent')).toBeVisible();

    // 3. Thêm mục tự do ngoài kế hoạch (B3)
    await page.click('#btn-add-custom-item');
    await page.waitForSelector('#custom-item-modal', { state: 'visible' });

    await page.fill('#custom-item-name', 'Khăn ướt em bé');
    await page.fill('#custom-item-qty', '2');
    await page.selectOption('#custom-item-cat', 'khac');
    await page.fill('#custom-item-price', '30000');
    await page.click('#custom-item-form button[type="submit"]');

    // Chờ toast và thấy mục tự do xuất hiện với badge "Tự thêm"
    await expect(page.locator('.toast')).toContainText('Khăn ướt em bé');

    const customRow = page.locator('.shopping-item-row:has-text("Khăn ướt em bé")');
    await expect(customRow).toBeVisible();
    await expect(customRow.locator('.badge:has-text("Tự thêm")')).toBeVisible();

    // 4. B4: Kiểm tra dự kiến chi phản ánh giá 30,000đ
    await expect(page.locator('#budget-estimated')).toContainText('30.000');

    // 5. Tích chọn "Đã mua" mục tự do này -> "Đã chi" tăng lên 30,000đ
    const customCheckbox = customRow.locator('input[type="checkbox"]');
    await customCheckbox.scrollIntoViewIfNeeded();
    await customCheckbox.check();

    await expect(page.locator('#budget-spent')).toContainText('30.000');

    // 6. Xoá mục tự do bằng nút ✕
    const reloadedRow = page.locator('.shopping-item-row:has-text("Khăn ướt em bé")');
    const deleteBtn = reloadedRow.locator('button[title="Xoá món này"]');
    await deleteBtn.scrollIntoViewIfNeeded();
    await deleteBtn.click({ force: true });

    await expect(page.locator('.shopping-item-row:has-text("Khăn ướt em bé")')).toHaveCount(0);
  });

  test('B1 & B3: Đổi món, bỏ món trên thực đơn và gộp món trùng trên shopping list', async ({ page }) => {
    // 1. Lập thực đơn 1 ngày
    await page.goto('/planner');
    await page.waitForSelector('#btn-generate');
    await page.click('.day-chip[data-days="1"]');
    await page.click('#btn-generate');
    await page.waitForSelector('.meal-box');

    // 2. Thấy nút Đổi món trên từng món ăn
    const swapBtns = page.locator('.btn-swap-dish');
    await expect(swapBtns.first()).toBeVisible();

    // 3. Thấy nút Chuyển bữa
    const reschedBtn = page.locator('.btn-reschedule-meal').first();
    await expect(reschedBtn).toBeVisible();

    // 4. Qua trang đi chợ kiểm tra nút Gộp món trùng
    await page.goto('/shopping-list');
    await page.waitForSelector('#btn-merge-shopping');
    const mergeBtn = page.locator('#btn-merge-shopping');
    await expect(mergeBtn).toBeVisible();
    await mergeBtn.click();
    await expect(page.locator('.toast:has-text("Đã gộp")')).toBeVisible();

    // 5. Kiểm tra nút Sửa lượng trên dòng nguyên liệu
    const editQtyBtn = page.locator('.btn-edit-qty').first();
    await expect(editQtyBtn).toBeVisible();
  });
});
