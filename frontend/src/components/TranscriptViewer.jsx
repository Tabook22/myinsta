import { useState } from 'react'
import { useLanguage } from '../context/LanguageContext.jsx'

export default function TranscriptViewer({ status, transcript }) {
  const { t } = useLanguage()
  const [copied, setCopied] = useState(false)

  async function handleCopy() {
    if (!transcript?.full_text) return
    try {
      await navigator.clipboard.writeText(transcript.full_text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Fallback for older browsers
      const ta = document.createElement('textarea')
      ta.value = transcript.full_text
      ta.style.cssText = 'position:fixed;opacity:0'
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  if (status === 'processing' || status === 'queued') {
    return (
      <section>
        <h3>{t('transcript')}</h3>
        <p>{t('transcriptProcessing')}</p>
      </section>
    )
  }

  if (status === 'failed') return null

  return (
    <section>
      <div className="transcript-header">
        <h3>{t('transcript')}</h3>
        {transcript?.full_text && (
          <button
            type="button"
            className={`copy-transcript-btn${copied ? ' copy-transcript-btn-done' : ''}`}
            onClick={handleCopy}
            title={t('copyTranscript')}
          >
            {copied ? (
              <>
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
                  stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
                {t('transcriptCopied')}
              </>
            ) : (
              <>
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
                  stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                </svg>
                {t('copyTranscript')}
              </>
            )}
          </button>
        )}
      </div>

      {transcript?.full_text ? (
        <p className="transcript">{transcript.full_text}</p>
      ) : (
        <p>{t('noSpeech')}</p>
      )}
    </section>
  )
}
