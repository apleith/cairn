// life-os-bridge service worker
// Strategy: network-first for navigations + form posts; cache-first for static assets.
// Bump CACHE_VERSION whenever static assets change to force re-cache.

const CACHE_VERSION = "life-os-v1-2026-05-09";
const STATIC_ASSETS = [
  "/static/style.css",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/icons/apple-touch-icon.png",
  "/static/manifest.json",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const req = event.request;

  // Never cache POSTs (form submissions); they must hit the network so writes happen.
  if (req.method !== "GET") {
    return;
  }

  const url = new URL(req.url);

  // Cache-first for static assets.
  if (url.pathname.startsWith("/static/")) {
    event.respondWith(
      caches.match(req).then((cached) => cached || fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(CACHE_VERSION).then((c) => c.put(req, copy));
        return res;
      }))
    );
    return;
  }

  // Network-first for HTML navigations; fall back to cached index if offline.
  if (req.mode === "navigate") {
    event.respondWith(
      fetch(req).catch(() => caches.match("/") || new Response(
        "<h1>life-os offline</h1><p>Phone is off-tailnet. Form submissions must wait until you're back on Tailscale.</p>",
        { headers: { "Content-Type": "text/html" } }
      ))
    );
    return;
  }
});
