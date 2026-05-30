import { useEffect, useState } from 'react'
import { deleteVideo, updateVideo } from '../api/client.js'
import { useLanguage } from '../context/LanguageContext.jsx'

export default function VideoEditor({ video, onUpdated, onDeleted }) {
  const { t } = useLanguage()
  const [title, setTitle]               = useState(video.title || '')
  const [description, setDescription]   = useState(video.description || '')
  const [transcriptText, setTranscriptText] = useState(video.transcript?.full_text || '')
  const [isSaving, setIsSaving]         = useState(false)
  const [isDeleting, setIsDeleting]     = useState(false)
  const [error, setError]               = useState('')

  useEffect(() => {
    setTitle(video.title || '')
    setDescription(video.description || '')
    setTranscriptText(video.transcript?.full_text || '')
    setError('')
  }, [video])

  async function handleSave(event) {
    event.preventDefault()
    setIsSaving(true)
    setError('')
    try {
      const updated = await updateVideo(video.id, {
        title: title.trim() || null,
        description: description.trim() || null,
        transcript_text: transcriptText,
      })
      onUpdated(updated)
    } catch (err) {
      setError(err.message)
    } finally {
      setIsSaving(false)
    }
  }

  async function handleDelete() {
    const label = video.title || video.storage_stamp || t('videoHash', video.id)
    if (!window.confirm(t('deleteConfirm', label))) return
    setIsDeleting(true)
    setError('')
    try {
      await deleteVideo(video.id)
      onDeleted(video.id)
    } catch (err) {
      setError(err.message)
      setIsDeleting(false)
    }
  }

  return (
    <section className="video-editor">
      <div className="editor-header">
        <h3>{t('editSavedVideo')}</h3>
        <button type="button" className="danger-button" onClick={handleDelete}
          disabled={isDeleting || isSaving}>
          {isDeleting ? t('deleting') : t('delete')}
        </button>
      </div>

      <form className="editor-form" onSubmit={handleSave}>
        <label>
          {t('fieldTitle')}
          <input value={title} onChange={(e) => setTitle(e.target.value)} />
        </label>
        <label>
          {t('fieldDescription')}
          <textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
        </label>
        <label>
          {t('fieldTranscript')}
          <textarea rows={8} value={transcriptText}
            onChange={(e) => setTranscriptText(e.target.value)}
            disabled={video.status !== 'ready'} />
        </label>
        <button type="submit" disabled={isSaving || isDeleting}>
          {isSaving ? t('saving') : t('saveChanges')}
        </button>
      </form>
      {error ? <p className="error">{error}</p> : null}
    </section>
  )
}
