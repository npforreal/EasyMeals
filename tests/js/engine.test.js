/**
 * Test equivalence between Python domain engine and JavaScript engine.js.
 *
 * Runs on shared fixture: tests/fixtures/engine_test_cases.json
 */

import { test, describe } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  Decimal,
  convertQuantity,
  checkRecipeStock,
  deductRecipeStockFifo,
  reverseStockMovements,
  generatePeriodPlan,
} from "../../app/static/js/engine.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const FIXTURE_PATH = path.resolve(__dirname, "../fixtures/engine_test_cases.json");

describe("Engine Equivalence Tests (Python vs JavaScript on Shared Fixture)", () => {
  const fixture = JSON.parse(fs.readFileSync(FIXTURE_PATH, "utf-8"));

  test("1. Unit conversions match Python Decimal exactly", () => {
    for (const item of fixture.unit_conversions) {
      const res = convertQuantity(item.quantity, item.from_unit, item.to_unit);
      assert.equal(
        res.toString(),
        item.expected,
        `Conversion ${item.quantity} ${item.from_unit} -> ${item.to_unit} must match ${item.expected}`
      );
    }
  });

  test("2. FIFO Stock Deduction matches Python exactly", () => {
    const fifoData = fixture.fifo_deduction;

    // Check stock
    const { canCook, deficits } = checkRecipeStock(fifoData.recipe, fifoData.pantry);
    assert.equal(canCook, fifoData.check_stock_expected.can_cook);
    assert.equal(Object.keys(deficits).length, fifoData.check_stock_expected.deficits_count);

    // Deduct stock
    const { updatedLots, movements } = deductRecipeStockFifo(
      fifoData.pantry,
      fifoData.recipe,
      "bbbbbbbb-0001-0000-0000-000000000001",
      "fifo_test"
    );

    const expLots = fifoData.deduction_expected.updated_lots;
    assert.equal(updatedLots.length, expLots.length);

    for (let i = 0; i < updatedLots.length; i++) {
      assert.equal(updatedLots[i].id, expLots[i].id);
      assert.equal(
        updatedLots[i].remaining_quantity,
        expLots[i].remaining_quantity,
        `Lot ${updatedLots[i].id} remaining quantity must match Python Decimal`
      );
    }

    const expMovs = fifoData.deduction_expected.movements;
    assert.equal(movements.length, expMovs.length);
    for (let i = 0; i < movements.length; i++) {
      assert.equal(movements[i].pantry_lot_id, expMovs[i].pantry_lot_id);
      assert.equal(movements[i].quantity_delta, expMovs[i].quantity_delta);
      assert.equal(movements[i].reason, expMovs[i].reason);
    }
  });

  test("3. Undo Consumption matches Python reversal exactly", () => {
    const fifoData = fixture.fifo_deduction;
    const undoData = fixture.undo_consumption;

    const { updatedLots, movements } = deductRecipeStockFifo(
      fifoData.pantry,
      fifoData.recipe,
      "bbbbbbbb-0001-0000-0000-000000000001",
      "fifo_test"
    );

    const { restoredLots, reversalMovements } = reverseStockMovements(
      updatedLots,
      movements,
      "bbbbbbbb-0001-0000-0000-000000000001"
    );

    assert.equal(restoredLots.length, undoData.restored_lots.length);
    for (let i = 0; i < restoredLots.length; i++) {
      assert.equal(restoredLots[i].id, undoData.restored_lots[i].id);
      assert.equal(
        restoredLots[i].remaining_quantity,
        undoData.restored_lots[i].remaining_quantity,
        `Restored lot ${restoredLots[i].id} remaining quantity must match Python`
      );
    }
  });

  test("4. Meal Planner Generation matches Python plan and shopping list", () => {
    const planData = fixture.planner_generation;

    const result = generatePeriodPlan(
      planData.start_date,
      planData.end_date,
      planData.recipes,
      planData.pantry,
      { allow_leftovers: true }
    );

    assert.equal(result.meals.length, planData.expected_meals_count);

    for (let m = 0; m < result.meals.length; m++) {
      const actualDishes = result.meals[m].dishes;
      const expDishes = planData.expected_dishes_per_meal[m];
      assert.equal(actualDishes.length, expDishes.length);

      for (let d = 0; d < actualDishes.length; d++) {
        assert.equal(actualDishes[d].recipe_name, expDishes[d].recipe_name);
        assert.equal(actualDishes[d].category, expDishes[d].category);
        assert.equal(actualDishes[d].is_leftover, expDishes[d].is_leftover);
      }
    }

    // Verify shopping items
    const sortedActualShopping = [...result.shopping_list].sort((a, b) =>
      a.ingredient_id.localeCompare(b.ingredient_id)
    );
    const expShopping = planData.expected_shopping_items;
    assert.equal(sortedActualShopping.length, expShopping.length);

    for (let s = 0; s < sortedActualShopping.length; s++) {
      assert.equal(sortedActualShopping[s].ingredient_id, expShopping[s].ingredient_id);
      assert.equal(
        sortedActualShopping[s].needed_quantity,
        expShopping[s].needed_quantity,
        `Shopping item ${sortedActualShopping[s].ingredient_name} quantity must match Python Decimal`
      );
      assert.equal(sortedActualShopping[s].unit, expShopping[s].unit);
    }
  });
});
