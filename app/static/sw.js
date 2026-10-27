/**
 * EasyMeals Service Worker (Offline Cache & PWA Support).
 */

const CACHE_NAME = "easymeals-v3";
const MAX_RUNTIME_ENTRIES = 80;
const ASSETS_TO_CACHE = [
  "/",
  "/planner",
  "/recipes",
  "/shopping-list",
  "/settings",
  "/manifest.json",
  "/static/styles.css",
  "/static/app.js",
  "/static/theme-init.js",
  "/static/icons.svg",
  "/static/icon.svg",
  "/static/fonts/fraunces/fraunces-latin.woff2",
  "/static/fonts/fraunces/fraunces-latin-ext.woff2",
  "/static/fonts/fraunces/fraunces-vietnamese.woff2",
  "/static/js/db.js",
  "/static/js/storage.js",
];

// Install: Cache core application shell
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    }).then(() => self.skipWaiting())
  );
});

// Activate: Clean up old caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    }).then(() => self.clients.claim())
  );
});

// Chỉ lưu cache app shell, tài nguyên tĩnh và danh mục công khai; không lưu các API khác.
function isCacheable(url) {
  return (
    ASSETS_TO_CACHE.includes(url.pathname) ||
    url.pathname.startsWith("/static/") ||
    url.pathname === "/api/catalogue"
  );
}

// Giữ số mục cache động trong giới hạn (xoá mục cũ nhất trước).
async function putLimited(request, response) {
  const cache = await caches.open(CACHE_NAME);
  await cache.put(request, response);
  const keys = await cache.keys();
  const extra = keys.length - (ASSETS_TO_CACHE.length + MAX_RUNTIME_ENTRIES);
  for (let i = 0; i < extra; i++) {
    await cache.delete(keys[ASSETS_TO_CACHE.length + i]);
  }
}

// Fetch: Network first with Cache fallback for navigation/API, Cache first for assets
self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);

  // Only handle GET requests within same origin
  if (request.method !== "GET" || url.origin !== self.location.origin) {
    return;
  }

  // Không can thiệp vào đường dẫn ngoài phạm vi cache (ví dụ các API khác)
  if (!isCacheable(url) && request.mode !== "navigate") {
    return;
  }

  // Static fonts and icons: Cache First
  if (url.pathname.startsWith("/static/fonts/") || url.pathname.endsWith(".svg")) {
    event.respondWith(
      caches.match(request).then((cached) => {
        if (cached) return cached;
        return fetch(request).then((response) => {
          if (response.status === 200 && isCacheable(url)) {
            putLimited(request, response.clone());
          }
          return response;
        });
      })
    );
    return;
  }

  // App shell and catalogue: Network First with Cache Fallback
  event.respondWith(
    fetch(request)
      .then((networkResponse) => {
        if (networkResponse.status === 200 && isCacheable(url)) {
          putLimited(request, networkResponse.clone());
        }
        return networkResponse;
      })
      .catch(() => {
        return caches.match(request).then((cached) => {
          if (cached) return cached;
          if (request.headers.get("accept")?.includes("text/html")) {
            return caches.match("/");
          }
          return new Response("Ngoại tuyến (Offline)", { status: 503, statusText: "Offline" });
        });
      })
  );
});
