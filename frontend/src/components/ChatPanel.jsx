import { useEffect, useState } from 'react'

import { chatWithVideo, getChatHistory } from '../api/client.js'

export default function ChatPanel({ video }) {
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState([])
  const [error, setError] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)

  const isReady = video.status === 'ready'

  useEffect(() => {
    let cancelled = false

    async function loadHistory() {
      setIsLoadingHistory(true)
      setError('')
      try {
        const history = await getChatHistory(video.id)
        if (!cancelled) {
          setMessages(history.messages)
        }
      } catch (err) {
        if (!cancelled) {
          setMessages([])
          setError(err.message)
        }
      } finally {
        if (!cancelled) {
          setIsLoadingHistory(false)
        }
      }
    }

    setMessage('')
    loadHistory()
    return () => {
      cancelled = true
    }
  }, [video.id])

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
      await chatWithVideo(video.id, outgoing)
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
      <h3>Chat with video</h3>
      <p className="chat-help">
        Ask questions about the transcript. Answers are pulled from the saved transcript text.
      </p>

      <div className="chat-box">
        {isLoadingHistory ? <p className="chat-placeholder">Loading conversation...</p> : null}
        {!isLoadingHistory && !messages.length ? (
          <p className="chat-placeholder">
            {isReady
              ? 'Ask something like "What is this video about?" or mention a topic from the transcript.'
              : 'Chat unlocks after the video finishes processing.'}
          </p>
        ) : null}
        {messages.map((item) => (
          <div key={item.id} className={`chat-message chat-message-${item.role}`}>
            <strong>{item.role === 'user' ? 'You' : 'MyInsta'}</strong>
            <p>{item.content}</p>
          </div>
        ))}
      </div>

      <form className="url-form chat-form" onSubmit={handleSubmit}>
        <input
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder={isReady ? 'Ask about the video...' : 'Chat is available after transcription finishes'}
          disabled={!isReady || isSending}
        />
        <button type="submit" disabled={!isReady || isSending || !message.trim()}>
          {isSending ? 'Sending...' : 'Ask'}
        </button>
      </form>
      {error ? <p className="error">{error}</p> : null}
    </section>
  )
}
