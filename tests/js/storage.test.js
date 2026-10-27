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
  normalizeBackupPayload,
  importBackupJSON,
  setCatalogueSource,
  syncCatalogue,
  getCachedCatalogue,
  getShoppingItems,
  getLocalSetting,
  setLocalSetting,
  addShoppingItem,
  replacePlanShoppingItems,
  toggleShoppingItemBought,
  clearBoughtShoppingItems,
  deleteShoppingItemsByIds,
  executeBoughtToPantryAtomic,
  defaultExpiryDays,
  defaultExpiryDate,
  toApiPantryLots,
  mergeLocalPrices,
  SCHEMA_VERSION,
} from "../../app/static/js/storage.js";
import { getAllItems } from "../../app/static/js/db.js";

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
    assert.equal(backup.schema_version, SCHEMA_VERSION);
    assert.equal(backup.app_version, "2.0.0");
    assert.equal(typeof SCHEMA_VERSION, "number");
    assert.ok(Array.isArray(backup.data.shopping), "Backup phải chứa data.shopping");
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

  test("A3: danh sách đi chợ nằm trong kho versioned và giữ mục tự thêm khi kế hoạch đổi", async () => {
    // Người dùng tự thêm mục (source "manual")
    const manual = await addShoppingItem({
      ingredient_id: "ing-manual-1",
      ingredient_name: "Nước mắm",
      needed_quantity: "500",
      unit: "ml",
    });
    assert.equal(manual.source, "manual");
    assert.equal(manual.id, "ing-manual-1_ml");
    assert.deepEqual(manual.plan_ids, []);

    // Lập kế hoạch sinh danh sách đi chợ của đợt (source "plan")
    const itemsAfterPlan = await replacePlanShoppingItems(
      [
        { ingredient_id: "ing-plan-1", ingredient_name: "Sườn non heo", needed_quantity: "600", unit: "g", dish_names: ["Canh sườn"] },
        { ingredient_id: "ing-plan-2", ingredient_name: "Cà chua", needed_quantity: "200", unit: "g", dish_names: ["Canh cà chua"] },
      ],
      ["period-001"]
    );
    assert.equal(itemsAfterPlan.length, 3);
    const planItem = itemsAfterPlan.find((i) => i.ingredient_id === "ing-plan-1");
    assert.equal(planItem.source, "plan");
    assert.deepEqual(planItem.plan_ids, ["period-001"]);
    assert.ok(itemsAfterPlan.some((i) => i.id === manual.id && i.source === "manual"));

    // Đổi kế hoạch -> chỉ thay mục plan, giữ nguyên mục manual (kể cả trạng thái đã tích)
    await toggleShoppingItemBought("ing-plan-1_g");
    let items = await getShoppingItems();
    assert.ok(items.find((i) => i.id === "ing-plan-1_g").bought === true);

    await replacePlanShoppingItems(
      [
        { ingredient_id: "ing-plan-1", ingredient_name: "Sườn non heo", needed_quantity: "300", unit: "g", dish_names: ["Món mới"] },
      ],
      ["period-002"]
    );
    items = await getShoppingItems();
    assert.ok(
      items.find((i) => i.id === manual.id),
      "Mục tự thêm phải còn sau khi đổi kế hoạch"
    );
    assert.ok(
      !items.some((i) => i.id === "ing-plan-2_g"),
      "Mục plan cũ phải bị thay"
    );
    const replaced = items.find((i) => i.id === "ing-plan-1_g");
    assert.equal(replaced.needed_quantity, "300");
    assert.equal(replaced.bought, false, "Mục mới của đợt mới chưa được mua");
    assert.equal(replaced.source, "plan");
    assert.deepEqual(replaced.plan_ids, ["period-002"]);

    // Xoá mục plan cũ & rõ ràng mục đã mua
    await clearBoughtShoppingItems();
    items = await getShoppingItems();
    assert.ok(!items.some((i) => i.bought));
    assert.ok(items.some((i) => i.id === manual.id));

    await deleteShoppingItemsByIds([manual.id]);
    items = await getShoppingItems();
    assert.ok(!items.some((i) => i.id === manual.id));

    // Ngăn trùng: mục plan trùng nguyên liệu+đơn vị với mục manual -> không thêm bản sao
    await addShoppingItem({
      ingredient_id: "ing-manual-1",
      ingredient_name: "Nước mắm",
      needed_quantity: "500",
      unit: "ml",
    });
    const dup = await replacePlanShoppingItems(
      [{ ingredient_id: "ing-manual-1", ingredient_name: "Nước mắm", needed_quantity: "250", unit: "ml" }],
      ["period-003"]
    );
    assert.ok(dup.some((i) => i.id === "ing-manual-1_ml" && i.source === "manual"));
    assert.equal(dup.filter((i) => i.id === "ing-manual-1_ml").length, 1);
  });

  test("A3: backup v2 mang theo danh sách đi chợ và phục hồi đúng nguồn phát sinh", async () => {
    await addShoppingItem({
      ingredient_id: "ing-manual-1",
      ingredient_name: "Nước mắm",
      needed_quantity: "500",
      unit: "ml",
    });
    await replacePlanShoppingItems(
      [{ ingredient_id: "ing-plan-1", ingredient_name: "Sườn non heo", needed_quantity: "600", unit: "g", dish_names: ["Canh sườn"] }],
      ["period-001"]
    );

    const backup = await exportBackupJSON();
    assert.equal(backup.schema_version, SCHEMA_VERSION);
    assert.equal(backup.data.shopping.length, 2);
    assert.equal(backup.data.shopping.find((i) => i.source === "manual").ingredient_id, "ing-manual-1");

    // Xoá sạch -> phục hồi -> danh sách trở lại nguyên trạng
    await clearAllPersonalData();
    assert.equal((await getShoppingItems()).length, 0);

    await importBackupJSON(JSON.parse(JSON.stringify(backup)));
    const restored = await getShoppingItems();
    assert.equal(restored.length, 2);
    assert.ok(restored.some((i) => i.source === "manual" && i.id === "ing-manual-1_ml"));
    assert.ok(restored.some((i) => i.source === "plan" && i.plan_ids.includes("period-001")));
  });

  test("backup giữ và phục hồi tuỳ chọn nguyên liệu cần tránh cùng settings cục bộ", async () => {
    const preferences = {
      avoidedIngredientIds: ["canonical-ing-1"],
      preferredIngredientIds: ["canonical-ing-2"],
      diet: "vegan",
      maxSpice: 2,
    };
    await setLocalSetting("recipe_preferences_v1", preferences);
    const backup = await exportBackupJSON();
    assert.ok(backup.data.settings.some((entry) => entry.key === "recipe_preferences_v1"));

    await clearAllPersonalData();
    await importBackupJSON(JSON.parse(JSON.stringify(backup)));
    assert.deepEqual(await getLocalSetting("recipe_preferences_v1"), preferences);
  });

  test("A3: backup cũ (schema_version 1 không có shopping) vẫn nhập được - migration tương thích", async () => {
    await addPantryLot({
      ingredient_id: "ing-legacy",
      ingredient_name: "Thịt ba chỉ",
      quantity: "1000",
      unit: "g",
      created_at: new Date().toISOString(),
    });
    const legacy = await exportBackupJSON();
    const legacyV1 = {
      ...legacy,
      schema_version: 1,
      data: {
        pantry: legacy.data.pantry,
        plans: legacy.data.plans,
        movements: legacy.data.movements,
        settings: legacy.data.settings,
      },
    };
    assert.equal(validateBackupJSON(legacyV1), true);

    await clearAllPersonalData();
    const res = await importBackupJSON(JSON.parse(JSON.stringify(legacyV1)));
    assert.equal(res.success, true);
    assert.equal((await getPantryLots()).length, 1);
    // Danh sách đi chợ sau import từ bản v1: rỗng (mục chưa có trong bản cũ).
    assert.deepEqual(await getShoppingItems(), []);

    // Bản v1 có trường shopping lảng ngoài (dựa vào người dùng thêm mới) -> bỏ qua, không văng.
    const weirdV1 = { ...legacyV1, data: { ...legacyV1.data, shopping: "khong-phai-mang" } };
    assert.equal(validateBackupJSON(weirdV1), true);

    // Bản v2 mới phải kiểm tra schema shopping.
    const badV2 = { ...legacyV1, schema_version: 2, data: { ...legacyV1.data, shopping: "khong-phai-mang" } };
    assert.throws(() => validateBackupJSON(badV2), /data\.shopping/);
  });

  test("A3: backup v2 sai nguồn phát sinh hoặc schema sai bị từ chối", async () => {
    const base = await exportBackupJSON();
    assert.throws(
      () =>
        validateBackupJSON({
          ...base,
          data: { ...base.data, shopping: [{ id: "x", ingredient_id: "ing", needed_quantity: "1", unit: "g", source: "kỳ lạ" }] },
        }),
      /Nguồn phát sinh/
    );
    assert.throws(
      () =>
        validateBackupJSON({
          ...base,
          data: { ...base.data, shopping: [{ id: "x", ingredient_id: "ing", needed_quantity: "không phải số", unit: "g" }] },
        }),
      /Số lượng cần mua/
    );
  });

  test("A4: hạn dùng mặc định theo nhóm nguyên liệu", async () => {
    assert.equal(defaultExpiryDays("thit"), 3);
    assert.equal(defaultExpiryDays("hai_san"), 2);
    assert.equal(defaultExpiryDays("rau_cu"), 5);
    assert.equal(defaultExpiryDays("cu_qua"), 10);
    assert.equal(defaultExpiryDays("gao_bot_mi"), 180);
    assert.equal(defaultExpiryDays("khac"), 7);
    assert.equal(defaultExpiryDays("nhom-khong-tim-thay"), 7);
    assert.equal(defaultExpiryDays(null), 7);

    const exp = defaultExpiryDate("hai_san", "2026-10-25T08:00:00Z");
    assert.match(exp, /^\d{4}-\d{2}-\d{2}$/);
    const diff = (new Date(exp) - new Date("2026-10-25")) / 86400000;
    assert.equal(diff, 2, "hai_san mặc định +2 ngày kể từ ngày mua");
  });

  test("A4: mua vào tủ một giao dịch - lượng thực mua, hạn dùng, idempotent", async () => {
    const catalogue = {
      ingredients: [
        { id: "ing-thit", name: "Thịt heo", normalized_name: "thit heo", category: "thit", default_unit: "g", aliases: [] },
      ],
      recipes: [],
    };

    const a = await addShoppingItem(
      { ingredient_id: "ing-thit", ingredient_name: "Thịt heo", needed_quantity: "600", unit: "g" },
      { source: "plan" }
    );
    const b = await addShoppingItem(
      { ingredient_id: "ing-rau", ingredient_name: "Cải xanh", needed_quantity: "300", unit: "g" },
      { source: "manual" }
    );

    // Mua: ghi đè lượng thực mua + hạn dùng cho mục a; mục b dùng mặc định nhóm "khac".
    await executeBoughtToPantryAtomic(
      [
        { id: a.id, ingredient_id: "ing-thit", ingredient_name: "Thịt heo", needed_quantity: "600", unit: "g" },
        { id: b.id, ingredient_id: "ing-rau", ingredient_name: "Cải xanh", needed_quantity: "300", unit: "g" },
      ],
      { [a.id]: { quantity: "450" } },
      catalogue
    );

    const lots = await getPantryLots();
    const lotThit = lots.find((l) => l.ingredient_id === "ing-thit");
    const lotRau = lots.find((l) => l.ingredient_id === "ing-rau");
    assert.equal(lotThit.purchased_quantity, "450", "Lượng thực mua khác ước tính được áp dụng");
    assert.equal(lotThit.expires_at, lotThit.expires_at && /^\d{4}-\d{2}-\d{2}$/.test(lotThit.expires_at) ? lotThit.expires_at : null);
    assert.ok(/^\d{4}-\d{2}-\d{2}$/.test(lotThit.expires_at), "Có hạn dùng");
    assert.ok(/^\d{4}-\d{2}-\d{2}$/.test(lotRau?.expires_at || ""), "Mục còn lại có hạn dùng mặc định");

    const diffThit = (new Date(lotThit.expires_at) - new Date(lotThit.purchased_at)) / 86400000;
    assert.ok(diffThit <= 3 && diffThit >= 2, "th mặc định +3 ngày (làm tròn theo múi giờ ±)");
    assert.ok(/^\d{4}-\d{2}-\d{2}$/.test(lotRau.expires_at));

    // Danh sách đi chợ: các mục đã mua bị xoá trong cùng giao dịch.
    assert.equal((await getShoppingItems()).length, 0);

    // Idempotent: bấm lặp với mục đã xoá -> không thêm lot mới.
    const before = (await getPantryLots()).length;
    await executeBoughtToPantryAtomic(
      [{ id: a.id, ingredient_id: "ing-thit", ingredient_name: "Thịt heo", needed_quantity: "600", unit: "g" }],
      {},
      catalogue
    );
    assert.equal((await getPantryLots()).length, before, "Không nhân đôi lot khi bấm lặp");
  });
});

describe("F3 — chuyển thiết bị: đọc file sao lưu của ứng dụng di động", () => {
  beforeEach(async () => {
    await clearAllPersonalData();
  });

  afterEach(() => {
    closeDB();
  });

  function mobileBackup() {
    return {
      schema_version: 2,
      app_version: "2.0.0",
      exported_at: "2026-10-20T09:00:00Z",
      pantry_lots: [
        {
          id: "lot-mobile-1",
          ingredient_id: "ing-1",
          ingredient_name: "Thịt heo",
          remaining_quantity: "300",
          purchased_quantity: "500",
          unit: "g",
          purchased_at: "2026-10-19T09:00:00Z",
          expires_at: "2026-10-22",
        },
      ],
      meal_plans: [
        {
          id: "plan-mobile-1",
          planned_for: "2026-10-21",
          meal_period: "dinner",
          eaten_at: "2026-10-21T12:00:00Z",
          dishes: [{ id: "d1", recipe_id: "r-1", recipe_name: "Thịt kho", category: "man", is_leftover: false }],
        },
      ],
      stock_movements: [
        {
          id: "mov-mobile-1",
          pantry_lot_id: "lot-mobile-1",
          quantity_delta: "-200",
          reason: "meal_consumption",
          meal_plan_id: "plan-mobile-1",
          created_at: "2026-10-21T12:00:00Z",
        },
      ],
      shopping_items: [],
      recipe_preferences: {
        avoided_ingredient_ids: [],
        preferred_ingredient_ids: [],
        dietary_filter: "",
        max_spice: "",
      },
    };
  }

  test("chuẩn hoá định dạng phẳng và import được, movements được điền khoá ngoại", async () => {
    const raw = normalizeBackupPayload(mobileBackup());
    assert.equal(raw.app, "EasyMeals");
    assert.equal(raw.data.pantry.length, 1);

    const result = await importBackupJSON(mobileBackup());
    assert.equal(result.imported_lots, 1);
    assert.equal(result.imported_plans, 1);
    assert.equal(result.imported_movements, 1);

    const movements = await getStockMovements();
    assert.equal(movements[0].ingredient_id, "ing-1");
    assert.equal(movements[0].recipe_id, "r-1");
    const lots = await getPantryLots();
    assert.equal(lots[0].ingredient_name, "Thịt heo");
  });

  test("file có schema mới hơn ứng dụng bị từ chối kèm hướng xử lý", () => {
    const backup = mobileBackup();
    backup.schema_version = 99;
    assert.throws(
      () => validateBackupJSON(backup),
      /Hãy cập nhật ứng dụng lên bản mới hơn/
    );
  });

  test("giá đã nhập ở danh sách đi chợ được giữ trên lô khi cho vào tủ", async () => {
    const item = await addShoppingItem({
      ingredient_id: "ing-1",
      ingredient_name: "Thịt heo",
      needed_quantity: "400",
      unit: "g",
      price: "55000",
    });
    await executeBoughtToPantryAtomic([item], {}, null);
    const lots = await getPantryLots();
    assert.equal(lots[0].price, "55000");
  });

  test("backup v3 giữ price và đọc lại được", async () => {
    const item = await addShoppingItem({
      ingredient_id: "ing-1",
      ingredient_name: "Thịt heo",
      needed_quantity: "400",
      unit: "g",
      price: "55000",
    });
    await executeBoughtToPantryAtomic([item], {}, null);
    const backup = await exportBackupJSON();
    assert.equal(backup.data.pantry[0].price, "55000");
    await clearAllPersonalData();
    await importBackupJSON(backup);
    assert.equal((await getPantryLots())[0].price, "55000");
  });
});

describe("F1: giá là dữ liệu cục bộ, không gửi lên API lập thực đơn", () => {
  test("toApiPantryLots bỏ price nhưng giữ đủ trường backend chấp nhận", () => {
    const lot = {
      id: "lot-1",
      ingredient_id: "ing-1",
      ingredient_name: "Thịt heo",
      purchased_quantity: "400",
      remaining_quantity: "300",
      unit: "g",
      purchased_at: "2026-10-27T10:00:00.000Z",
      expires_at: "2026-10-30",
      created_at: "2026-10-27T10:00:00.000Z",
      price: "55000",
    };
    const [payload] = toApiPantryLots([lot]);
    assert.equal(payload.price, undefined, "không gửi giá lên máy chủ");
    assert.equal(payload.remaining_quantity, "300");
    assert.equal(payload.unit, "g");
    assert.deepEqual(Object.keys(payload).sort(), [
      "created_at",
      "expires_at",
      "id",
      "ingredient_id",
      "ingredient_name",
      "purchased_at",
      "purchased_quantity",
      "remaining_quantity",
      "unit",
    ]);
  });

  test("toApiPantryLots chịu được đầu vào rỗng/không hợp lệ", () => {
    assert.deepEqual(toApiPantryLots([]), []);
    assert.deepEqual(toApiPantryLots(null), []);
  });

  test("mergeLocalPrices gắn lại giá theo id sau khi máy chủ trả về", () => {
    const local = [
      { id: "lot-1", price: "55000" },
      { id: "lot-2", price: null },
      { id: "lot-3" },
    ];
    const fromApi = [
      { id: "lot-1", remaining_quantity: "100" },
      { id: "lot-2", remaining_quantity: "200" },
      { id: "lot-4", remaining_quantity: "300" },
    ];
    const merged = mergeLocalPrices(fromApi, local);
    assert.equal(merged[0].price, "55000");
    assert.equal(merged[0].remaining_quantity, "100");
    assert.equal(merged[1].price, null);
    assert.equal(merged[2].price, undefined, "lô mới không tự bịa giá");
  });
});
