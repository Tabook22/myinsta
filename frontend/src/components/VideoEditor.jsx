import { useEffect, useState } from 'react'
import { deleteVideo, updateVideo } from '../api/client.js'
import { useLanguage } from '../context/LanguageContext.jsx'

const TAG_COLORS = [
  '#4f46e5','#0891b2','#16a34a','#ca8a04','#dc2626',
  '#7c3aed','#0284c7','#15803d','#b45309','#be185d',
]

function tagColor(tag) {
  let hash = 0
  for (let i = 0; i < tag.length; i++) hash = tag.charCodeAt(i) + ((hash << 5) - hash)
  return TAG_COLORS[Math.abs(hash) % TAG_COLORS.length]
}

export default function VideoEditor({ video, onUpdated, onDeleted }) {
  const { t } = useLanguage()
  const [title, setTitle]               = useState(video.title || '')
  const [description, setDescription]   = useState(video.description || '')
  const [transcriptText, setTranscriptText] = useState(video.transcript?.full_text || '')
  const [tags, setTags]                 = useState(video.tags || [])
  const [tagInput, setTagInput]         = useState('')
  const [isSaving, setIsSaving]         = useState(false)
  const [isDeleting, setIsDeleting]     = useState(false)
  const [error, setError]               = useState('')

  useEffect(() => {
    setTitle(video.title || '')
    setDescription(video.description || '')
    setTranscriptText(video.transcript?.full_text || '')
    setTags(video.tags || [])
    setError('')
  }, [video])

  function addTag(raw) {
    const tag = raw.trim().toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9؀-ۿ\-]/g, '')
    if (!tag || tags.includes(tag)) return
    setTags((prev) => [...prev, tag])
  }

  function handleTagKeyDown(e) {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      addTag(tagInput)
      setTagInput('')
    } else if (e.key === 'Backspace' && !tagInput && tags.length) {
      setTags((prev) => prev.slice(0, -1))
    }
  }

  function removeTag(tag) {
    setTags((prev) => prev.filter((t) => t !== tag))
  }

  async function handleSave(event) {
    event.preventDefault()
    setIsSaving(true)
    setError('')
    try {
      const updated = await updateVideo(video.id, {
        title: title.trim() || null,
        description: description.trim() || null,
        transcript_text: transcriptText,
        tags,
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

        {/* Tags */}
        <div className="tag-field">
          <span className="tag-field-label">{t('fieldTags')}</span>
          <div className="tag-input-wrap">
            {tags.map((tag) => (
              <span key={tag} className="tag-chip" style={{ '--tag-color': tagColor(tag) }}>
                #{tag}
                <button
                  type="button"
                  className="tag-chip-remove"
                  onClick={() => removeTag(tag)}
                  aria-label={`Remove ${tag}`}
                >×</button>
              </span>
            ))}
            <input
              className="tag-input"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={handleTagKeyDown}
              onBlur={() => { if (tagInput.trim()) { addTag(tagInput); setTagInput('') } }}
              placeholder={tags.length === 0 ? t('tagPlaceholder') : ''}
            />
          </div>
        </div>

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
