export default function TranscriptViewer({ status, transcript }) {
  if (status === 'processing' || status === 'queued') {
    return (
      <section>
        <h3>Transcript</h3>
        <p>Processing… transcript will appear when the video is ready.</p>
      </section>
    )
  }

  if (status === 'failed') {
    return null
  }

  return (
    <section>
      <h3>Transcript</h3>
      {transcript?.full_text ? (
        <p className="transcript">{transcript.full_text}</p>
      ) : (
        <p>No speech detected in this video.</p>
      )}
    </section>
  )
}
