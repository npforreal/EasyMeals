/**
 * Tests for F1 history aggregation and the v2 -> v3 IndexedDB migration.
 */

import { test, describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import "fake-indexeddb/auto";

import { closeDB, openDB, getAllItems } from "../../app/static/js/db.js";
import { backfillMovementIds, buildHistorySummary } from "../../app/static/js/history.js";
import { clearAllPersonalData } from "../../app/static/js/db.js";

const DAY = 24 * 60 * 60 * 1000;
const NOW = new Date("2026-10-27T12:00:00Z");

function daysAgo(days) {
  return new Date(NOW.getTime() - days * DAY).toISOString();
}

describe("F1 — backfillMovementIds", () => {
  test("điền ingredient_id từ lô và recipe_id khi bữa chỉ có một món nấu", () => {
    const lots = [{ id: "lot-1", ingredient_id: "ing-1" }];
    const plans = [
      {
        id: "plan-1",
        dishes: [{ recipe_id: "r-1", is_leftover: false }],
      },
      {
        id: "plan-2",
        dishes: [
          { recipe_id: "r-1", is_leftover: false },
          { recipe_id: "r-2", is_leftover: false },
        ],
      },
    ];
    const movements = [
      { id: "m-1", pantry_lot_id: "lot-1", meal_plan_id: "plan-1" },
      { id: "m-2", pantry_lot_id: "lot-1", meal_plan_id: "plan-2" },
      { id: "m-3", pantry_lot_id: "lot-deleted", meal_plan_id: null },
      { id: "m-4", pantry_lot_id: "lot-1", ingredient_id: "ing-x", recipe_id: "r-keep" },
    ];

    const result = backfillMovementIds(movements, lots, plans);

    assert.equal(result.changed, true);
    assert.equal(result.movements[0].ingredient_id, "ing-1");
    assert.equal(result.movements[0].recipe_id, "r-1");
    assert.equal(result.movements[1].ingredient_id, "ing-1");
    assert.equal(result.movements[1].recipe_id, undefined, "nhiều món thì không suy đoán recipe_id");
    assert.equal(result.movements[2].ingredient_id, undefined, "lô đã xoá thì để trống");
    assert.equal(result.movements[3].ingredient_id, "ing-x", "không ghi đè giá trị đã có");
    assert.equal(result.movements[3].recipe_id, "r-keep");
    assert.equal(movements[0].ingredient_id, undefined, "không sửa mảng đầu vào");
  });

  test("không thay đổi gì khi dữ liệu đã đầy đủ", () => {
    const result = backfillMovementIds(
      [{ id: "m-1", pantry_lot_id: "lot-1", ingredient_id: "ing-1", recipe_id: "r-1" }],
      [{ id: "lot-1", ingredient_id: "ing-1" }],
      []
    );
    assert.equal(result.changed, false);
  });
});

describe("F1 — buildHistorySummary", () => {
  const plans = [
    {
      id: "p1",
      planned_for: "2026-10-26",
      meal_period: "dinner",
      eaten_at: daysAgo(1),
      dishes: [
        { recipe_id: "r1", recipe_name: "Thịt kho", is_leftover: false, servings: 2 },
        { recipe_id: "r1", recipe_name: "Thịt kho", is_leftover: true },
      ],
    },
    {
      id: "p2",
      planned_for: "2026-09-01",
      meal_period: "lunch",
      eaten_at: daysAgo(50),
      dishes: [{ recipe_id: "r2", recipe_name: "Canh chua", is_leftover: false, servings: 4 }],
    },
    { id: "p3", planned_for: "2026-10-27", meal_period: "lunch", eaten_at: null, dishes: [] },
  ];

  test("đếm bữa trong cửa sổ 30 ngày và ngoài cửa sổ", () => {
    const summary = buildHistorySummary({ plans, now: NOW });
    assert.equal(summary.cooked.total, 2);
    assert.equal(summary.cooked.in_window, 1);
    assert.equal(summary.cooked.meals[0].plan_id, "p1");
    assert.deepEqual(summary.cooked.top_recipes, [{ recipe_id: "r1", name: "Thịt kho", count: 1 }]);
    assert.equal(summary.leftovers.reused_dishes_in_window, 1);
  });

  test("tổng hợp biến động kho theo lý do, không cộng trộn đơn vị", () => {
    const summary = buildHistorySummary({
      plans,
      now: NOW,
      movements: [
        { id: "m1", reason: "meal_consumption", quantity_delta: "-200", created_at: daysAgo(1) },
        { id: "m2", reason: "meal_consumption", quantity_delta: "-0.5", created_at: daysAgo(2) },
        { id: "m3", reason: "correction", quantity_delta: "200", created_at: daysAgo(60) },
      ],
    });
    assert.equal(summary.stock.total_movements, 3);
    assert.equal(summary.stock.in_window, 2);
    assert.equal(summary.stock.consumed_count, 2);
    assert.equal(summary.stock.restored_count, 0);
    assert.deepEqual(summary.stock.by_reason, { meal_consumption: 2, correction: 1 });
  });

  test("chi tiêu chỉ tính lô có giá và báo rõ phần thiếu giá", () => {
    const summary = buildHistorySummary({
      plans: [],
      now: NOW,
      pantryLots: [
        { id: "l1", price: "45000", purchased_at: daysAgo(3), remaining_quantity: "100" },
        { id: "l2", price: 15000, purchased_at: daysAgo(40), remaining_quantity: "100" },
        { id: "l3", purchased_at: daysAgo(2), remaining_quantity: "100" },
      ],
    });
    assert.equal(summary.spending.lots_with_price, 2);
    assert.equal(summary.spending.lots_missing_price, 1);
    assert.equal(summary.spending.total, 60000);
    assert.equal(summary.spending.in_window, 45000);
  });

  test("đồ quá hạn còn trong tủ được nêu, lãng phí không bị suy diễn", () => {
    const summary = buildHistorySummary({
      plans: [],
      now: NOW,
      pantryLots: [
        { id: "l1", ingredient_id: "ing-1", ingredient_name: "Sữa", remaining_quantity: "1", unit: "l", expires_at: "2026-10-20" },
        { id: "l2", ingredient_id: "ing-2", ingredient_name: "Gạo", remaining_quantity: "1", unit: "kg", expires_at: null },
        { id: "l3", ingredient_id: "ing-3", ingredient_name: "Trứng", remaining_quantity: "0", unit: "piece", expires_at: "2026-10-01" },
      ],
    });
    assert.equal(summary.waste.tracked, false);
    assert.equal(summary.waste.expired_lot_count, 1);
    assert.equal(summary.waste.expired_lots[0].ingredient_name, "Sữa");
  });

  test("dữ liệu rỗng không lỗi", () => {
    const summary = buildHistorySummary({ now: NOW });
    assert.equal(summary.cooked.total, 0);
    assert.equal(summary.stock.total_movements, 0);
    assert.equal(summary.spending.total, 0);
  });
});

describe("F1 — IndexedDB v2 -> v3 migration", () => {
  const DB_NAME = "easymeals_local_db";

  beforeEach(async () => {
    closeDB();
    await new Promise((resolve, reject) => {
      const req = indexedDB.deleteDatabase(DB_NAME);
      req.onsuccess = resolve;
      req.onerror = () => reject(req.error);
    });
  });

  afterEach(async () => {
    closeDB();
  });

  function createV2Database({ lots, plans, movements }) {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, 2);
      req.onupgradeneeded = () => {
        const db = req.result;
        const pantry = db.createObjectStore("pantry", { keyPath: "id" });
        pantry.createIndex("by_ingredient_id", "ingredient_id", { unique: false });
        const plansStore = db.createObjectStore("plans", { keyPath: "id" });
        plansStore.createIndex("by_start_date", "start_date", { unique: false });
        const movs = db.createObjectStore("movements", { keyPath: "id" });
        movs.createIndex("by_lot_id", "pantry_lot_id", { unique: false });
        db.createObjectStore("settings", { keyPath: "key" });
        db.createObjectStore("catalogue", { keyPath: "key" });
        const shopping = db.createObjectStore("shopping", { keyPath: "id" });
        shopping.createIndex("by_source", "source", { unique: false });

        const tx = req.transaction;
        for (const lot of lots) tx.objectStore("pantry").put(lot);
        for (const plan of plans) tx.objectStore("plans").put(plan);
        for (const mov of movements) tx.objectStore("movements").put(mov);
      };
      req.onsuccess = () => {
        req.result.close();
        resolve();
      };
      req.onerror = () => reject(req.error);
    });
  }

  test("giữ nguyên movement cũ và điền khoá ngoại", async () => {
    await createV2Database({
      lots: [{ id: "lot-1", ingredient_id: "ing-1", remaining_quantity: "0" }],
      plans: [{ id: "plan-1", dishes: [{ recipe_id: "r-1", is_leftover: false }] }],
      movements: [
        {
          id: "mov-1",
          pantry_lot_id: "lot-1",
          quantity_delta: "-100",
          reason: "meal_consumption",
          meal_plan_id: "plan-1",
          created_at: "2026-10-01T10:00:00Z",
        },
      ],
    });

    const db = await openDB();
    assert.equal(db.version, 3);

    const movements = await getAllItems("movements");
    assert.equal(movements.length, 1, "không mất movement khi nâng cấp");
    assert.equal(movements[0].id, "mov-1");
    assert.equal(movements[0].quantity_delta, "-100");
    assert.equal(movements[0].ingredient_id, "ing-1");
    assert.equal(movements[0].recipe_id, "r-1");
  });

  test("lô đã bị xoá thì movement vẫn được giữ, khoá ngoại để trống", async () => {
    await createV2Database({
      lots: [],
      plans: [],
      movements: [
        {
          id: "mov-orphan",
          pantry_lot_id: "lot-gone",
          quantity_delta: "50",
          reason: "correction",
          created_at: "2026-09-01T10:00:00Z",
        },
      ],
    });

    await openDB();
    const movements = await getAllItems("movements");
    assert.equal(movements.length, 1);
    assert.equal(movements[0].ingredient_id, undefined);
    assert.equal(movements[0].recipe_id, undefined);
  });

  test("mở lại lần 2 không chạy migration lần nữa và không nhân đôi dữ liệu", async () => {
    await createV2Database({
      lots: [{ id: "lot-1", ingredient_id: "ing-1" }],
      plans: [],
      movements: [{ id: "mov-1", pantry_lot_id: "lot-1", quantity_delta: "-1", reason: "meal_consumption" }],
    });
    await openDB();
    closeDB();
    await openDB();
    assert.equal((await getAllItems("movements")).length, 1);
  });
});

describe("F1 — clearAllPersonalData vẫn xoá đủ store ở v3", () => {
  test("xoá sạch dữ liệu cá nhân", async () => {
    const db = await openDB();
    const tx = db.transaction("pantry", "readwrite");
    tx.objectStore("pantry").put({ id: "l1", ingredient_id: "i1" });
    await new Promise((resolve) => (tx.oncomplete = resolve));

    await clearAllPersonalData();
    assert.deepEqual(await getAllItems("pantry"), []);
  });
});
