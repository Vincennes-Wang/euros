// Service worker: offline support for GitHub Pages (scope = the directory of this file).
//
// - App shell: stale-while-revalidate, so a deploy shows up on the next load.
// - data/coins.json: stale-while-revalidate; each fresh copy also warms the thumbnail cache.
// - Thumbnails and flags: cache-first, all precached after install (~7 MB).
// - Full images: cache-first, cached when first viewed.

const SHELL = "euros-shell-v1";
const DATA = "euros-data-v1";
const IMAGES = "euros-images-v1";
const CACHES = [SHELL, DATA, IMAGES];

const scope = new URL(self.registration.scope);
const url = (path) => new URL(path, scope).href;
const COINS = url("data/coins.json");
const SHELL_FILES = [
  "./", "index.html", "app/main.js", "app/filter.js", "app/i18n.js", "app/store.js", "app/styles.css",
  "manifest.webmanifest", "icons/icon-192.png", "icons/icon-512.png",
].map(url);

self.addEventListener("install", (event) => {
  event.waitUntil((async () => {
    await (await caches.open(SHELL)).addAll(SHELL_FILES);
    await (await caches.open(DATA)).add(COINS);
    self.skipWaiting();
  })());
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    for (const name of await caches.keys()) if (!CACHES.includes(name)) await caches.delete(name);
    await self.clients.claim();
    const cached = await (await caches.open(DATA)).match(COINS);
    if (cached) await warmData(await cached.json());
  })());
});

/** Precache every thumbnail and flag referenced by coins.json that is not cached yet. */
async function warmData(coins) {
  const cache = await caches.open(DATA);
  const wanted = new Set();
  for (const c of coins) {
    wanted.add(url(`flags/${c.country_code}.svg`));
    for (const image of [c.image, ...Object.values(c.variant_images || {}).map((v) => v.image)]) {
      if (image) wanted.add(url(image.replace(/^data\/images\//, "data/thumbs/").replace(/\.[^./]+$/, ".webp")));
    }
  }
  const have = new Set((await cache.keys()).map((r) => r.url));
  const missing = [...wanted].filter((u) => !have.has(u));
  for (let i = 0; i < missing.length; i += 16) {
    await Promise.allSettled(missing.slice(i, i + 16).map((u) => cache.add(u)));
  }
}

async function cacheFirst(cacheName, request) {
  const cache = await caches.open(cacheName);
  const hit = await cache.match(request);
  if (hit) return hit;
  const res = await fetch(request);
  if (res.ok) cache.put(request, res.clone());
  return res;
}

async function staleWhileRevalidate(cacheName, request, event, onFresh) {
  const cache = await caches.open(cacheName);
  const hit = await cache.match(request, { ignoreSearch: true });
  const update = fetch(request).then(async (res) => {
    if (res.ok) {
      await cache.put(request, res.clone());
      if (onFresh) await onFresh(res.clone());
    }
    return res;
  });
  if (hit) {
    event.waitUntil(update.catch(() => {}));
    return hit;
  }
  return update;
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const u = new URL(req.url);
  if (u.origin !== scope.origin || !u.pathname.startsWith(scope.pathname)) return;
  const path = u.pathname.slice(scope.pathname.length);

  if (path === "data/coins.json") {
    event.respondWith(staleWhileRevalidate(DATA, req, event, async (res) => warmData(await res.json())));
  } else if (path.startsWith("data/thumbs/") || path.startsWith("flags/")) {
    event.respondWith(cacheFirst(DATA, req));
  } else if (path.startsWith("data/images/")) {
    event.respondWith(cacheFirst(IMAGES, req));
  } else if (req.mode === "navigate") {
    event.respondWith(staleWhileRevalidate(SHELL, new Request(url("./")), event));
  } else if (SHELL_FILES.includes(u.href)) {
    event.respondWith(staleWhileRevalidate(SHELL, req, event));
  }
});
