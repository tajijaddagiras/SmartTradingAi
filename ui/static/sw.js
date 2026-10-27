/**
 * NexusTrade AI — Progressive Web App (PWA) Service Worker
 * Ensures fast offline shell loading & instant startup.
 * CRITICAL: Never caches live market data, streaming ticks, or MT5 trade orders (/api/*).
 */

const CACHE_NAME = "nexustrade-pwa-v1";

const STATIC_PRECACHE = [
  "/",
  "/static/index.html",
  "/static/index.css?v=8.2",
  "/static/app.js?v=8.2",
  "/static/libs/lightweight-charts.js?v=8.2",
  "/static/manifest.json",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/icons/icon-maskable-512.png",
  "/static/icons/apple-touch-icon.png",
  "/static/icons/favicon.png",
  "/static/icons/favicon-32x32.png"
];

// Service Worker Installation: Cache Core Application Shell
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_PRECACHE).catch((err) => {
        console.warn("[PWA SW] Pre-caching warning:", err);
      });
    })
  );
  self.skipWaiting();
});

// Service Worker Activation: Clean up stale caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            console.log("[PWA SW] Removing old cache:", key);
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Fetch Interceptor: Safe routing for Financial Trading SPA
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // 1. Strict Bypass: NEVER cache live API calls or non-GET requests
  if (url.pathname.startsWith("/api/") || event.request.method !== "GET") {
    return;
  }

  // 2. Navigation Requests: Network-first with cache fallback for the app shell
  if (event.request.mode === "navigate") {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          if (response && response.status === 200) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          }
          return response;
        })
        .catch(() => {
          return caches.match("/") || caches.match("/static/index.html");
        })
    );
    return;
  }

  // 3. Static Assets: Stale-While-Revalidate
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      const fetchPromise = fetch(event.request)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const clone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          }
          return networkResponse;
        })
        .catch(() => cachedResponse);

      return cachedResponse || fetchPromise;
    })
  );
});
