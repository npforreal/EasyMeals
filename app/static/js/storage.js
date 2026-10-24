/**
 * EasyMeals Business Storage API.
 *
 * Implements high-level operations for:
 * - Pantry inventory (with decimal string quantities, FIFO tracking)
 * - Meal planning & atomic consumption ("đã ăn") / undo
 * - Public catalogue synchronization with ETag caching
 * - Backup & Restore JSON with strict schema validation
 */

import {
  clearAllPersonalData,
  deleteItem,
  getAllItems,
  getItem,
  openDB,
  putItem,
} from "./db.js";

export const SCHEMA_VERSION = 1;
export const VALID_UNITS = ["g", "kg", "ml", "l", "piece"];
export const VALID_CATEGORIES = ["man", "rau", "canh"];

/**
 * Generate a cryptographically secure UUIDv4.
 */
export function generateUUID() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  // Fallback RFC4122 v4
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

// ==========================================
// 1. Pantry Operations
// ==========================================

export async function getPantryLots() {
  const lots = await getAllItems("pantry");
  return lots.sort((a, b) => new Date(a.purchased_at) - new Date(b.purchased_at));
}

export async function addPantryLot({
  ingredient_id,
  ingredient_name,
  quantity,
  unit,
  expires_at = null,
}) {
  if (!ingredient_id) throw new Error("Thiếu mã nguyên liệu (ingredient_id).");
  if (!quantity || Number(quantity) <= 0) throw new Error("Số lượng phải lớn hơn 0.");
  if (!VALID_UNITS.includes(unit)) throw new Error(`Đơn vị '${unit}' không hợp lệ.`);

  const lot = {
    id: generateUUID(),
    ingredient_id,
    ingredient_name: ingredient_name || "Nguyên liệu",
    purchased_quantity: String(quantity),
    remaining_quantity: String(quantity),
    unit,
    purchased_at: new Date().toISOString(),
    expires_at: expires_at || null,
    created_at: new Date().toISOString(),
  };

  await putItem("pantry", lot);
  return lot;
}

export async function updatePantryLot(lot) {
  if (!lot.id) throw new Error("Thiếu lot ID.");
  await putItem("pantry", lot);
  return lot;
}

export async function deletePantryLot(lotId) {
  return await deleteItem("pantry", lotId);
}

// ==========================================
// 2. Meal Plans & Atomic Consumption
// ==========================================

export async function getMealPlans() {
  const plans = await getAllItems("plans");
  return plans.sort((a, b) => new Date(a.planned_for) - new Date(b.planned_for));
}

export async function getMealPlanById(id) {
  return await getItem("plans", id);
}

export async function saveMealPlans(plans) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction("plans", "readwrite");
    const store = tx.objectStore("plans");
    for (const plan of plans) {
      store.put(plan);
    }
    tx.oncomplete = () => resolve(true);
    tx.onerror = (e) => reject(e.target.error);
  });
}

/**
 * Mark a meal as eaten with an ATOMIC transaction in IndexedDB.
 *
 * Prevents double deduction / race conditions (such as clicking twice or opening two tabs):
 * 1. Reads the plan record inside the active transaction.
 * 2. Checks if `eaten_at` is already set. If yes -> throws Error and aborts transaction.
 * 3. Updates all affected pantry lots.
 * 4. Records new stock movements for auditing.
 * 5. Sets plan `eaten_at` timestamp.
 */
export async function executeEatMealAtomic(mealPlanId, updatedLots, newMovements) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(["plans", "pantry", "movements"], "readwrite");
    const plansStore = tx.objectStore("plans");
    const pantryStore = tx.objectStore("pantry");
    const movementsStore = tx.objectStore("movements");

    const getPlanReq = plansStore.get(mealPlanId);

    getPlanReq.onsuccess = () => {
      const plan = getPlanReq.result;
      if (!plan) {
        tx.abort();
        reject(new Error("Không tìm thấy kế hoạch bữa ăn để đánh dấu đã ăn."));
        return;
      }

      if (plan.eaten_at) {
        tx.abort();
        reject(new Error("Bữa ăn này đã được đánh dấu 'Đã ăn' trước đó."));
        return;
      }

      // 1. Update lots
      for (const lot of updatedLots) {
        pantryStore.put(lot);
      }

      // 2. Insert movements
      for (const mov of newMovements) {
        movementsStore.put(mov);
      }

      // 3. Mark plan as eaten
      plan.eaten_at = new Date().toISOString();
      plansStore.put(plan);
    };

    getPlanReq.onerror = () => {
      reject(getPlanReq.error);
    };

    tx.oncomplete = () => resolve(true);
    tx.onerror = (event) => reject(event.target.error);
    tx.onabort = () => reject(new Error("Giao dịch đánh dấu đã ăn bị huỷ."));
  });
}

/**
 * Undo eating a meal with an ATOMIC transaction in IndexedDB.
 */
export async function executeUndoEatMealAtomic(mealPlanId, restoredLots, reversalMovements) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(["plans", "pantry", "movements"], "readwrite");
    const plansStore = tx.objectStore("plans");
    const pantryStore = tx.objectStore("pantry");
    const movementsStore = tx.objectStore("movements");

    const getPlanReq = plansStore.get(mealPlanId);

    getPlanReq.onsuccess = () => {
      const plan = getPlanReq.result;
      if (!plan) {
        tx.abort();
        reject(new Error("Không tìm thấy bữa ăn để hoàn tác."));
        return;
      }

      if (!plan.eaten_at) {
        tx.abort();
        reject(new Error("Bữa ăn này chưa được đánh dấu đã ăn, không thể hoàn tác."));
        return;
      }

      // 1. Restore lots
      for (const lot of restoredLots) {
        pantryStore.put(lot);
      }

      // 2. Insert reversal movements
      for (const mov of reversalMovements) {
        movementsStore.put(mov);
      }

      // 3. Unmark eaten
      plan.eaten_at = null;
      plansStore.put(plan);
    };

    getPlanReq.onerror = () => {
      reject(getPlanReq.error);
    };

    tx.oncomplete = () => resolve(true);
    tx.onerror = (event) => reject(event.target.error);
    tx.onabort = () => reject(new Error("Giao dịch hoàn tác bị huỷ."));
  });
}

export async function getStockMovements() {
  const movements = await getAllItems("movements");
  return movements.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
}

// ==========================================
// 3. Public Catalogue Synchronization
// ==========================================

export let CATALOGUE_SOURCE = (typeof window !== "undefined" && window.CATALOGUE_SOURCE) || "remote";

export function setCatalogueSource(source) {
  CATALOGUE_SOURCE = source;
}

export async function getCachedCatalogue() {
  const item = await getItem("catalogue", "bundle");
  return item ? item.data : null;
}

export async function syncCatalogue(baseUrl = "", bundledData = null) {
  const currentBundle = await getCachedCatalogue();

  // Mode 1: Bundled catalogue (Mobile App Offline)
  if (CATALOGUE_SOURCE === "bundled") {
    let bundleToLoad = bundledData;
    if (!bundleToLoad) {
      if (typeof window !== "undefined" && window.__EASYMEALS_BUNDLED_CATALOGUE__) {
        bundleToLoad = window.__EASYMEALS_BUNDLED_CATALOGUE__;
      } else {
        const localPath = baseUrl ? `${baseUrl}/data/catalogue.json` : "data/catalogue.json";
        const response = await fetch(localPath);
        if (!response.ok) {
          throw new Error(`Không thể nạp danh mục đóng gói: HTTP ${response.status}`);
        }
        bundleToLoad = await response.json();
      }
    }

    // If current bundle has exact same version and etag, do not re-save
    if (
      currentBundle &&
      currentBundle.catalogue_version === bundleToLoad.catalogue_version &&
      currentBundle.etag === bundleToLoad.etag
    ) {
      return { data: currentBundle, updated: false, cached: true };
    }

    // Refresh catalogue store in IndexedDB without touching pantry, plans, movements
    await putItem("catalogue", {
      key: "bundle",
      synced_at: new Date().toISOString(),
      data: bundleToLoad,
    });

    await putItem("settings", {
      key: "catalogue_version",
      value: bundleToLoad.catalogue_version,
    });

    return { data: bundleToLoad, updated: true, cached: false };
  }

  // Mode 2: Remote catalogue (Web with Supabase via /api/catalogue)
  const cachedEtag = currentBundle?.etag || "";

  const headers = {};
  if (cachedEtag) {
    headers["If-None-Match"] = cachedEtag;
  }

  const endpoint = `${baseUrl}/api/catalogue`;
  const response = await fetch(endpoint, { method: "GET", headers });

  if (response.status === 304 && currentBundle) {
    // 304 Not Modified: cache is fresh
    return { data: currentBundle, updated: false, cached: true };
  }

  if (!response.ok) {
    throw new Error(`Lỗi đồng bộ danh mục từ server: HTTP ${response.status}`);
  }

  const newBundle = await response.json();
  const etagHeader = response.headers.get("ETag");
  if (etagHeader) {
    newBundle.etag = etagHeader;
  }

  await putItem("catalogue", {
    key: "bundle",
    synced_at: new Date().toISOString(),
    data: newBundle,
  });

  await putItem("settings", {
    key: "catalogue_version",
    value: newBundle.catalogue_version,
  });

  return { data: newBundle, updated: true, cached: false };
}

// ==========================================
// 4. Backup & Restore (JSON)
// ==========================================

export async function exportBackupJSON() {
  const pantry = await getAllItems("pantry");
  const plans = await getAllItems("plans");
  const movements = await getAllItems("movements");
  const settings = await getAllItems("settings");

  const backupObject = {
    schema_version: SCHEMA_VERSION,
    app: "EasyMeals",
    exported_at: new Date().toISOString(),
    metadata: {
      total_lots: pantry.length,
      total_plans: plans.length,
      total_movements: movements.length,
    },
    data: {
      pantry,
      plans,
      movements,
      settings,
    },
  };

  // Record last backup time in settings
  await putItem("settings", {
    key: "last_backup_at",
    value: backupObject.exported_at,
  });

  return backupObject;
}

const DANGEROUS_KEYS = ["__proto__", "constructor", "prototype"];
const ISO_DATE_REGEX = /^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?)?$/;

function scanDangerousKeys(val) {
  if (!val || typeof val !== "object") return;
  const keys = Object.getOwnPropertyNames(val);
  for (const k of keys) {
    if (DANGEROUS_KEYS.includes(k)) {
      throw new Error(`Khoá không an toàn '${k}' bị từ chối.`);
    }
    if (typeof val[k] === "object" && val[k] !== null) {
      scanDangerousKeys(val[k]);
    }
  }
}

function isValidISODate(dStr) {
  if (typeof dStr !== "string" || !ISO_DATE_REGEX.test(dStr)) {
    return false;
  }
  return !isNaN(new Date(dStr).getTime());
}

/**
 * Strict schema validation for imported backup JSON.
 */
export function validateBackupJSON(raw) {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    throw new Error("File sao lưu không đúng định dạng JSON hợp lệ.");
  }

  // Scan against dangerous prototype pollution keys
  scanDangerousKeys(raw);

  if (raw.app !== "EasyMeals") {
    throw new Error("File này không phải là bản sao lưu của EasyMeals.");
  }

  if (raw.schema_version !== 1) {
    throw new Error(`Phiên bản file sao lưu (${raw.schema_version}) không tương thích với ứng dụng (1).`);
  }

  if (!raw.data || typeof raw.data !== "object") {
    throw new Error("Thiếu cấu trúc dữ liệu 'data' trong file sao lưu.");
  }

  const { pantry, plans, movements, settings = [] } = raw.data;

  if (!Array.isArray(pantry) || !Array.isArray(plans) || !Array.isArray(movements) || !Array.isArray(settings)) {
    throw new Error("Dữ liệu pantry, plans, movements hoặc settings phải là danh sách mảng.");
  }

  // Size constraints against denial-of-service/memory bombs
  if (pantry.length > 5000) {
    throw new Error("Số lượng thực phẩm trong file vượt quá giới hạn an toàn (tối đa 5,000 items).");
  }
  if (plans.length > 500) {
    throw new Error("Số lượng kế hoạch bữa ăn vượt quá giới hạn an toàn (tối đa 500 items).");
  }
  if (movements.length > 10000) {
    throw new Error("Số lượng lịch sử biến động vượt quá giới hạn an toàn (tối đa 10,000 items).");
  }

  const knownLotIds = new Set();

  // Validate items in pantry
  for (const lot of pantry) {
    if (!lot || typeof lot !== "object") {
      throw new Error("Mục thực phẩm không hợp lệ.");
    }
    if (!lot.id || typeof lot.id !== "string" || lot.id.length > 128) {
      throw new Error("ID thực phẩm phải là chuỗi có độ dài từ 1 đến 128 ký tự.");
    }
    knownLotIds.add(lot.id);

    if (!lot.ingredient_id || typeof lot.ingredient_id !== "string" || lot.ingredient_id.length > 128) {
      throw new Error("ID nguyên liệu phải là chuỗi hợp lệ.");
    }

    if (lot.ingredient_name) {
      if (typeof lot.ingredient_name !== "string" || lot.ingredient_name.length > 100) {
        throw new Error("Tên nguyên liệu không được vượt quá 100 ký tự.");
      }
    }

    const pQty = Number(lot.purchased_quantity);
    if (!Number.isFinite(pQty) || pQty <= 0 || pQty > 100000) {
      throw new Error(`Số lượng mua của '${lot.ingredient_name || lot.id}' phải là số hữu hạn > 0 và <= 100,000.`);
    }

    const rQty = Number(lot.remaining_quantity);
    if (!Number.isFinite(rQty) || rQty < 0 || rQty > 100000) {
      throw new Error(`Số lượng còn lại của '${lot.ingredient_name || lot.id}' phải là số hữu hạn >= 0 và <= 100,000.`);
    }

    if (rQty > pQty) {
      throw new Error(`Số lượng còn lại (${rQty}) không được lớn hơn số lượng mua (${pQty}) của '${lot.ingredient_name || lot.id}'.`);
    }

    if (lot.unit && !VALID_UNITS.includes(lot.unit)) {
      throw new Error(`Đơn vị '${lot.unit}' của thực phẩm '${lot.ingredient_name || ""}' không được hỗ trợ.`);
    }

    if (lot.purchased_at && !isValidISODate(lot.purchased_at)) {
      throw new Error(`Ngày mua '${lot.purchased_at}' không đúng định dạng ISO.`);
    }

    if (lot.expires_at) {
      if (!isValidISODate(lot.expires_at)) {
        throw new Error(`Hạn sử dụng '${lot.expires_at}' không đúng định dạng ISO.`);
      }
      if (lot.purchased_at) {
        const pTime = new Date(lot.purchased_at).getTime();
        const eTime = new Date(lot.expires_at).getTime();
        if (eTime < pTime) {
          throw new Error(`Hạn sử dụng phải sau hoặc bằng ngày mua của '${lot.ingredient_name || lot.id}'.`);
        }
      }
    }
  }

  // Validate items in movements (must reference existing lots in backup)
  for (const mov of movements) {
    if (!mov || typeof mov !== "object") {
      throw new Error("Mục lịch sử biến động không hợp lệ.");
    }
    if (!mov.id || typeof mov.id !== "string" || mov.id.length > 128) {
      throw new Error("ID biến động kho phải là chuỗi hợp lệ.");
    }
    if (!mov.pantry_lot_id || !knownLotIds.has(mov.pantry_lot_id)) {
      throw new Error(`Lịch sử biến động '${mov.id}' tham chiếu thực phẩm không tồn tại trong bản sao lưu.`);
    }
    const delta = Number(mov.quantity_delta);
    if (!Number.isFinite(delta) || Math.abs(delta) > 100000) {
      throw new Error(`Độ biến động định lượng '${mov.quantity_delta}' không hợp lệ.`);
    }
    if (mov.created_at && !isValidISODate(mov.created_at)) {
      throw new Error(`Thời điểm ghi nhận biến động '${mov.created_at}' không đúng định dạng ISO.`);
    }
  }

  // Validate items in plans
  for (const plan of plans) {
    if (!plan || typeof plan !== "object") {
      throw new Error("Kế hoạch bữa ăn không hợp lệ.");
    }
    if (!plan.id || typeof plan.id !== "string" || plan.id.length > 128) {
      throw new Error("ID kế hoạch bữa ăn phải là chuỗi từ 1 đến 128 ký tự.");
    }
    if (!plan.planned_for || !isValidISODate(plan.planned_for)) {
      throw new Error("Ngày lập kế hoạch bữa ăn không đúng định dạng ISO.");
    }
    if (plan.notes && (typeof plan.notes !== "string" || plan.notes.length > 500)) {
      throw new Error("Ghi chú kế hoạch bữa ăn không được vượt quá 500 ký tự.");
    }
    if (plan.eaten_at && !isValidISODate(plan.eaten_at)) {
      throw new Error("Thời điểm đánh dấu đã ăn không đúng định dạng ISO.");
    }
    if (plan.dishes) {
      if (!Array.isArray(plan.dishes) || plan.dishes.length > 10) {
        throw new Error("Số lượng món ăn trong một bữa không được vượt quá 10 món.");
      }
      for (const dish of plan.dishes) {
        if (!dish || typeof dish !== "object") {
          throw new Error("Món ăn trong kế hoạch không hợp lệ.");
        }
        if (dish.recipe_name && (typeof dish.recipe_name !== "string" || dish.recipe_name.length > 100)) {
          throw new Error("Tên món ăn không được vượt quá 100 ký tự.");
        }
        if (dish.servings !== undefined) {
          const s = Number(dish.servings);
          if (!Number.isInteger(s) || s < 1 || s > 20) {
            throw new Error(`Khẩu phần món ăn '${dish.recipe_name || ""}' phải là số nguyên từ 1 đến 20.`);
          }
        }
        if (dish.notes && (typeof dish.notes !== "string" || dish.notes.length > 500)) {
          throw new Error("Ghi chú món ăn không được vượt quá 500 ký tự.");
        }
      }
    }
  }

  return true;
}

export async function importBackupJSON(backupData, mode = "replace") {
  validateBackupJSON(backupData);

  const { pantry, plans, movements, settings = [] } = backupData.data;

  if (mode === "replace") {
    await clearAllPersonalData();
  }

  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(["pantry", "plans", "movements", "settings"], "readwrite");
    const pStore = tx.objectStore("pantry");
    const mStore = tx.objectStore("plans");
    const movStore = tx.objectStore("movements");
    const sStore = tx.objectStore("settings");

    for (const lot of pantry) {
      pStore.put(lot);
    }
    for (const plan of plans) {
      mStore.put(plan);
    }
    for (const mov of movements) {
      movStore.put(mov);
    }
    for (const s of settings) {
      sStore.put(s);
    }

    sStore.put({
      key: "last_import_at",
      value: new Date().toISOString(),
    });

    tx.oncomplete = () => {
      resolve({
        success: true,
        imported_lots: pantry.length,
        imported_plans: plans.length,
        imported_movements: movements.length,
      });
    };
    tx.onerror = (e) => reject(e.target.error);
  });
}
