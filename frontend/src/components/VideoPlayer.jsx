import { getVideoStreamUrl } from '../api/client.js'

export default function VideoPlayer({ video }) {
  const streamUrl = getVideoStreamUrl(video)

  if (!streamUrl) {
    return null
  }

  return (
    <section className="video-player-wrap">
      <video className="video-player" controls preload="metadata" src={streamUrl}>
        Your browser does not support video playback.
      </video>
    </section>
  )
}
