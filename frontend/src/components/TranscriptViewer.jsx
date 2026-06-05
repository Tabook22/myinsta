import { useCallback, useEffect, useState } from 'react'
import { translateTranscriptToArabic } from '../api/client.js'
import { useLanguage } from '../context/LanguageContext.jsx'
import QuoteCardModal from './QuoteCardModal.jsx'

export default function TranscriptViewer({ status, transcript, video }) {
  const { t } = useLanguage()
  const [copied,      setCopied]      = useState(false)
  const [selectedQuote, setSelectedQuote] = useState('')
  const [showQuoteCard, setShowQuoteCard] = useState(false)
  const [viewMode, setViewMode] = useState('original')
  const [arabicText, setArabicText] = useState(transcript?.translation_ar || '')
  const [isTranslating, setIsTranslating] = useState(false)
  const [translationError, setTranslationError] = useState('')

  useEffect(() => {
    setViewMode('original')
    setArabicText(transcript?.translation_ar || '')
    setTranslationError('')
    setSelectedQuote('')
  }, [transcript?.full_text, transcript?.translation_ar])

  const displayText = viewMode === 'arabic' ? arabicText : transcript?.full_text
  const canTranslate = Boolean(transcript?.full_text?.trim())

  async function handleCopy() {
    if (!displayText) return
    try {
      await navigator.clipboard.writeText(displayText)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      const ta = document.createElement('textarea')
      ta.value = displayText
      ta.style.cssText = 'position:fixed;opacity:0'
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  async function handleShowArabic() {
    if (!canTranslate) return
    setTranslationError('')
    if (arabicText) {
      setViewMode('arabic')
      return
    }

    setIsTranslating(true)
    try {
      const result = await translateTranscriptToArabic(video.id)
      setArabicText(result.translated_text)
      setViewMode('arabic')
    } catch (err) {
      setTranslationError(err.message)
    } finally {
      setIsTranslating(false)
    }
  }

  const handleTextSelect = useCallback(() => {
    const sel = window.getSelection()
    if (!sel || sel.isCollapsed) return
    const text = sel.toString().trim()
    if (text.length >= 20) setSelectedQuote(text)
    else setSelectedQuote('')
  }, [])

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
        <div className="transcript-header-actions">
          {selectedQuote && (
            <button type="button" className="quote-card-trigger-btn"
              onClick={() => setShowQuoteCard(true)}
              title={t('quoteCreateCard')}>
              ✨ {t('quoteCreateCard')}
            </button>
          )}
          {canTranslate && (
            <div className="transcript-mode-toggle" aria-label={t('transcriptViewMode')}>
              <button
                type="button"
                className={viewMode === 'original' ? 'transcript-mode-active' : ''}
                onClick={() => setViewMode('original')}
              >
                {t('originalTranscript')}
              </button>
              <button
                type="button"
                className={viewMode === 'arabic' ? 'transcript-mode-active' : ''}
                onClick={handleShowArabic}
                disabled={isTranslating}
              >
                {isTranslating ? t('translatingTranscript') : t('arabicTranscript')}
              </button>
            </div>
          )}
          {displayText && (
            <button type="button"
              className={`copy-transcript-btn${copied ? ' copy-transcript-btn-done' : ''}`}
              onClick={handleCopy} title={t(viewMode === 'arabic' ? 'copyArabicTranscript' : 'copyTranscript')}>
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
                  {t(viewMode === 'arabic' ? 'copyArabicTranscript' : 'copyTranscript')}
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {selectedQuote && (
        <p className="quote-selection-hint">{t('quoteSelectionHint')}</p>
      )}
      {translationError && (
        <p className="error">{translationError}</p>
      )}

      {displayText ? (
        <p
          className="transcript"
          dir={viewMode === 'arabic' ? 'rtl' : undefined}
          lang={viewMode === 'arabic' ? 'ar' : transcript?.language || undefined}
          onMouseUp={handleTextSelect}
          onTouchEnd={handleTextSelect}
        >
          {displayText}
        </p>
      ) : (
        <p>{t('noSpeech')}</p>
      )}

      {showQuoteCard && selectedQuote && (
        <QuoteCardModal
          quote={selectedQuote}
          video={video || {}}
          onClose={() => setShowQuoteCard(false)}
        />
      )}
    </section>
  )
}
