import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import './styles.css'

async function clearMyInstaBrowserCache() {
  const registrations = await navigator.serviceWorker.getRegistrations()
  const myInstaRegistrations = registrations.filter((registration) =>
    registration.scope.includes('/myinsta/')
  )

  const cacheKeys = 'caches' in window ? await caches.keys() : []
  const myInstaCacheKeys = cacheKeys.filter((key) => key.startsWith('myinsta-'))

  if (myInstaRegistrations.length > 0) {
    const cleanupRegistration = await navigator.serviceWorker.register('/myinsta/sw.js', {
      scope: '/myinsta/',
      updateViaCache: 'none',
    })
    await cleanupRegistration.update()
    if (cleanupRegistration.waiting) {
      cleanupRegistration.waiting.postMessage({ type: 'SKIP_WAITING' })
    }
    return
  }

  await Promise.all(myInstaCacheKeys.map((key) => caches.delete(key)))
}

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    clearMyInstaBrowserCache()
      .catch((err) => console.warn('SW cleanup failed:', err))
  })
}

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
