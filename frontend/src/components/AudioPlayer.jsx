import { getAudioDownloadUrl, getAudioStreamUrl } from '../api/client.js'

export default function AudioPlayer({ video }) {
  const streamUrl  = getAudioStreamUrl(video)
  const downloadUrl = getAudioDownloadUrl(video)

  if (!streamUrl) return null

  const filename = (video.title || `audio-${video.id}`).replace(/[/\\]/g, '-')

  return (
    <div className="audio-player-wrap">
      <div className="audio-player-header">
        {/* Music note icon */}
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M9 18V5l12-2v13"/>
          <circle cx="6" cy="18" r="3"/>
          <circle cx="18" cy="16" r="3"/>
        </svg>
        <span>Audio track</span>

        {/* Download button */}
        <a
          className="audio-download-btn"
          href={downloadUrl}
          download={filename}
          title="Download audio file"
        >
          {/* Download icon */}
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          Download
        </a>
      </div>

      <audio
        className="audio-player"
        controls
        preload="metadata"
        src={streamUrl}
      >
        Your browser does not support audio playback.
      </audio>
    </div>
  )
}
