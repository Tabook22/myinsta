function getDefaultApiBaseUrl() {
  if (typeof window === 'undefined') {
    return 'http://localhost:8000'
  }

  const isLocalDevHost = ['localhost', '127.0.0.1', '::1'].includes(window.location.hostname)
  if (!isLocalDevHost && window.location.pathname.startsWith('/myinsta')) {
    return '/myinsta-api'
  }

  return 'http://localhost:8000'
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? getDefaultApiBaseUrl()

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

const REQUEST_TIMEOUT_MS = 10_000 // 10 seconds - fail fast if backend is down
const TRANSLATION_TIMEOUT_MS = 60_000 // Longer text can take a little while

async function request(path, options = {}) {
  const { timeoutMs = REQUEST_TIMEOUT_MS, ...fetchOptions } = options
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)

  let response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        'Content-Type': 'application/json',
        ...(fetchOptions.headers ?? {}),
      },
      signal: controller.signal,
      ...fetchOptions,
    })
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error('Server is not responding — please check back in a moment.')
    }
    throw new Error('Cannot reach server — check your connection.')
  } finally {
    clearTimeout(timer)
  }

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

export function getAudioStreamUrl(video) {
  if (!video?.audio_url) return null
  return `${API_BASE_URL}${video.audio_url}`
}

export function getAudioDownloadUrl(video) {
  if (!video?.audio_url) return null
  return `${API_BASE_URL}${video.audio_url}?download=true`
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

export function translateTranscriptToArabic(videoId) {
  return request(`/api/videos/${videoId}/translate`, {
    method: 'POST',
    timeoutMs: TRANSLATION_TIMEOUT_MS,
  })
}

export function cleanTranscript(videoId, targetLanguage = 'en') {
  return request(`/api/videos/${videoId}/cleanup?target_language=${encodeURIComponent(targetLanguage)}`, {
    method: 'POST',
    timeoutMs: TRANSLATION_TIMEOUT_MS,
  })
}

export function translateDescriptionToArabic(videoId) {
  return request(`/api/videos/${videoId}/translate-description`, {
    method: 'POST',
    timeoutMs: TRANSLATION_TIMEOUT_MS,
  })
}

/** Returns all videos (legacy — used for backward compat, loads first page only) */
export function listVideos() {
  return request('/api/videos?limit=20&offset=0')
}

/** Paginated list — returns { items, total, hasMore } */
export async function listVideosPaginated(limit = 20, offset = 0) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
  let response
  try {
    response = await fetch(`${API_BASE_URL}/api/videos?limit=${limit}&offset=${offset}`, {
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
    })
  } catch (err) {
    if (err.name === 'AbortError') throw new Error('Server is not responding — please check back in a moment.')
    throw new Error('Cannot reach server — check your connection.')
  } finally {
    clearTimeout(timer)
  }
  if (!response.ok) {
    const text = await response.text()
    throw new Error(parseErrorMessage(text) || `Request failed with status ${response.status}`)
  }
  const items = await response.json()
  const total = parseInt(response.headers.get('X-Total-Count') || '0', 10)
  return { items, total, hasMore: offset + items.length < total }
}

/** URL for direct CSV download (no JS needed — browser handles it) */
export function getExportUrl() {
  return `${API_BASE_URL}/api/videos/export`
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

export function chatWithVideo(videoId, message, mode = 'transcript', answerLanguage = 'english') {
  return request(`/api/videos/${videoId}/chat`, {
    method: 'POST',
    body: JSON.stringify({ message, mode, answer_language: answerLanguage }),
  })
}

export function getChatHistory(videoId) {
  return request(`/api/videos/${videoId}/chat`)
}

export function exportToNotion(videoId, apiKey, databaseId) {
  return request(`/api/videos/${videoId}/export-notion`, {
    method: 'POST',
    body: JSON.stringify({ api_key: apiKey, database_id: databaseId }),
  })
}

export function getStats() {
  return request('/api/videos/stats')
}

export function listTrash() {
  return request('/api/videos/trash')
}

export function restoreVideo(videoId) {
  return request(`/api/videos/${videoId}/restore`, { method: 'POST' })
}

export function permanentDeleteVideo(videoId) {
  return request(`/api/videos/${videoId}/permanent`, { method: 'DELETE' })
}
