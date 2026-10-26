import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { filterRecipesByPreferences, filterRecipesForBrowse } from "../../app/static/js/recipe-preferences.js";

const base = (id, ingredientId, extra = {}) => ({
  id,
  category: "man",
  ingredients: [{ ingredient_id: ingredientId }],
  dietary_status: "unknown",
  spice_level: null,
  ...extra,
});

describe("recipe preference filters", () => {
  it("excludes by canonical ingredient ID and ranks liked ingredients", () => {
    const recipes = [base("a", "avoided"), base("b", "liked"), base("c", "other")];
    const result = filterRecipesByPreferences(recipes, {
      avoidedIngredientIds: ["avoided"],
      preferredIngredientIds: ["liked"],
    });
    assert.deepEqual(result.map((recipe) => recipe.id), ["b", "c"]);
  });

  it("fails closed for missing or unverified dietary and spice metadata", () => {
    const verified = base("verified", "x", {
      dietary_status: "vegetarian",
      dietary_source_url: "https://example.test/source",
      dietary_verified_at: "2026-10-26",
      spice_level: 1,
      spice_source_url: "https://example.test/spice",
      spice_verified_at: "2026-10-26",
    });
    const unknown = base("unknown", "y", { dietary_status: "vegetarian" });
    assert.deepEqual(
      filterRecipesByPreferences([verified, unknown], { diet: "vegetarian", maxSpice: "2" }).map((r) => r.id),
      ["verified"],
    );
  });
});

describe("recipe browsing filters", () => {
  const recipes = [
    { id: "soup", name: "Canh chua cá", ingredients: [{ ingredient_id: "tomato", ingredient_name: "Cà chua" }, { ingredient_id: "fish", ingredient_name: "Cá lóc" }] },
    { id: "stir-fry", name: "Rau xào", ingredients: [{ ingredient_id: "greens", ingredient_name: "Rau muống" }] },
  ];

  it("searches recipe and ingredient names with or without Vietnamese diacritics", () => {
    assert.deepEqual(filterRecipesForBrowse(recipes, { query: "ca chua" }).map((r) => r.id), ["soup"]);
    assert.deepEqual(filterRecipesForBrowse(recipes, { query: "Cà chua" }).map((r) => r.id), ["soup"]);
  });

  it("requires every selected ingredient and excludes any matching canonical ID", () => {
    assert.deepEqual(filterRecipesForBrowse(recipes, { includeIngredientIds: ["tomato", "fish"] }).map((r) => r.id), ["soup"]);
    assert.deepEqual(filterRecipesForBrowse(recipes, { excludeIngredientIds: ["fish"] }).map((r) => r.id), ["stir-fry"]);
  });
});
