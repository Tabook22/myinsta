import { useState } from 'react'
import { useLanguage } from '../context/LanguageContext.jsx'

export default function UrlSubmitForm({ onSubmit, isSubmitting }) {
  const { t } = useLanguage()
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
        placeholder={t('urlPlaceholder')}
        value={url}
        onChange={(event) => setUrl(event.target.value)}
        required
      />
      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? t('submitting') : t('processVideo')}
      </button>
    </form>
  )
}
