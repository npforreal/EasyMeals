import { test, expect } from "@playwright/test";

/**
 * A4 (Vòng 13) — Mua vào tủ chính xác:
 * - Chống thêm trùng khi bấm lặp (nút bị khoá trong suốt quá trình).
 * - Cho nhập lượng thực mua khác ước tính trước khi cho vào tủ.
 * - Ghi ngày mua và hạn dùng mặc định theo nhóm nguyên liệu.
 * - Cập nhật danh sách trong một giao dịch an toàn (mua xong mục biến mất khỏi list).
 */
test.describe("A4 - Mua vào tủ chính xác", () => {
  test("Điền lượng thực mua, hạn dùng theo nhóm, mua vào tủ đúng", async ({ page }) => {
    await page.goto("/shopping-list");
    await expect(page).toHaveTitle(/Đi Chợ/);

    await page.evaluate(async () => {
      const storage = await import("/static/js/storage.js");
      const db = await import("/static/js/db.js");
      await db.clearAllPersonalData();
      // "ing-thit" là nguyên liệu nhóm thịt trong catalogue thật (nạp sẵn).
      await storage.addShoppingItem(
        { ingredient_id: "11111111-0001-0000-0000-000000000001", ingredient_name: "Thịt ba chỉ", needed_quantity: "1000", unit: "g" },
        { source: "plan" }
      );
    });
    await page.reload();

    // Tích chọn mục đã mua trên UI.
    const checkbox = page.locator("#shopping-list-container input[type='checkbox']").first();
    await checkbox.check();
    // Hàng mua hiển thị trường nhập lượng thực mua (mặc định = ước tính 1000).
    const qtyInput = page.locator("#shopping-list-container input[type='number']").first();
    await expect(qtyInput).toBeVisible();
    await expect(qtyInput).toHaveValue("1000");
    const expInput = page.locator("#shopping-list-container input[type='date']").first();
    await expect(expInput).toBeVisible();

    // Nhập lượng thực mua khác ước tính: 850.
    await qtyInput.fill("850");

    await page.locator("#btn-add-to-pantry").click();
    // Toàn bộ giao dịch mua xong -> list về trạng thái rỗng trong UI (chờ cả khi commit & re-render).
    await expect(page.locator("#shopping-list-container")).toContainText("Không có món nào cần mua");

    // Vào trang Tủ: lot có lượng thực mua VÀ hạn dùng (được ghi theo nhóm).
    const lot = await page.evaluate(async () => {
      const storage = await import("/static/js/storage.js");
      const lots = await storage.getPantryLots();
      return lots.find((l) => l.ingredient_name === "Thịt ba chỉ") || null;
    });
    expect(lot, "Lot vào tủ là lot đã mua").not.toBeNull();
    expect(lot.purchased_quantity).toBe("850");
    expect(lot.remaining_quantity).toBe("850");
    expect(lot.unit).toBe("g");
    expect(lot.purchased_at).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    expect(lot.expires_at, "Có hạn dùng mặc định theo nhóm").toMatch(/^\d{4}-\d{2}-\d{2}$/);

    // Danh sách đi chợ hết mục đã mua (cùng giao dịch).
    await page.goto("/shopping-list");
    await expect(page.locator("#shopping-list-container")).toContainText("Không có món nào cần mua");

    // Chống bấm lặp: vài lần bấm nhanh chỉ còn một lượt mua vào tủ.
    const bought = { ingredient_id: "ing-a4-idem", ingredient_name: "Đậu hũ", needed_quantity: "400", unit: "g" };
    await page.evaluate(async (i) => {
      const storage = await import("/static/js/storage.js");
      await storage.addShoppingItem(i, { source: "manual" });
    }, bought);
    await page.reload();
    const checkbox2 = page.locator("#shopping-list-container input[type='checkbox']").first();
    await checkbox2.check();
    for (let i = 0; i < 3; i++) {
      await page.locator("#btn-add-to-pantry").click();
    }
    await expect(page.locator("#shopping-list-container")).toContainText("Không có món nào cần mua");
    const idemCount = await page.evaluate(async (ingId) => {
      const storage = await import("/static/js/storage.js");
      return (await storage.getPantryLots()).filter((l) => l.ingredient_id === ingId).length;
    }, bought.ingredient_id);
    expect(idemCount).toBe(1, "Chỉ một lượt mua vào tủ dù bấm nhiều lần");
  });
});
