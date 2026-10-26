/**
 * Ca logic bổ sung dùng chung Python/JS (tests/fixtures/engine_logic_cases.json).
 * Python tương ứng: tests/test_engine_logic_cases.py. Hai bên phải cho cùng kết quả.
 */

import { test, describe } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  checkRecipeStock,
  deductRecipeStockFifo,
  deductRecipeStockAvailable,
  reverseStockMovements,
  generatePeriodPlan,
  mergeNewPlansIntoExisting,
  calculateShoppingBudget,
  Decimal,
} from "../../app/static/js/engine.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const { cases } = JSON.parse(
  fs.readFileSync(path.resolve(__dirname, "../fixtures/engine_logic_cases.json"), "utf-8")
);

const toRecipe = (r) => ({
  id: r.id,
  name: r.name,
  category: r.category,
  servings: r.servings,
  ingredients: r.ingredients.map((i) => ({
    ingredient_id: i.ingredient_id,
    ingredient_name: i.name,
    quantity: i.quantity,
    unit: i.unit,
  })),
});

const toLots = (items) =>
  items.map((x) => ({
    id: x.id,
    ingredient_id: x.ingredient_id,
    ingredient_name: x.name,
    purchased_quantity: x.purchased,
    remaining_quantity: x.remaining,
    unit: x.unit,
    purchased_at: "2025-12-01T00:00:00",
    expires_at: x.expires_at || null,
  }));

const norm = (v) => new Decimal(String(v)).toString();

describe("Ca logic dùng chung Python/JS", () => {
  for (const c of cases) {
    test(c.name, () => {
      if (c.op === "check") {
        const { canCook, deficits } = checkRecipeStock(
          toRecipe(c.recipe),
          toLots(c.pantry),
          c.multiplier,
          c.conversions
        );
        assert.equal(canCook, c.expect.can_cook);
        const got = Object.fromEntries(
          Object.entries(deficits).map(([k, v]) => [k, norm(v.missing_quantity)])
        );
        assert.deepEqual(got, c.expect.deficits);
      } else if (c.op === "fifo") {
        const lots = toLots(c.pantry);
        const res = deductRecipeStockFifo(
          lots,
          toRecipe(c.recipe),
          "plan-1",
          "key",
          c.multiplier,
          c.conversions
        );
        assert.ok(res.movements.length > 0);
        const remaining = Object.fromEntries(lots.map((l) => [l.id, norm(l.remaining_quantity)]));
        for (const u of res.updatedLots) remaining[u.id] = norm(u.remaining_quantity);
        assert.deepEqual(remaining, c.expect.remaining);
      } else if (c.op === "deduct_available") {
        const lots = toLots(c.pantry);
        const res = deductRecipeStockAvailable(
          lots,
          toRecipe(c.recipe),
          "plan-1",
          "key",
          c.multiplier,
          c.conversions
        );
        const remaining = Object.fromEntries(lots.map((l) => [l.id, norm(l.remaining_quantity)]));
        for (const u of res.updatedLots) remaining[u.id] = norm(u.remaining_quantity);
        assert.deepEqual(remaining, c.expect.remaining);

        const gotDeficits = Object.fromEntries(
          Object.entries(res.deficits).map(([k, v]) => [k, norm(v.missing_quantity)])
        );
        assert.deepEqual(gotDeficits, c.expect.deficits);

        const gotMovements = Object.fromEntries(
          res.movements.map((m) => [m.pantry_lot_id, norm(m.quantity_delta)])
        );
        assert.deepEqual(gotMovements, c.expect.movements);
      } else if (c.op === "undo") {
        const lots = toLots(c.pantry);
        const movements = c.movements.map((m) => ({
          id: m.id,
          pantry_lot_id: m.pantry_lot_id,
          quantity_delta: m.delta,
          reason: m.reason,
          meal_plan_id: m.meal_plan_id,
          idempotency_key: m.idempotency_key,
        }));
        const { restoredLots } = reverseStockMovements(lots, movements, c.meal_plan_id);
        const remaining = Object.fromEntries(lots.map((l) => [l.id, norm(l.remaining_quantity)]));
        for (const u of restoredLots) remaining[u.id] = norm(u.remaining_quantity);
        assert.deepEqual(remaining, c.expect.remaining);
      } else if (c.op === "merge_plans") {
        const kept = mergeNewPlansIntoExisting(c.existing, c.new_plans, c.mode || "replace");
        assert.deepEqual(
          kept.map((p) => String(p.id)),
          c.expect.kept_ids
        );
      } else if (c.op === "shopping_budget") {
        const budget = calculateShoppingBudget(c.items);
        assert.equal(norm(budget.total_estimated_budget), c.expect.total_estimated);
        assert.equal(norm(budget.total_spent), c.expect.total_spent);
        assert.equal(budget.items_with_price_count, c.expect.items_with_price_count);
        assert.equal(budget.total_items_count, c.expect.total_items_count);
      } else if (c.op === "plan" || c.op === "plan_avoided") {
        const end = new Date(`${c.start}T00:00:00Z`);
        end.setUTCDate(end.getUTCDate() + c.days - 1);
        const endStr = end.toISOString().slice(0, 10);
        if (c.expect && c.expect.error) {
          assert.throws(
            () => {
              generatePeriodPlan(
                c.start,
                endStr,
                c.recipes.map(toRecipe),
                toLots(c.pantry),
                {
                  allow_leftovers: c.allow_leftovers,
                  leftover_days: c.leftover_days,
                  conversions: c.conversions,
                }
              );
            },
            Error
          );
          return;
        }
        const plan = generatePeriodPlan(
          c.start,
          endStr,
          c.recipes.map(toRecipe),
          toLots(c.pantry),
          {
            allow_leftovers: c.allow_leftovers,
            leftover_days: c.leftover_days,
            conversions: c.conversions,
            avoided_ingredient_ids: c.op === "plan_avoided" ? c.avoided_ingredient_ids : [],
          }
        );
        const dishes = plan.meals.flatMap((m) => m.dishes);
        if (c.op === "plan_avoided") {
          const blocked = new Set(c.avoided_ingredient_ids);
          assert.equal(
            dishes.some((dish) => {
              const recipe = c.recipes.find((r) => r.id === dish.recipe_id);
              return recipe.ingredients.some((ingredient) => blocked.has(ingredient.ingredient_id));
            }),
            false,
          );
          assert.equal(plan.excluded_recipe_count, c.expect.excluded_recipe_count);
          assert.equal(plan.warnings.length, c.expect.warning_count);
          return;
        }
        assert.deepEqual(
          dishes.map((d) => d.recipe_name),
          c.expect.dishes
        );
        assert.deepEqual(
          dishes.map((d) => d.servings),
          c.expect.servings
        );
        const shopping = Object.fromEntries(
          plan.shopping_list.map((s) => [s.ingredient_id, [norm(s.needed_quantity), s.unit]])
        );
        assert.deepEqual(shopping, c.expect.shopping);
      } else {
        assert.fail(`op không hỗ trợ: ${c.op}`);
      }
    });
  }
});
