import VideoPlayer from './VideoPlayer.jsx'

export default function VideoDetails({ video }) {
  return (
    <section>
      <VideoPlayer video={video} />
      {!video.video_url && video.thumbnail_url ? (
        <img
          className="thumbnail"
          src={video.thumbnail_url}
          alt={video.title || 'Video thumbnail'}
        />
      ) : null}
      <h2>{video.title || 'Untitled video'}</h2>
      <p><span className="status">{video.status}</span></p>
      {video.storage_stamp ? (
        <p><strong>Saved as:</strong> {video.storage_stamp}</p>
      ) : null}
      {video.storage_folder ? (
        <p><strong>Folder:</strong> {video.storage_folder}</p>
      ) : null}
      <p><strong>Source:</strong> <a href={video.source_url} target="_blank" rel="noreferrer">Open original</a></p>
      {video.uploader ? <p><strong>Uploader:</strong> {video.uploader}</p> : null}
      {video.duration_seconds ? <p><strong>Duration:</strong> {Math.round(video.duration_seconds)} seconds</p> : null}
      {video.description ? <p><strong>Description:</strong> {video.description}</p> : null}
      {video.error_message ? <p className="error">{video.error_message}</p> : null}
    </section>
  )
}
