import { test, expect } from "@playwright/test";
import fs from "node:fs";

/**
 * A3 (Vòng 13) — Backup đầy đủ gồm danh sách đi chợ:
 * - Danh sách đi chợ nằm trong kho versioned IndexedDB (store "shopping"),
 *   không còn phụ thuộc localStorage.
 * - Backup v2 mang theo shopping (kể cả nguồn phát sinh plan/manual).
 * - Giữ mục người dùng tự thêm khi kế hoạch đổi (chỉ thay mục sinh tự từ kế hoạch).
 */

test.describe("A3 - Danh sách đi chợ trong kho versioned & backup", () => {
  test("Giữ mục tự thêm khi đổi kế hoạch; backup & phục hồi đầy đủ", async ({ page }) => {
    await page.goto("/shopping-list");
    await expect(page).toHaveTitle(/Đi Chợ/);

    // 1. Người dùng tự thêm mục vào danh sách đi chợ (kho versioned, source "manual").
    await page.evaluate(async () => {
      const storage = await import("/static/js/storage.js");
      const db = await import("/static/js/db.js");
      await db.clearAllPersonalData();
      await storage.addShoppingItem(
        { ingredient_id: "z-a3-manual", ingredient_name: "Nước mắm pha", needed_quantity: "500", unit: "ml" },
        { source: "manual" }
      );
    });

    // 2. Lập thực đơn 3 ngày -> sinh mục "plan" của đợt.
    await page.goto("/planner");
    await page.locator("#btn-generate").click({ force: true });
    await expect(page.locator(".meal-box").first()).toBeVisible({ timeout: 5000 });
    await expect(page.locator("#btn-generate")).toBeEnabled({ timeout: 10000 });

    // 3. Trang đi chợ hiện cả mục manual lẫn mục plan; localStorage cũ đã bỏ.
    await page.goto("/shopping-list");
    await expect(page.locator("#shopping-list-container")).toContainText("Nước mắm pha");
    const listState = await page.evaluate(async () => {
      const storage = await import("/static/js/storage.js");
      const items = await storage.getShoppingItems();
      return {
        items,
        legacyKey: localStorage.getItem("easymeals_shopping_list"),
      };
    });
    expect(listState.legacyKey, "Không còn khoá localStorage cũ").toBeNull();
    const manual = listState.items.find((i) => i.source === "manual");
    const planItems = listState.items.filter((i) => i.source === "plan");
    expect(manual?.ingredient_name).toBe("Nước mắm pha");
    expect(planItems.length).toBeGreaterThan(0);

    // 4. Xuất backup v2 -> chờ tải về file, kiểm tra dữ liệu shopping.
    await page.goto("/settings");
    await page.on("dialog", (dialog) => dialog.accept());
    const downloadPromise = page.waitForEvent("download");
    await page.locator("#btn-export-json").click({ force: true });
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toContain("easymeals-backup-");
    const backupPath = await download.path();
    const backup = JSON.parse(fs.readFileSync(backupPath, "utf-8"));
    expect(backup.schema_version).toBe(2);
    const backupManual = backup.data.shopping.find((i) => i.source === "manual");
    const backupPlan = backup.data.shopping.find((i) => i.source === "plan");
    expect(backupManual?.ingredient_id).toBe("z-a3-manual");
    expect(backupPlan).toBeDefined();

    // 5. Đổi kế hoạch (tạo lại thực đơn) -> chỉ thay mục plan, mục manual còn nguyên.
    await page.goto("/planner");
    await page.locator("#btn-generate").click({ force: true });
    const overlay = page.locator("#plan-conflict-overlay");
    await expect(overlay).toBeVisible({ timeout: 5000 });
    await overlay.locator("#btn-replace-plans").click();
    await expect(overlay).not.toBeVisible({ timeout: 5000 });
    await expect(page.locator("#btn-generate")).toBeEnabled({ timeout: 10000 });

    await page.goto("/shopping-list");
    await expect(page.locator("#shopping-list-container")).toContainText("Nước mắm pha");

    // 6. Xoá sạch dữ liệu -> danh sách đi chợ rỗng.
    await page.goto("/settings");
    await page.locator("#btn-clear-all-data").scrollIntoViewIfNeeded();
    await page.locator("#btn-clear-all-data").click();
    await page.locator("#btn-confirm-clear").click();
    await expect(page.locator("#clear-modal-overlay")).not.toBeVisible({ timeout: 5000 });
    await page.goto("/shopping-list");
    await expect(page.locator("#shopping-list-container")).toContainText("Không có món nào cần mua");

    // 7. Phục hồi từ backup v2 -> danh sách đi chợ trở lại nguyên trạng nguồn phát sinh.
    await page.goto("/settings");
    await page.locator("#import-file-input").setInputFiles(backupPath);
    await expect(page.locator("#import-modal-overlay")).toBeVisible({ timeout: 5000 });
    await page.locator("#btn-confirm-replace").click();
    await expect(page.locator("#import-modal-overlay")).not.toBeVisible({ timeout: 5000 });

    const restoredCount = await page.evaluate(async () => {
      const storage = await import("/static/js/storage.js");
      const items = await storage.getShoppingItems();
      return {
        total: items.length,
        manual: items.filter((i) => i.source === "manual").length,
        plan: items.filter((i) => i.source === "plan").length,
      };
    });
    expect(restoredCount.total).toBe(backup.data.shopping.length);
    expect(restoredCount.manual).toBeGreaterThanOrEqual(1);
    expect(restoredCount.plan).toBe(backup.data.shopping.filter((i) => i.source === "plan").length);

    await page.goto("/shopping-list");
    await expect(page.locator("#shopping-list-container")).toContainText("Nước mắm pha");
  });
});
