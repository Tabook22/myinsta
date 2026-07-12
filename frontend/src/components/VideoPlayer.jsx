import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react'
import { getVideoStreamUrl } from '../api/client.js'

const VideoPlayer = forwardRef(function VideoPlayer({ video, sticky = false }, ref) {
  const videoRef = useRef(null)
  const streamUrl = getVideoStreamUrl(video)

  useImperativeHandle(ref, () => ({
    seekTo(seconds) {
      const el = videoRef.current
      if (!el || seconds == null || Number.isNaN(Number(seconds))) return
      const target = Math.max(0, Number(seconds))
      const apply = () => {
        try {
          el.currentTime = target
          const playPromise = el.play()
          if (playPromise?.catch) playPromise.catch(() => {})
        } catch {
          // Ignore seek errors on unloaded media
        }
      }
      if (el.readyState >= 1) apply()
      else el.addEventListener('loadedmetadata', apply, { once: true })
    },
    get currentTime() {
      return videoRef.current?.currentTime ?? 0
    },
  }), [])

  useEffect(() => {
    // Reset playback when switching videos
    const el = videoRef.current
    if (el) {
      el.pause()
      el.currentTime = 0
    }
  }, [video?.id, streamUrl])

  if (!streamUrl) {
    return null
  }

  return (
    <section className={`video-player-wrap${sticky ? ' video-player-sticky' : ''}`}>
      <video
        ref={videoRef}
        className="video-player"
        controls
        preload="metadata"
        src={streamUrl}
      >
        Your browser does not support video playback.
      </video>
    </section>
  )
})

export default VideoPlayer
