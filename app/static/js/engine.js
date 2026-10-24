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

export function getTotalIngredientStock(pantryLots, ingredientId, targetUnit) {
  let total = new Decimal(0);
  for (const lot of pantryLots) {
    if (lot.ingredient_id === ingredientId) {
      const rem = Decimal.from(lot.remaining_quantity);
      if (rem.gt(0)) {
        const converted = convertQuantity(rem, lot.unit, targetUnit);
        total = total.add(converted);
      }
    }
  }
  return total;
}

export function checkRecipeStock(recipe, pantryLots, multiplier = "1") {
  const mult = Decimal.from(multiplier);
  const deficits = {};

  for (const req of recipe.ingredients) {
    const requiredQty = Decimal.from(req.quantity).mul(mult);
    let available = new Decimal(0);
    try {
      available = getTotalIngredientStock(pantryLots, req.ingredient_id, req.unit);
    } catch (err) {
      if (err instanceof IncompatibleUnitError) {
        deficits[req.ingredient_id] = {
          ingredient_name: req.ingredient_name,
          missing_quantity: requiredQty.toString(),
          unit: req.unit,
        };
        continue;
      }
      throw err;
    }

    if (available.lt(requiredQty)) {
      const missing = requiredQty.sub(available);
      deficits[req.ingredient_id] = {
        ingredient_name: req.ingredient_name,
        missing_quantity: missing.toString(),
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

  const mult = Decimal.from(multiplier);

  // Clone lots so we don't mutate input directly until successful
  const clonedLots = pantryLots.map((lot) => ({
    ...lot,
    remaining_quantity: Decimal.from(lot.remaining_quantity).toString(),
  }));

  // Sort lots by earliest expiration (null last), then earliest purchase
  function lotSortKey(lot) {
    const exp = lot.expires_at ? lot.expires_at : "9999-12-31";
    const pur = lot.purchased_at ? lot.purchased_at : "1970-01-01";
    return `${exp}_${pur}`;
  }

  const reqIngIds = new Set(recipe.ingredients.map((i) => i.ingredient_id));
  const candidateLots = clonedLots.filter((lot) => reqIngIds.has(lot.ingredient_id));
  candidateLots.sort((a, b) => lotSortKey(a).localeCompare(lotSortKey(b)));

  const updatedLotsMap = new Map();
  const movements = [];

  for (const req of recipe.ingredients) {
    let remainingNeeded = Decimal.from(req.quantity).mul(mult);
    const ingredientLots = candidateLots.filter(
      (l) => l.ingredient_id === req.ingredient_id && Decimal.from(l.remaining_quantity).gt(0)
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

  const mealMovements = movements.filter(
    (m) => m.meal_plan_id === mealPlanId && m.reason === "meal_consumption"
  );

  for (const mov of mealMovements) {
    const lot = lotMap.get(mov.pantry_lot_id);
    if (!lot) continue;

    const deltaAbs = Decimal.from(mov.quantity_delta).abs();
    const currentRem = Decimal.from(lot.remaining_quantity);
    lot.remaining_quantity = currentRem.add(deltaAbs).toString();

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
  const start = new Date(startDateStr);
  const end = new Date(endDateStr);
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
  const shoppingItemsMap = new Map();

  const periods = ["lunch", "dinner"];
  const curr = new Date(start);

  for (let d = 0; d < diffDays; d++) {
    const dateStr = curr.toISOString().split("T")[0];

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
              servings: 1,
            };
          }
        }

        // 2. Fresh recipe respecting no-repeat rule
        if (!dishChosen) {
          const candidateRecipes = recipesByCat[cat].filter((r) => !cookedRecipeIds.has(r.id));

          let fullyStockedRecipe = null;
          for (const r of candidateRecipes) {
            const { canCook } = checkRecipeStock(r, simulatedLots);
            if (canCook) {
              fullyStockedRecipe = r;
              break;
            }
          }

          let chosenRecipe = null;
          if (fullyStockedRecipe) {
            chosenRecipe = fullyStockedRecipe;
            // Deduct from simulated stock
            for (const req of chosenRecipe.ingredients) {
              let needed = Decimal.from(req.quantity);
              for (const lot of simulatedLots) {
                if (lot.ingredient_id === req.ingredient_id) {
                  const rem = Decimal.from(lot.remaining_quantity);
                  if (rem.gt(0)) {
                    const take = rem.lt(needed) ? rem : needed;
                    lot.remaining_quantity = rem.sub(take).toString();
                    needed = needed.sub(take);
                    if (needed.lte(0)) break;
                  }
                }
              }
            }
          } else if (candidateRecipes.length > 0) {
            chosenRecipe = candidateRecipes[0];
            const { deficits } = checkRecipeStock(chosenRecipe, simulatedLots);
            for (const [ingId, def] of Object.entries(deficits)) {
              if (!shoppingItemsMap.has(ingId)) {
                shoppingItemsMap.set(ingId, {
                  ingredient_id: ingId,
                  ingredient_name: def.ingredient_name,
                  needed_quantity: def.missing_quantity,
                  unit: def.unit,
                  dish_names: [chosenRecipe.name],
                });
              } else {
                const item = shoppingItemsMap.get(ingId);
                item.needed_quantity = Decimal.from(item.needed_quantity)
                  .add(def.missing_quantity)
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
              servings: 1,
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

    curr.setDate(curr.getDate() + 1);
  }

  return {
    period_id: periodId,
    start_date: startDateStr,
    end_date: endDateStr,
    meals: mealPlans,
    shopping_list: Array.from(shoppingItemsMap.values()),
  };
}
