import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  regenerateSingleMeal,
  recomputeShoppingList,
  calculateShoppingBudget,
  groupShoppingItemsByCategory,
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
});
