import { useEffect, useState } from 'react'
import { translateDescriptionToArabic } from '../api/client.js'
import { useLanguage } from '../context/LanguageContext.jsx'
import AudioPlayer from './AudioPlayer.jsx'
import NotesEditor from './NotesEditor.jsx'
import NotionExport from './NotionExport.jsx'
import ProcessingSteps from './ProcessingSteps.jsx'
import VideoPlayer from './VideoPlayer.jsx'
import WikiDocuments from './WikiDocuments.jsx'

// ── Helpers ───────────────────────────────────────────────────────────────────
function formatDuration(seconds) {
  if (!seconds) return null
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.round(seconds % 60)
  if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  return `${m}:${s.toString().padStart(2, '0')}`
}

const AVATAR_COLORS = [
  '#4f46e5','#0891b2','#16a34a','#ca8a04',
  '#7c3aed','#0284c7','#be185d','#dc2626',
]
function avatarColor(name) {
  let h = 0
  for (const c of name) h = c.charCodeAt(0) + ((h << 5) - h)
  return AVATAR_COLORS[Math.abs(h) % AVATAR_COLORS.length]
}

function sourceLabel(platform, t) {
  if (platform === 'instagram') return t('sourceInstagram')
  if (platform === 'youtube') return t('sourceYoutube')
  return t('sourceUnknown')
}

// ── Creator card ──────────────────────────────────────────────────────────────
function CreatorCard({ video, allVideos }) {
  const { t } = useLanguage()
  if (!video.uploader) return null

  const count = allVideos.filter(
    (v) => v.uploader === video.uploader && !v.deleted_at
  ).length
  const initial = video.uploader.charAt(0).toUpperCase()
  const color   = avatarColor(video.uploader)

  return (
    <div className="creator-card">
      <div className="creator-avatar" style={{ background: color }}>
        {initial}
      </div>
      <div className="creator-card-info">
        {video.creator_url ? (
          <a href={video.creator_url} target="_blank" rel="noreferrer"
            className="creator-card-name">
            @{video.uploader}
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
              <polyline points="15 3 21 3 21 9"/>
              <line x1="10" y1="14" x2="21" y2="3"/>
            </svg>
          </a>
        ) : (
          <span className="creator-card-name">@{video.uploader}</span>
        )}
        <span className="creator-card-count">
          {t('creatorVideoCount', count)}
        </span>
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────
export default function VideoDetails({ video, allVideos = [] }) {
  const { t } = useLanguage()
  const duration = formatDuration(video.duration_seconds)
  const [descriptionMode, setDescriptionMode] = useState('original')
  const [arabicDescription, setArabicDescription] = useState(video.description_translation_ar || '')
  const [isTranslatingDescription, setIsTranslatingDescription] = useState(false)
  const [descriptionTranslationError, setDescriptionTranslationError] = useState('')

  useEffect(() => {
    setDescriptionMode('original')
    setArabicDescription(video.description_translation_ar || '')
    setDescriptionTranslationError('')
  }, [video.id, video.description, video.description_translation_ar])

  const displayedDescription =
    descriptionMode === 'arabic' ? arabicDescription : video.description

  async function handleShowArabicDescription() {
    if (!video.description?.trim()) return
    setDescriptionTranslationError('')
    if (arabicDescription) {
      setDescriptionMode('arabic')
      return
    }

    setIsTranslatingDescription(true)
    try {
      const result = await translateDescriptionToArabic(video.id)
      setArabicDescription(result.translated_text)
      setDescriptionMode('arabic')
    } catch (err) {
      setDescriptionTranslationError(err.message)
    } finally {
      setIsTranslatingDescription(false)
    }
  }

  return (
    <section>
      <VideoPlayer video={video} />
      <AudioPlayer video={video} />

      {!video.video_url && video.thumbnail_url ? (
        <img className="thumbnail" src={video.thumbnail_url}
          alt={video.title || t('untitledVideo')} />
      ) : null}

      <h2>{video.title || t('untitledVideo')}</h2>

      {/* Status + duration inline */}
      <div className="video-meta-row">
        <span className={`source-badge source-badge-${video.platform || 'unknown'}`}>
          {sourceLabel(video.platform, t)}
        </span>
        <span className="status">{video.status}</span>
        {duration && (
          <span className="video-duration-badge">⏱ {duration}</span>
        )}
      </div>

      {/* Processing step stepper */}
      <ProcessingSteps video={video} />

      {/* Creator card */}
      <CreatorCard video={video} allVideos={allVideos} />

      {video.storage_stamp ? (
        <p><strong>{t('labelSavedAs')}</strong> {video.storage_stamp}</p>
      ) : null}
      {video.storage_folder ? (
        <p><strong>{t('labelFolder')}</strong> {video.storage_folder}</p>
      ) : null}

      <p>
        <strong>{t('labelSource')}</strong>{' '}
        <a href={video.source_url} target="_blank" rel="noreferrer">{t('openOriginal')}</a>
      </p>

      {video.description ? (
        <div className="description-block">
          <div className="description-header">
            <strong>{t('labelDescription')}</strong>
            <div className="transcript-mode-toggle" aria-label={t('descriptionViewMode')}>
              <button
                type="button"
                className={descriptionMode === 'original' ? 'transcript-mode-active' : ''}
                onClick={() => setDescriptionMode('original')}
              >
                {t('originalTranscript')}
              </button>
              <button
                type="button"
                className={descriptionMode === 'arabic' ? 'transcript-mode-active' : ''}
                onClick={handleShowArabicDescription}
                disabled={isTranslatingDescription}
              >
                {isTranslatingDescription ? t('translatingDescription') : t('arabicTranscript')}
              </button>
            </div>
          </div>
          {descriptionTranslationError && (
            <p className="error">{descriptionTranslationError}</p>
          )}
          <p
            className="description-text"
            dir={descriptionMode === 'arabic' ? 'rtl' : undefined}
            lang={descriptionMode === 'arabic' ? 'ar' : undefined}
          >
            {displayedDescription}
          </p>
        </div>
      ) : null}
      {video.error_message ? (
        <p className="error">{video.error_message}</p>
      ) : null}

      {/* Notion export */}
      {video.status === 'ready' && <NotionExport video={video} />}
      <WikiDocuments video={video} />

      <NotesEditor video={video} />
    </section>
  )
}
