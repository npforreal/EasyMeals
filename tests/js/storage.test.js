/**
 * Tests for EasyMeals client storage layer (IndexedDB).
 *
 * Runs with Node.js built-in test runner (`node --test`) using `fake-indexeddb`.
 */

import { test, describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import "fake-indexeddb/auto"; // Injects indexedDB and IDBKeyRange into global scope

import { closeDB, clearAllPersonalData } from "../../app/static/js/db.js";
import {
  addPantryLot,
  getPantryLots,
  deletePantryLot,
  saveMealPlans,
  getMealPlanById,
  executeEatMealAtomic,
  executeUndoEatMealAtomic,
  getStockMovements,
  exportBackupJSON,
  validateBackupJSON,
  importBackupJSON,
  setCatalogueSource,
  syncCatalogue,
  getCachedCatalogue,
} from "../../app/static/js/storage.js";

describe("EasyMeals IndexedDB Storage Tests", () => {
  beforeEach(async () => {
    await clearAllPersonalData();
  });

  afterEach(() => {
    closeDB();
  });

  test("Pantry CRUD operations", async () => {
    // 1. Add pantry lots
    const lot1 = await addPantryLot({
      ingredient_id: "ing-001",
      ingredient_name: "Thịt ba chỉ",
      quantity: "500",
      unit: "g",
    });

    const lot2 = await addPantryLot({
      ingredient_id: "ing-002",
      ingredient_name: "Rau muống",
      quantity: "300",
      unit: "g",
    });

    assert.ok(lot1.id, "Lot 1 must have generated ID");
    assert.equal(lot1.remaining_quantity, "500");

    // 2. List pantry lots
    const lots = await getPantryLots();
    assert.equal(lots.length, 2);
    assert.ok(lots.some((l) => l.ingredient_id === "ing-001"));

    // 3. Delete a lot
    await deletePantryLot(lot1.id);
    const lotsAfterDelete = await getPantryLots();
    assert.equal(lotsAfterDelete.length, 1);
    assert.equal(lotsAfterDelete[0].id, lot2.id);
  });

  test("Atomic 'Đã ăn' transaction & double-click protection", async () => {
    // Setup initial pantry and planned meal
    const lot = await addPantryLot({
      ingredient_id: "ing-pork",
      ingredient_name: "Thịt ba chỉ",
      quantity: "1000",
      unit: "g",
    });

    const mealPlanId = "plan-meal-20261025";
    const initialPlan = {
      id: mealPlanId,
      planned_for: "2026-10-25",
      meal_period: "lunch",
      eaten_at: null,
      dishes: [{ recipe_name: "Thịt kho tàu" }],
    };
    await saveMealPlans([initialPlan]);

    // Prepare deduction
    const updatedLot = { ...lot, remaining_quantity: "500" };
    const movements = [
      {
        id: "mov-001",
        pantry_lot_id: lot.id,
        meal_plan_id: mealPlanId,
        quantity_delta: "-500",
        reason: "meal_consumption",
        created_at: new Date().toISOString(),
      },
    ];

    // 1. First execution succeeds
    await executeEatMealAtomic(mealPlanId, [updatedLot], movements);

    const savedPlan = await getMealPlanById(mealPlanId);
    assert.ok(savedPlan.eaten_at, "Plan eaten_at must be populated");

    const savedLots = await getPantryLots();
    assert.equal(savedLots[0].remaining_quantity, "500");

    const savedMovs = await getStockMovements();
    assert.equal(savedMovs.length, 1);
    assert.equal(savedMovs[0].quantity_delta, "-500");

    // 2. Second execution (e.g. double click or second tab) MUST fail and abort
    await assert.rejects(
      async () => {
        await executeEatMealAtomic(mealPlanId, [updatedLot], movements);
      },
      {
        message: /trước đó/,
      }
    );

    // Verify lots were not deducted a second time
    const lotsAfterSecondAttempt = await getPantryLots();
    assert.equal(lotsAfterSecondAttempt[0].remaining_quantity, "500");
  });

  test("Atomic 'Hoàn tác' transaction reverses meal consumption", async () => {
    const lot = await addPantryLot({
      ingredient_id: "ing-pork",
      ingredient_name: "Thịt ba chỉ",
      quantity: "500",
      unit: "g",
    });

    const mealPlanId = "plan-meal-undo";
    const eatenPlan = {
      id: mealPlanId,
      planned_for: "2026-10-25",
      meal_period: "dinner",
      eaten_at: new Date().toISOString(),
      dishes: [],
    };
    await saveMealPlans([eatenPlan]);

    const restoredLot = { ...lot, remaining_quantity: "1000" };
    const reversalMovements = [
      {
        id: "mov-rev-001",
        pantry_lot_id: lot.id,
        meal_plan_id: mealPlanId,
        quantity_delta: "500",
        reason: "correction",
        created_at: new Date().toISOString(),
      },
    ];

    // Execute undo
    await executeUndoEatMealAtomic(mealPlanId, [restoredLot], reversalMovements);

    const planAfterUndo = await getMealPlanById(mealPlanId);
    assert.equal(planAfterUndo.eaten_at, null);

    const lotsAfterUndo = await getPantryLots();
    assert.equal(lotsAfterUndo[0].remaining_quantity, "1000");
  });

  test("Backup JSON export and strict schema validation", async () => {
    await addPantryLot({
      ingredient_id: "ing-fish",
      ingredient_name: "Cá lóc",
      quantity: "400",
      unit: "g",
    });

    const backup = await exportBackupJSON();
    assert.equal(backup.app, "EasyMeals");
    assert.equal(backup.schema_version, 1);
    assert.equal(backup.data.pantry.length, 1);

    // Validate valid backup
    assert.equal(validateBackupJSON(backup), true);

    // Validate rejects wrong app
    assert.throws(
      () => validateBackupJSON({ ...backup, app: "MaliciousApp" }),
      /EasyMeals/
    );

    // Validate rejects wrong schema version
    assert.throws(
      () => validateBackupJSON({ ...backup, schema_version: 99 }),
      /Phiên bản/
    );

    // Validate rejects excessive items (memory exhaustion protection)
    const excessivePantry = new Array(5001).fill(backup.data.pantry[0]);
    assert.throws(
      () =>
        validateBackupJSON({
          ...backup,
          data: { ...backup.data, pantry: excessivePantry },
        }),
      /vượt quá giới hạn/
    );

    // --- Strict checks for backup import ---

    // 1. Rejects dangerous prototype pollution keys
    assert.throws(
      () => validateBackupJSON(JSON.parse('{"app":"EasyMeals","schema_version":1,"__proto__":{"polluted":true},"data":{"pantry":[],"plans":[],"movements":[]}}')),
      /Khoá không an toàn|không hợp lệ/
    );

    // 2. String length limits (ingredient_name <= 100, id <= 128)
    const longNameLot = {
      ...backup.data.pantry[0],
      ingredient_name: "a".repeat(101),
    };
    assert.throws(
      () => validateBackupJSON({ ...backup, data: { ...backup.data, pantry: [longNameLot] } }),
      /Tên nguyên liệu/
    );

    // 3. Quantity limits: purchased > 0, <= 100000; remaining >= 0; remaining <= purchased
    const invalidQtyLot1 = {
      ...backup.data.pantry[0],
      purchased_quantity: "0",
    };
    assert.throws(
      () => validateBackupJSON({ ...backup, data: { ...backup.data, pantry: [invalidQtyLot1] } }),
      /Số lượng mua/
    );

    const invalidQtyLot2 = {
      ...backup.data.pantry[0],
      purchased_quantity: "500",
      remaining_quantity: "600",
    };
    assert.throws(
      () => validateBackupJSON({ ...backup, data: { ...backup.data, pantry: [invalidQtyLot2] } }),
      /Số lượng còn lại/
    );

    // 4. Date validation: ISO format & expires_at >= purchased_at
    const invalidDateLot = {
      ...backup.data.pantry[0],
      purchased_at: "2026-10-24T12:00:00Z",
      expires_at: "2026-10-20T00:00:00Z",
    };
    assert.throws(
      () => validateBackupJSON({ ...backup, data: { ...backup.data, pantry: [invalidDateLot] } }),
      /Hạn sử dụng/
    );

    // 5. Movements must reference existing lot
    const orphanedMovement = {
      id: "mov-ghost",
      pantry_lot_id: "lot-non-existent",
      quantity_delta: "-100",
      reason: "meal_consumption",
      created_at: "2026-10-24T12:00:00Z",
    };
    assert.throws(
      () => validateBackupJSON({ ...backup, data: { ...backup.data, movements: [orphanedMovement] } }),
      /tham chiếu/
    );

    // 6. Meal plans: dishes per meal <= 10, servings 1-20, notes <= 500
    const invalidDishPlan = {
      id: "plan-1",
      planned_for: "2026-10-25",
      meal_period: "lunch",
      dishes: [
        {
          recipe_name: "Món quá nhiều phần",
          servings: 25,
        },
      ],
    };
    assert.throws(
      () => validateBackupJSON({ ...backup, data: { ...backup.data, plans: [invalidDishPlan] } }),
      /Khẩu phần/
    );
  });

  test("Import backup JSON (Replace vs Merge modes)", async () => {
    // Current data: lot A
    const lotA = await addPantryLot({
      ingredient_id: "ing-A",
      ingredient_name: "Nguyên liệu A",
      quantity: "100",
      unit: "g",
    });

    const externalBackup = {
      schema_version: 1,
      app: "EasyMeals",
      exported_at: "2026-10-24T00:00:00Z",
      metadata: { total_lots: 1, total_plans: 0, total_movements: 0 },
      data: {
        pantry: [
          {
            id: "lot-B",
            ingredient_id: "ing-B",
            ingredient_name: "Nguyên liệu B",
            purchased_quantity: "200",
            remaining_quantity: "200",
            unit: "g",
            purchased_at: "2026-10-24T00:00:00Z",
          },
        ],
        plans: [],
        movements: [],
        settings: [],
      },
    };

    // 1. Merge mode: should have both A and B
    await importBackupJSON(externalBackup, "merge");
    let lots = await getPantryLots();
    assert.equal(lots.length, 2);

    // 2. Replace mode: should ONLY have B
    await importBackupJSON(externalBackup, "replace");
    lots = await getPantryLots();
    assert.equal(lots.length, 1);
    assert.equal(lots[0].id, "lot-B");
  });

  test("Bundled mode: nạp danh mục và nâng cấp phiên bản không làm mất dữ liệu cá nhân", async () => {
    // 1. Setup personal data in IndexedDB
    const userLot = await addPantryLot({
      ingredient_id: "ing-personal-001",
      ingredient_name: "Thịt heo nhà làm",
      quantity: "800",
      unit: "g",
    });

    const userPlan = {
      id: "plan-personal-001",
      planned_for: "2026-10-26",
      meal_period: "lunch",
      dishes: [{ recipe_name: "Món cá nhân" }],
    };
    await saveMealPlans([userPlan]);

    // 2. Initial bundled catalogue v1.0.0
    setCatalogueSource("bundled");
    const bundleV1 = {
      catalogue_version: "1.0.0",
      etag: '"v1-hash"',
      ingredients: [{ id: "ing-01", name: "Rau", normalized_name: "rau" }],
      recipes: [{ id: "rec-01", name: "Rau luộc", category: "rau" }],
    };

    const res1 = await syncCatalogue("", bundleV1);
    assert.equal(res1.updated, true);
    assert.equal(res1.data.catalogue_version, "1.0.0");

    let cached = await getCachedCatalogue();
    assert.equal(cached.catalogue_version, "1.0.0");
    assert.equal(cached.recipes.length, 1);

    // Verify personal data is completely untouched
    let lots = await getPantryLots();
    assert.equal(lots.length, 1);
    assert.equal(lots[0].id, userLot.id);

    let plan = await getMealPlanById("plan-personal-001");
    assert.equal(plan.id, "plan-personal-001");

    // 3. App upgrade with bundled catalogue v2.0.0
    const bundleV2 = {
      catalogue_version: "2.0.0",
      etag: '"v2-hash"',
      ingredients: [
        { id: "ing-01", name: "Rau", normalized_name: "rau" },
        { id: "ing-02", name: "Thịt", normalized_name: "thit" },
      ],
      recipes: [
        { id: "rec-01", name: "Rau luộc", category: "rau" },
        { id: "rec-02", name: "Thịt kho", category: "man" },
      ],
    };

    const res2 = await syncCatalogue("", bundleV2);
    assert.equal(res2.updated, true);
    assert.equal(res2.data.catalogue_version, "2.0.0");

    cached = await getCachedCatalogue();
    assert.equal(cached.catalogue_version, "2.0.0");
    assert.equal(cached.recipes.length, 2);

    // 4. Verify personal data is STILL 100% intact after upgrade
    lots = await getPantryLots();
    assert.equal(lots.length, 1);
    assert.equal(lots[0].id, userLot.id);
    assert.equal(lots[0].remaining_quantity, "800");

    plan = await getMealPlanById("plan-personal-001");
    assert.equal(plan.id, "plan-personal-001");
    assert.equal(plan.dishes[0].recipe_name, "Món cá nhân");

    // Reset source
    setCatalogueSource("remote");
  });
});
