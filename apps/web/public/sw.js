const CACHE = "openbrec-offline-shell-v2";
const OFFLINE_ASSETS = [
  "/",
  "/favicon.svg",
  "/manifest.webmanifest",
  "/m0-projection.json",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(OFFLINE_ASSETS)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET" || new URL(event.request.url).origin !== self.location.origin) return;
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;
      return fetch(event.request).then((response) => {
        if (!response.ok) return response;
        const copy = response.clone();
        event.waitUntil(caches.open(CACHE).then((cache) => cache.put(event.request, copy)));
        return response;
      });
    }),
  );
});
