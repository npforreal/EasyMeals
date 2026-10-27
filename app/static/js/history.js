/**
 * EasyMeals — Lịch sử & thống kê (F1 - Vòng 13).
 *
 * Mô-đun THUẦN (không đọc IndexedDB, không gọi mạng) để:
 * - Điền ngược khoá ngoại cho biến động kho cũ (migration v2 -> v3);
 * - Tổng hợp lịch sử bữa đã nấu, biến động kho, đồ dư và chi tiêu đã nhập.
 *
 * Quy ước dữ liệu (theo quyết định schema F1 ngày 2026-10-27):
 * - Biến động kho chỉ thêm khoá ngoại tuỳ chọn: `ingredient_id`, `recipe_id`,
 *   `leftover_source_meal_id`. KHÔNG lưu bản sao tên nguyên liệu/món ăn.
 * - Toàn bộ tính toán chạy trên thiết bị; không có API nào nhận dữ liệu lịch sử.
 */

export const HISTORY_SCHEMA_VERSION = 1;
export const DEFAULT_WINDOW_DAYS = 30;

function isObject(value) {
  return value != null && typeof value === "object";
}

function toIsoDate(value) {
  if (typeof value !== "string" || value.length < 10) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return value.slice(0, 10);
}

function dayKey(value) {
  return toIsoDate(value);
}

function safeNumber(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

/**
 * Điền `ingredient_id` (từ lô kho) và `recipe_id` (khi bữa chỉ có một món không phải
 * đồ dư) cho biến động cũ. Không ghi đè giá trị đã có, không xoá bản ghi nào.
 *
 * @returns {{movements: Array<object>, changed: boolean}}
 */
export function backfillMovementIds(movements, lots = [], plans = []) {
  const lotById = new Map();
  for (const lot of Array.isArray(lots) ? lots : []) {
    if (isObject(lot) && typeof lot.id === "string") lotById.set(lot.id, lot);
  }

  const planById = new Map();
  for (const plan of Array.isArray(plans) ? plans : []) {
    if (isObject(plan) && typeof plan.id === "string") planById.set(plan.id, plan);
  }

  let changed = false;
  const result = (Array.isArray(movements) ? movements : []).map((movement) => {
    if (!isObject(movement)) return movement;
    const next = { ...movement };

    if (!next.ingredient_id) {
      const lot = lotById.get(next.pantry_lot_id);
      if (lot && typeof lot.ingredient_id === "string" && lot.ingredient_id) {
        next.ingredient_id = lot.ingredient_id;
        changed = true;
      }
    }

    if (!next.recipe_id && next.meal_plan_id) {
      const plan = planById.get(next.meal_plan_id);
      const dishes = Array.isArray(plan?.dishes) ? plan.dishes : [];
      const cooked = dishes.filter((dish) => isObject(dish) && !dish.is_leftover);
      if (cooked.length === 1 && typeof cooked[0].recipe_id === "string" && cooked[0].recipe_id) {
        next.recipe_id = cooked[0].recipe_id;
        changed = true;
      }
    }

    return next;
  });

  return { movements: result, changed };
}

/**
 * Tổng hợp lịch sử từ trạng thái cục bộ.
 *
 * @param {object} state
 * @param {Array<object>} [state.plans] Kế hoạch bữa ăn (MealPlan).
 * @param {Array<object>} [state.movements] Biến động kho (StockMovement).
 * @param {Array<object>} [state.pantryLots] Lô trong tủ.
 * @param {Array<object>} [state.recipes] Danh mục món (để lấy tên).
 * @param {Date|string} [state.now] Mốc "hiện tại" (cho test và đơn vị ngày).
 * @param {number} [state.windowDays=30] Cửa sổ thống kê (ngày).
 */
export function buildHistorySummary(state = {}) {
  const plans = Array.isArray(state.plans) ? state.plans : [];
  const movements = Array.isArray(state.movements) ? state.movements : [];
  const lots = Array.isArray(state.pantryLots) ? state.pantryLots : [];
  const recipes = Array.isArray(state.recipes) ? state.recipes : [];

  const nowDate = state.now instanceof Date ? state.now : new Date(state.now ?? Date.now());
  const windowDays = Number.isInteger(state.windowDays) && state.windowDays > 0
    ? state.windowDays
    : DEFAULT_WINDOW_DAYS;

  const toDay = Number.isNaN(nowDate.getTime())
    ? new Date().toISOString().slice(0, 10)
    : nowDate.toISOString().slice(0, 10);
  const fromDate = new Date(`${toDay}T00:00:00Z`);
  fromDate.setUTCDate(fromDate.getUTCDate() - (windowDays - 1));
  const fromDay = fromDate.toISOString().slice(0, 10);

  const inWindow = (value) => {
    const day = dayKey(value);
    return day != null && day >= fromDay && day <= toDay;
  };

  const recipeName = new Map();
  for (const recipe of recipes) {
    if (isObject(recipe) && typeof recipe.id === "string") {
      recipeName.set(recipe.id, recipe.name || recipe.id);
    }
  }
  // Dự phòng: dùng tên đã lưu trong thực đơn khi danh mục không còn món đó.
  for (const plan of plans) {
    for (const dish of Array.isArray(plan?.dishes) ? plan.dishes : []) {
      if (!isObject(dish) || typeof dish.recipe_id !== "string") continue;
      if (!recipeName.has(dish.recipe_id) && dish.recipe_name) {
        recipeName.set(dish.recipe_id, dish.recipe_name);
      }
    }
  }

  // ---- Bữa đã nấu ----
  const eatenPlans = plans
    .filter((plan) => isObject(plan) && typeof plan.eaten_at === "string" && plan.eaten_at)
    .sort((a, b) => String(b.eaten_at).localeCompare(String(a.eaten_at)));

  const meals = eatenPlans.map((plan) => {
    const dishes = Array.isArray(plan.dishes) ? plan.dishes.filter(isObject) : [];
    const cookedDishes = dishes.filter((dish) => !dish.is_leftover);
    const leftoverDishes = dishes.filter((dish) => dish.is_leftover);
    return {
      plan_id: plan.id,
      planned_for: dayKey(plan.planned_for),
      meal_period: plan.meal_period || "",
      eaten_at: plan.eaten_at,
      dish_names: cookedDishes.map((dish) => dish.recipe_name || recipeName.get(dish.recipe_id) || dish.recipe_id || ""),
      recipe_ids: cookedDishes.map((dish) => dish.recipe_id).filter((id) => typeof id === "string" && id),
      servings_total: cookedDishes.reduce((sum, dish) => sum + (Number.isFinite(Number(dish.servings)) ? Number(dish.servings) : 0), 0),
      leftover_reuse_count: leftoverDishes.length,
    };
  });

  const mealsInWindow = meals.filter((meal) => inWindow(meal.eaten_at));

  const recipeCounts = new Map();
  for (const meal of mealsInWindow) {
    meal.recipe_ids.forEach((id) => recipeCounts.set(id, (recipeCounts.get(id) || 0) + 1));
  }
  const topRecipes = [...recipeCounts.entries()]
    .map(([recipeId, count]) => ({
      recipe_id: recipeId,
      name: recipeName.get(recipeId) || recipeId,
      count,
    }))
    .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name))
    .slice(0, 5);

  // ---- Biến động kho ----
  const byReason = {};
  let movementsInWindow = 0;
  let consumedCount = 0;
  let restoredCount = 0;
  for (const movement of movements) {
    if (!isObject(movement)) continue;
    const reason = typeof movement.reason === "string" ? movement.reason : "unknown";
    byReason[reason] = (byReason[reason] || 0) + 1;
    if (!inWindow(movement.created_at)) continue;
    movementsInWindow += 1;
    const delta = safeNumber(movement.quantity_delta);
    if (delta < 0) consumedCount += 1;
    if (delta > 0) restoredCount += 1;
  }

  // ---- Đồ dư & lãng phí ----
  const leftoverReuse = mealsInWindow.reduce((sum, meal) => sum + meal.leftover_reuse_count, 0);

  const expired = lots
    .filter((lot) => isObject(lot))
    .filter((lot) => {
      const expiry = dayKey(lot.expires_at);
      return expiry != null && expiry < toDay && safeNumber(lot.remaining_quantity) > 0;
    })
    .map((lot) => ({
      lot_id: lot.id,
      ingredient_id: lot.ingredient_id,
      ingredient_name: lot.ingredient_name || "",
      remaining_quantity: String(lot.remaining_quantity ?? "0"),
      unit: lot.unit || "",
      expires_at: dayKey(lot.expires_at),
    }))
    .sort((a, b) => String(a.expires_at).localeCompare(String(b.expires_at)));

  // ---- Chi tiêu đã nhập ----
  // Giá chỉ có khi người dùng nhập ở danh sách đi chợ và món đó đã được "cho vào tủ".
  let spendingTotal = 0;
  let lotsWithPrice = 0;
  let lotsMissingPrice = 0;
  let spendingInWindow = 0;
  for (const lot of lots) {
    if (!isObject(lot)) continue;
    const boughtAt = dayKey(lot.purchased_at);
    const price = lot.price == null ? null : Number(lot.price);
    const hasPrice = price != null && Number.isFinite(price) && price >= 0;
    if (hasPrice) {
      lotsWithPrice += 1;
      spendingTotal += price;
      if (boughtAt && inWindow(boughtAt)) spendingInWindow += price;
    } else {
      lotsMissingPrice += 1;
    }
  }

  return {
    schema_version: HISTORY_SCHEMA_VERSION,
    window_days: windowDays,
    from: fromDay,
    to: toDay,
    cooked: {
      total: meals.length,
      in_window: mealsInWindow.length,
      last_eaten_at: meals.length ? meals[0].eaten_at : null,
      meals: meals.slice(0, 30),
      top_recipes: topRecipes,
    },
    stock: {
      total_movements: movements.filter(isObject).length,
      in_window: movementsInWindow,
      consumed_count: consumedCount,
      restored_count: restoredCount,
      by_reason: byReason,
    },
    leftovers: {
      reused_dishes_in_window: leftoverReuse,
      available: mealsInWindow.length > 0,
    },
    waste: {
      tracked: false,
      expired_lot_count: expired.length,
      expired_lots: expired.slice(0, 20),
    },
    spending: {
      currency: "VND",
      total: spendingTotal,
      in_window: spendingInWindow,
      lots_with_price: lotsWithPrice,
      lots_missing_price: lotsMissingPrice,
    },
  };
}
