import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import './styles.css'

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.getRegistrations()
      .then((registrations) => {
        registrations
          .filter((registration) => registration.scope.includes('/myinsta/'))
          .forEach((registration) => registration.unregister())
      })
      .catch((err) => console.warn('SW cleanup failed:', err))

    if ('caches' in window) {
      caches.keys()
        .then((keys) => {
          keys
            .filter((key) => key.startsWith('myinsta-'))
            .forEach((key) => caches.delete(key))
        })
        .catch((err) => console.warn('Cache cleanup failed:', err))
    }
  })
}

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
