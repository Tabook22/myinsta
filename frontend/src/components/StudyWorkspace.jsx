import { useEffect, useRef, useState } from 'react'
import { useLanguage } from '../context/LanguageContext.jsx'
import AudioPlayer from './AudioPlayer.jsx'
import ChatPanel from './ChatPanel.jsx'
import NotesEditor from './NotesEditor.jsx'
import TranscriptViewer from './TranscriptViewer.jsx'
import VideoDetails from './VideoDetails.jsx'
import VideoEditor from './VideoEditor.jsx'
import VideoPlayer from './VideoPlayer.jsx'

const TABS = [
  { id: 'overview', labelKey: 'tabOverview' },
  { id: 'transcript', labelKey: 'tabTranscript' },
  { id: 'chat', labelKey: 'tabChat' },
  { id: 'notes', labelKey: 'tabNotes' },
]

export default function StudyWorkspace({
  video,
  allVideos = [],
  showEditor = false,
  onShowEditor,
  onVideoUpdated,
  onVideoDeleted,
}) {
  const { t } = useLanguage()
  const playerRef = useRef(null)
  const [tab, setTab] = useState('overview')

  useEffect(() => {
    // Prefer transcript when ready; stay on overview while processing
    if (video.status === 'ready') setTab('transcript')
    else setTab('overview')
  }, [video.id, video.status])

  function seekTo(seconds) {
    playerRef.current?.seekTo(seconds)
    // Keep player in view when seeking from transcript/chat
    const el = document.querySelector('.study-player-dock')
    el?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }

  const isReady = video.status === 'ready'

  return (
    <section className="study-workspace card">
      <div className="study-workspace-header">
        <div>
          <p className="study-kicker">{t('studyMode')}</p>
          <h2 className="study-title">{video.title || t('untitledVideo')}</h2>
        </div>
        {!showEditor && (
          <button type="button" className="btn-secondary" onClick={onShowEditor}>
            {t('editThisVideo')}
          </button>
        )}
      </div>

      {/* Sticky player dock shared across tabs */}
      <div className="study-player-dock">
        <VideoPlayer ref={playerRef} video={video} sticky />
        <AudioPlayer video={video} />
      </div>

      <div className="study-tabs" role="tablist" aria-label={t('studyMode')}>
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={tab === item.id}
            className={`study-tab${tab === item.id ? ' study-tab-active' : ''}`}
            onClick={() => setTab(item.id)}
          >
            {t(item.labelKey)}
          </button>
        ))}
      </div>

      <div className="study-tab-panel" role="tabpanel">
        {tab === 'overview' && (
          <VideoDetails
            video={video}
            allVideos={allVideos}
            onVideoUpdated={onVideoUpdated}
            hidePlayer
            hideNotes
            compact
          />
        )}

        {tab === 'transcript' && (
          <TranscriptViewer
            status={video.status}
            transcript={video.transcript}
            video={video}
            onSeek={seekTo}
          />
        )}

        {tab === 'chat' && (
          <ChatPanel
            video={video}
            onSeek={seekTo}
            onOpenTranscript={() => setTab('transcript')}
          />
        )}

        {tab === 'notes' && (
          isReady ? (
            <NotesEditor video={video} />
          ) : (
            <p className="study-locked-note">{t('notesLocked')}</p>
          )
        )}
      </div>

      {showEditor && (
        <VideoEditor
          video={video}
          onUpdated={onVideoUpdated}
          onDeleted={onVideoDeleted}
        />
      )}
    </section>
  )
}
