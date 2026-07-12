import { useCallback, useEffect, useMemo, useState } from 'react'
import { cleanTranscript, reviewTranscript } from '../api/client.js'
import { useLanguage } from '../context/LanguageContext.jsx'
import QuoteCardModal from './QuoteCardModal.jsx'

function formatStamp(seconds) {
  if (seconds == null || Number.isNaN(Number(seconds))) return ''
  const total = Math.max(0, Math.floor(Number(seconds)))
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

export default function TranscriptViewer({ status, transcript, video, onSeek }) {
  const { t } = useLanguage()
  const [copied,      setCopied]      = useState(false)
  const [selectedQuote, setSelectedQuote] = useState('')
  const [showQuoteCard, setShowQuoteCard] = useState(false)
  const [viewMode, setViewMode] = useState('original')
  const [layoutMode, setLayoutMode] = useState('segments') // segments | prose
  const [cleanedText, setCleanedText] = useState(transcript?.cleaned_text || '')
  const [arabicText, setArabicText] = useState(transcript?.cleaned_translation_ar || transcript?.translation_ar || '')
  const [reviewText, setReviewText] = useState(transcript?.professional_review || '')
  const [cleanupTarget, setCleanupTarget] = useState('')
  const [cleanupError, setCleanupError] = useState('')

  const segments = useMemo(() => {
    const list = transcript?.segments
    if (!Array.isArray(list)) return []
    return list
      .map((seg) => ({
        id: seg.id,
        start: seg.start,
        end: seg.end,
        text: (seg.text || '').trim(),
      }))
      .filter((seg) => seg.text)
  }, [transcript?.segments])

  const hasSegments = segments.length > 0

  useEffect(() => {
    setViewMode('original')
    setLayoutMode(hasSegments ? 'segments' : 'prose')
    setCleanedText(transcript?.cleaned_text || '')
    setArabicText(transcript?.cleaned_translation_ar || transcript?.translation_ar || '')
    setReviewText(transcript?.professional_review || '')
    setCleanupTarget('')
    setCleanupError('')
    setSelectedQuote('')
  }, [
    transcript?.full_text,
    transcript?.translation_ar,
    transcript?.cleaned_text,
    transcript?.cleaned_translation_ar,
    transcript?.professional_review,
    hasSegments,
  ])

  const displayText = viewMode === 'review'
    ? reviewText
    : viewMode === 'arabic'
      ? arabicText
      : viewMode === 'cleaned'
        ? cleanedText
        : transcript?.full_text
  const canClean = Boolean(transcript?.full_text?.trim())
  const isCleaningEnglish = cleanupTarget === 'en'
  const isCleaningArabic = cleanupTarget === 'ar'
  const isReviewing = cleanupTarget === 'review'
  const showSegments = layoutMode === 'segments' && hasSegments && viewMode === 'original'

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

  async function handleShowCleaned() {
    if (!canClean) return
    setCleanupError('')
    if (cleanedText) {
      setViewMode('cleaned')
      setLayoutMode('prose')
      return
    }

    setCleanupTarget('en')
    try {
      const result = await cleanTranscript(video.id, 'en')
      setCleanedText(result.cleaned_text)
      setViewMode('cleaned')
      setLayoutMode('prose')
    } catch (err) {
      setCleanupError(err.message)
    } finally {
      setCleanupTarget('')
    }
  }

  async function handleShowArabic() {
    if (!canClean) return
    setCleanupError('')
    if (arabicText && transcript?.cleaned_translation_ar) {
      setViewMode('arabic')
      setLayoutMode('prose')
      return
    }

    setCleanupTarget('ar')
    try {
      const result = await cleanTranscript(video.id, 'ar')
      setArabicText(result.cleaned_text)
      setViewMode('arabic')
      setLayoutMode('prose')
    } catch (err) {
      setCleanupError(err.message)
    } finally {
      setCleanupTarget('')
    }
  }

  async function handleShowReview() {
    if (!canClean) return
    setCleanupError('')
    if (reviewText) {
      setViewMode('review')
      setLayoutMode('prose')
      return
    }

    setCleanupTarget('review')
    try {
      const result = await reviewTranscript(video.id)
      setReviewText(result.review_text)
      setViewMode('review')
      setLayoutMode('prose')
    } catch (err) {
      setCleanupError(err.message)
    } finally {
      setCleanupTarget('')
    }
  }

  const handleTextSelect = useCallback(() => {
    const sel = window.getSelection()
    if (!sel || sel.isCollapsed) return
    const text = sel.toString().trim()
    if (text.length >= 20) setSelectedQuote(text)
    else setSelectedQuote('')
  }, [])

  function handleSegmentClick(seg) {
    if (seg.start == null) return
    onSeek?.(seg.start)
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
    <section className="transcript-section">
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
          {canClean && (
            <div className="transcript-mode-toggle" aria-label={t('transcriptViewMode')}>
              <button
                type="button"
                className={viewMode === 'original' ? 'transcript-mode-active' : ''}
                disabled={Boolean(cleanupTarget)}
                onClick={() => {
                  setViewMode('original')
                  if (hasSegments) setLayoutMode('segments')
                }}
              >
                {t('originalTranscript')}
              </button>
              <button
                type="button"
                className={viewMode === 'cleaned' ? 'transcript-mode-active' : ''}
                onClick={handleShowCleaned}
                disabled={Boolean(cleanupTarget)}
              >
                {isCleaningEnglish ? t('cleaningTranscript') : t('cleanTranscript')}
              </button>
              <button
                type="button"
                className={viewMode === 'arabic' ? 'transcript-mode-active' : ''}
                onClick={handleShowArabic}
                disabled={Boolean(cleanupTarget)}
              >
                {isCleaningArabic ? t('cleaningTranscript') : t('arabicTranscript')}
              </button>
              <button
                type="button"
                className={viewMode === 'review' ? 'transcript-mode-active' : ''}
                onClick={handleShowReview}
                disabled={Boolean(cleanupTarget)}
              >
                {isReviewing ? t('reviewingTranscript') : t('professionalReview')}
              </button>
            </div>
          )}
          {displayText && (
            <button type="button"
              className={`copy-transcript-btn${copied ? ' copy-transcript-btn-done' : ''}`}
              onClick={handleCopy} title={t(
                viewMode === 'arabic'
                  ? 'copyArabicTranscript'
                  : viewMode === 'review'
                    ? 'copyProfessionalReview'
                    : 'copyTranscript'
              )}>
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
                  {t(
                    viewMode === 'arabic'
                      ? 'copyArabicTranscript'
                      : viewMode === 'review'
                        ? 'copyProfessionalReview'
                        : 'copyTranscript'
                  )}
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {hasSegments && viewMode === 'original' && (
        <div className="transcript-layout-toggle" role="group" aria-label={t('transcriptLayout')}>
          <button
            type="button"
            className={layoutMode === 'segments' ? 'transcript-mode-active' : ''}
            onClick={() => setLayoutMode('segments')}
          >
            {t('layoutSegments')}
          </button>
          <button
            type="button"
            className={layoutMode === 'prose' ? 'transcript-mode-active' : ''}
            onClick={() => setLayoutMode('prose')}
          >
            {t('layoutProse')}
          </button>
        </div>
      )}

      {showSegments && (
        <p className="transcript-seek-hint">{t('transcriptSeekHint')}</p>
      )}

      {selectedQuote && (
        <p className="quote-selection-hint">{t('quoteSelectionHint')}</p>
      )}
      {cleanupError && (
        <p className="error">{cleanupError}</p>
      )}

      {showSegments ? (
        <div className="transcript-segments" onMouseUp={handleTextSelect} onTouchEnd={handleTextSelect}>
          {segments.map((seg, index) => (
            <button
              key={seg.id ?? `${seg.start}-${index}`}
              type="button"
              className="transcript-segment"
              onClick={() => handleSegmentClick(seg)}
              title={t('seekToTimestamp', formatStamp(seg.start))}
            >
              <span className="transcript-segment-time">{formatStamp(seg.start)}</span>
              <span className="transcript-segment-text">{seg.text}</span>
            </button>
          ))}
        </div>
      ) : displayText ? (
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
