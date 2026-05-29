import { useEffect, useRef, useState } from 'react'

import { createVideo, getVideo, listVideos } from '../api/client.js'
import ChatPanel from '../components/ChatPanel.jsx'
import TranscriptViewer from '../components/TranscriptViewer.jsx'
import UrlSubmitForm from '../components/UrlSubmitForm.jsx'
import VideoDetails from '../components/VideoDetails.jsx'
import VideoEditor from '../components/VideoEditor.jsx'
import VideoLibrary from '../components/VideoLibrary.jsx'

export default function HomePage() {
  const [video, setVideo] = useState(null)
  const [recentVideos, setRecentVideos] = useState([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [showEditor, setShowEditor] = useState(false)
  const [error, setError] = useState('')
  const detailRef = useRef(null)

  async function loadRecentVideos() {
    try {
      const videos = await listVideos()
      setRecentVideos(videos)
    } catch {
      // Keep the page usable if the list endpoint fails.
    }
  }

  useEffect(() => {
    loadRecentVideos()
  }, [])

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
        <h1>MyInsta</h1>
        <p>Paste an Instagram video link, save it to your library, transcribe it, then chat with the transcript.</p>
      </section>

      <section className="card">
        <UrlSubmitForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />
        {error ? <p className="error">{error}</p> : null}
      </section>

      <VideoLibrary
        videos={recentVideos}
        selectedId={video?.id}
        onView={(videoId) => openVideo(videoId, { edit: false })}
        onEdit={(videoId) => openVideo(videoId, { edit: true })}
        onDeleted={handleVideoDeleted}
      />

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
                  Edit this video
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
