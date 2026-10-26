import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { generatePeriodPlan } from "../../app/static/js/engine.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const fixture = JSON.parse(fs.readFileSync(path.resolve(here, "../fixtures/planner_preferences.json"), "utf-8"));

test("shared planner preference fixture prioritizes soon-expiring stock", () => {
  const end = fixture.reference_date;
  const { meals } = generatePeriodPlan(end, end, fixture.recipes, fixture.pantry, {
    allow_leftovers: fixture.allow_leftovers,
    household_settings: { household_size: 1, default_servings: 2, meal_periods: fixture.meal_periods },
    recently_cooked_recipe_ids: fixture.recently_cooked_recipe_ids,
  });
  const selected = meals[0].dishes.find((dish) => dish.category === "man");
  assert.equal(selected.recipe_id, fixture.expected_recipe_id);
  assert.equal(selected.selection_reason, fixture.expected_reason);

  const recency = fixture.recency_case;
  const withRecency = generatePeriodPlan(end, end, fixture.recipes, fixture.pantry, {
    allow_leftovers: fixture.allow_leftovers,
    household_settings: { household_size: 1, default_servings: 2, meal_periods: fixture.meal_periods },
    recently_cooked_recipe_ids: recency.recently_cooked_recipe_ids,
  });
  const varied = withRecency.meals[0].dishes.find((dish) => dish.category === "man");
  assert.equal(varied.recipe_id, recency.expected_recipe_id);
  assert.equal(varied.selection_reason, recency.expected_reason);
});
