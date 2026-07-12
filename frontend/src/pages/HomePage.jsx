import { useEffect, useRef, useState } from 'react'

import { createVideo, getVideo, listVideosPaginated, retryVideo } from '../api/client.js'
import { useLanguage } from '../context/LanguageContext.jsx'
import { useTheme } from '../context/ThemeContext.jsx'
import { useToast } from '../context/ToastContext.jsx'
import OnboardingModal, { shouldShowOnboarding, markOnboardingDone } from '../components/OnboardingModal.jsx'
import ShortcutsModal from '../components/ShortcutsModal.jsx'
import StatsPanel from '../components/StatsPanel.jsx'
import StudyWorkspace from '../components/StudyWorkspace.jsx'
import UrlSubmitForm from '../components/UrlSubmitForm.jsx'
import VideoLibrary from '../components/VideoLibrary.jsx'

// ── Notification helper ──────────────────────────────────────────────────────
async function requestNotificationPermission() {
  if (!('Notification' in window)) return
  if (Notification.permission === 'default') {
    await Notification.requestPermission()
  }
}

function fireNotification(title, body) {
  if (!('Notification' in window) || Notification.permission !== 'granted') return
  try {
    new Notification(title, { body, icon: '/myinsta/favicon.ico' })
  } catch {
    // Some browsers block notifications in certain contexts — fail silently
  }
}

// ── Header controls ──────────────────────────────────────────────────────────
function LanguageToggle() {
  const { lang, switchLang } = useLanguage()
  return (
    <div className="lang-toggle" aria-label="Language selector">
      <button
        type="button"
        className={`lang-btn${lang === 'en' ? ' lang-btn-active' : ''}`}
        onClick={() => switchLang('en')}
        aria-pressed={lang === 'en'}
      >
        EN
      </button>
      <button
        type="button"
        className={`lang-btn${lang === 'ar' ? ' lang-btn-active' : ''}`}
        onClick={() => switchLang('ar')}
        aria-pressed={lang === 'ar'}
      >
        ع
      </button>
    </div>
  )
}

function ThemeToggle() {
  const { theme, toggleTheme } = useTheme()
  const { t } = useLanguage()
  const isDark = theme === 'dark'
  return (
    <button
      type="button"
      className="theme-toggle-btn"
      onClick={toggleTheme}
      title={isDark ? t('switchToLight') : t('switchToDark')}
      aria-label={isDark ? t('switchToLight') : t('switchToDark')}
    >
      {isDark ? (
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="5"/>
          <line x1="12" y1="1"  x2="12" y2="3"/>
          <line x1="12" y1="21" x2="12" y2="23"/>
          <line x1="4.22" y1="4.22"   x2="5.64"  y2="5.64"/>
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
          <line x1="1"  y1="12" x2="3"  y2="12"/>
          <line x1="21" y1="12" x2="23" y2="12"/>
          <line x1="4.22"  y1="19.78" x2="5.64"  y2="18.36"/>
          <line x1="18.36" y1="5.64"  x2="19.78" y2="4.22"/>
        </svg>
      ) : (
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
        </svg>
      )}
    </button>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────
export default function HomePage() {
  const { t } = useLanguage()
  const { showToast } = useToast()
  const [video, setVideo]               = useState(null)
  const [recentVideos, setRecentVideos]   = useState([])
  const [totalVideos,  setTotalVideos]    = useState(0)
  const [hasMore,      setHasMore]        = useState(false)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const offsetRef = useRef(0)
  const PAGE_SIZE = 20

  const [isSubmitting, setIsSubmitting] = useState(false)
  const [showEditor, setShowEditor]     = useState(false)
  const [error, setError]               = useState('')
  const [backendError, setBackendError] = useState('')
  const [showOnlineBanner, setShowOnlineBanner] = useState(false)
  const [onlineBannerHiding, setOnlineBannerHiding] = useState(false)
  const [loadingLibrary, setLoadingLibrary] = useState(true)
  const [showOnboarding, setShowOnboarding] = useState(shouldShowOnboarding)
  const [showShortcuts, setShowShortcuts]   = useState(false)
  const [statsKey, setStatsKey]         = useState(0) // bump to re-fetch stats
  const detailRef   = useRef(null)
  const prevStatus  = useRef(null)  // track status changes for notifications
  const wasOffline  = useRef(false)

  async function loadRecentVideos() {
    // Reset to first page
    offsetRef.current = 0
    try {
      const { items, total, hasMore: more } = await listVideosPaginated(PAGE_SIZE, 0)
      setRecentVideos(items)
      setTotalVideos(total)
      setHasMore(more)
      offsetRef.current = items.length
      setBackendError('')
      // Only flash online banner after recovery or first successful connect
      if (wasOffline.current || !sessionStorage.getItem('myinsta-online-seen')) {
        setShowOnlineBanner(true)
        setOnlineBannerHiding(false)
        sessionStorage.setItem('myinsta-online-seen', '1')
      }
      wasOffline.current = false
    } catch (err) {
      setBackendError(err.message)
      wasOffline.current = true
      setShowOnlineBanner(false)
    } finally {
      setLoadingLibrary(false)
    }
  }

  async function loadMoreVideos() {
    if (isLoadingMore || !hasMore) return
    setIsLoadingMore(true)
    try {
      const { items, total, hasMore: more } = await listVideosPaginated(PAGE_SIZE, offsetRef.current)
      setRecentVideos((prev) => {
        // Avoid duplicates (in case a new video was added between loads)
        const existingIds = new Set(prev.map((v) => v.id))
        const fresh = items.filter((v) => !existingIds.has(v.id))
        return [...prev, ...fresh]
      })
      setTotalVideos(total)
      setHasMore(more)
      offsetRef.current += items.length
    } catch (err) {
      setError(err.message)
      showToast(err.message, 'error')
    } finally {
      setIsLoadingMore(false)
    }
  }

  useEffect(() => { loadRecentVideos() }, [])

  // Auto-dismiss backend online banner
  useEffect(() => {
    if (!showOnlineBanner) return undefined
    const hideTimer = window.setTimeout(() => setOnlineBannerHiding(true), 2600)
    const removeTimer = window.setTimeout(() => {
      setShowOnlineBanner(false)
      setOnlineBannerHiding(false)
    }, 3000)
    return () => {
      window.clearTimeout(hideTimer)
      window.clearTimeout(removeTimer)
    }
  }, [showOnlineBanner])

  function normalizeUrl(value) {
    return (value || '').trim().replace(/\/+$/, '').toLowerCase()
  }

  async function handleSubmit(url) {
    // Request notification permission on first submit (requires user gesture)
    requestNotificationPermission()
    // Dismiss onboarding on first real action
    if (showOnboarding) { markOnboardingDone(); setShowOnboarding(false) }

    const existing = recentVideos.find(
      (item) => normalizeUrl(item.source_url) === normalizeUrl(url),
    )
    if (existing) {
      const label = existing.title || t('videoHash', existing.id)
      const openExisting = window.confirm(t('duplicateUrlConfirm', label))
      if (openExisting) {
        await openVideo(existing.id, { edit: false })
        return
      }
      // User chose to process again — continue below
    }

    setIsSubmitting(true)
    setError('')
    try {
      const created = await createVideo(url)
      setVideo(created)
      prevStatus.current = created.status
      setShowEditor(false)
      showToast(t('toastVideoQueued'), 'success')
      await loadRecentVideos()
      setStatsKey((k) => k + 1)
      window.setTimeout(() => {
        detailRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }, 80)
    } catch (err) {
      setError(err.message)
      showToast(err.message, 'error')
    } finally {
      setIsSubmitting(false)
    }
  }

  async function openVideo(videoId, { edit = false } = {}) {
    setError('')
    try {
      const selected = await getVideo(videoId)
      setVideo(selected)
      prevStatus.current = selected.status
      setShowEditor(edit)
      window.setTimeout(() => {
        detailRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }, 50)
    } catch (err) {
      setError(err.message)
      showToast(err.message, 'error')
    }
  }

  function handleVideoUpdated(updated) {
    setVideo(updated)
    setShowEditor(false)
    loadRecentVideos()
  }

  function handleVideoDeleted(deletedId) {
    setVideo((current) => (current?.id === deletedId ? null : current))
    setShowEditor(false)
    loadRecentVideos()
    setStatsKey((k) => k + 1)
    showToast(t('toastVideoDeleted'), 'info')
  }

  async function handleRetryVideo(videoId) {
    try {
      const updated = await retryVideo(videoId)
      showToast(t('toastRetryStarted'), 'success')
      if (video?.id === videoId) {
        setVideo(updated)
        prevStatus.current = updated.status
      }
      await loadRecentVideos()
      setStatsKey((k) => k + 1)
    } catch (err) {
      showToast(err.message, 'error')
    }
  }

  // Global keyboard shortcuts
  useEffect(() => {
    function onKeyDown(e) {
      // ? → open shortcuts modal (only when not in an input/textarea)
      if (e.key === '?' && !['INPUT','TEXTAREA'].includes(e.target.tagName)) {
        e.preventDefault()
        setShowShortcuts((prev) => !prev)
        return
      }
      // Escape → close shortcuts modal or editor
      if (e.key === 'Escape') {
        if (showShortcuts) { setShowShortcuts(false); return }
        if (showEditor)    { setShowEditor(false);    return }
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [showEditor, showShortcuts])

  // Polling: refresh video status + fire notification when ready
  useEffect(() => {
    if (!video || video.status === 'ready' || video.status === 'failed') return
    const timer = setInterval(async () => {
      try {
        const refreshed = await getVideo(video.id)
        setVideo(refreshed)

        // Fire notification on status transition → ready / failed
        if (prevStatus.current !== 'ready' && refreshed.status === 'ready') {
          const title = refreshed.title || t('untitledVideo')
          fireNotification(t('notificationReady', title), t('notificationBody'))
          showToast(t('notificationReady', title), 'success')
          await loadRecentVideos()
          setStatsKey((k) => k + 1)
        }
        if (prevStatus.current !== 'failed' && refreshed.status === 'failed') {
          const title = refreshed.title || t('untitledVideo')
          fireNotification(
            t('notificationFailed', title),
            refreshed.error_message || t('notificationFailedBody'),
          )
          showToast(refreshed.error_message || t('notificationFailed', title), 'error')
          await loadRecentVideos()
        }
        prevStatus.current = refreshed.status
      } catch (err) {
        setError(err.message)
      }
    }, 1500)
    return () => clearInterval(timer)
  }, [video, t, showToast])

  const hasLibrary = totalVideos > 0 || recentVideos.length > 0

  return (
    <main className="page">
      {/* Modals */}
      {showOnboarding && (
        <OnboardingModal onDone={() => setShowOnboarding(false)} />
      )}
      {showShortcuts && (
        <ShortcutsModal onClose={() => setShowShortcuts(false)} />
      )}

      {/* ── Hero ── */}
      <section className="hero">
        <div className="hero-top">
          <div className="hero-text">
            <p className="hero-kicker">{t('heroKicker')}</p>
            <h1>{t('appName')}</h1>
            <p>{t('appSubtitle')}</p>
          </div>
          <div className="hero-controls">
            <button type="button" className="shortcuts-hint-btn"
              onClick={() => setShowShortcuts(true)}
              title={t('shortcutsTitle')}
              aria-label={t('shortcutsTitle')}>
              ?
            </button>
            <ThemeToggle />
            <LanguageToggle />
          </div>
        </div>
      </section>

      {backendError && (
        <div className="backend-error-banner">
          <span>{t('backendOffline')} {backendError}</span>
          <button type="button" onClick={loadRecentVideos}>{t('retry')}</button>
        </div>
      )}
      {!backendError && showOnlineBanner && (
        <div
          className={`backend-online-banner${onlineBannerHiding ? ' is-hiding' : ''}`}
          role="status"
        >
          <span>{t('backendOnline')}</span>
        </div>
      )}

      <section className="card capture-card">
        <p className="capture-heading">{t('captureHeading')}</p>
        <p className="capture-hint">{t('captureHint')}</p>
        <UrlSubmitForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />
        <div className="capture-chips" aria-hidden="true">
          <span className="capture-chip">▶ {t('chipInstagram')}</span>
          <span className="capture-chip">▶ {t('chipYoutube')}</span>
          <span className="capture-chip">✎ {t('chipTranscript')}</span>
        </div>
        {error ? <p className="error">{error}</p> : null}
      </section>

      {/* Stats panel — only when library has content */}
      {hasLibrary && <StatsPanel key={statsKey} />}

      {loadingLibrary ? (
        <div className="library-loading">
          <span className="library-loading-spinner" />
          {t('connectingToServer')}
        </div>
      ) : (
        <VideoLibrary
          videos={recentVideos}
          totalVideos={totalVideos}
          hasMore={hasMore}
          isLoadingMore={isLoadingMore}
          onLoadMore={loadMoreVideos}
          selectedId={video?.id}
          onView={(videoId) => openVideo(videoId, { edit: false })}
          onEdit={(videoId) => openVideo(videoId, { edit: true })}
          onDeleted={handleVideoDeleted}
          onRetry={handleRetryVideo}
          onRefresh={loadRecentVideos}
        />
      )}

      {video ? (
        <div ref={detailRef}>
          <StudyWorkspace
            video={video}
            allVideos={recentVideos}
            showEditor={showEditor}
            onShowEditor={() => setShowEditor(true)}
            onVideoUpdated={handleVideoUpdated}
            onVideoDeleted={handleVideoDeleted}
          />
        </div>
      ) : null}
    </main>
  )
}
