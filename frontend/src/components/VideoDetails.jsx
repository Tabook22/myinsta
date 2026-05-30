import { useLanguage } from '../context/LanguageContext.jsx'
import AudioPlayer from './AudioPlayer.jsx'
import NotesEditor from './NotesEditor.jsx'
import VideoPlayer from './VideoPlayer.jsx'

export default function VideoDetails({ video }) {
  const { t } = useLanguage()

  return (
    <section>
      <VideoPlayer video={video} />
      <AudioPlayer video={video} />

      {!video.video_url && video.thumbnail_url ? (
        <img className="thumbnail" src={video.thumbnail_url} alt={video.title || t('untitledVideo')} />
      ) : null}

      <h2>{video.title || t('untitledVideo')}</h2>
      <p><span className="status">{video.status}</span></p>

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

      {video.uploader ? (
        <p>
          <strong>{t('labelCreator')}</strong>{' '}
          {video.creator_url ? (
            <a href={video.creator_url} target="_blank" rel="noreferrer" className="creator-link">
              {video.uploader}
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                <polyline points="15 3 21 3 21 9"/>
                <line x1="10" y1="14" x2="21" y2="3"/>
              </svg>
            </a>
          ) : video.uploader}
        </p>
      ) : null}

      {video.duration_seconds ? (
        <p><strong>{t('labelDuration')}</strong> {Math.round(video.duration_seconds)} {t('seconds')}</p>
      ) : null}
      {video.description ? (
        <p><strong>{t('labelDescription')}</strong> {video.description}</p>
      ) : null}
      {video.error_message ? (
        <p className="error">{video.error_message}</p>
      ) : null}

      <NotesEditor video={video} />
    </section>
  )
}
