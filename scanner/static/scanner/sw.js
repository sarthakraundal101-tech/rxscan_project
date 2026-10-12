// MediScan AI Progressive Web App Service Worker
const CACHE_NAME = "mediscan-ai-v2.0";
const ASSETS_TO_CACHE = [
  "/static/scanner/css/style.css",
  "/static/scanner/js/app.js",
  "/static/scanner/js/viewer.js",
  "/static/scanner/manifest.json"
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  // Only cache GET static assets, pass dynamic requests to network
  if (e.request.method === "GET" && e.request.url.includes("/static/")) {
    e.respondWith(
      caches.match(e.request).then((cached) => {
        return cached || fetch(e.request);
      })
    );
  }
});
