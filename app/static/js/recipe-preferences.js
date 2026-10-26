/** Apply local recipe preferences to catalogue records without name matching. */
export function filterRecipesByPreferences(recipes, preferences = {}, category = "") {
  const avoided = new Set(preferences.avoidedIngredientIds || []);
  const preferred = new Set(preferences.preferredIngredientIds || []);
  const filtered = (recipes || []).filter((recipe) => {
    if (category && recipe.category !== category) return false;
    if ((recipe.ingredients || []).some((item) => avoided.has(item.ingredient_id))) return false;
    if (preferences.diet && (
      recipe.dietary_status !== preferences.diet ||
      !recipe.dietary_source_url ||
      !recipe.dietary_verified_at
    )) return false;
    if (preferences.maxSpice !== "" && preferences.maxSpice != null) {
      const maxSpice = Number(preferences.maxSpice);
      if (!Number.isInteger(recipe.spice_level) || recipe.spice_level > maxSpice ||
        !recipe.spice_source_url || !recipe.spice_verified_at) return false;
    }
    return true;
  });
  return filtered.sort((a, b) => {
    const score = (recipe) => (recipe.ingredients || []).filter((item) => preferred.has(item.ingredient_id)).length;
    return score(b) - score(a);
  });
}
