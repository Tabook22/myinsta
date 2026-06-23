const MYINSTA_CACHE_PREFIX = 'myinsta-'

self.addEventListener('install', (event) => {
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys
          .filter((key) => key.startsWith(MYINSTA_CACHE_PREFIX))
          .map((key) => caches.delete(key))
      ))
      .then(() => self.registration.unregister())
      .then(() => self.clients.matchAll({ type: 'window' }))
      .then((clients) => Promise.all(clients.map((client) => client.navigate(client.url))))
  )
})

self.addEventListener('fetch', () => {
  return
})
