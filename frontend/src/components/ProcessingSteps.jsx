import { useLanguage } from '../context/LanguageContext.jsx'

const STEPS = [
  { key: 'downloading',  icon: '⬇',  labelKey: 'stepDownloading'  },
  { key: 'extracting',   icon: '🎵', labelKey: 'stepExtracting'   },
  { key: 'transcribing', icon: '🎤', labelKey: 'stepTranscribing' },
]

function stepIndex(step) {
  return STEPS.findIndex((s) => s.key === step)
}

export default function ProcessingSteps({ video }) {
  const { t } = useLanguage()

  // Only show while actively processing
  if (video.status !== 'processing' && video.status !== 'queued') return null

  const activeIdx = stepIndex(video.processing_step ?? 'downloading')

  return (
    <div className="processing-steps">
      {STEPS.map((step, idx) => {
        const isDone   = idx < activeIdx
        const isActive = idx === activeIdx
        const isPending = idx > activeIdx

        return (
          <div
            key={step.key}
            className={[
              'proc-step',
              isDone    ? 'proc-step-done'    : '',
              isActive  ? 'proc-step-active'  : '',
              isPending ? 'proc-step-pending' : '',
            ].filter(Boolean).join(' ')}
          >
            {/* Connector line (before all except first) */}
            {idx > 0 && (
              <div className={`proc-line${isDone || isActive ? ' proc-line-done' : ''}`} />
            )}

            {/* Circle */}
            <div className="proc-circle">
              {isDone ? (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                  strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
              ) : isActive ? (
                <span className="proc-spinner" />
              ) : (
                <span className="proc-num">{idx + 1}</span>
              )}
            </div>

            {/* Label */}
            <span className="proc-label">
              <span className="proc-icon">{step.icon}</span>
              {t(step.labelKey)}
            </span>
          </div>
        )
      })}
    </div>
  )
}
