/**
 * EasyMeals Local Database Layer (IndexedDB).
 *
 * Provides a lightweight Promise-based API for interacting with IndexedDB.
 * Works in modern browsers, WebView (Capacitor), and Node.js testing environments.
 */

const DB_NAME = "easymeals_local_db";
const DB_VERSION = 2;

let dbInstance = null;

/**
 * Get the active IndexedDB implementation (window.indexedDB or globalThis.indexedDB).
 */
export function getIDBFactory() {
  if (typeof globalThis !== "undefined" && globalThis.indexedDB) {
    return globalThis.indexedDB;
  }
  if (typeof window !== "undefined" && window.indexedDB) {
    return window.indexedDB;
  }
  throw new Error("Trình duyệt hoặc môi trường không hỗ trợ IndexedDB.");
}

/**
 * Open or initialize easymeals_local_db with version migration support.
 */
export function openDB() {
  if (dbInstance) {
    return Promise.resolve(dbInstance);
  }

  const idb = getIDBFactory();

  return new Promise((resolve, reject) => {
    const request = idb.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      const oldVersion = event.oldVersion;

      if (oldVersion < 1) {
        // 1. Pantry store
        if (!db.objectStoreNames.contains("pantry")) {
          const pantryStore = db.createObjectStore("pantry", { keyPath: "id" });
          pantryStore.createIndex("by_ingredient_id", "ingredient_id", { unique: false });
          pantryStore.createIndex("by_purchased_at", "purchased_at", { unique: false });
        }

        // 2. Plans store
        if (!db.objectStoreNames.contains("plans")) {
          const plansStore = db.createObjectStore("plans", { keyPath: "id" });
          plansStore.createIndex("by_start_date", "start_date", { unique: false });
        }

        // 3. Movements store
        if (!db.objectStoreNames.contains("movements")) {
          const movementsStore = db.createObjectStore("movements", { keyPath: "id" });
          movementsStore.createIndex("by_lot_id", "pantry_lot_id", { unique: false });
          movementsStore.createIndex("by_meal_id", "meal_plan_id", { unique: false });
          movementsStore.createIndex("by_created_at", "created_at", { unique: false });
        }

        // 4. Settings store
        if (!db.objectStoreNames.contains("settings")) {
          db.createObjectStore("settings", { keyPath: "key" });
        }

        // 5. Catalogue cache store
        if (!db.objectStoreNames.contains("catalogue")) {
          db.createObjectStore("catalogue", { keyPath: "key" });
        }
      }

      // A3 - Vòng 13: danh sách đi chợ vào kho versioned (từ v1 cũ chỉ có localStorage).
      if (oldVersion < 2) {
        if (!db.objectStoreNames.contains("shopping")) {
          const shoppingStore = db.createObjectStore("shopping", { keyPath: "id" });
          shoppingStore.createIndex("by_source", "source", { unique: false });
          shoppingStore.createIndex("by_ingredient_id", "ingredient_id", { unique: false });
        }
      }
    };

    request.onsuccess = (event) => {
      dbInstance = event.target.result;
      resolve(dbInstance);
    };

    request.onerror = (event) => {
      reject(new Error("Lỗi khi mở IndexedDB: " + event.target.error));
    };

    request.onblocked = () => {
      console.warn("IndexedDB bị chặn bởi một tab khác đang mở phiên bản cũ.");
    };
  });
}

/**
 * Close database connection (useful during tests or reset).
 */
export function closeDB() {
  if (dbInstance) {
    dbInstance.close();
    dbInstance = null;
  }
}

/**
 * Helper to execute a single-store transaction.
 */
export async function withStore(storeName, mode, callback) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, mode);
    const store = tx.objectStore(storeName);

    let result;
    try {
      result = callback(store, tx);
    } catch (err) {
      reject(err);
      return;
    }

    tx.oncomplete = () => resolve(result);
    tx.onerror = (event) => reject(event.target.error);
    tx.onabort = (event) => reject(new Error("Giao dịch bị huỷ: " + event.target.error));
  });
}

/**
 * Get an item by key from a store.
 */
export async function getItem(storeName, key) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, "readonly");
    const store = tx.objectStore(storeName);
    const req = store.get(key);
    req.onsuccess = () => resolve(req.result || null);
    req.onerror = () => reject(req.error);
  });
}

/**
 * Get all items from a store.
 */
export async function getAllItems(storeName) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, "readonly");
    const store = tx.objectStore(storeName);
    const req = store.getAll();
    req.onsuccess = () => resolve(req.result || []);
    req.onerror = () => reject(req.error);
  });
}

/**
 * Put an item into a store (insert or update).
 */
export async function putItem(storeName, value) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, "readwrite");
    const store = tx.objectStore(storeName);
    const req = store.put(value);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

/**
 * Delete an item by key from a store.
 */
export async function deleteItem(storeName, key) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, "readwrite");
    const store = tx.objectStore(storeName);
    const req = store.delete(key);
    req.onsuccess = () => resolve(true);
    req.onerror = () => reject(req.error);
  });
}

/**
 * Clear all records in a single store.
 */
export async function clearStore(storeName) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, "readwrite");
    const store = tx.objectStore(storeName);
    const req = store.clear();
    req.onsuccess = () => resolve(true);
    req.onerror = () => reject(req.error);
  });
}

/**
 * Clear all personal data (pantry, plans, movements, settings).
 */
export async function clearAllPersonalData() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const stores = ["pantry", "plans", "movements", "settings", "shopping"];
    const tx = db.transaction(stores, "readwrite");
    for (const name of stores) {
      tx.objectStore(name).clear();
    }
    tx.oncomplete = () => resolve(true);
    tx.onerror = (event) => reject(event.target.error);
  });
}

/**
 * Request persistent storage from browser to prevent accidental eviction.
 */
export async function requestStoragePersistence() {
  if (typeof navigator !== "undefined" && navigator.storage && navigator.storage.persist) {
    try {
      const isPersisted = await navigator.storage.persist();
      return isPersisted;
    } catch (e) {
      console.warn("Không thể kích hoạt persistent storage:", e);
      return false;
    }
  }
  return false;
}
