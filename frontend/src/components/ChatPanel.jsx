import { useEffect, useMemo, useRef, useState } from 'react'
import { chatWithVideo, getChatHistory } from '../api/client.js'
import { useLanguage } from '../context/LanguageContext.jsx'

function defaultMode(video) {
  return video.content_type === 'music' ? 'web' : 'transcript'
}

function parseTimestampToSeconds(stamp) {
  // Supports [m:ss], [mm:ss], [h:mm:ss]
  const parts = stamp.replace(/[\[\]]/g, '').split(':').map((p) => Number(p))
  if (parts.some((n) => Number.isNaN(n))) return null
  if (parts.length === 2) return parts[0] * 60 + parts[1]
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2]
  return null
}

/** Render assistant text with clickable [mm:ss] timestamps when onSeek is provided. */
function MessageContent({ content, onSeek }) {
  if (!onSeek || !content) return <p className="chat-message-body">{content}</p>

  const parts = content.split(/(\[\d{1,2}:\d{2}(?::\d{2})?\])/g)
  return (
    <p className="chat-message-body">
      {parts.map((part, index) => {
        const match = part.match(/^\[(\d{1,2}:\d{2}(?::\d{2})?)\]$/)
        if (!match) return <span key={index}>{part}</span>
        const seconds = parseTimestampToSeconds(match[0])
        if (seconds == null) return <span key={index}>{part}</span>
        return (
          <button
            key={index}
            type="button"
            className="chat-timestamp-btn"
            onClick={() => onSeek(seconds)}
            title={`Seek to ${match[1]}`}
          >
            {part}
          </button>
        )
      })}
    </p>
  )
}

export default function ChatPanel({ video, onSeek, onOpenTranscript }) {
  const { t } = useLanguage()
  const [message, setMessage]               = useState('')
  const [messages, setMessages]             = useState([])
  const [error, setError]                   = useState('')
  const [isSending, setIsSending]           = useState(false)
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const [mode, setMode]                     = useState(() => defaultMode(video))
  const [answerLanguage, setAnswerLanguage] = useState('english')
  const messagesEndRef = useRef(null)

  const isReady     = video.status === 'ready'
  const hasTranscript = Boolean(video.transcript?.full_text?.trim())
  const isMusic     = video.content_type === 'music'

  const suggestedPrompts = useMemo(() => {
    if (!isReady) return []
    if (mode === 'web') {
      return [
        t('promptWebOverview'),
        t('promptWebContext'),
        t('promptWebLearnMore'),
      ]
    }
    if (isMusic || !hasTranscript) {
      return [t('promptMusicFallback')]
    }
    return [
      t('promptSummary'),
      t('promptKeyPoints'),
      t('promptAdvice'),
      t('promptArabicIdea'),
    ]
  }, [isReady, mode, isMusic, hasTranscript, t])

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

  async function sendMessage(text) {
    const outgoing = (text || '').trim()
    if (!outgoing || !isReady || isSending) return
    setIsSending(true)
    setError('')
    setMessage('')
    setMessages((current) => [
      ...current,
      { id: `pending-user-${Date.now()}`, role: 'user', content: outgoing, created_at: new Date().toISOString() },
    ])
    try {
      await chatWithVideo(video.id, outgoing, mode, answerLanguage)
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

  async function handleSubmit(event) {
    event.preventDefault()
    await sendMessage(message)
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

      <div className="chat-language-row">
        <span className="chat-language-label">{t('answerLanguage')}</span>
        <div className="chat-mode-toggle chat-language-toggle" role="group" aria-label={t('answerLanguage')}>
          <button type="button"
            className={`chat-mode-btn ${answerLanguage === 'english' ? 'chat-mode-btn-active' : ''}`}
            onClick={() => setAnswerLanguage('english')}
            title={t('answerEnglishTitle')}
            disabled={!isReady}>
            {t('answerEnglish')}
          </button>
          <button type="button"
            className={`chat-mode-btn ${answerLanguage === 'arabic' ? 'chat-mode-btn-active' : ''}`}
            onClick={() => setAnswerLanguage('arabic')}
            title={t('answerArabicTitle')}
            disabled={!isReady}>
            {t('answerArabic')}
          </button>
          <button type="button"
            className={`chat-mode-btn ${answerLanguage === 'bilingual' ? 'chat-mode-btn-active' : ''}`}
            onClick={() => setAnswerLanguage('bilingual')}
            title={t('answerBilingualTitle')}
            disabled={!isReady}>
            {t('answerBilingual')}
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
          <div className="chat-empty-state">
            <p className="chat-placeholder">
              {isReady
                ? mode === 'web' ? t('chatPlaceholderWeb') : t('chatPlaceholderTranscript')
                : t('chatLocked')}
            </p>
            {isReady && suggestedPrompts.length > 0 && (
              <div className="chat-suggestions">
                <p className="chat-suggestions-label">{t('suggestedQuestions')}</p>
                <div className="chat-suggestion-chips">
                  {suggestedPrompts.map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      className="chat-suggestion-chip"
                      disabled={isSending}
                      onClick={() => sendMessage(prompt)}
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
                {mode === 'transcript' && hasTranscript && onOpenTranscript && (
                  <button type="button" className="chat-open-transcript-link" onClick={onOpenTranscript}>
                    {t('openTranscriptTab')}
                  </button>
                )}
              </div>
            )}
          </div>
        ) : null}
        {messages.map((item) => (
          <div key={item.id} className={`chat-message chat-message-${item.role}`}>
            <strong>{item.role === 'user' ? t('you') : t('appName')}</strong>
            {item.role === 'assistant' ? (
              <MessageContent content={item.content} onSeek={onSeek} />
            ) : (
              <p className="chat-message-body">{item.content}</p>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <form className="url-form chat-form" onSubmit={handleSubmit}>
        <input
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => {
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
