import { useState } from 'react'
import { exportToNotion } from '../api/client.js'
import { useLanguage } from '../context/LanguageContext.jsx'

const KEY_API   = 'notion-api-key'
const KEY_DB    = 'notion-database-id'

export default function NotionExport({ video }) {
  const { t } = useLanguage()
  const [apiKey,      setApiKey]      = useState(() => localStorage.getItem(KEY_API)  || '')
  const [databaseId,  setDatabaseId]  = useState(() => localStorage.getItem(KEY_DB)   || '')
  const [showSetup,   setShowSetup]   = useState(false)
  const [status,      setStatus]      = useState('idle') // idle | loading | success | error
  const [resultUrl,   setResultUrl]   = useState('')
  const [errorMsg,    setErrorMsg]    = useState('')

  const isConfigured = apiKey.startsWith('secret_') && databaseId.length > 10

  function saveConfig(e) {
    e.preventDefault()
    localStorage.setItem(KEY_API, apiKey.trim())
    localStorage.setItem(KEY_DB,  databaseId.trim())
    setShowSetup(false)
  }

  async function handleExport() {
    if (!isConfigured) { setShowSetup(true); return }
    setStatus('loading')
    setErrorMsg('')
    try {
      const result = await exportToNotion(video.id, apiKey, databaseId)
      setResultUrl(result.url)
      setStatus('success')
    } catch (err) {
      setErrorMsg(err.message)
      setStatus('error')
    }
  }

  return (
    <div className="notion-export">
      <div className="notion-export-row">
        {/* Notion logo icon */}
        <svg className="notion-icon" viewBox="0 0 24 24" fill="currentColor">
          <path d="M4.459 4.208c.746.606 1.026.56 2.428.466l13.215-.793c.28 0 .047-.28-.046-.326L17.86 1.968c-.42-.326-.981-.7-2.055-.607L3.01 2.295c-.466.046-.56.28-.374.466zm.793 3.08v13.904c0 .747.373 1.027 1.214.98l14.523-.84c.841-.046.935-.56.935-1.167V6.354c0-.606-.233-.933-.748-.887l-15.177.887c-.56.047-.747.327-.747.933zm14.337.745c.093.42 0 .84-.42.888l-.7.14v10.264c-.608.327-1.168.514-1.635.514-.748 0-.935-.234-1.495-.933l-4.577-7.186v6.952L12.21 19s0 .84-1.168.84l-3.222.186c-.093-.186 0-.653.327-.746l.84-.233V9.854L7.822 9.76c-.094-.42.14-1.026.793-1.073l3.456-.233 4.764 7.279v-6.44l-1.215-.139c-.093-.514.28-.887.747-.933zM1.936 1.035l13.31-.98c1.634-.14 2.055-.047 3.08.7l4.249 2.986c.7.513.934.653.934 1.213v16.378c0 1.026-.373 1.634-1.68 1.726l-15.458.934c-.98.047-1.448-.093-1.962-.747l-3.129-4.06c-.56-.747-.793-1.306-.793-1.96V2.667c0-.839.374-1.54 1.449-1.632z"/>
        </svg>
        <span className="notion-export-label">{t('notionExport')}</span>

        {status === 'success' ? (
          <a href={resultUrl} target="_blank" rel="noreferrer"
            className="notion-success-link">
            ✓ {t('notionOpenPage')} →
          </a>
        ) : (
          <button type="button"
            className="notion-export-btn"
            onClick={handleExport}
            disabled={status === 'loading'}>
            {status === 'loading' ? t('notionExporting') : t('notionSend')}
          </button>
        )}

        <button type="button" className="notion-settings-btn"
          onClick={() => setShowSetup((s) => !s)}
          title={t('notionSettings')}>
          ⚙
        </button>
      </div>

      {status === 'error' && (
        <p className="notion-error">{errorMsg}</p>
      )}

      {showSetup && (
        <form className="notion-setup-form" onSubmit={saveConfig}>
          <p className="notion-setup-hint">{t('notionSetupHint')}</p>
          <label>
            {t('notionApiKey')}
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="secret_…"
              autoComplete="off"
            />
          </label>
          <label>
            {t('notionDatabaseId')}
            <input
              value={databaseId}
              onChange={(e) => setDatabaseId(e.target.value)}
              placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            />
          </label>
          <div className="notion-setup-actions">
            <button type="submit">{t('notionSaveSettings')}</button>
            <button type="button" className="notion-cancel-btn"
              onClick={() => setShowSetup(false)}>{t('cancel') || 'Cancel'}</button>
          </div>
          <p className="notion-privacy-note">🔒 {t('notionPrivacyNote')}</p>
        </form>
      )}
    </div>
  )
}
