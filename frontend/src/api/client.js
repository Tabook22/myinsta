const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

function parseErrorMessage(text) {
  if (!text) return 'Request failed'
  try {
    const data = JSON.parse(text)
    if (typeof data.detail === 'string') return data.detail
    if (Array.isArray(data.detail)) {
      return data.detail.map((item) => item.msg || JSON.stringify(item)).join(', ')
    }
  } catch {
    // Keep raw text fallback below.
  }
  return text
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers ?? {}),
    },
    ...options,
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(parseErrorMessage(text) || `Request failed with status ${response.status}`)
  }

  if (response.status === 204) {
    return null
  }

  return response.json()
}

export function getApiBaseUrl() {
  return API_BASE_URL
}

export function getVideoStreamUrl(video) {
  if (!video?.video_url) return null
  return `${API_BASE_URL}${video.video_url}`
}

export function createVideo(url) {
  return request('/api/videos', {
    method: 'POST',
    body: JSON.stringify({ url }),
  })
}

export function getVideo(videoId) {
  return request(`/api/videos/${videoId}`)
}

export function listVideos() {
  return request('/api/videos')
}

export function updateVideo(videoId, payload) {
  return request(`/api/videos/${videoId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteVideo(videoId) {
  return request(`/api/videos/${videoId}`, {
    method: 'DELETE',
  })
}

export function chatWithVideo(videoId, message) {
  return request(`/api/videos/${videoId}/chat`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  })
}

export function getChatHistory(videoId) {
  return request(`/api/videos/${videoId}/chat`)
}
