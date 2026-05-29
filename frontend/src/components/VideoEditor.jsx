import { useEffect, useState } from 'react'

import { deleteVideo, updateVideo } from '../api/client.js'

export default function VideoEditor({ video, onUpdated, onDeleted }) {
  const [title, setTitle] = useState(video.title || '')
  const [description, setDescription] = useState(video.description || '')
  const [transcriptText, setTranscriptText] = useState(video.transcript?.full_text || '')
  const [isSaving, setIsSaving] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [error, setError] = useState('')

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
    const label = video.title || video.storage_stamp || `Video #${video.id}`
    if (!window.confirm(`Delete "${label}" and all saved files?`)) {
      return
    }

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
        <h3>Edit saved video</h3>
        <button
          type="button"
          className="danger-button"
          onClick={handleDelete}
          disabled={isDeleting || isSaving}
        >
          {isDeleting ? 'Deleting…' : 'Delete'}
        </button>
      </div>

      <form className="editor-form" onSubmit={handleSave}>
        <label>
          Title
          <input value={title} onChange={(event) => setTitle(event.target.value)} />
        </label>
        <label>
          Description
          <textarea
            rows={3}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
        </label>
        <label>
          Transcript
          <textarea
            rows={8}
            value={transcriptText}
            onChange={(event) => setTranscriptText(event.target.value)}
            disabled={video.status !== 'ready'}
          />
        </label>
        <button type="submit" disabled={isSaving || isDeleting}>
          {isSaving ? 'Saving…' : 'Save changes'}
        </button>
      </form>
      {error ? <p className="error">{error}</p> : null}
    </section>
  )
}
