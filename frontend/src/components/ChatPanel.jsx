import { useEffect, useRef, useState } from 'react'

import { chatWithVideo, getChatHistory } from '../api/client.js'

/**
 * Automatically pick the best default chat mode.
 * - Music-only videos default to 'web' (no transcript to query)
 * - Everything else defaults to 'transcript'
 */
function defaultMode(video) {
  return video.content_type === 'music' ? 'web' : 'transcript'
}

export default function ChatPanel({ video }) {
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState([])
  const [error, setError] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const [mode, setMode] = useState(() => defaultMode(video))
  const messagesEndRef = useRef(null)

  const isReady = video.status === 'ready'
  const hasTranscript = Boolean(video.transcript?.full_text?.trim())
  const isMusic = video.content_type === 'music'

  // Reset mode and history when video changes
  useEffect(() => {
    setMode(defaultMode(video))
  }, [video.id, video.content_type])

  useEffect(() => {
    let cancelled = false

    async function loadHistory() {
      setIsLoadingHistory(true)
      setError('')
      try {
        const history = await getChatHistory(video.id)
        if (!cancelled) setMessages(history.messages)
      } catch (err) {
        if (!cancelled) {
          setMessages([])
          setError(err.message)
        }
      } finally {
        if (!cancelled) setIsLoadingHistory(false)
      }
    }

    setMessage('')
    loadHistory()
    return () => { cancelled = true }
  }, [video.id])

  // Auto-scroll to latest message
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
      {
        id: `pending-user-${Date.now()}`,
        role: 'user',
        content: outgoing,
        created_at: new Date().toISOString(),
      },
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
        <h3>Chat with video</h3>

        {/* Mode toggle */}
        <div className="chat-mode-toggle" role="group" aria-label="Chat mode">
          <button
            type="button"
            className={`chat-mode-btn ${mode === 'transcript' ? 'chat-mode-btn-active' : ''}`}
            onClick={() => setMode('transcript')}
            title="Answer questions using the video transcript"
            disabled={!isReady}
          >
            🎯 Transcript
          </button>
          <button
            type="button"
            className={`chat-mode-btn ${mode === 'web' ? 'chat-mode-btn-active' : ''}`}
            onClick={() => setMode('web')}
            title="Search the web to answer your question"
            disabled={!isReady}
          >
            🌐 Web
          </button>
        </div>
      </div>

      {/* Context notice */}
      {isReady && (
        <p className="chat-mode-notice">
          {isMusic && mode === 'transcript' && (
            <span className="notice-warning">
              ⚠️ This video appears to be music only — transcript may be empty.
              <button type="button" className="notice-link" onClick={() => setMode('web')}>
                Switch to Web mode
              </button>
            </span>
          )}
          {!isMusic && mode === 'transcript' && hasTranscript && (
            <span className="notice-info">🎯 Answering from the saved transcript.</span>
          )}
          {!isMusic && mode === 'transcript' && !hasTranscript && (
            <span className="notice-warning">⚠️ No transcript found — answers may be limited.</span>
          )}
          {mode === 'web' && (
            <span className="notice-info">🌐 Searching the web using the video title and your question.</span>
          )}
        </p>
      )}

      <div className="chat-box">
        {isLoadingHistory ? (
          <p className="chat-placeholder">Loading conversation...</p>
        ) : null}

        {!isLoadingHistory && !messages.length ? (
          <p className="chat-placeholder">
            {isReady
              ? mode === 'web'
                ? 'Ask anything — results come from the web based on the video title.'
                : 'Ask something like "What is this video about?" or "What topics are covered?"'
              : 'Chat unlocks after the video finishes processing.'}
          </p>
        ) : null}

        {messages.map((item) => (
          <div key={item.id} className={`chat-message chat-message-${item.role}`}>
            <strong>{item.role === 'user' ? 'You' : 'MyInsta'}</strong>
            <p>{item.content}</p>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <form className="url-form chat-form" onSubmit={handleSubmit}>
        <input
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder={
            isReady
              ? mode === 'web'
                ? 'Ask anything about this video or topic...'
                : 'Ask about the transcript...'
              : 'Chat is available after transcription finishes'
          }
          disabled={!isReady || isSending}
        />
        <button type="submit" disabled={!isReady || isSending || !message.trim()}>
          {isSending ? 'Searching...' : 'Ask'}
        </button>
      </form>

      {error ? <p className="error">{error}</p> : null}
    </section>
  )
}
