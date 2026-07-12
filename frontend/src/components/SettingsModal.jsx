import { useEffect, useRef, useState } from 'react'
import { getYoutubeCookiesStatus, uploadYoutubeCookies } from '../api/client.js'
import { useLanguage } from '../context/LanguageContext.jsx'
import { useToast } from '../context/ToastContext.jsx'

function StatusPill({ ok, label }) {
  return (
    <span className={`settings-pill${ok ? ' settings-pill-ok' : ' settings-pill-bad'}`}>
      {ok ? '✓' : '!'} {label}
    </span>
  )
}

export default function SettingsModal({ onClose }) {
  const { t } = useLanguage()
  const { showToast } = useToast()
  const fileRef = useRef(null)
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [status, setStatus] = useState(null)
  const [selectedName, setSelectedName] = useState('')

  async function loadStatus() {
    setLoading(true)
    setError('')
    try {
      const data = await getYoutubeCookiesStatus()
      setStatus(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadStatus()
  }, [])

  useEffect(() => {
    function onKey(e) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  async function handleUpload(event) {
    event.preventDefault()
    const file = fileRef.current?.files?.[0]
    if (!file) {
      setError(t('settingsPickFile'))
      return
    }
    setUploading(true)
    setError('')
    try {
      const result = await uploadYoutubeCookies(file)
      setStatus({
        path: result.path,
        cookies: result.cookies,
        hint: status?.hint,
        configured_env: status?.configured_env,
      })
      showToast(result.message || t('settingsUploadOk'), 'success')
      if (fileRef.current) fileRef.current.value = ''
      setSelectedName('')
    } catch (err) {
      setError(err.message)
      showToast(err.message, 'error')
    } finally {
      setUploading(false)
    }
  }

  const cookies = status?.cookies || {}
  const usable = Boolean(cookies.usable)

  return (
    <div className="settings-backdrop" onClick={onClose} role="presentation">
      <div
        className="settings-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="settings-header">
          <h2 id="settings-title">{t('settingsTitle')}</h2>
          <button type="button" className="btn-ghost settings-close" onClick={onClose} aria-label={t('close')}>
            ×
          </button>
        </div>

        <section className="settings-section">
          <h3>{t('settingsYoutubeCookies')}</h3>
          <p className="settings-help">{t('settingsYoutubeHelp')}</p>
          <p className="settings-privacy">{t('settingsPrivacyNote')}</p>

          {loading ? (
            <p className="settings-muted">{t('loading')}</p>
          ) : (
            <div className="settings-status-card">
              <div className="settings-status-row">
                <StatusPill ok={usable} label={usable ? t('settingsCookiesUsable') : t('settingsCookiesNotUsable')} />
                <StatusPill
                  ok={Boolean(cookies.has_login_info)}
                  label={cookies.has_login_info ? t('settingsHasLogin') : t('settingsMissingLogin')}
                />
                <StatusPill
                  ok={Boolean(cookies.has_session_ids)}
                  label={cookies.has_session_ids ? t('settingsHasSession') : t('settingsMissingSession')}
                />
              </div>
              <dl className="settings-meta">
                <div>
                  <dt>{t('settingsPath')}</dt>
                  <dd><code>{status?.path || '—'}</code></dd>
                </div>
                <div>
                  <dt>{t('settingsSize')}</dt>
                  <dd>{cookies.size != null ? `${cookies.size} bytes` : '—'}</dd>
                </div>
                <div>
                  <dt>{t('settingsAge')}</dt>
                  <dd>
                    {cookies.age_days != null
                      ? t('settingsAgeDays', cookies.age_days)
                      : '—'}
                  </dd>
                </div>
                <div>
                  <dt>{t('settingsYoutubeRows')}</dt>
                  <dd>{cookies.youtube_rows ?? '—'}</dd>
                </div>
              </dl>
              {Array.isArray(cookies.issues) && cookies.issues.length > 0 && (
                <ul className="settings-issues">
                  {cookies.issues.map((issue) => (
                    <li key={issue}>{issue}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          <form className="settings-upload-form" onSubmit={handleUpload}>
            <label className="settings-file-label">
              <span>{t('settingsChooseFile')}</span>
              <input
                ref={fileRef}
                type="file"
                accept=".txt,text/plain"
                onChange={(e) => setSelectedName(e.target.files?.[0]?.name || '')}
              />
            </label>
            {selectedName ? (
              <p className="settings-file-name">{selectedName}</p>
            ) : null}
            <div className="settings-actions">
              <button type="submit" className="btn-primary" disabled={uploading || loading}>
                {uploading ? t('settingsUploading') : t('settingsUploadBtn')}
              </button>
              <button type="button" className="btn-secondary" onClick={loadStatus} disabled={loading || uploading}>
                {t('settingsRefresh')}
              </button>
            </div>
          </form>

          {error ? <p className="error">{error}</p> : null}

          <ol className="settings-steps">
            <li>{t('settingsStep1')}</li>
            <li>{t('settingsStep2')}</li>
            <li>{t('settingsStep3')}</li>
            <li>{t('settingsStep4')}</li>
          </ol>
        </section>
      </div>
    </div>
  )
}
