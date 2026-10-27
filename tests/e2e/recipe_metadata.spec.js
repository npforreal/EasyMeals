import { test, expect } from "@playwright/test";

test.describe("Recipe metadata filters and detail", () => {
  test("time chip narrows the list and shows hidden-count status", async ({ page }) => {
    await page.goto("/recipes");
    const cards = page.locator("#recipes-grid .recipe-card");
    await expect(cards.first()).toBeVisible({ timeout: 10000 });
    const before = await cards.count();

    const chip = page.locator('.meta-chip[data-meta="time"][data-value="15"]');
    await chip.click();
    await expect(chip).toHaveAttribute("aria-pressed", "true");
    await expect(page.locator("#recipe-metadata-status")).toContainText("chưa có dữ liệu thời gian nên bị ẩn");
    expect(await cards.count()).toBeLessThan(before);

    await page.locator('.meta-chip[data-meta="time"][data-value="0"]').click();
    await expect(page.locator("#recipe-metadata-status")).toBeHidden();
    await expect(cards).toHaveCount(before);
  });

  test("difficulty chip filters and detail shows storage tips", async ({ page }) => {
    await page.goto("/recipes");
    await expect(page.locator("#recipes-grid .recipe-card").first()).toBeVisible({ timeout: 10000 });
    await page.locator('.meta-chip[data-meta="difficulty"][data-value="de"]').click();
    await expect(page.locator("#recipe-metadata-status")).toContainText("độ khó nên bị ẩn");
    await page.locator("#recipes-grid .recipe-card").first().click();
    await expect(page.getByText("Độ khó: Dễ").first()).toBeVisible();
    await expect(page.getByText("ước lượng, nguồn:").first()).toBeVisible();
  });

  test("detail shows storage tips with FDA source", async ({ page }) => {
    await page.goto("/recipes");
    const cards = page.locator("#recipes-grid .recipe-card");
    await expect(cards.first()).toBeVisible({ timeout: 10000 });
    await cards.first().click();
    await expect(page.locator("#recipe-storage-tips")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Mẹo bảo quản" })).toBeVisible();
    await expect(page.getByText("Nguồn: FDA (phạm vi công cộng)")).toBeVisible();
  });
});
