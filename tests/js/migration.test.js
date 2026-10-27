/**
 * G4 (Vòng 13) — Chứng minh nâng cấp IndexedDB từ schema cũ không mất dữ liệu.
 *
 * Kịch bản: người dùng đang có kho v1 (pantry, plans, movements, settings,
 * catalogue) và danh sách đi chợ cũ trong localStorage. Sau khi mở ứng dụng
 * mới (schema v3), toàn bộ dữ liệu phải còn nguyên, store "shopping" được tạo
 * và danh sách cũ được chuyển vào kho đúng một lần.
 */

import { test, describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import "fake-indexeddb/auto";

import { closeDB, openDB, getAllItems } from "../../app/static/js/db.js";
import { getShoppingItems, migrateLegacyShoppingList } from "../../app/static/js/storage.js";

const DB_NAME = "easymeals_local_db";

function deleteDatabase() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.deleteDatabase(DB_NAME);
    req.onsuccess = resolve;
    req.onerror = () => reject(req.error);
    req.onblocked = resolve;
  });
}

function createV1Database({ lots = [], plans = [], movements = [], settings = [], catalogue = [] } = {}) {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => {
      const db = req.result;
      const pantry = db.createObjectStore("pantry", { keyPath: "id" });
      pantry.createIndex("by_ingredient_id", "ingredient_id", { unique: false });
      pantry.createIndex("by_purchased_at", "purchased_at", { unique: false });
      const plansStore = db.createObjectStore("plans", { keyPath: "id" });
      plansStore.createIndex("by_start_date", "start_date", { unique: false });
      const movs = db.createObjectStore("movements", { keyPath: "id" });
      movs.createIndex("by_lot_id", "pantry_lot_id", { unique: false });
      movs.createIndex("by_meal_id", "meal_plan_id", { unique: false });
      movs.createIndex("by_created_at", "created_at", { unique: false });
      db.createObjectStore("settings", { keyPath: "key" });
      db.createObjectStore("catalogue", { keyPath: "key" });

      const tx = req.transaction;
      for (const lot of lots) tx.objectStore("pantry").put(lot);
      for (const plan of plans) tx.objectStore("plans").put(plan);
      for (const mov of movements) tx.objectStore("movements").put(mov);
      for (const setting of settings) tx.objectStore("settings").put(setting);
      for (const entry of catalogue) tx.objectStore("catalogue").put(entry);
    };
    req.onsuccess = () => {
      req.result.close();
      resolve();
    };
    req.onerror = () => reject(req.error);
  });
}

function installMemoryLocalStorage(initial = {}) {
  const store = new Map(Object.entries(initial));
  const previous = Object.getOwnPropertyDescriptor(globalThis, "localStorage");
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    writable: true,
    value: {
      getItem: (key) => (store.has(key) ? store.get(key) : null),
      setItem: (key, value) => store.set(key, String(value)),
      removeItem: (key) => store.delete(key),
    },
  });
  return () => {
    if (previous) Object.defineProperty(globalThis, "localStorage", previous);
    else delete globalThis.localStorage;
  };
}

describe("G4 — nâng cấp IndexedDB v1 -> v3", () => {
  beforeEach(deleteDatabase);
  afterEach(async () => {
    closeDB();
    await deleteDatabase();
  });

  test("giữ nguyên pantry, plans, settings, catalogue và điền khoá ngoại cho movements", async () => {
    await createV1Database({
      lots: [
        {
          id: "lot-1",
          ingredient_id: "ing-1",
          ingredient_name: "Thịt ba chỉ",
          purchased_quantity: "500",
          remaining_quantity: "400",
          unit: "g",
          purchased_at: "2026-10-01T08:00:00.000Z",
        },
      ],
      plans: [
        {
          id: "plan-1",
          planned_for: "2026-10-02",
          meal_period: "lunch",
          dishes: [{ id: "dish-1", recipe_id: "recipe-1", is_leftover: false }],
          eaten_at: "2026-10-02T11:00:00.000Z",
        },
      ],
      movements: [
        {
          id: "mov-1",
          pantry_lot_id: "lot-1",
          quantity_delta: "-100",
          reason: "meal_consumption",
          meal_plan_id: "plan-1",
          created_at: "2026-10-02T11:00:00.000Z",
        },
      ],
      settings: [{ key: "theme", value: "dark" }],
      catalogue: [{ key: "bundle", value: { version: 7, recipes: [] } }],
    });

    const db = await openDB();
    assert.equal(db.version, 3, "nâng cấp lên schema v3");

    const pantry = await getAllItems("pantry");
    assert.equal(pantry.length, 1);
    assert.equal(pantry[0].ingredient_name, "Thịt ba chỉ");
    assert.equal(pantry[0].remaining_quantity, "400");

    const plans = await getAllItems("plans");
    assert.equal(plans.length, 1);
    assert.equal(plans[0].id, "plan-1");
    assert.equal(plans[0].eaten_at, "2026-10-02T11:00:00.000Z");

    const movements = await getAllItems("movements");
    assert.equal(movements.length, 1);
    assert.equal(movements[0].quantity_delta, "-100");
    assert.equal(movements[0].ingredient_id, "ing-1", "khoá ngoại được điền từ lô");
    assert.equal(movements[0].recipe_id, "recipe-1", "khoá ngoại được điền từ bữa một món");

    assert.deepEqual(await getAllItems("settings"), [{ key: "theme", value: "dark" }]);
    assert.deepEqual(await getAllItems("catalogue"), [
      { key: "bundle", value: { version: 7, recipes: [] } },
    ]);
    assert.deepEqual(await getAllItems("shopping"), [], "store shopping mới được tạo và rỗng");
  });

  test("danh sách đi chợ cũ trong localStorage được chuyển vào kho v3 đúng một lần", async () => {
    await createV1Database();
    const restoreLocalStorage = installMemoryLocalStorage({
      easymeals_shopping_list: JSON.stringify([
        { ingredient_id: "ing-1", ingredient_name: "Rau muống", needed_quantity: "300", unit: "g" },
        {
          ingredient_id: "ing-2",
          ingredient_name: "Nước mắm",
          needed_quantity: "1",
          unit: "l",
          dish_names: ["Thịt kho"],
        },
      ]),
    });
    try {
      await openDB();
      const first = await getShoppingItems();
      assert.equal(first.length, 2, "chuyển đủ hai mục cũ");
      assert.equal(globalThis.localStorage.getItem("easymeals_shopping_list"), null, "xoá khoá cũ");

      const manual = first.find((i) => i.ingredient_name === "Rau muống");
      const fromPlan = first.find((i) => i.ingredient_name === "Nước mắm");
      assert.equal(manual.source, "manual", "mục không gắn món là người dùng tự thêm");
      assert.equal(fromPlan.source, "plan", "mục có tên món là sinh từ kế hoạch");

      await migrateLegacyShoppingList();
      const second = await getShoppingItems();
      assert.equal(second.length, 2, "chạy lại không nhân đôi mục");
    } finally {
      restoreLocalStorage();
    }
  });
});
