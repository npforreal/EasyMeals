import { test, expect } from "@playwright/test";

/**
 * A8 (Vòng 13) — Hành trình hồi quy lõi một chuỗi: MUA vào tủ (A4) -> TỦ đúng
 * lượng/hạn -> LẬP món (A1/A5 dùng kho hiện có) -> ĂN trừ kho FIFO -> HOÀN TÁC
 * khôi phục đúng nguyên trạng. Snapshot tủ trước khi ăn phải khớp tuyệt đối sau
 * khi hoàn tác (mọi lô, mọi trường remaining).
 */

const EXTRAS = [
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

async function pantrySnapshot(page) {
  return page.evaluate(async () => {
    const storage = await import("/static/js/storage.js");
    const lots = await storage.getPantryLots();
    return lots.map((l) => ({ id: l.id, purchased: l.purchased_quantity, remaining: l.remaining_quantity, unit: l.unit }));
  });
}

test.describe("A8 - Hành trình hồi quy lõi: mua -> tủ -> lập món -> ăn -> hoàn tác", () => {
  test("Mua chỉnh lượng, tủ nhận đúng, ăn trừ kho, hoàn tác khôi phục đúng nguyên trạng", async ({
    page,
  }) => {
    // 1. MUA: mục đi chợ sinh từ thực đơn (source: plan) -> mua 850g thay ước tính 1000g.
    await page.goto("/shopping-list");
    await expect(page).toHaveTitle(/Đi Chợ/);
    await page.evaluate(async () => {
      const storage = await import("/static/js/storage.js");
      const db = await import("/static/js/db.js");
      await db.clearAllPersonalData();
      await storage.addShoppingItem(
        { ingredient_id: "11111111-0001-0000-0000-000000000001", ingredient_name: "Thịt ba chỉ", needed_quantity: "1000", unit: "g" },
        { source: "plan" }
      );
    });
    await page.reload();

    const checkbox = page.locator("#shopping-list-container input[type='checkbox']").first();
    await checkbox.check();
    const qtyInput = page.locator("#shopping-list-container input[type='number']").first();
    await expect(qtyInput).toHaveValue("1000");
    await qtyInput.fill("850");
    await page.locator("#btn-add-to-pantry").click();
    await expect(page.locator("#shopping-list-container")).toContainText("Không có món nào cần mua");

    // 2. TỦ: lot đã mua có lượng thực mua + hạn dùng theo nhóm, đúng 850g.
    const boughtLot = await page.evaluate(async () => {
      const storage = await import("/static/js/storage.js");
      return (await storage.getPantryLots()).find((l) => l.ingredient_name === "Thịt ba chỉ") || null;
    });
    expect(boughtLot).not.toBeNull();
    expect(boughtLot.purchased_quantity).toBe("850");
    expect(boughtLot.remaining_quantity).toBe("850");
    expect(boughtLot.expires_at, "Hạn dùng mặc định theo nhóm nguyên liệu").toMatch(/^\d{4}-\d{2}-\d{2}$/);

    // 3. Bổ sung nguyên liệu như Full Journey để bữa "Đã ăn" không rơi vào hộp thiếu hàng.
    await page.evaluate(async (items) => {
      const storage = await import("/static/js/storage.js");
      for (const item of items) {
        await storage.addPantryLot(item);
      }
    }, EXTRAS);
    await page.goto("/");
    await expect(page.locator("#stock-total")).toContainText("11 nguyên liệu");

    // 4. LẬP MÓN: dùng kho hiện có (A5: FIFO theo lô), sinh thực đơn 3 ngày.
    await page.goto("/planner");
    await expect(page).toHaveTitle(/Kế Hoạch Bữa Ăn/);
    await page.locator("#btn-generate").click({ force: true });
    const mealCards = page.locator(".meal-box");
    await expect(mealCards.first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator("#btn-generate")).toBeEnabled({ timeout: 10000 });

    // 5. ĂN: chọn bữa có món nấu mới (Bữa Trưa) để trừ kho FIFO thực sự.
    const beforeEat = await pantrySnapshot(page);
    const lunchBox = page.locator(".meal-box:has-text('Bữa Trưa')").first();
    await lunchBox.locator("button:has-text('Đánh dấu Đã ăn')").click({ force: true });
    await expect(lunchBox.locator(".badge:has-text('Đã nấu ăn')")).toBeVisible({
      timeout: 5000,
    });
    // Chờ giao dịch IndexedDB commit + re-render: thăm dò cho tới khi có thay đổi lượng còn lại.
    let afterEat = beforeEat;
    for (let i = 0; i < 20; i++) {
      afterEat = await pantrySnapshot(page);
      const byIdEat = new Map(afterEat.map((l) => [l.id, l]));
      const changedNow = beforeEat.some((l) => {
        const cur = byIdEat.get(l.id);
        return cur && cur.remaining !== l.remaining;
      });
      if (changedNow) break;
      await page.waitForTimeout(250);
    }
    const byIdEat = new Map(afterEat.map((l) => [l.id, l]));
    const changed = beforeEat.some((l) => {
      const cur = byIdEat.get(l.id);
      return cur && cur.remaining !== l.remaining;
    });
    expect(changed, "Ăn phải trừ ít nhất một lô trong tủ").toBe(true);

    // 6. HOÀN TÁC: tủ khôi phục tuyệt đối nguyên trạng trước khi ăn.
    await lunchBox.locator("button:has-text('Hoàn tác bữa ăn')").click({ force: true });
    await expect(lunchBox.locator(".badge:has-text('Chưa ăn')")).toBeVisible({
      timeout: 5000,
    });
    // Thăm dò cho tới khi tủ khôi phục nguyên trạng (commit + re-render).
    let afterUndo = [];
    for (let i = 0; i < 20; i++) {
      afterUndo = await pantrySnapshot(page);
      const byIdUndo = new Map(afterUndo.map((l) => [l.id, l]));
      const restored = beforeEat.every((l) => {
        const cur = byIdUndo.get(l.id);
        return cur && `${cur.purchased}/${cur.remaining}/${cur.unit}` === `${l.purchased}/${l.remaining}/${l.unit}`;
      });
      if (restored) break;
      await page.waitForTimeout(250);
    }
    expect(afterUndo.length, "Không được thêm mới lô sau hoàn tác").toBe(beforeEat.length);
    const byIdUndo = new Map(afterUndo.map((l) => [l.id, l]));
    for (const l of beforeEat) {
      const cur = byIdUndo.get(l.id);
      expect(cur, `Lô ${l.id} còn tồn tại sau hoàn tác`).toBeTruthy();
      expect(`${cur.purchased}/${cur.remaining}/${cur.unit}`).toBe(
        `${l.purchased}/${l.remaining}/${l.unit}`
      );
    }
  });
});
