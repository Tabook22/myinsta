import { useEffect, useRef, useState } from 'react'

import { createVideo, getVideo, listVideosPaginated } from '../api/client.js'
import { useLanguage } from '../context/LanguageContext.jsx'
import { useTheme } from '../context/ThemeContext.jsx'
import ChatPanel from '../components/ChatPanel.jsx'
import OnboardingModal, { shouldShowOnboarding, markOnboardingDone } from '../components/OnboardingModal.jsx'
import ShortcutsModal from '../components/ShortcutsModal.jsx'
import StatsPanel from '../components/StatsPanel.jsx'
import TranscriptViewer from '../components/TranscriptViewer.jsx'
import UrlSubmitForm from '../components/UrlSubmitForm.jsx'
import VideoDetails from '../components/VideoDetails.jsx'
import VideoEditor from '../components/VideoEditor.jsx'
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
  const [loadingLibrary, setLoadingLibrary] = useState(true)
  const [showOnboarding, setShowOnboarding] = useState(shouldShowOnboarding)
  const [showShortcuts, setShowShortcuts]   = useState(false)
  const [statsKey, setStatsKey]         = useState(0) // bump to re-fetch stats
  const detailRef   = useRef(null)
  const prevStatus  = useRef(null)  // track status changes for notifications

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
    } catch (err) {
      setBackendError(err.message)
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
    } finally {
      setIsLoadingMore(false)
    }
  }

  useEffect(() => { loadRecentVideos() }, [])

  async function handleSubmit(url) {
    // Request notification permission on first submit (requires user gesture)
    requestNotificationPermission()
    // Dismiss onboarding on first real action
    if (showOnboarding) { markOnboardingDone(); setShowOnboarding(false) }

    setIsSubmitting(true)
    setError('')
    try {
      const created = await createVideo(url)
      setVideo(created)
      prevStatus.current = created.status
      setShowEditor(false)
      await loadRecentVideos()
      setStatsKey((k) => k + 1)
    } catch (err) {
      setError(err.message)
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

        // Fire notification on status transition → ready
        if (prevStatus.current !== 'ready' && refreshed.status === 'ready') {
          const title = refreshed.title || t('untitledVideo')
          fireNotification(t('notificationReady', title), t('notificationBody'))
          await loadRecentVideos()
          setStatsKey((k) => k + 1)
        }
        prevStatus.current = refreshed.status

        if (refreshed.status === 'failed') {
          await loadRecentVideos()
        }
      } catch (err) {
        setError(err.message)
      }
    }, 1500)
    return () => clearInterval(timer)
  }, [video, t])

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

      <section className="card">
        <UrlSubmitForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />
        {error ? <p className="error">{error}</p> : null}
      </section>

      {/* Stats panel — re-fetches when statsKey changes */}
      <StatsPanel key={statsKey} />

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
          onRefresh={loadRecentVideos}
        />
      )}

      {video ? (
        <section className="grid" ref={detailRef}>
          <div className="card">
            <VideoDetails video={video} allVideos={recentVideos} />
            <TranscriptViewer status={video.status} transcript={video.transcript} video={video} />
            {showEditor ? (
              <VideoEditor
                video={video}
                onUpdated={handleVideoUpdated}
                onDeleted={handleVideoDeleted}
              />
            ) : (
              <div className="detail-actions">
                <button type="button" onClick={() => setShowEditor(true)}>
                  {t('editThisVideo')}
                </button>
              </div>
            )}
          </div>
          <div className="card">
            <ChatPanel video={video} />
          </div>
        </section>
      ) : null}
    </main>
  )
}
