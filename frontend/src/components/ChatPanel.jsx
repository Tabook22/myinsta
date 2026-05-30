import { useEffect, useRef, useState } from 'react'
import { chatWithVideo, getChatHistory } from '../api/client.js'
import { useLanguage } from '../context/LanguageContext.jsx'

function defaultMode(video) {
  return video.content_type === 'music' ? 'web' : 'transcript'
}

export default function ChatPanel({ video }) {
  const { t } = useLanguage()
  const [message, setMessage]               = useState('')
  const [messages, setMessages]             = useState([])
  const [error, setError]                   = useState('')
  const [isSending, setIsSending]           = useState(false)
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const [mode, setMode]                     = useState(() => defaultMode(video))
  const messagesEndRef = useRef(null)

  const isReady     = video.status === 'ready'
  const hasTranscript = Boolean(video.transcript?.full_text?.trim())
  const isMusic     = video.content_type === 'music'

  useEffect(() => { setMode(defaultMode(video)) }, [video.id, video.content_type])

  useEffect(() => {
    let cancelled = false
    async function loadHistory() {
      setIsLoadingHistory(true)
      setError('')
      try {
        const history = await getChatHistory(video.id)
        if (!cancelled) setMessages(history.messages)
      } catch (err) {
        if (!cancelled) { setMessages([]); setError(err.message) }
      } finally {
        if (!cancelled) setIsLoadingHistory(false)
      }
    }
    setMessage('')
    loadHistory()
    return () => { cancelled = true }
  }, [video.id])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function handleSubmit(event) {
    event.preventDefault()
    if (!message.trim() || !isReady || isSending) return
    const outgoing = message.trim()
    setIsSending(true)
    setError('')
    setMessage('')
    setMessages((current) => [
      ...current,
      { id: `pending-user-${Date.now()}`, role: 'user', content: outgoing, created_at: new Date().toISOString() },
    ])
    try {
      await chatWithVideo(video.id, outgoing, mode)
      const history = await getChatHistory(video.id)
      setMessages(history.messages)
    } catch (err) {
      setMessages((current) => current.filter((item) => !String(item.id).startsWith('pending-')))
      setMessage(outgoing)
      setError(err.message)
    } finally {
      setIsSending(false)
    }
  }

  return (
    <section className="chat-panel">
      <div className="chat-panel-header">
        <h3>{t('chatWithVideo')}</h3>

        <div className="chat-mode-toggle" role="group" aria-label={t('chatWithVideo')}>
          <button type="button"
            className={`chat-mode-btn ${mode === 'transcript' ? 'chat-mode-btn-active' : ''}`}
            onClick={() => setMode('transcript')}
            title={t('titleTranscript')}
            disabled={!isReady}>
            {t('modeTranscript')}
          </button>
          <button type="button"
            className={`chat-mode-btn ${mode === 'web' ? 'chat-mode-btn-active' : ''}`}
            onClick={() => setMode('web')}
            title={t('titleWeb')}
            disabled={!isReady}>
            {t('modeWeb')}
          </button>
        </div>
      </div>

      {isReady && (
        <p className="chat-mode-notice">
          {isMusic && mode === 'transcript' && (
            <span className="notice-warning">
              {t('noticeMusicWarning')}
              <button type="button" className="notice-link" onClick={() => setMode('web')}>
                {t('switchToWeb')}
              </button>
            </span>
          )}
          {!isMusic && mode === 'transcript' && hasTranscript && (
            <span className="notice-info">{t('noticeTranscriptReady')}</span>
          )}
          {!isMusic && mode === 'transcript' && !hasTranscript && (
            <span className="notice-warning">{t('noticeNoTranscript')}</span>
          )}
          {mode === 'web' && (
            <span className="notice-info">{t('noticeWebMode')}</span>
          )}
        </p>
      )}

      <div className="chat-box">
        {isLoadingHistory ? <p className="chat-placeholder">{t('loadingConversation')}</p> : null}
        {!isLoadingHistory && !messages.length ? (
          <p className="chat-placeholder">
            {isReady
              ? mode === 'web' ? t('chatPlaceholderWeb') : t('chatPlaceholderTranscript')
              : t('chatLocked')}
          </p>
        ) : null}
        {messages.map((item) => (
          <div key={item.id} className={`chat-message chat-message-${item.role}`}>
            <strong>{item.role === 'user' ? t('you') : t('appName')}</strong>
            <p>{item.content}</p>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <form className="url-form chat-form" onSubmit={handleSubmit}>
        <input
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => {
            // Ctrl+Enter or Cmd+Enter submits even when textarea would add newline
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
              e.preventDefault()
              if (message.trim() && isReady && !isSending) handleSubmit(e)
            }
          }}
          placeholder={
            isReady
              ? mode === 'web' ? t('inputPlaceholderWeb') : t('inputPlaceholderTranscript')
              : t('inputPlaceholderLocked')
          }
          disabled={!isReady || isSending}
        />
        <button type="submit" disabled={!isReady || isSending || !message.trim()}>
          {isSending ? t('searching') : t('ask')}
        </button>
      </form>

      {error ? <p className="error">{error}</p> : null}
    </section>
  )
}
