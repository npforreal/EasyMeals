/**
 * EasyMeals Computational Engine (Client-side / Mobile Offline).
 *
 * Implements deterministic domain logic with exact Decimal arithmetic:
 * - Unit conversions (g <-> kg, ml <-> l, piece <-> piece)
 * - Pantry stock evaluation and FIFO recipe stock deduction
 * - Stock movement reversal (Undo meal consumption)
 * - Meal plan generation with no-repeat rule, leftover reuse, and shopping list
 */

const SCALE = 1000000n; // 6 decimal places fixed-point BigInt
const SCALE_INT = 1000000;

export class Decimal {
  constructor(value) {
    if (typeof value === "bigint") {
      this.val = value;
    } else if (typeof value === "number") {
      this.val = BigInt(Math.round(value * SCALE_INT));
    } else if (typeof value === "string") {
      const trimmed = value.trim();
      const parts = trimmed.split(".");
      const sign = parts[0].startsWith("-") ? -1n : 1n;
      const intStr = parts[0].replace("-", "");
      const intPart = BigInt(intStr || "0") * SCALE;
      let fracPart = 0n;
      if (parts.length > 1) {
        const fracStr = parts[1].padEnd(6, "0").slice(0, 6);
        fracPart = BigInt(fracStr);
      }
      this.val = sign * (intPart + fracPart);
    } else if (value instanceof Decimal) {
      this.val = value.val;
    } else {
      this.val = 0n;
    }
  }

  static from(v) {
    return v instanceof Decimal ? v : new Decimal(v);
  }

  add(other) {
    return new Decimal(this.val + Decimal.from(other).val);
  }

  sub(other) {
    return new Decimal(this.val - Decimal.from(other).val);
  }

  mul(other) {
    return new Decimal((this.val * Decimal.from(other).val) / SCALE);
  }

  div(other) {
    const o = Decimal.from(other).val;
    if (o === 0n) throw new Error("Phép chia cho 0");
    return new Decimal((this.val * SCALE) / o);
  }

  cmp(other) {
    const diff = this.val - Decimal.from(other).val;
    if (diff > 0n) return 1;
    if (diff < 0n) return -1;
    return 0;
  }

  eq(other) {
    return this.cmp(other) === 0;
  }

  gt(other) {
    return this.cmp(other) > 0;
  }

  gte(other) {
    return this.cmp(other) >= 0;
  }

  lt(other) {
    return this.cmp(other) < 0;
  }

  lte(other) {
    return this.cmp(other) <= 0;
  }

  abs() {
    return new Decimal(this.val < 0n ? -this.val : this.val);
  }

  toString() {
    const isNeg = this.val < 0n;
    const absVal = isNeg ? -this.val : this.val;
    const intPart = (absVal / SCALE).toString();
    const fracPart = (absVal % SCALE).toString().padStart(6, "0");
    const trimmedFrac = fracPart.replace(/0+$/, "");
    const sign = isNeg ? "-" : "";
    if (!trimmedFrac) {
      return `${sign}${intPart}`;
    }
    return `${sign}${intPart}.${trimmedFrac}`;
  }

  toJSON() {
    return this.toString();
  }
}

export class IncompatibleUnitError extends Error {
  constructor(message) {
    super(message);
    this.name = "IncompatibleUnitError";
  }
}

export class InsufficientStockError extends Error {
  constructor(message, deficits = {}) {
    super(message);
    this.name = "InsufficientStockError";
    this.deficits = deficits;
  }
}

export const UNIT_DIMENSIONS = {
  g: "mass",
  kg: "mass",
  ml: "volume",
  l: "volume",
  piece: "count",
};

export const UNIT_BASE_MULTIPLIER = {
  g: new Decimal("1"),
  kg: new Decimal("1000"),
  ml: new Decimal("1"),
  l: new Decimal("1000"),
  piece: new Decimal("1"),
};

export function convertQuantity(quantity, fromUnit, toUnit) {
  const q = Decimal.from(quantity);
  if (fromUnit === toUnit) {
    return q;
  }

  const dimFrom = UNIT_DIMENSIONS[fromUnit];
  const dimTo = UNIT_DIMENSIONS[toUnit];

  if (!dimFrom || !dimTo || dimFrom !== dimTo) {
    throw new IncompatibleUnitError(
      `Không thể chuyển đổi đơn vị '${fromUnit}' (${dimFrom || "không rõ"}) ` +
      `sang '${toUnit}' (${dimTo || "không rõ"}) vì khác thứ nguyên.`
    );
  }

  const baseQty = q.mul(UNIT_BASE_MULTIPLIER[fromUnit]);
  const targetQty = baseQty.div(UNIT_BASE_MULTIPLIER[toUnit]);
  return targetQty;
}

export function unitsCompatible(a, b) {
  const da = UNIT_DIMENSIONS[a];
  const db = UNIT_DIMENSIONS[b];
  return Boolean(da) && da === db;
}

/**
 * Gộp các dòng nguyên liệu trùng nhau (cùng nguyên liệu, cùng thứ nguyên) của công thức.
 * Trả về mảng {ingredient_id, name, quantity: Decimal, unit}.
 */
export function aggregateRequirements(recipe, multiplier = "1") {
  const mult = Decimal.from(multiplier);
  const merged = new Map();
  for (const req of recipe.ingredients) {
    const qty = Decimal.from(req.quantity).mul(mult);
    const key = `${req.ingredient_id}|${UNIT_DIMENSIONS[req.unit]}`;
    const prev = merged.get(key);
    if (prev) {
      prev.quantity = prev.quantity.add(convertQuantity(qty, req.unit, prev.unit));
    } else {
      merged.set(key, {
        ingredient_id: req.ingredient_id,
        name: req.ingredient_name,
        quantity: qty,
        unit: req.unit,
      });
    }
  }
  return Array.from(merged.values());
}

function lotSortKeyFor(lot) {
  const exp = lot.expires_at ? lot.expires_at : "9999-12-31";
  const pur = lot.purchased_at ? lot.purchased_at : "1970-01-01";
  return `${exp}_${pur}`;
}

/**
 * Tổng tồn kho của nguyên liệu quy về targetUnit. Lô khác thứ nguyên bị bỏ qua
 * (không thể quy đổi nên không được tính là đủ hàng) thay vì làm hỏng cả phép tính.
 */
export function getTotalIngredientStock(pantryLots, ingredientId, targetUnit) {
  let total = new Decimal(0);
  for (const lot of pantryLots) {
    if (lot.ingredient_id !== ingredientId || !unitsCompatible(lot.unit, targetUnit)) continue;
    const rem = Decimal.from(lot.remaining_quantity);
    if (rem.gt(0)) {
      total = total.add(convertQuantity(rem, lot.unit, targetUnit));
    }
  }
  return total;
}

/**
 * Trừ tối đa `quantity` (FIFO, có quy đổi đơn vị) khỏi các lô, sửa trực tiếp
 * `remaining_quantity` của lô truyền vào. Trả về lượng đã trừ (Decimal).
 */
export function consumeAvailable(pantryLots, ingredientId, quantity, unit) {
  let needed = Decimal.from(quantity);
  let consumed = new Decimal(0);
  const ordered = [...pantryLots].sort((a, b) => lotSortKeyFor(a).localeCompare(lotSortKeyFor(b)));
  for (const lot of ordered) {
    if (needed.lte(0)) break;
    if (lot.ingredient_id !== ingredientId || !unitsCompatible(lot.unit, unit)) continue;
    const rem = Decimal.from(lot.remaining_quantity);
    if (rem.lte(0)) continue;
    const available = convertQuantity(rem, lot.unit, unit);
    const take = available.lt(needed) ? available : needed;
    const takeInLotUnit = take.eq(available) ? rem : convertQuantity(take, unit, lot.unit);
    lot.remaining_quantity = rem.sub(takeInLotUnit).toString();
    needed = needed.sub(take);
    consumed = consumed.add(take);
  }
  return consumed;
}

export function checkRecipeStock(recipe, pantryLots, multiplier = "1") {
  const deficits = {};

  for (const req of aggregateRequirements(recipe, multiplier)) {
    const available = getTotalIngredientStock(pantryLots, req.ingredient_id, req.unit);
    if (available.lt(req.quantity)) {
      deficits[req.ingredient_id] = {
        ingredient_name: req.name,
        missing_quantity: req.quantity.sub(available).toString(),
        unit: req.unit,
      };
    }
  }

  return {
    canCook: Object.keys(deficits).length === 0,
    deficits,
  };
}

function generateEngineUUID() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export function deductRecipeStockFifo(
  pantryLots,
  recipe,
  mealPlanId,
  idempotencyKey,
  multiplier = "1"
) {
  const { canCook, deficits } = checkRecipeStock(recipe, pantryLots, multiplier);
  if (!canCook) {
    throw new InsufficientStockError(
      `Không đủ nguyên liệu để nấu món '${recipe.name}'`,
      deficits
    );
  }

  const requirements = aggregateRequirements(recipe, multiplier);

  // Clone lots so we don't mutate input directly until successful
  const clonedLots = pantryLots.map((lot) => ({
    ...lot,
    remaining_quantity: Decimal.from(lot.remaining_quantity).toString(),
  }));

  // Sort lots by earliest expiration (null last), then earliest purchase
  const reqIngIds = new Set(requirements.map((r) => r.ingredient_id));
  const candidateLots = clonedLots.filter((lot) => reqIngIds.has(lot.ingredient_id));
  candidateLots.sort((x, y) => lotSortKeyFor(x).localeCompare(lotSortKeyFor(y)));

  const updatedLotsMap = new Map();
  const movements = [];

  for (const req of requirements) {
    let remainingNeeded = req.quantity;
    const ingredientLots = candidateLots.filter(
      (l) =>
        l.ingredient_id === req.ingredient_id &&
        unitsCompatible(l.unit, req.unit) &&
        Decimal.from(l.remaining_quantity).gt(0)
    );

    for (const lot of ingredientLots) {
      if (remainingNeeded.lte(0)) break;

      const lotRem = Decimal.from(lot.remaining_quantity);
      const lotAvailableInReqUnit = convertQuantity(lotRem, lot.unit, req.unit);

      let deductedLotUnit;
      if (lotAvailableInReqUnit.lte(remainingNeeded)) {
        // Deduct all
        const deductedReqUnit = lotAvailableInReqUnit;
        deductedLotUnit = lotRem;
        lot.remaining_quantity = "0";
        remainingNeeded = remainingNeeded.sub(deductedReqUnit);
      } else {
        // Partial deduction
        const deductedReqUnit = remainingNeeded;
        deductedLotUnit = convertQuantity(deductedReqUnit, req.unit, lot.unit);
        lot.remaining_quantity = lotRem.sub(deductedLotUnit).toString();
        remainingNeeded = new Decimal(0);
      }

      updatedLotsMap.set(lot.id, lot);
      movements.push({
        id: generateEngineUUID(),
        pantry_lot_id: lot.id,
        quantity_delta: `-${deductedLotUnit.toString()}`,
        reason: "meal_consumption",
        meal_plan_id: mealPlanId,
        idempotency_key: `${idempotencyKey}_${lot.id}`,
        created_at: new Date().toISOString(),
      });
    }
  }

  return {
    updatedLots: Array.from(updatedLotsMap.values()),
    movements,
  };
}

export function reverseStockMovements(pantryLots, movements, mealPlanId) {
  const lotMap = new Map(pantryLots.map((l) => [l.id, { ...l }]));
  const restoredLotsMap = new Map();
  const reversalMovements = [];

  // Bỏ qua các biến động đã được hoàn tác (có biến động `reversal_<id>`) để hoàn tác lặp lại
  // không cộng kho thêm lần nữa.
  const alreadyReversed = new Set(
    movements
      .filter((m) => typeof m.idempotency_key === "string" && m.idempotency_key.startsWith("reversal_"))
      .map((m) => m.idempotency_key.slice("reversal_".length))
  );
  const mealMovements = movements.filter(
    (m) =>
      m.meal_plan_id === mealPlanId &&
      m.reason === "meal_consumption" &&
      Decimal.from(m.quantity_delta).lt(0) &&
      !alreadyReversed.has(String(m.id))
  );

  for (const mov of mealMovements) {
    const lot = lotMap.get(mov.pantry_lot_id);
    if (!lot) continue;

    const deltaAbs = Decimal.from(mov.quantity_delta).abs();
    const currentRem = Decimal.from(lot.remaining_quantity);
    // Không vượt quá lượng đã mua ban đầu (khớp với engine Python).
    const restored = currentRem.add(deltaAbs);
    const cap = Decimal.from(lot.purchased_quantity);
    lot.remaining_quantity = (restored.gt(cap) ? cap : restored).toString();

    restoredLotsMap.set(lot.id, lot);
    reversalMovements.push({
      id: generateEngineUUID(),
      pantry_lot_id: lot.id,
      quantity_delta: deltaAbs.toString(),
      reason: "correction",
      meal_plan_id: mealPlanId,
      idempotency_key: `reversal_${mov.id}`,
      created_at: new Date().toISOString(),
    });
  }

  return {
    restoredLots: Array.from(restoredLotsMap.values()),
    reversalMovements,
  };
}

export function generatePeriodPlan(
  startDateStr,
  endDateStr,
  recipes,
  currentPantryLots,
  options = { allowLeftovers: true }
) {
  // Ngày dạng YYYY-MM-DD được hiểu là UTC; mọi phép tính ngày bên dưới đều dùng UTC để
  // không lệch ngày theo múi giờ hay giờ mùa hè.
  const start = new Date(`${startDateStr}T00:00:00Z`);
  const end = new Date(`${endDateStr}T00:00:00Z`);
  const diffDays = Math.round((end - start) / (1000 * 60 * 60 * 24)) + 1;

  if (diffDays <= 0) {
    throw new Error("Ngày kết thúc phải lớn hơn hoặc bằng ngày bắt đầu.");
  }

  const periodId = generateEngineUUID();
  const allowLeftovers = options.allow_leftovers !== false && options.allowLeftovers !== false;

  const recipesByCat = {
    man: recipes.filter((r) => r.category === "man"),
    rau: recipes.filter((r) => r.category === "rau"),
    canh: recipes.filter((r) => r.category === "canh"),
  };

  // Simulated lots for planning evaluation
  const simulatedLots = currentPantryLots.map((l) => ({
    ...l,
    remaining_quantity: Decimal.from(l.remaining_quantity).toString(),
  }));

  const cookedRecipeIds = new Set();
  const availableLeftovers = [];
  const mealPlans = [];
  const shoppingItemsMap = new Map(); // khoá: `${ingredient_id}|${thứ nguyên}`

  const periods = ["lunch", "dinner"];
  const curr = new Date(start);

  for (let d = 0; d < diffDays; d++) {
    const dateStr = curr.toISOString().split("T")[0];
    // Lô đã quá hạn tại ngày đang lập kế hoạch không được tính là có hàng
    // (cùng đối tượng với simulatedLots nên việc trừ kho mô phỏng vẫn có tác dụng).
    const usableLots = simulatedLots.filter((l) => !l.expires_at || l.expires_at >= dateStr);

    for (const period of periods) {
      const mealPlan = {
        id: generateEngineUUID(),
        planned_for: dateStr,
        meal_period: period,
        period_id: periodId,
        eaten_at: null,
        dishes: [],
      };

      for (const cat of ["man", "rau", "canh"]) {
        let dishChosen = null;

        // 1. Try to use leftover from earlier meals
        if (allowLeftovers && availableLeftovers.length > 0) {
          const leftIdx = availableLeftovers.findIndex((l) => l.category === cat);
          if (leftIdx !== -1) {
            const leftover = availableLeftovers.splice(leftIdx, 1)[0];
            dishChosen = {
              id: generateEngineUUID(),
              meal_plan_id: mealPlan.id,
              recipe_id: leftover.recipe_id,
              recipe_name: `${leftover.recipe_name} (Ăn lại)`,
              category: cat,
              is_leftover: true,
              original_dish_id: leftover.id,
              servings: leftover.servings,
            };
          }
        }

        // 2. Fresh recipe respecting no-repeat rule
        if (!dishChosen) {
          const candidateRecipes = recipesByCat[cat].filter((r) => !cookedRecipeIds.has(r.id));

          let fullyStockedRecipe = null;
          for (const r of candidateRecipes) {
            const { canCook } = checkRecipeStock(r, usableLots);
            if (canCook) {
              fullyStockedRecipe = r;
              break;
            }
          }

          let chosenRecipe = null;
          if (fullyStockedRecipe) {
            chosenRecipe = fullyStockedRecipe;
            // Trừ kho mô phỏng (có quy đổi đơn vị, theo FIFO)
            for (const req of aggregateRequirements(chosenRecipe)) {
              consumeAvailable(usableLots, req.ingredient_id, req.quantity, req.unit);
            }
          } else if (candidateRecipes.length > 0) {
            chosenRecipe = candidateRecipes[0];
            const { deficits } = checkRecipeStock(chosenRecipe, usableLots);
            // Phần đã có trong kho được dùng cho món này, để món sau không đếm lại.
            for (const req of aggregateRequirements(chosenRecipe)) {
              consumeAvailable(usableLots, req.ingredient_id, req.quantity, req.unit);
            }
            for (const [ingId, def] of Object.entries(deficits)) {
              const key = `${ingId}|${UNIT_DIMENSIONS[def.unit]}`;
              const item = shoppingItemsMap.get(key);
              if (!item) {
                shoppingItemsMap.set(key, {
                  ingredient_id: ingId,
                  ingredient_name: def.ingredient_name,
                  needed_quantity: def.missing_quantity,
                  unit: def.unit,
                  dish_names: [chosenRecipe.name],
                });
              } else {
                item.needed_quantity = Decimal.from(item.needed_quantity)
                  .add(convertQuantity(def.missing_quantity, def.unit, item.unit))
                  .toString();
                if (!item.dish_names.includes(chosenRecipe.name)) {
                  item.dish_names.push(chosenRecipe.name);
                }
              }
            }
          }

          if (chosenRecipe) {
            dishChosen = {
              id: generateEngineUUID(),
              meal_plan_id: mealPlan.id,
              recipe_id: chosenRecipe.id,
              recipe_name: chosenRecipe.name,
              category: cat,
              is_leftover: false,
              servings: chosenRecipe.servings,
            };
            cookedRecipeIds.add(chosenRecipe.id);

            // Leftover opportunity if recipe serves >= 4
            if (allowLeftovers && chosenRecipe.servings >= 4) {
              availableLeftovers.push(dishChosen);
            }
          }
        }

        if (dishChosen) {
          mealPlan.dishes.push(dishChosen);
        }
      }

      mealPlans.push(mealPlan);
    }

    curr.setUTCDate(curr.getUTCDate() + 1);
  }

  return {
    period_id: periodId,
    start_date: startDateStr,
    end_date: endDateStr,
    meals: mealPlans,
    shopping_list: Array.from(shoppingItemsMap.values()),
  };
}
