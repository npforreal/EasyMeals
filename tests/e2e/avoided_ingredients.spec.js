import { test, expect } from "@playwright/test";

async function selectAvoidedIngredients(page, values) {
  await page.goto("/recipes");
  const select = page.locator("#recipe-avoid-ingredients");
  await expect(select.locator("option").first()).toBeAttached({ timeout: 10000 });
  await select.selectOption(values);
  await expect.poll(() => page.evaluate(async () => {
    const storage = await import("/static/js/storage.js");
    return (await storage.getLocalSetting("recipe_preferences_v1"))?.avoidedIngredientIds || [];
  })).toEqual(values);
}

test.describe("D2b avoided ingredients", () => {
  test("preference excludes matching canonical IDs from generated plan", async ({ page }) => {
    await page.goto("/recipes");
    const select = page.locator("#recipe-avoid-ingredients");
    await expect(select.locator("option").first()).toBeAttached({ timeout: 10000 });
    const avoidedId = await select.locator("option").first().getAttribute("value");
    await selectAvoidedIngredients(page, [avoidedId]);

    await page.goto("/planner");
    await expect(page.locator("#avoid-ingredients-disclaimer")).toBeVisible();
    await page.locator('.day-chip[data-days="1"]').click();
    await page.locator("#btn-generate").click();
    await expect(page.locator("#btn-generate")).toBeEnabled({ timeout: 10000 });

    const result = await page.evaluate(async () => {
      const storage = await import("/static/js/storage.js");
      const catalogue = await storage.getCachedCatalogue();
      const plans = await storage.getMealPlans();
      const recipes = new Map(catalogue.recipes.map((recipe) => [recipe.id, recipe]));
      const prefs = await storage.getLocalSetting("recipe_preferences_v1");
      return { plans, recipes: Object.fromEntries(recipes), avoided: prefs.avoidedIngredientIds };
    });
    for (const meal of result.plans) for (const dish of meal.dishes) {
      const recipe = result.recipes[dish.recipe_id];
      expect(recipe.ingredients.some((ingredient) => result.avoided.includes(ingredient.ingredient_id))).toBe(false);
    }
  });

  test("all catalogue ingredients avoided produces a shortage warning", async ({ page }) => {
    await page.goto("/recipes");
    const select = page.locator("#recipe-avoid-ingredients");
    await expect(select.locator("option").first()).toBeAttached({ timeout: 10000 });
    const ids = await select.locator("option").evaluateAll((options) => options.map((option) => option.value));
    await selectAvoidedIngredients(page, ids);

    await page.goto("/planner");
    await expect(page.locator("#avoid-ingredients-disclaimer")).toBeVisible();
    await page.locator('.day-chip[data-days="1"]').click();
    await page.locator("#btn-generate").click();
    await expect(page.locator("#btn-generate")).toBeEnabled({ timeout: 10000 });
    await expect(page.locator(".meal-box").first()).toContainText("Không đủ món phù hợp với nguyên liệu bạn tránh cho bữa này.");
  });

  test("manual swap warns and asks for confirmation when every catalogue ingredient is avoided", async ({ page }) => {
    await page.goto("/planner");
    await page.locator('.day-chip[data-days="1"]').click();
    await page.locator("#btn-generate").click();
    await expect(page.locator("#btn-generate")).toBeEnabled({ timeout: 10000 });
    await expect(page.locator(".btn-swap-dish").first()).toBeVisible();

    await page.goto("/recipes");
    const select = page.locator("#recipe-avoid-ingredients");
    await expect(select.locator("option").first()).toBeAttached({ timeout: 10000 });
    const ids = await select.locator("option").evaluateAll((options) => options.map((option) => option.value));
    await selectAvoidedIngredients(page, ids);
    await page.goto("/planner");

    let confirmationText = "";
    page.on("dialog", async (dialog) => {
      if (dialog.type() === "prompt") await dialog.accept("1");
      else {
        confirmationText = dialog.message();
        await dialog.accept();
      }
    });
    await page.locator(".btn-swap-dish").first().click();
    await expect.poll(() => confirmationText).toContain("mà bạn đã đặt cần tránh. Vẫn thêm?");
  });
});
