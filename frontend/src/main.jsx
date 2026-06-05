import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import './styles.css'

// Register service worker for PWA support
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/myinsta/sw.js', { scope: '/myinsta/' })
      .then((registration) => {
        registration.update()
        if (registration.waiting) registration.waiting.postMessage({ type: 'SKIP_WAITING' })
      })
      .catch((err) => console.warn('SW registration failed:', err))
  })
}

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
