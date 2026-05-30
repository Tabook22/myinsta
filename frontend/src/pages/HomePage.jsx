import { useEffect, useRef, useState } from 'react'

import { createVideo, getVideo, listVideos } from '../api/client.js'
import { useLanguage } from '../context/LanguageContext.jsx'
import { useTheme } from '../context/ThemeContext.jsx'
import ChatPanel from '../components/ChatPanel.jsx'
import TranscriptViewer from '../components/TranscriptViewer.jsx'
import UrlSubmitForm from '../components/UrlSubmitForm.jsx'
import VideoDetails from '../components/VideoDetails.jsx'
import VideoEditor from '../components/VideoEditor.jsx'
import VideoLibrary from '../components/VideoLibrary.jsx'

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
        // Sun icon
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
        // Moon icon
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
        </svg>
      )}
    </button>
  )
}

export default function HomePage() {
  const { t } = useLanguage()
  const [video, setVideo]               = useState(null)
  const [recentVideos, setRecentVideos] = useState([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [showEditor, setShowEditor]     = useState(false)
  const [error, setError]               = useState('')
  const [backendError, setBackendError] = useState('')
  const [loadingLibrary, setLoadingLibrary] = useState(true)
  const detailRef = useRef(null)

  async function loadRecentVideos() {
    try {
      const videos = await listVideos()
      setRecentVideos(videos)
      setBackendError('')
    } catch (err) {
      setBackendError(err.message)
    } finally {
      setLoadingLibrary(false)
    }
  }

  useEffect(() => { loadRecentVideos() }, [])

  async function handleSubmit(url) {
    setIsSubmitting(true)
    setError('')
    try {
      const created = await createVideo(url)
      setVideo(created)
      setShowEditor(false)
      await loadRecentVideos()
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
  }

  // Escape key: close the video editor panel when it's open
  useEffect(() => {
    function onKeyDown(e) {
      if (e.key === 'Escape' && showEditor) setShowEditor(false)
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [showEditor])

  useEffect(() => {
    if (!video || video.status === 'ready' || video.status === 'failed') return
    const timer = setInterval(async () => {
      try {
        const refreshed = await getVideo(video.id)
        setVideo(refreshed)
        if (refreshed.status === 'ready' || refreshed.status === 'failed') {
          await loadRecentVideos()
        }
      } catch (err) {
        setError(err.message)
      }
    }, 1500)
    return () => clearInterval(timer)
  }, [video])

  return (
    <main className="page">
      <section className="hero">
        <div className="hero-top">
          <div className="hero-text">
            <h1>{t('appName')}</h1>
            <p>{t('appSubtitle')}</p>
          </div>
          <div className="hero-controls">
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

      {loadingLibrary ? (
        <div className="library-loading">
          <span className="library-loading-spinner" />
          {t('connectingToServer')}
        </div>
      ) : (
        <VideoLibrary
          videos={recentVideos}
          selectedId={video?.id}
          onView={(videoId) => openVideo(videoId, { edit: false })}
          onEdit={(videoId) => openVideo(videoId, { edit: true })}
          onDeleted={handleVideoDeleted}
        />
      )}

      {video ? (
        <section className="grid" ref={detailRef}>
          <div className="card">
            <VideoDetails video={video} />
            <TranscriptViewer status={video.status} transcript={video.transcript} />
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
