import { useLanguage } from '../context/LanguageContext.jsx'

export default function TranscriptViewer({ status, transcript }) {
  const { t } = useLanguage()

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
      <h3>{t('transcript')}</h3>
      {transcript?.full_text ? (
        <p className="transcript">{transcript.full_text}</p>
      ) : (
        <p>{t('noSpeech')}</p>
      )}
    </section>
  )
}
