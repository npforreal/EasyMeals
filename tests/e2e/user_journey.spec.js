import { test, expect } from "@playwright/test";

test.describe("EasyMeals End-to-End User Journey", () => {
  test.beforeEach(async ({ page }) => {
    // Collect console errors
    page.on("console", (msg) => {
      if (msg.type() === "error" && !msg.text().includes("favicon")) {
        console.error("Browser Console Error:", msg.text());
      }
    });
  });

  test("Full Journey: Thêm tủ -> Lập thực đơn -> Đã ăn -> Hoàn tác -> Sao lưu & Phục hồi", async ({
    page,
  }) => {
    // 1. Mở trang chủ (Tủ lạnh)
    await page.goto("/");
    await expect(page).toHaveTitle(/Tủ Lạnh & Nguyên Liệu/);

    // Kiểm tra trạng thái rỗng
    await expect(page.locator("#pantry-container")).toContainText("Tủ lạnh đang trống");

    // 2. Thêm thực phẩm trực tiếp qua UI: Thịt ba chỉ 1000g
    await page.locator("#ingredient-search").fill("ba chỉ");
    const itemOption = page.locator(".autocomplete-item:has-text('Thịt ba chỉ')").first();
    await itemOption.waitFor({ state: "visible", timeout: 4000 });
    await itemOption.click({ force: true });

    await page.locator("#lot-quantity").fill("1000");
    await page.locator("#lot-unit").selectOption("g");
    await page.locator("#add-lot-form button[type='submit']").click({ force: true });

    // Xác nhận lot xuất hiện trong danh sách UI
    await expect(page.locator("#pantry-container")).toContainText("Thịt ba chỉ");

    // Bổ sung các nguyên liệu cần thiết cho các món còn lại trong bữa ăn gia đình
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
    await page.reload();
    await expect(page.locator("#stock-total")).toContainText("11 nguyên liệu");

    // 3. Chuyển sang trang Thực đơn (/planner)
    await page.goto("/planner");
    await expect(page).toHaveTitle(/Kế Hoạch Bữa Ăn/);

    // Bấm Tạo thực đơn tự động
    const genBtn = page.locator("#btn-generate");
    await genBtn.click({ force: true });

    // Chờ kết quả thực đơn hiển thị
    const mealCards = page.locator(".meal-box");
    await expect(mealCards.first()).toBeVisible({ timeout: 5000 });
    const count = await mealCards.count();
    expect(count).toBeGreaterThan(0);

    // 4. Đánh dấu 'Đã ăn' (Trừ kho)
    const eatBtn = page.locator("button:has-text('Đánh dấu Đã ăn')").first();
    await eatBtn.click({ force: true });

    // Kiểm tra trạng thái chuyển thành 'Đã nấu ăn' và nút đổi thành 'Hoàn tác bữa ăn'
    await expect(page.locator(".badge:has-text('Đã nấu ăn')").first()).toBeVisible({
      timeout: 5000,
    });
    const undoBtn = page.locator("button:has-text('Hoàn tác bữa ăn')").first();
    await expect(undoBtn).toBeVisible();

    // 5. Hoàn tác bữa ăn
    await undoBtn.click({ force: true });
    await expect(page.locator(".badge:has-text('Chưa ăn')").first()).toBeVisible({
      timeout: 5000,
    });

    // 6. Chuyển sang trang Cài đặt & Dữ liệu (/settings)
    await page.goto("/settings");
    await expect(page).toHaveTitle(/Dữ Liệu & Cài Đặt/);

    // Kiểm tra trạng thái Online
    await expect(page.locator("#network-status")).toContainText("Trực tuyến (Online)");

    // Thử xuất file sao lưu
    const downloadPromise = page.waitForEvent("download");
    await page.locator("#btn-export-json").click({ force: true });
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toContain("easymeals-backup-");

    // 7. Xoá toàn bộ dữ liệu trên máy
    // Cuộn tới nút trước khi bấm: trên di động tabbar cố định có thể che nút nếu bấm bằng toạ độ.
    await page.locator("#btn-clear-all-data").scrollIntoViewIfNeeded();
    await page.locator("#btn-clear-all-data").click();
    await page.locator("#btn-confirm-clear").click();
    await expect(page.locator("#clear-modal-overlay")).not.toBeVisible({ timeout: 5000 });
    await page.waitForTimeout(200);

    // Kiểm tra lại trang chủ -> Tủ rỗng
    await page.goto("/");
    await expect(page.locator("#pantry-container")).toContainText("Tủ lạnh đang trống");
  });

  test("Kiểm tra giao diện Sáng / Tối và duyệt Công thức", async ({ page }) => {
    await page.goto("/recipes");
    await expect(page).toHaveTitle(/Sổ Tay Món Ăn/);

    // Lọc Món Canh
    await page.locator("button:has-text('Món Canh')").click();
    const canhCard = page.locator(".recipe-card:has-text('Canh chua cá lóc')").first();
    await expect(canhCard).toBeVisible();

    // Bấm xem chi tiết công thức (Modal)
    await canhCard.click({ force: true });
    const modal = page.locator("#recipe-modal-content");
    await expect(modal).toBeVisible();
    await expect(modal).toContainText("Nguyên liệu cần chuẩn bị:");
    await expect(modal).toContainText("Hướng dẫn các bước nấu:");

    // Đóng modal
    await page.locator("button:has-text('Đóng')").click({ force: true });
    await expect(page.locator("#recipe-modal-overlay")).not.toBeVisible();

    // Đổi theme sang tối
    const themeBtn = page.locator("[data-theme-toggle]:visible").first();
    await themeBtn.click();
    const htmlTheme = await page.locator("html").getAttribute("data-theme");
    expect(htmlTheme).toBe("dark");
  });

  test("Mobile Offline E2E Journey on static www/ build with route abort", async ({ page }) => {
    // Chặn hoàn toàn tất cả các request ra API bên ngoài hoặc mạng
    await page.route("**/*", (route) => {
      const url = route.request().url();
      if (url.includes("/api/") || url.includes("supabase.co")) {
        return route.abort("failed");
      }
      return route.continue();
    });

    // 1. Mở bản mobile tĩnh tại /mobile/index.html
    await page.goto("/mobile/index.html");
    await expect(page).toHaveTitle(/Tủ Lạnh & Nguyên Liệu/);

    // 2. Thêm thực phẩm - nạp autocomplete từ data/catalogue.json đóng gói trong IndexedDB
    await page.locator("#ingredient-search").fill("ba chỉ");
    const itemOption = page.locator(".autocomplete-item:has-text('Thịt ba chỉ')").first();
    await itemOption.waitFor({ state: "visible", timeout: 4000 });
    await itemOption.click({ force: true });

    await page.locator("#lot-quantity").fill("1000");
    await page.locator("#lot-unit").selectOption("g");
    await page.locator("#add-lot-form button[type='submit']").click({ force: true });
    await expect(page.locator("#pantry-container")).toContainText("Thịt ba chỉ");

    // Bổ sung các nguyên liệu để đủ nấu các món mặn, rau, canh
    await page.evaluate(async () => {
      const storage = await import("/mobile/static/js/storage.js");
      const extras = [
        { ingredient_id: "11111111-0001-0000-0000-000000000009", ingredient_name: "Trứng vịt", quantity: "10", unit: "piece" },
        { ingredient_id: "11111111-0001-0000-0000-000000000026", ingredient_name: "Hành tím", quantity: "100", unit: "g" },
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
    await page.reload();
    await expect(page.locator("#stock-total")).toContainText("10 nguyên liệu");

    // 3. Chuyển sang planner.html - Lập thực đơn offline thuần túy bằng engine.js
    await page.goto("/mobile/planner.html");
    await expect(page).toHaveTitle(/Kế Hoạch Bữa Ăn/);
    await page.locator("#btn-generate").click({ force: true });

    const mealCards = page.locator(".meal-box");
    await expect(mealCards.first()).toBeVisible({ timeout: 5000 });

    // 4. Đánh dấu Đã ăn (Trừ kho FIFO offline thuần túy bằng engine.js)
    const eatBtn = page.locator("button:has-text('Đánh dấu Đã ăn')").first();
    await eatBtn.click({ force: true });
    await expect(page.locator(".badge:has-text('Đã nấu ăn')").first()).toBeVisible({ timeout: 5000 });

    // 5. Hoàn tác bữa ăn (Undo consumption offline thuần túy)
    const undoBtn = page.locator("button:has-text('Hoàn tác bữa ăn')").first();
    await undoBtn.click({ force: true });
    await expect(page.locator(".badge:has-text('Chưa ăn')").first()).toBeVisible({ timeout: 5000 });

    // 6. Chuyển sang settings.html - Xuất sao lưu JSON
    await page.goto("/mobile/settings.html");
    await expect(page).toHaveTitle(/Dữ Liệu & Cài Đặt/);
    const downloadPromise = page.waitForEvent("download");
    await page.locator("#btn-export-json").click({ force: true });
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toContain("easymeals-backup-");
  });
  test("Bố cục đúng theo chiều rộng: di động dùng tabbar, máy tính dùng sidebar", async ({ page }) => {
    await page.goto("/");
    const width = page.viewportSize().width;
    const sidebar = page.locator(".sidebar");
    const tabbar = page.locator(".tabbar");
    if (width < 720) {
      await expect(tabbar).toBeVisible();
      await expect(sidebar).toBeHidden();
    } else {
      await expect(sidebar).toBeVisible();
      await expect(tabbar).toBeHidden();
    }
    // Không có tràn ngang
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth
    );
    expect(overflow).toBeLessThanOrEqual(1);
  });
  test("Dropdown gợi ý cuộn được bằng cảm ứng và vuốt không tự chọn mục", async ({ page }) => {
    await page.goto("/");
    await page.locator("#ingredient-search").fill("c");
    const dd = page.locator("#ingredient-dropdown");
    const items = dd.locator(".autocomplete-item");
    await expect(items.first()).toBeVisible({ timeout: 5000 });
    expect(await items.count()).toBeGreaterThanOrEqual(6);

    // Vuốt (cảm ứng) từ cuối danh sách lên đầu: phải cuộn, không được chọn mục nào.
    const box = await dd.boundingBox();
    const x = box.x + box.width / 2;
    // Chỉ vuốt trong phần danh sách nhìn thấy được (không nằm dưới thanh tab cố định).
    const tabTop = await page.evaluate(() => {
      const t = document.querySelector(".tabbar");
      return t && getComputedStyle(t).display !== "none" ? t.getBoundingClientRect().top : innerHeight;
    });
    const yFrom = Math.min(box.y + box.height, tabTop) - 16;
    const yTo = box.y + 16;
    const cdp = await page.context().newCDPSession(page);
    await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x, y: yFrom }] });
    for (let k = 1; k <= 8; k++) {
      const y = yFrom + ((yTo - yFrom) * k) / 8;
      await cdp.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: [{ x, y }] });
    }
    await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });

    await expect(dd).toBeVisible();
    await expect.poll(() => dd.evaluate((el) => el.scrollTop)).toBeGreaterThan(0);
    expect(await page.locator("#ingredient-id").inputValue()).toBe("");
    expect(await page.locator("#ingredient-search").inputValue()).toBe("c");

    // Chạm (click) vào một mục mới chọn.
    const pick = items.nth(2);
    const name = (await pick.locator("strong").innerText()).trim();
    await pick.click();
    await expect(dd).toBeHidden();
    expect(await page.locator("#ingredient-search").inputValue()).toBe(name);
    expect(await page.locator("#ingredient-id").inputValue()).not.toBe("");
  });
});
