import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  regenerateSingleMeal,
  recomputeShoppingList,
  calculateShoppingBudget,
  groupShoppingItemsByCategory,
  swapDishInMeal,
  addDishToMeal,
  removeDishFromMeal,
  rescheduleMeal,
  mergeCompatibleShoppingItems,
} from "../../app/static/js/engine.js";

describe("Plan Editing & Shopping Budget (JS Engine)", () => {
  it("B2: regenerateSingleMeal throws on already eaten meal", () => {
    const meal = {
      id: "meal-1",
      planned_for: "2026-10-26",
      meal_period: "lunch",
      eaten_at: "2026-10-26T12:00:00Z",
      dishes: [],
    };
    assert.throws(
      () => regenerateSingleMeal("meal-1", [meal], [], []),
      /đã được đánh dấu ăn/
    );
  });

  it("B1: regenerateSingleMeal regenerates dishes avoiding other meals in period", () => {
    const recipes = [
      { id: "r-man-1", name: "Thịt kho", category: "man", servings: 4, ingredients: [] },
      { id: "r-man-2", name: "Gà rán", category: "man", servings: 4, ingredients: [] },
      { id: "r-rau-1", name: "Rau muống", category: "rau", servings: 4, ingredients: [] },
      { id: "r-canh-1", name: "Canh chua", category: "canh", servings: 4, ingredients: [] },
    ];
    const meal1 = {
      id: "meal-1",
      planned_for: "2026-10-26",
      meal_period: "lunch",
      dishes: [
        { id: "d1", recipe_id: "r-man-1", recipe_name: "Thịt kho", category: "man", is_leftover: false },
        { id: "d2", recipe_id: "r-rau-1", recipe_name: "Rau muống", category: "rau", is_leftover: false },
        { id: "d3", recipe_id: "r-canh-1", recipe_name: "Canh chua", category: "canh", is_leftover: false },
      ],
    };
    const meal2 = {
      id: "meal-2",
      planned_for: "2026-10-26",
      meal_period: "dinner",
      dishes: [
        { id: "d4", recipe_id: "r-man-1", recipe_name: "Thịt kho", category: "man", is_leftover: false },
      ],
    };

    const updated = regenerateSingleMeal("meal-2", [meal1, meal2], recipes, []);
    assert.equal(updated.id, "meal-2");
    // r-man-1 đã nấu ở meal1 nên meal2 phải chọn r-man-2
    const manDish = updated.dishes.find((d) => d.category === "man");
    assert.equal(manDish.recipe_id, "r-man-2");
  });

  it("B4: calculateShoppingBudget sums only items with user prices", () => {
    const items = [
      { id: "1", ingredient_name: "Thịt bò", price: "80000", is_bought: true },
      { id: "2", ingredient_name: "Rau cải", price: "12000", is_bought: false },
      { id: "3", ingredient_name: "Muối", price: null, is_bought: false },
    ];
    const budget = calculateShoppingBudget(items);
    assert.equal(budget.total_estimated_budget, "92000");
    assert.equal(budget.total_spent, "80000");
    assert.equal(budget.items_with_price_count, 2);
    assert.equal(budget.total_items_count, 3);
  });

  it("B3: groupShoppingItemsByCategory correctly buckets items", () => {
    const items = [
      { id: "1", ingredient_name: "Thịt gà", category: "gia_cam" },
      { id: "2", ingredient_name: "Rau ngót", category: "rau_cu" },
      { id: "3", ingredient_name: "Chảo chống dính", category: "khac" },
    ];
    const grouped = groupShoppingItemsByCategory(items);
    assert.equal(grouped.gia_cam.length, 1);
    assert.equal(grouped.rau_cu.length, 1);
    assert.equal(grouped.khac.length, 1);
  });

  it("B1 & B2: swapDishInMeal replaces specific dish and enforces eaten history protection", () => {
    const meal = {
      id: "m1",
      planned_for: "2026-10-26",
      meal_period: "lunch",
      dishes: [
        { id: "d1", recipe_id: "r1", recipe_name: "Thịt heo luộc", category: "man" },
        { id: "d2", recipe_id: "r2", recipe_name: "Rau luộc", category: "rau" },
      ],
    };
    const newRecipe = { id: "r3", name: "Sườn xào chua ngọt", category: "man", servings: 4 };

    // Đổi món thành công
    const swapped = swapDishInMeal(meal, "d1", newRecipe, [meal]);
    assert.equal(swapped.dishes.length, 2);
    assert.equal(swapped.dishes[0].recipe_id, "r3");
    assert.equal(swapped.dishes[0].recipe_name, "Sườn xào chua ngọt");

    // Đã ăn -> ném lỗi
    const eatenMeal = { ...meal, eaten_at: "2026-10-26T12:00:00Z" };
    assert.throws(
      () => swapDishInMeal(eatenMeal, "d1", newRecipe, [eatenMeal]),
      /đã được đánh dấu ăn/
    );
  });

  it("B1 & B2: addDishToMeal respects category max limit and removeDishFromMeal prevents empty meal", () => {
    const meal = {
      id: "m1",
      planned_for: "2026-10-26",
      meal_period: "lunch",
      dishes: [
        { id: "d1", recipe_id: "r1", recipe_name: "Thịt kho", category: "man" },
      ],
    };
    const man2 = { id: "r2", name: "Gà kho", category: "man", servings: 4 };
    const man3 = { id: "r3", name: "Bò xào", category: "man", servings: 4 };

    // Thêm món thứ 2 thành công
    const with2 = addDishToMeal(meal, man2);
    assert.equal(with2.dishes.length, 2);

    // Thêm món thứ 3 cùng nhóm mặn -> ném lỗi
    assert.throws(() => addDishToMeal(with2, man3), /tối đa 2 món/);

    // Bỏ món
    const with1 = removeDishFromMeal(with2, with2.dishes[1].id);
    assert.equal(with1.dishes.length, 1);

    // Bỏ món duy nhất còn lại -> ném lỗi
    assert.throws(() => removeDishFromMeal(with1, with1.dishes[0].id), /món duy nhất/);
  });

  it("B1 & B2: rescheduleMeal changes date and checks conflict", () => {
    const m1 = { id: "m1", planned_for: "2026-10-26", meal_period: "lunch", dishes: [] };
    const m2 = { id: "m2", planned_for: "2026-10-27", meal_period: "dinner", dishes: [] };

    // Chuyển hợp lệ
    const moved = rescheduleMeal(m1, "2026-10-28", "lunch", [m1, m2]);
    assert.equal(moved.planned_for, "2026-10-28");

    // Trùng lịch với m2 -> ném lỗi xung đột
    assert.throws(() => rescheduleMeal(m1, "2026-10-27", "dinner", [m1, m2]), /Đã có bữa ăn khác/);
  });

  it("B3: mergeCompatibleShoppingItems merges same ingredient within same dimension", () => {
    const items = [
      { ingredient_id: "ing1", ingredient_name: "Đường", needed_quantity: "200", unit: "g", price: "10000" },
      { ingredient_id: "ing1", ingredient_name: "Đường", needed_quantity: "0.5", unit: "kg", price: "25000" },
    ];
    const merged = mergeCompatibleShoppingItems(items);
    assert.equal(merged.length, 1);
    assert.equal(merged[0].needed_quantity, "700");
    assert.equal(merged[0].unit, "g");
    assert.equal(merged[0].price, "35000");
  });
});
