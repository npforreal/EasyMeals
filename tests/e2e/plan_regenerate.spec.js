import { test, expect } from "@playwright/test";

/**
 * A2 (Vòng 13) — Tạo lại kế hoạch an toàn:
 * - Tạo thực đơn trùng ngày với bữa CHƯA ăn -> hộp thoại hai lựa chọn + Huỷ.
 * - "Thay": bữa chưa ăn bị thay; bữa ĐÃ ĂN luôn giữ cùng lịch sử kho.
 * - "Giữ": thực đơn cũ giữ nguyên, chỉ thêm ngày chưa có.
 * - Chống bấm lặp: nút submit bị khoá tới khi lưu xong (KHÔNG có bản ghi trùng theo ngày+bữa).
 */

async function getPlans(page) {
  return page.evaluate(async () => {
    const storage = await import("/static/js/storage.js");
    return storage.getMealPlans();
  });
}

/** Save hoàn tất -> khối `finally` khôi phục nút submit (bỏ khoá chống bấm lặp). */
async function waitForPlanSave(page) {
  await expect(page.locator("#btn-generate")).toBeEnabled({ timeout: 10000 });
}

test.describe("A2 - Tạo lại kế hoạch an toàn", () => {
  test("Hộp thoại giữ/thay khi trùng ngày bữa chưa ăn; bữa đã ăn luôn giữ", async ({
    page,
  }) => {
    await page.goto("/planner");
    await expect(page).toHaveTitle(/Kế Hoạch Bữa Ăn/);

    // Seed tủ như Full Journey để việc "Đã ăn" không rơi vào hộp thoại thiếu nguyên liệu.
    await page.evaluate(async () => {
      const storage = await import("/static/js/storage.js");
      const extras = [
        { ingredient_id: "11111111-0001-0000-0000-000000000009", ingredient_name: "Trứng vịt", quantity: "10", unit: "piece" },
        { ingredient_id: "11111111-0001-0000-0000-000000000026", ingredient_name: "Hành tím", quantity: "100", unit: "g" },
        { ingredient_id: "11111111-0001-0000-0000-000000000003", ingredient_name: "Sườn non heo", quantity: "1000", unit: "g" },
        { ingredient_id: "11111111-0001-0000-0000-000000000011", ingredient_name: "Rau muống", quantity: "1000", unit: "g" },
        { ingredient_id: "11111111-0001-0000-0000-000000000025", ingredient_name: "Tỏi", quantity: "200", unit: "g" },
        { ingredient_id: "11111111-0001-0000-0000-000000000006", ingredient_name: "Cá lóc", quantity: "1000", unit: "g" },
        { ingredient_id: "11111111-0001-0000-0000-000000000015", ingredient_name: "Cà chua", quantity: "500", unit: "g" },
        { ingredient_id: "11111111-0001-0000-0000-000000000021", ingredient_name: "Thơm (Dứa)", quantity: "500", unit: "g" },
        { ingredient_id: "11111111-0001-0000-0000-000000000022", ingredient_name: "Đậu bắp", quantity: "500", unit: "g" },
        { ingredient_id: "11111111-0001-0000-0000-000000000023", ingredient_name: "Giá đỗ", quantity: "500", unit: "g" },
      ];
      for (const item of extras) {
        await storage.addPantryLot(item);
      }
    });

    // 1. Lập thực đơn 3 ngày đầu tiên.
    await page.locator("#btn-generate").click({ force: true });
    await expect(page.locator(".meal-box").first()).toBeVisible({ timeout: 5000 });
    await waitForPlanSave(page);
    const firstCount = await getPlans(page);
    expect(firstCount.length).toBeGreaterThan(0);

    // 2. Đánh dấu bữa đầu -> đã ăn.
    await page.locator("button:has-text('Đánh dấu Đã ăn')").first().click({ force: true });
    await expect(page.locator(".badge:has-text('Đã nấu ăn')").first()).toBeVisible({
      timeout: 5000,
    });
    const eatenBefore = (await getPlans(page)).filter((p) => p.eaten_at).length;
    expect(eatenBefore).toBe(1);
    const plansBeforeRegenerate = await getPlans(page);

    // 3. Tạo lại trùng 3 ngày -> hộp thoại phải xuất hiện; Huỷ không thay đổi gì.
    await page.locator("#btn-generate").click({ force: true });
    const overlay = page.locator("#plan-conflict-overlay");
    await expect(overlay).toBeVisible({ timeout: 5000 });
    await expect(
      overlay.locator("#btn-replace-plans"),
      "Chọn Thay các bữa chưa ăn trong khoảng ngày này"
    ).toBeVisible();
    await expect(overlay.locator("#btn-keep-plans")).toBeVisible();
    await overlay.locator("#btn-cancel-plans").click();
    await expect(overlay).not.toBeVisible({ timeout: 3000 });
    expect(await getPlans(page)).toEqual(plansBeforeRegenerate);

    // 4. Nhánh "Thay": bữa đã ăn vẫn giữ, không có bản ghi trùng (ngày, bữa).
    await page.locator("#btn-generate").click({ force: true });
    await expect(page.locator("#plan-conflict-overlay")).toBeVisible({ timeout: 5000 });
    await page.locator("#btn-replace-plans").click();
    await expect(page.locator("#plan-conflict-overlay")).not.toBeVisible({ timeout: 5000 });
    await waitForPlanSave(page);

    const afterReplace = await getPlans(page);
    // Bữa ĐÃ ĂN được giữ song song với bữa mới cùng khung giờ (lịch sử không bị xoá),
    // nên tính trùng lặp chỉ trên các bữa CHƯA ăn.
    const uneatenKeys = afterReplace
      .filter((p) => !p.eaten_at)
      .map((p) => String(p.planned_for).slice(0, 10) + "|" + p.meal_period);
    expect(new Set(uneatenKeys).size, "Không có bữa chưa ăn nào trùng theo ngày+bữa").toBe(
      uneatenKeys.length
    );
    expect(afterReplace.filter((p) => p.eaten_at).length, "Bữa đã ăn phải còn nguyên").toBe(
      eatenBefore
    );
    await expect(page.locator(".badge:has-text('Đã nấu ăn')").first()).toBeVisible();

    // 5. Nhánh "Giữ": mọi ngày đã được phủ -> không thêm gì, bữa đã ăn vẫn còn.
    await page.locator("#btn-generate").click({ force: true });
    await expect(page.locator("#plan-conflict-overlay")).toBeVisible({ timeout: 5000 });
    await page.locator("#btn-keep-plans").click();
    await expect(page.locator("#plan-conflict-overlay")).not.toBeVisible({ timeout: 5000 });
    await waitForPlanSave(page);

    const afterKeep = await getPlans(page);
    expect(afterKeep.length, "Giữ thực đơn cũ: số bữa không đổi").toBe(afterReplace.length);
    expect(afterKeep.filter((p) => p.eaten_at).length).toBe(eatenBefore);
  });
});
