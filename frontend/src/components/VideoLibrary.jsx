import { useMemo, useRef, useState } from 'react'
import { deleteVideo, getExportUrl, getVideoStreamUrl, listTrash, permanentDeleteVideo, restoreVideo, updateVideo } from '../api/client.js'
import { useLanguage } from '../context/LanguageContext.jsx'

// ── Shared helpers ────────────────────────────────────────────────────────────
const TAG_COLORS = [
  '#4f46e5','#0891b2','#16a34a','#ca8a04','#dc2626',
  '#7c3aed','#0284c7','#15803d','#b45309','#be185d',
]
function tagColor(tag) {
  let h = 0
  for (let i = 0; i < tag.length; i++) h = tag.charCodeAt(i) + ((h << 5) - h)
  return TAG_COLORS[Math.abs(h) % TAG_COLORS.length]
}

function parseDate(value) {
  if (!value) return new Date()
  return new Date(value.includes('T') ? value : `${value.replace(' ', 'T')}Z`)
}

function formatDate(value, locale) {
  return parseDate(value).toLocaleString(locale, {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function formatDuration(seconds) {
  if (!seconds) return null
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

function daysLeft(deletedAt) {
  const deleted = parseDate(deletedAt)
  const expiry  = new Date(deleted.getTime() + 30 * 864e5)
  return Math.max(0, Math.ceil((expiry - Date.now()) / 864e5))
}

function sortVideos(videos, sortBy) {
  const v = [...videos]
  if (sortBy === 'oldest')    return v.sort((a, b) => parseDate(a.created_at) - parseDate(b.created_at))
  if (sortBy === 'duration')  return v.sort((a, b) => (b.duration_seconds || 0) - (a.duration_seconds || 0))
  if (sortBy === 'title-asc') return v.sort((a, b) => (a.title || '').localeCompare(b.title || ''))
  if (sortBy === 'title-desc')return v.sort((a, b) => (b.title || '').localeCompare(a.title || ''))
  return v.sort((a, b) => parseDate(b.created_at) - parseDate(a.created_at)) // newest
}

function groupByMonth(videos, locale) {
  const groups = new Map()
  for (const v of videos) {
    const d = parseDate(v.created_at)
    const key = `${d.getUTCFullYear()}-${d.getUTCMonth()}`
    if (!groups.has(key)) {
      groups.set(key, {
        key,
        label: d.toLocaleString(locale, { month: 'long', timeZone: 'UTC' }) + ' ' + d.getUTCFullYear(),
        items: [],
        duration: 0,
      })
    }
    groups.get(key).items.push(v)
    groups.get(key).duration += v.duration_seconds || 0
  }
  return Array.from(groups.values())
}

function monthKey(date) {
  return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}`
}

function groupByYearMonth(videos, locale) {
  const years = new Map()
  for (const video of videos) {
    const date = parseDate(video.created_at)
    const yearKey = String(date.getUTCFullYear())
    const month = monthKey(date)
    if (!years.has(yearKey)) {
      years.set(yearKey, {
        key: yearKey,
        label: yearKey,
        items: [],
        months: new Map(),
        duration: 0,
      })
    }
    const year = years.get(yearKey)
    if (!year.months.has(month)) {
      year.months.set(month, {
        key: month,
        label: date.toLocaleString(locale, { month: 'long', year: 'numeric', timeZone: 'UTC' }),
        items: [],
        duration: 0,
      })
    }
    const monthGroup = year.months.get(month)
    const duration = video.duration_seconds || 0
    year.items.push(video)
    year.duration += duration
    monthGroup.items.push(video)
    monthGroup.duration += duration
  }

  return Array.from(years.values()).map((year) => ({
    ...year,
    months: Array.from(year.months.values()),
  }))
}

function formatDurationTotal(seconds) {
  if (!seconds) return '0m'
  const h = Math.floor(seconds / 3600)
  const m = Math.round((seconds % 3600) / 60)
  return h > 0 ? `${h}h ${m}m` : `${m}m`
}

function searchText(video) {
  return [
    video.title,
    video.description,
    video.uploader,
    video.platform,
    video.storage_stamp,
    video.storage_folder,
    video.status,
    video.content_type,
    ...(video.tags || []),
  ].filter(Boolean).join(' ').toLowerCase()
}

function sourceLabel(platform, t) {
  if (platform === 'instagram') return t('sourceInstagram')
  if (platform === 'youtube') return t('sourceYoutube')
  return t('sourceUnknown')
}

function StatusIcon({ status }) {
  const label = status || 'unknown'
  const symbol = status === 'ready' ? '✓' : status === 'failed' ? '!' : status === 'processing' ? '…' : '•'
  return (
    <span className={`library-status-icon library-status-icon-${label}`} title={label} aria-label={label}>
      {symbol}
    </span>
  )
}

// ── Tag chips (reusable inline) ───────────────────────────────────────────────
function TagChips({ tags, activeTag, onTagClick, size = 'sm' }) {
  if (!tags?.length) return null
  return (
    <div className="library-tag-chips">
      {tags.map((tag) => (
        <span
          key={tag}
          className={`tag-chip tag-chip-${size}`}
          style={{ '--tag-color': tagColor(tag) }}
          onClick={(e) => { e.stopPropagation(); onTagClick?.(tag) }}
          title={`#${tag}`}
        >
          #{tag}
        </span>
      ))}
    </div>
  )
}

// ── Grid card ─────────────────────────────────────────────────────────────────
function VideoCard({
  item, selected, favorite, onSelect, onView, onEdit, onDelete, onToggleFavorite,
  activeTag, onTagClick, t, locale,
}) {
  const [isHovering, setIsHovering] = useState(false)
  const hoverTimer  = useRef(null)
  const videoUrl    = getVideoStreamUrl(item)

  function handleMouseEnter() {
    if (!videoUrl) return
    hoverTimer.current = setTimeout(() => setIsHovering(true), 350)
  }
  function handleMouseLeave() {
    clearTimeout(hoverTimer.current)
    setIsHovering(false)
  }

  return (
    <div className={`lib-card${selected ? ' lib-card-selected' : ''}`}
      onMouseEnter={handleMouseEnter} onMouseLeave={handleMouseLeave}>
      {/* Checkbox */}
      <input
        type="checkbox"
        className="lib-card-check"
        checked={selected}
        onChange={() => onSelect(item.id)}
        onClick={(e) => e.stopPropagation()}
        aria-label={`Select ${item.title || item.id}`}
      />

      <button
        type="button"
        className={`favorite-btn${favorite ? ' favorite-btn-active' : ''}`}
        onClick={(e) => { e.stopPropagation(); onToggleFavorite(item.id) }}
        title={favorite ? t('favoriteRemove') : t('favoriteAdd')}
        aria-label={favorite ? t('favoriteRemove') : t('favoriteAdd')}
      >
        {favorite ? '★' : '☆'}
      </button>

      {/* Thumbnail / preview */}
      <div className="lib-card-thumb" onClick={() => onView(item.id)}>
        {item.thumbnail_url ? (
          <img src={item.thumbnail_url} alt="" loading="lazy"
            onError={(e) => { e.target.style.display = 'none' }} />
        ) : (
          <span className="lib-card-thumb-placeholder">▶</span>
        )}

        {/* Video preview on hover */}
        {isHovering && videoUrl && (
          <video
            className="lib-card-preview"
            src={videoUrl}
            autoPlay muted loop playsInline
          />
        )}

        {item.duration_seconds ? (
          <span className="lib-card-duration">{formatDuration(item.duration_seconds)}</span>
        ) : null}
        <span className={`lib-card-status status-dot-${item.status}`} title={item.status} />
      </div>

      {/* Body */}
      <div className="lib-card-body">
        <span className={`source-badge source-badge-${item.platform || 'unknown'}`}>
          {sourceLabel(item.platform, t)}
        </span>
        <p className="lib-card-title" onClick={() => onView(item.id)} title={item.title}>
          {item.title || t('videoHash', item.id)}
        </p>
        {item.description && (
          <p className="lib-card-description">{item.description}</p>
        )}
        <TagChips tags={item.tags} activeTag={activeTag} onTagClick={onTagClick} />
        <p className="lib-card-date">{formatDate(item.created_at, locale)}</p>
      </div>

      {/* Actions */}
      <div className="lib-card-actions">
        <button type="button" className="icon-btn icon-btn-view" title={t('view')}
          onClick={() => onView(item.id)}>
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
            <circle cx="12" cy="12" r="3"/>
          </svg>
        </button>
        <button type="button" className="icon-btn icon-btn-edit" title={t('edit')}
          onClick={() => onEdit(item.id)}>
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
          </svg>
        </button>
        <button type="button" className="icon-btn icon-btn-delete" title={t('delete')}
          onClick={() => onDelete(item)}>
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="3 6 5 6 21 6"/>
            <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
            <path d="M10 11v6M14 11v6"/>
            <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>
          </svg>
        </button>
      </div>
    </div>
  )
}

// ── Action icon buttons for table rows ───────────────────────────────────────
function RowActions({ item, favorite, onView, onEdit, onDelete, onToggleFavorite, t }) {
  return (
    <div className="library-actions">
      <button type="button"
        className={`icon-btn icon-btn-favorite${favorite ? ' icon-btn-favorite-active' : ''}`}
        title={favorite ? t('favoriteRemove') : t('favoriteAdd')}
        onClick={() => onToggleFavorite(item.id)}>
        {favorite ? '★' : '☆'}
      </button>
      <button type="button" className="icon-btn icon-btn-view" title={t('view')} onClick={() => onView(item.id)}>
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
          <circle cx="12" cy="12" r="3"/>
        </svg>
      </button>
      <button type="button" className="icon-btn icon-btn-edit" title={t('edit')} onClick={() => onEdit(item.id)}>
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
        </svg>
      </button>
      <button type="button" className="icon-btn icon-btn-delete" title={t('delete')} onClick={() => onDelete(item)}>
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="3 6 5 6 21 6"/>
          <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
          <path d="M10 11v6M14 11v6"/>
          <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>
        </svg>
      </button>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────
export default function VideoLibrary({
  videos, totalVideos = 0, hasMore = false, isLoadingMore = false,
  onLoadMore, selectedId, onView, onEdit, onDeleted, onRefresh,
}) {
  const { t, lang } = useLanguage()
  const locale = lang === 'ar' ? 'ar-SA' : 'en-US'

  // Persistent preferences
  const [viewMode, setViewMode] = useState(() => localStorage.getItem('lib-view') || 'list')
  const [sortBy,   setSortBy]   = useState(() => localStorage.getItem('lib-sort') || 'newest')
  const [favoriteIds, setFavoriteIds] = useState(() => {
    try { return new Set(JSON.parse(localStorage.getItem('lib-favorites') || '[]')) }
    catch { return new Set() }
  })
  const [collapsedGroups, setCollapsedGroups] = useState(() => {
    try { return JSON.parse(localStorage.getItem('lib-collapsed-groups') || '{}') }
    catch { return {} }
  })

  // Transient state
  const [activeTag,      setActiveTag]      = useState(null)
  const [searchQuery,    setSearchQuery]    = useState('')
  const [quickFilter,    setQuickFilter]    = useState('all')
  const [creatorFilter,  setCreatorFilter]  = useState('all')
  const [selectedIds,    setSelectedIds]    = useState(new Set())
  const [batchTagInput,  setBatchTagInput]  = useState('')
  const [showBatchTag,   setShowBatchTag]   = useState(false)

  // Trash
  const [trashItems,    setTrashItems]    = useState([])
  const [showTrash,     setShowTrash]     = useState(false)
  const [loadingTrash,  setLoadingTrash]  = useState(false)

  // Collect unique tags
  const allTags = useMemo(() => {
    const s = new Set()
    videos.forEach((v) => (v.tags || []).forEach((tag) => s.add(tag)))
    return Array.from(s).sort()
  }, [videos])

  const creators = useMemo(() => {
    const counts = new Map()
    videos.forEach((v) => {
      if (!v.uploader) return
      counts.set(v.uploader, (counts.get(v.uploader) || 0) + 1)
    })
    return Array.from(counts.entries())
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([name, count]) => ({ name, count }))
  }, [videos])

  // Apply tag filter → sort → group
  const filtered = useMemo(() => {
    const query = searchQuery.trim().toLowerCase()
    const base = videos.filter((v) => {
      if (activeTag && !(v.tags || []).includes(activeTag)) return false
      if (creatorFilter !== 'all' && v.uploader !== creatorFilter) return false
      if (quickFilter === 'favorites' && !favoriteIds.has(v.id)) return false
      if (quickFilter === 'ready' && v.status !== 'ready') return false
      if (quickFilter === 'failed' && v.status !== 'failed') return false
      if (quickFilter === 'speech' && v.content_type !== 'speech') return false
      if (quickFilter === 'music' && v.content_type !== 'music') return false
      if (quickFilter === 'instagram' && v.platform !== 'instagram') return false
      if (quickFilter === 'youtube' && v.platform !== 'youtube') return false
      if (query && !searchText(v).includes(query)) return false
      return true
    })
    return sortVideos(base, sortBy)
  }, [videos, activeTag, creatorFilter, favoriteIds, quickFilter, searchQuery, sortBy])

  const grouped = useMemo(() => groupByMonth(filtered, locale), [filtered, locale])

  // ── Preferences persistence ────────────────────────────────────────────────
  function changeView(mode) { setViewMode(mode); localStorage.setItem('lib-view', mode) }
  function changeSort(s)    { setSortBy(s);   localStorage.setItem('lib-sort', s);
                              setSelectedIds(new Set()) }

  function toggleFavorite(id) {
    setFavoriteIds((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      localStorage.setItem('lib-favorites', JSON.stringify(Array.from(next)))
      return next
    })
  }

  function toggleCollapsed(key) {
    setCollapsedGroups((prev) => {
      const next = { ...prev, [key]: !prev[key] }
      localStorage.setItem('lib-collapsed-groups', JSON.stringify(next))
      return next
    })
  }

  // ── Selection helpers ──────────────────────────────────────────────────────
  function toggleSelect(id) {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  function selectAll()   { setSelectedIds(new Set(filtered.map((v) => v.id))) }
  function deselectAll() { setSelectedIds(new Set()) }

  // ── Soft-delete ────────────────────────────────────────────────────────────
  async function handleDelete(item) {
    const label = item.title || item.storage_stamp || t('videoHash', item.id)
    if (!window.confirm(t('deleteConfirm', label))) return
    try {
      await deleteVideo(item.id)
      setSelectedIds((prev) => { const n = new Set(prev); n.delete(item.id); return n })
      onDeleted(item.id)
    } catch (err) { window.alert(err.message) }
  }

  // ── Batch operations ───────────────────────────────────────────────────────
  async function handleBatchDelete() {
    const count = selectedIds.size
    if (!window.confirm(t('batchDeleteConfirm', count))) return
    for (const id of selectedIds) {
      try { await deleteVideo(id) } catch { /* continue */ }
      onDeleted(id)
    }
    setSelectedIds(new Set())
  }

  async function handleBatchTag(e) {
    e.preventDefault()
    const tag = batchTagInput.trim().toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9؀-ۿ\-]/g, '')
    if (!tag) return
    for (const id of selectedIds) {
      const video = videos.find((v) => v.id === id)
      if (!video) continue
      const existing = video.tags || []
      if (!existing.includes(tag)) {
        try { await updateVideo(id, { tags: [...existing, tag] }) } catch { /* continue */ }
      }
    }
    setBatchTagInput('')
    setShowBatchTag(false)
    setSelectedIds(new Set())
    onRefresh?.()
  }

  // ── Trash operations ───────────────────────────────────────────────────────
  async function openTrash() {
    setShowTrash(true)
    setLoadingTrash(true)
    try { setTrashItems(await listTrash()) } catch { setTrashItems([]) }
    finally { setLoadingTrash(false) }
  }

  async function handleRestore(id) {
    try {
      await restoreVideo(id)
      setTrashItems((prev) => prev.filter((v) => v.id !== id))
      onRefresh?.()
    } catch (err) { window.alert(err.message) }
  }

  async function handlePermanentDelete(id) {
    if (!window.confirm(t('deleteForeverConfirm'))) return
    try {
      await permanentDeleteVideo(id)
      setTrashItems((prev) => prev.filter((v) => v.id !== id))
    } catch (err) { window.alert(err.message) }
  }

  async function handleEmptyTrash() {
    if (!trashItems.length || !window.confirm(t('emptyTrashConfirm'))) return
    for (const item of trashItems) {
      try { await permanentDeleteVideo(item.id) } catch { /* continue */ }
    }
    setTrashItems([])
  }

  // ── Render ─────────────────────────────────────────────────────────────────
  const hasSelection = selectedIds.size > 0

  return (
    <section className="card library-panel">

      {/* ── Panel header ── */}
      <div className="library-panel-header">
        <div className="library-header-row">
          <div>
            <h3>{t('yourVideos')}</h3>
            <p className="library-panel-subtitle">{t('librarySubtitle')}</p>
          </div>

          <div className="library-header-controls">
            {/* Export CSV */}
            {videos.length > 0 && (
              <a href={getExportUrl()} download="myinsta-library.csv"
                className="export-csv-btn" title={t('exportCsvTitle')}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                  strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="7 10 12 15 17 10"/>
                  <line x1="12" y1="15" x2="12" y2="3"/>
                </svg>
                {t('exportCsv')}
              </a>
            )}

            {/* Sort dropdown */}
            <select
              className="lib-sort-select"
              value={sortBy}
              onChange={(e) => changeSort(e.target.value)}
              title={t('sortLabel')}
            >
              <option value="newest">{t('sortNewest')}</option>
              <option value="oldest">{t('sortOldest')}</option>
              <option value="duration">{t('sortDuration')}</option>
              <option value="title-asc">{t('sortTitleAZ')}</option>
              <option value="title-desc">{t('sortTitleZA')}</option>
            </select>

            {/* View toggle */}
            <div className="lib-view-toggle">
              <button type="button"
                className={`lib-view-btn${viewMode === 'list' ? ' lib-view-btn-active' : ''}`}
                onClick={() => changeView('list')} title={t('viewList')}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="8" y1="6"  x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/>
                  <line x1="8" y1="18" x2="21" y2="18"/><circle cx="3" cy="6"  r="1" fill="currentColor"/>
                  <circle cx="3" cy="12" r="1" fill="currentColor"/><circle cx="3" cy="18" r="1" fill="currentColor"/>
                </svg>
              </button>
              <button type="button"
                className={`lib-view-btn${viewMode === 'grid' ? ' lib-view-btn-active' : ''}`}
                onClick={() => changeView('grid')} title={t('viewGrid')}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/>
                  <rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ── Tag filter bar ── */}
      <div className="library-discovery-bar">
        <input
          type="search"
          className="library-search-input"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder={t('librarySearchPlaceholder')}
        />
        <select
          className="lib-sort-select"
          value={creatorFilter}
          onChange={(e) => setCreatorFilter(e.target.value)}
          title={t('creatorFilter')}
        >
          <option value="all">{t('allCreators')}</option>
          {creators.map((creator) => (
            <option key={creator.name} value={creator.name}>
              @{creator.name} ({creator.count})
            </option>
          ))}
        </select>
      </div>

      <div className="quick-filter-bar">
        {['all', 'ready', 'failed', 'speech', 'music', 'instagram', 'youtube', 'favorites'].map((filter) => (
          <button
            key={filter}
            type="button"
            className={`quick-filter-btn${quickFilter === filter ? ' quick-filter-btn-active' : ''}`}
            onClick={() => setQuickFilter(filter)}
          >
            {t(`filter${filter.charAt(0).toUpperCase()}${filter.slice(1)}`)}
          </button>
        ))}
      </div>

      {allTags.length > 0 && (
        <div className="tag-filter-bar">
          <button type="button"
            className={`tag-filter-btn${!activeTag ? ' tag-filter-btn-active' : ''}`}
            onClick={() => setActiveTag(null)}>{t('filterAll')}</button>
          {allTags.map((tag) => (
            <button key={tag} type="button"
              className={`tag-filter-btn${activeTag === tag ? ' tag-filter-btn-active' : ''}`}
              style={{ '--tag-color': tagColor(tag) }}
              onClick={() => setActiveTag(activeTag === tag ? null : tag)}>
              #{tag}
            </button>
          ))}
        </div>
      )}

      {/* ── Batch action bar ── */}
      {hasSelection && (
        <div className="batch-bar">
          <span className="batch-count">{t('selectedCount', selectedIds.size)}</span>
          <button type="button" className="batch-btn batch-btn-ghost"
            onClick={selectedIds.size === filtered.length ? deselectAll : selectAll}>
            {selectedIds.size === filtered.length ? t('deselectAll') : t('selectAll')}
          </button>
          <div className="batch-bar-actions">
            <button type="button" className="batch-btn batch-btn-danger" onClick={handleBatchDelete}>
              🗑 {t('batchDelete')}
            </button>
            {showBatchTag ? (
              <form className="batch-tag-form" onSubmit={handleBatchTag}>
                <input
                  autoFocus
                  value={batchTagInput}
                  onChange={(e) => setBatchTagInput(e.target.value)}
                  placeholder={t('tagPlaceholder')}
                  className="batch-tag-input"
                />
                <button type="submit" className="batch-btn batch-btn-primary">{t('batchTagApply')}</button>
                <button type="button" className="batch-btn batch-btn-ghost"
                  onClick={() => setShowBatchTag(false)}>✕</button>
              </form>
            ) : (
              <button type="button" className="batch-btn batch-btn-primary"
                onClick={() => setShowBatchTag(true)}>
                {t('batchAddTag')}
              </button>
            )}
          </div>
          <button type="button" className="batch-close" onClick={deselectAll}
            aria-label={t('deselectAll')}>✕</button>
        </div>
      )}

      {/* ── Empty state ── */}
      {!filtered.length && (
        <p className="library-empty">{t('noVideos')}</p>
      )}

      {/* ── Grid view ── */}
      {viewMode === 'grid' && filtered.length > 0 && (
        <div className="lib-grid">
          {filtered.map((item) => (
            <VideoCard
              key={item.id}
              item={item}
              selected={selectedIds.has(item.id)}
              favorite={favoriteIds.has(item.id)}
              onSelect={toggleSelect}
              onView={onView}
              onEdit={onEdit}
              onDelete={handleDelete}
              onToggleFavorite={toggleFavorite}
              activeTag={activeTag}
              onTagClick={(tag) => setActiveTag(activeTag === tag ? null : tag)}
              t={t}
              locale={locale}
            />
          ))}
        </div>
      )}

      {/* ── List (table) view ── */}
      {viewMode === 'list' && filtered.length > 0 && grouped.map((group, gi) => (
        <div key={gi} className="library-group">
          <button type="button" className="library-month-toggle"
            onClick={() => toggleCollapsed(`month-${group.key}`)}>
            <span className="library-toggle-caret">{collapsedGroups[`month-${group.key}`] ? '+' : '-'}</span>
            <span>{group.label}</span>
            <span className="library-group-meta">
              {t('groupSummary', group.items.length, formatDurationTotal(group.duration))}
            </span>
          </button>
          {!collapsedGroups[`month-${group.key}`] && (
          <div className="library-table-wrap">
            <table className="library-table">
              <thead>
                <tr>
                  <th style={{ width: 32 }}>
                    <input type="checkbox"
                      checked={group.items.every((v) => selectedIds.has(v.id))}
                      onChange={(e) => {
                        const ids = group.items.map((v) => v.id)
                        setSelectedIds((prev) => {
                          const n = new Set(prev)
                          ids.forEach((id) => e.target.checked ? n.add(id) : n.delete(id))
                          return n
                        })
                      }}
                      aria-label={t('selectAll')}
                    />
                  </th>
                  <th>{t('colTitle')}</th>
                  <th>{t('colSavedAs')}</th>
                  <th className="library-status-heading">{t('colStatus')}</th>
                  <th>{t('colDate')}</th>
                  <th>{t('colActions')}</th>
                </tr>
              </thead>
              <tbody>
                {group.items.map((item) => (
                  <tr key={item.id}
                    className={[
                      selectedId === item.id ? 'library-row-active' : '',
                      selectedIds.has(item.id) ? 'library-row-selected' : '',
                    ].filter(Boolean).join(' ')}>
                    <td>
                      <input type="checkbox"
                        checked={selectedIds.has(item.id)}
                        onChange={() => toggleSelect(item.id)}
                        aria-label={`Select ${item.title || item.id}`}
                      />
                    </td>
                    <td className="library-title-cell">
                      {item.thumbnail_url && (
                        <img className="library-thumb" src={item.thumbnail_url} alt=""
                          loading="lazy" onError={(e) => { e.target.style.display = 'none' }} />
                      )}
                      <div className="library-title-stack">
                        <span className="library-title-text">{item.title || t('videoHash', item.id)}</span>
                        <span className={`source-badge source-badge-${item.platform || 'unknown'}`}>
                          {sourceLabel(item.platform, t)}
                        </span>
                        {item.description && (
                          <span className="library-description-preview">{item.description}</span>
                        )}
                        <TagChips tags={item.tags} activeTag={activeTag}
                          onTagClick={(tag) => setActiveTag(activeTag === tag ? null : tag)} />
                      </div>
                      {item.creator_url && (
                        <a className="insta-link" href={item.creator_url} target="_blank" rel="noreferrer"
                          title={t('openOnSource', item.uploader || t('creator'), sourceLabel(item.platform, t))}
                          onClick={(e) => e.stopPropagation()}>
                          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
                            stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                            <polyline points="15 3 21 3 21 9"/>
                            <line x1="10" y1="14" x2="21" y2="3"/>
                          </svg>
                        </a>
                      )}
                    </td>
                    <td className="library-stamp-cell">{item.storage_stamp || '—'}</td>
                    <td className="library-status-cell">
                      <StatusIcon status={item.status} />
                      {item.duration_seconds ? (
                        <span className="library-duration">{formatDuration(item.duration_seconds)}</span>
                      ) : null}
                    </td>
                    <td className="library-date-cell">{formatDate(item.created_at, locale)}</td>
                    <td>
                      <RowActions
                        item={item}
                        favorite={favoriteIds.has(item.id)}
                        onView={onView}
                        onEdit={onEdit}
                        onDelete={handleDelete}
                        onToggleFavorite={toggleFavorite}
                        t={t}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          )}
        </div>
      ))}

      {/* ── Load more / all-loaded indicator ── */}
      {videos.length > 0 && (
        <div className="load-more-row">
          {hasMore ? (
            <button type="button" className="load-more-btn"
              onClick={onLoadMore} disabled={isLoadingMore}>
              {isLoadingMore ? t('loadingMore') : t('loadMore')}
            </button>
          ) : (
            <span className="all-loaded-label">{t('allLoaded', totalVideos)}</span>
          )}
        </div>
      )}

      {/* ── Trash section ── */}
      <div className="trash-section">
        <button type="button" className="trash-toggle"
          onClick={showTrash ? () => setShowTrash(false) : openTrash}>
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="3 6 5 6 21 6"/>
            <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
            <path d="M10 11v6M14 11v6"/>
            <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>
          </svg>
          {t('trash')}
          <span className="trash-toggle-arrow">{showTrash ? '▲' : '▼'}</span>
        </button>

        {showTrash && (
          <div className="trash-panel">
            <div className="trash-panel-header">
              <span className="trash-notice">{t('trashNotice')}</span>
              {trashItems.length > 0 && (
                <button type="button" className="trash-empty-btn" onClick={handleEmptyTrash}>
                  {t('emptyTrash')}
                </button>
              )}
            </div>

            {loadingTrash && <p className="library-empty">{t('connectingToServer')}</p>}
            {!loadingTrash && !trashItems.length && (
              <p className="library-empty">{t('trashEmpty')}</p>
            )}
            {trashItems.map((item) => (
              <div key={item.id} className="trash-item">
                {item.thumbnail_url && (
                  <img className="trash-thumb" src={item.thumbnail_url} alt=""
                    loading="lazy" onError={(e) => { e.target.style.display = 'none' }} />
                )}
                <div className="trash-item-body">
                  <span className="trash-item-title">{item.title || t('videoHash', item.id)}</span>
                  <span className="trash-item-meta">
                    {t('trashDaysLeft', daysLeft(item.deleted_at))}
                  </span>
                </div>
                <div className="trash-item-actions">
                  <button type="button" className="trash-restore-btn"
                    onClick={() => handleRestore(item.id)}>
                    ↩ {t('restore')}
                  </button>
                  <button type="button" className="trash-delete-btn"
                    onClick={() => handlePermanentDelete(item.id)}>
                    {t('deleteForever')}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}
