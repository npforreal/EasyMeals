import { test, expect } from "@playwright/test";

/**
 * A7 (Vòng 13) — Đường chạy OFFLINE (www/ mobile build) phải truyền conversions +
 * tên nguyên liệu gốc xuống engine.js giống đường API:
 * pantry rỗng, đợt 7 ngày -> món mặn thứ 5 là "Cơm chiên Dương Châu..." cần
 * 500g "Cơm nguội". Quy đổi gạo -> cơm ratio 2.5 nên danh sách mua phải nêu
 * "Gạo" 200g; KHÔNG được nêu "Cơm nguội"/"Cơm nóng" lẫn "Nguyên liệu gốc cho...".
 */

test.describe("A7 - Offline: mua gạo thay vì cơm theo quy đổi", () => {
  test("Pantry rỗng 7 ngày: danh sách mua nêu Gạo 200g, không nêu cơm", async ({
    page,
  }) => {
    // Chặn hoàn toàn API/mạng để ép đường engine.js tại chỗ.
    await page.route("**/*", (route) => {
      const url = route.request().url();
      if (url.includes("/api/") || url.includes("supabase.co")) {
        return route.abort("failed");
      }
      return route.continue();
    });

    await page.goto("/mobile/planner.html");
    await expect(page).toHaveTitle(/Kế Hoạch Bữa Ăn/);

    // Chọn 7 ngày qua chip chính thức để cập nhật cả ngày bắt đầu/kết thúc và
    // localStorage (set trực tiếp input ẩn sẽ bị các bộ khởi tạo ghi đè).
    await page.locator("#days-selector .day-chip[data-days='7']").click({ force: true });

    await page.locator("#btn-generate").click({ force: true });
    await expect(page.locator(".meal-box").first()).toBeVisible({ timeout: 15000 });
    await expect(page.locator("#btn-generate")).toBeEnabled({ timeout: 15000 });

    await page.goto("/mobile/shopping.html");
    const body = await page.locator("main").textContent();

    // Tên lỗi "Nguyên liệu gốc cho ..." không được xuất hiện.
    expect(body).not.toContain("Nguyên liệu gốc cho");
    // Quy đổi đúng nguyên liệu gốc: mua gạo.
    expect(body).toContain("Gạo");
    expect(body).toContain("200");
    // Không gợi ý mua trực tiếp nguyên liệu đã qua chế biến.
    expect(body).not.toContain("Cơm nguội");
    expect(body).not.toContain("Cơm nóng");
  });
});
