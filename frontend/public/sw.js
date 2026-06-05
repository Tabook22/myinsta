/**
 * MyInsta Service Worker
 * Strategy: network-first for navigation, cache-first for static assets.
 * API calls are always passed through to the network.
 */
const CACHE = 'myinsta-v3'
const SHELL = ['/myinsta/', '/myinsta/index.html']

// ── Install: cache the app shell ──────────────────────────────────────────
self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)))
  self.skipWaiting()
})

// ── Activate: remove old caches ───────────────────────────────────────────
self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  )
  self.clients.claim()
})

self.addEventListener('message', (e) => {
  if (e.data?.type === 'SKIP_WAITING') self.skipWaiting()
})

// ── Fetch ─────────────────────────────────────────────────────────────────
self.addEventListener('fetch', (e) => {
  const { request } = e
  const url = new URL(request.url)

  // Always hit the network for API calls
  if (url.pathname.startsWith('/myinsta-api/') || url.pathname.startsWith('/api/')) return

  // Navigation requests: network first, fall back to cached index
  if (request.mode === 'navigate') {
    e.respondWith(
      fetch(request).catch(() => caches.match('/myinsta/index.html'))
    )
    return
  }

  // Static assets: network first, then cached fallback. This avoids serving
  // stale JS/CSS after a VPS deploy.
  e.respondWith(
    fetch(request)
      .then((res) => {
        if (res.ok) {
          const clone = res.clone()
          caches.open(CACHE).then((c) => c.put(request, clone))
        }
        return res
      })
      .catch(() => caches.match(request))
  )
})
