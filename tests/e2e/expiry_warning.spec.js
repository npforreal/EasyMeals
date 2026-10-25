import { test, expect } from "@playwright/test";

/**
 * A5 (Vòng 13) — Cảnh báo tồn theo lô trên trang Kế hoạch:
 * - Chỉ lô CÒN LƯỢNG (remaining > 0) mới được cảnh báo; lô đã dùng hết bỏ qua.
 * - Phân biệt ĐÃ hết hạn (< hôm nay) với SẮP hết hạn (trong phạm vi chu kỳ thực đơn).
 * - Mỗi nguyên liệu nêu đúng ngày cuối cùng có thể dùng (theo hạn của lô nó,
 *   lấy ngày sớm nhất nếu nhiều lô) — không dùng ngày cuối kế hoạch đại diện cho tất cả.
 */

function iso(offsetDays) {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  return d.toISOString().slice(0, 10);
}

test.describe("A5 - Cảnh báo tồn theo lô", () => {
  test("Phân biệt hết hạn/sắp hết hạn, chỉ lô còn lượng, ngày dùng theo từng lô", async ({
    page,
  }) => {
    await page.goto("/planner");
    await expect(page).toHaveTitle(/Kế Hoạch Bữa Ăn/);

    // Seed tủ bằng nguyên liệu thật của catalogue với hạn dùng quanh chu kỳ 3 ngày.
    await page.evaluate(async (isoDates) => {
      const storage = await import("/static/js/storage.js");
      const db = await import("/static/js/db.js");
      await db.clearAllPersonalData();
      const [yesterday, tom2, tom10] = isoDates;
      // Lô đã hết hạn: còn lượng -> nhóm "đã quá hạn".
      await storage.addPantryLot({ ingredient_id: "11111111-0001-0000-0000-000000000006", ingredient_name: "Cá lóc", quantity: "1000", unit: "g", expires_at: yesterday });
      // Lô sắp hết hạn đúng vào ngày cuối của chu kỳ 3 ngày -> "dùng trước ngày ...".
      await storage.addPantryLot({ ingredient_id: "11111111-0001-0000-0000-000000000015", ingredient_name: "Cà chua", quantity: "500", unit: "g", expires_at: tom2 });
      // Lô hết hạn ra sau chu kỳ -> không cảnh báo lần này.
      await storage.addPantryLot({ ingredient_id: "11111111-0001-0000-0000-000000000011", ingredient_name: "Rau muống", quantity: "1000", unit: "g", expires_at: tom10 });
      // Lô hết hạn nhưng ĐÃ dùng hết (lượng 0) -> KHÔNG cảnh báo.
      await storage.addPantryLot({ ingredient_id: "11111111-0001-0000-0000-000000000003", ingredient_name: "Sườn non heo", quantity: "500", unit: "g", expires_at: yesterday });
      const lotsNow = await storage.getPantryLots();
      const zeroLot = lotsNow.find((l) => l.ingredient_id === "11111111-0001-0000-0000-000000000003");
      await storage.updatePantryLot({ ...zeroLot, remaining_quantity: "0" });
      // Lô không hạn dùng -> không cảnh báo.
      await storage.addPantryLot({ ingredient_id: "11111111-0001-0000-0000-000000000008", ingredient_name: "Trứng gà", quantity: "10", unit: "piece" });
    }, [iso(-1), iso(2), iso(10)]);

    // Lập kế hoạch 3 ngày -> chu kỳ [hôm nay, hôm nay + 2].
    await page.locator("#btn-generate").click({ force: true });
    await expect(page.locator(".meal-box").first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator("#btn-generate")).toBeEnabled({ timeout: 10000 });

    const alert = page.locator("#freshness-alert");
    await expect(alert).toBeVisible({ timeout: 5000 });
    const text = await page.locator("#freshness-alert-text").textContent();

    // Lô đã hết hạn (còn lượng) được nêu ở nhóm "Đã quá hạn" với ngày hạn của nó.
    expect(text).toContain("Đã quá hạn");
    expect(text).toContain("Cá lóc (hết hạn");
    // Lô sắp hết hạn: nêu nguyên liệu + ngày cuối có thể dùng theo lô.
    expect(text).toContain("Cà chua (dùng trước ngày");
    // Lô ngoài chu kỳ / hết lượng / không hạn dùng KHÔNG được nêu.
    expect(text).not.toContain("Rau muống");
    expect(text).not.toContain("Sườn non heo");
    expect(text).not.toContain("Trứng gà");
  });
});
