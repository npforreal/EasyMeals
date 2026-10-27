import { test, expect } from "@playwright/test";
import fs from "node:fs";

/**
 * G2 (Vòng 13) — Hành trình người dùng còn thiếu trong bộ E2E:
 * 1. Cập nhật tủ lạnh: gia hạn +3 ngày, xoá lô, quay về trạng thái trống.
 * 2. Sao lưu -> xoá sạch -> phục hồi: giữ nguyên tủ, thực đơn, biến động kho,
 *    danh sách đi chợ và cài đặt cục bộ (chuyển máy không mất dữ liệu).
 */

test.describe("G2 — Hành trình cập nhật tủ và phục hồi sao lưu", () => {
  test("Gia hạn +3 ngày, xoá lô và hiện lại trạng thái tủ trống", async ({ page }) => {
    await page.goto("/");
    await page.evaluate(async () => {
      const storage = await import("/static/js/storage.js");
      const db = await import("/static/js/db.js");
      await db.clearAllPersonalData();
      await storage.addPantryLot({
        ingredient_id: "11111111-0001-0000-0000-000000000001",
        ingredient_name: "Thịt ba chỉ",
        quantity: "500",
        unit: "g",
        expires_at: "2026-12-31",
      });
    });
    await page.reload();
    await expect(page.locator("#pantry-container")).toContainText("Thịt ba chỉ");

    await page.getByRole("button", { name: "Gia hạn thêm 3 ngày cho Thịt ba chỉ" }).click();

    const extended = await page.evaluate(async () => {
      const storage = await import("/static/js/storage.js");
      const lots = await storage.getPantryLots();
      return lots.find((l) => l.ingredient_name === "Thịt ba chỉ")?.expires_at || null;
    });
    expect(extended, "Gia hạn +3 ngày từ 31/12/2026").toBe("2027-01-03");

    page.once("dialog", (dialog) => dialog.accept());
    await page.getByRole("button", { name: "Xoá Thịt ba chỉ khỏi tủ lạnh" }).click();
    await expect(page.locator("#pantry-container")).toContainText("Tủ lạnh đang trống", {
      timeout: 5000,
    });
  });

  test("Sao lưu rồi phục hồi giữ đủ tủ, thực đơn, biến động, đi chợ và cài đặt", async ({
    page,
  }) => {
    await page.goto("/settings");
    await page.evaluate(async () => {
      const storage = await import("/static/js/storage.js");
      const db = await import("/static/js/db.js");
      await db.clearAllPersonalData();

      const lot = await storage.addPantryLot({
        ingredient_id: "11111111-0001-0000-0000-000000000001",
        ingredient_name: "Thịt ba chỉ",
        quantity: "500",
        unit: "g",
        expires_at: "2026-12-31",
      });
      await storage.updatePantryLot({ ...lot, remaining_quantity: "400" });
      await db.putItem("movements", {
        id: "g2-movement-1",
        pantry_lot_id: lot.id,
        quantity_delta: "-100",
        reason: "meal_consumption",
        created_at: "2026-10-27T10:00:00.000Z",
      });
      await storage.saveMealPlans([
        {
          id: "g2-plan-1",
          planned_for: "2026-10-28",
          meal_period: "lunch",
          dishes: [
            {
              id: "g2-dish-1",
              recipe_id: "11111111-0002-0000-0000-000000000001",
              recipe_name: "Thịt kho trứng",
              category: "man",
              servings: 2,
              is_leftover: false,
            },
          ],
          eaten_at: null,
          notes: "Bữa trưa G2",
        },
      ]);
      await storage.addShoppingItem(
        {
          ingredient_id: "z-g2-manual",
          ingredient_name: "Nước mắm pha",
          needed_quantity: "250",
          unit: "ml",
        },
        { source: "manual" }
      );
      await storage.setLocalSetting("g2_test_setting", { household_size: 4, note: "giữ nguyên" });
    });

    const downloadPromise = page.waitForEvent("download");
    await page.locator("#btn-export-json").click({ force: true });
    const download = await downloadPromise;
    const backupPath = await download.path();
    const backup = JSON.parse(fs.readFileSync(backupPath, "utf-8"));
    expect(backup.schema_version).toBe(3);
    expect(backup.data.pantry).toHaveLength(1);
    expect(backup.data.plans).toHaveLength(1);
    expect(backup.data.movements).toHaveLength(1);
    expect(backup.data.settings.some((s) => s.key === "g2_test_setting")).toBe(true);

    // Xoá sạch dữ liệu trên máy rồi phục hồi bằng chính file vừa xuất.
    await page.locator("#btn-clear-all-data").scrollIntoViewIfNeeded();
    await page.locator("#btn-clear-all-data").click();
    await page.locator("#btn-confirm-clear").click();
    await expect(page.locator("#clear-modal-overlay")).not.toBeVisible({ timeout: 5000 });

    await page.locator("#import-file-input").setInputFiles(backupPath);
    await expect(page.locator("#import-modal-overlay")).toBeVisible({ timeout: 5000 });
    // Ghi đè còn một bước xác nhận native; chấp nhận trong hành trình phục hồi.
    page.once("dialog", (dialog) => dialog.accept());
    await page.locator("#btn-confirm-replace").click();
    await expect(page.locator("#import-modal-overlay")).not.toBeVisible({ timeout: 5000 });

    const restored = await page.evaluate(async () => {
      const storage = await import("/static/js/storage.js");
      const db = await import("/static/js/db.js");
      const lots = await storage.getPantryLots();
      return {
        lots: lots.map((l) => ({
          name: l.ingredient_name,
          remaining: l.remaining_quantity,
          expires: l.expires_at,
        })),
        plans: (await storage.getMealPlans()).map((p) => ({ id: p.id, notes: p.notes })),
        movements: (await db.getAllItems("movements")).map((m) => ({
          id: m.id,
          delta: m.quantity_delta,
        })),
        shopping: (await storage.getShoppingItems()).map((i) => ({
          name: i.ingredient_name,
          source: i.source,
        })),
        setting: await storage.getLocalSetting("g2_test_setting"),
      };
    });

    expect(restored.lots).toEqual([
      { name: "Thịt ba chỉ", remaining: "400", expires: "2026-12-31" },
    ]);
    expect(restored.plans).toEqual([{ id: "g2-plan-1", notes: "Bữa trưa G2" }]);
    expect(restored.movements).toEqual([{ id: "g2-movement-1", delta: "-100" }]);
    expect(restored.shopping).toContainEqual({ name: "Nước mắm pha", source: "manual" });
    expect(restored.setting).toEqual({ household_size: 4, note: "giữ nguyên" });
  });
});
