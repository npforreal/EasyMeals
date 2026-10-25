import { test, expect } from "@playwright/test";

test.describe("E2E Planner 1–7 Days Selector & Boundaries", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/planner");
    // Wait for form to initialize
    await page.waitForSelector("#generate-plan-form");
  });

  test("Bộ chọn ngày chỉ có 1–7 và mặc định 3", async ({ page }) => {
    const chips = page.locator("#days-selector .day-chip");
    await expect(chips).toHaveCount(7);

    // Kiểm tra các giá trị 1 đến 7
    for (let i = 1; i <= 7; i++) {
      await expect(chips.nth(i - 1)).toHaveText(`${i}`);
    }

    // Mặc định chọn 3
    const activeChip = page.locator("#days-selector .day-chip.active");
    await expect(activeChip).toHaveText("3");

    const submitBtn = page.locator("#btn-generate");
    await expect(submitBtn).toContainText("3 ngày");
  });

  test("Chọn 7 ngày -> tạo thực đơn ra đủ 7 ngày", async ({ page }) => {
    // Chọn chip 7
    const chip7 = page.locator('#days-selector .day-chip[data-days="7"]');
    await chip7.click();
    await expect(chip7).toHaveClass(/active/);

    const submitBtn = page.locator("#btn-generate");
    await expect(submitBtn).toContainText("7 ngày");

    // Bấm tạo thực đơn
    await submitBtn.click();

    // Chờ danh sách ngày xuất hiện
    const dayCards = page.locator("#plans-container .day-plan-card");
    await expect(dayCards).toHaveCount(7, { timeout: 10000 });
  });

  test("Không thể tạo thực đơn với ngày vượt quá 7 (ví dụ 8 ngày)", async ({ page }) => {
    // Cố tình gán plan-days = 8 trong DOM
    await page.evaluate(() => {
      const input = document.getElementById("plan-days");
      if (input) input.value = "8";
    });

    const submitBtn = page.locator("#btn-generate");
    await submitBtn.click();

    // Khẳng định xuất hiện thông báo lỗi
    const toast = page.locator("#toast-container .toast");
    await expect(toast).toContainText("Số ngày phải từ 1 đến 7 ngày");
  });
});
