import { useState } from 'react'

export default function UrlSubmitForm({ onSubmit, isSubmitting }) {
  const [url, setUrl] = useState('')

  function handleSubmit(event) {
    event.preventDefault()
    if (!url.trim()) return
    onSubmit(url.trim())
  }

  return (
    <form className="url-form" onSubmit={handleSubmit}>
      <input
        type="url"
        placeholder="https://www.instagram.com/reel/..."
        value={url}
        onChange={(event) => setUrl(event.target.value)}
        required
      />
      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Submitting...' : 'Process video'}
      </button>
    </form>
  )
}
