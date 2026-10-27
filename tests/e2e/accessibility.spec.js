import { test, expect } from "@playwright/test";

/**
 * G3 (Vòng 13) — UX & accessibility trên bản web.
 *
 * - Mọi điều khiển nhìn thấy được phải có tên truy cập (aria-label, <label>,
 *   nội dung chữ hoặc title/placeholder), không dùng ký hiệu trơ như "✕".
 * - Hộp thoại nhận focus, giữ Tab bên trong, đóng bằng Escape và trả focus về
 *   nút đã mở.
 * - Trên khổ điện thoại, nút bấm có vùng chạm tối thiểu 44×44 px.
 */

const PAGES = ["/", "/planner", "/recipes", "/shopping-list", "/settings"];

async function collectA11yIssues(page) {
  return page.evaluate(() => {
    const visible = (el) => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
    const accessibleName = (el) => {
      const aria = (el.getAttribute("aria-label") || "").trim();
      if (aria) return aria;
      if (el.id) {
        const label = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
        if (label && (label.innerText || "").trim()) return label.innerText.trim();
      }
      const wrapping = el.closest("label");
      if (wrapping && (wrapping.innerText || "").trim()) return wrapping.innerText.trim();
      const text = (el.innerText || "").trim();
      if (text) return text;
      return (el.getAttribute("title") || el.getAttribute("placeholder") || "").trim();
    };

    const issues = [];
    const seenIds = new Set();
    document
      .querySelectorAll("button, a[href], input:not([type=hidden]), select, textarea")
      .forEach((el) => {
        if (!visible(el)) return;
        const name = accessibleName(el);
        const tag = el.tagName.toLowerCase();
        if (!name) {
          issues.push(`${tag} thiếu tên truy cập (${el.outerHTML.slice(0, 90)})`);
        } else if (/^[✕×+•.\-]+$/.test(name)) {
          issues.push(`${tag} chỉ có ký hiệu "${name}" làm tên truy cập`);
        }
        if (el.id) {
          if (seenIds.has(el.id)) issues.push(`id trùng trong trang: ${el.id}`);
          seenIds.add(el.id);
        }
      });

    if (document.documentElement.lang !== "vi") {
      issues.push(`html lang phải là "vi", đang là "${document.documentElement.lang}"`);
    }
    const toast = document.getElementById("toast-container");
    if (!toast || toast.getAttribute("role") !== "status" || toast.getAttribute("aria-live") !== "polite") {
      issues.push("vùng thông báo toast thiếu role=status/aria-live=polite");
    }
    return issues;
  });
}

test.describe("G3 — Accessibility web", () => {
  test("mọi điều khiển trên 5 trang chính đều có tên truy cập", async ({ page }) => {
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
      await storage.addShoppingItem(
        {
          ingredient_id: "11111111-0001-0000-0000-000000000011",
          ingredient_name: "Rau muống",
          needed_quantity: "300",
          unit: "g",
        },
        { source: "manual" }
      );
    });

    const allIssues = [];
    for (const path of PAGES) {
      await page.goto(path);
      await page.waitForLoadState("domcontentloaded");
      // Trang Thực đơn cần dữ liệu thật để các nút Đổi/Bỏ/Xem xuất hiện.
      if (path === "/planner") {
        await page.locator("#btn-generate").click({ force: true });
        await expect(page.locator(".meal-box").first()).toBeVisible({ timeout: 10000 });
        await expect(page.locator("#btn-generate")).toBeEnabled({ timeout: 10000 });
      }
      const issues = await collectA11yIssues(page);
      allIssues.push(...issues.map((issue) => `${path}: ${issue}`));
    }

    expect(allIssues).toEqual([]);
  });

  test("hộp thoại công thức: focus vào trong, Tab bị giữ, Escape đóng và trả focus", async ({ page }) => {
    await page.goto("/recipes");
    const openButton = page.locator("#recipes-grid .recipe-card button").first();
    await expect(openButton).toBeVisible();

    await openButton.focus();
    await openButton.press("Enter");

    const overlay = page.locator("#recipe-modal-overlay");
    await expect(overlay).toBeVisible();
    await expect
      .poll(() => page.evaluate(() => document.getElementById("recipe-modal-content").contains(document.activeElement)))
      .toBe(true);

    // Tab vài lần: focus phải ở lại trong hộp thoại.
    for (let i = 0; i < 6; i += 1) {
      await page.keyboard.press("Tab");
      const inside = await page.evaluate(() =>
        document.getElementById("recipe-modal-content").contains(document.activeElement)
      );
      expect(inside, `Tab lần ${i + 1} ra ngoài hộp thoại`).toBe(true);
    }

    await page.keyboard.press("Escape");
    await expect(overlay).toBeHidden();
    await expect
      .poll(() => openButton.evaluate((el) => el === document.activeElement))
      .toBe(true);
  });

  test("vùng chạm của nút trên khổ điện thoại tối thiểu 44×44 px", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
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
      await storage.addShoppingItem(
        {
          ingredient_id: "11111111-0001-0000-0000-000000000011",
          ingredient_name: "Rau muống",
          needed_quantity: "300",
          unit: "g",
        },
        { source: "manual" }
      );
    });

    const measure = async (path) => {
      await page.goto(path);
      await page.waitForLoadState("domcontentloaded");
      return page.evaluate(() => {
        const small = [];
        document.querySelectorAll("button").forEach((btn) => {
          if (!(btn.offsetWidth || btn.offsetHeight || btn.getClientRects().length)) return;
          const rect = btn.getBoundingClientRect();
          if (rect.width + 0.5 < 44 || rect.height + 0.5 < 44) {
            small.push(
              `"${(btn.getAttribute("aria-label") || btn.innerText || "").trim().slice(0, 40)}" ` +
                `${Math.round(rect.width)}×${Math.round(rect.height)}`
            );
          }
        });
        return small;
      });
    };

    const pantryIssues = await measure("/");
    const shoppingIssues = await measure("/shopping-list");
    const all = [
      ...pantryIssues.map((i) => `/ : ${i}`),
      ...shoppingIssues.map((i) => `/shopping-list : ${i}`),
    ];
    expect(all).toEqual([]);
  });
});
