import { deleteVideo } from '../api/client.js'

function parseCreatedAt(value) {
  if (!value) return new Date()
  const normalized = value.includes('T') ? value : `${value.replace(' ', 'T')}Z`
  return new Date(normalized)
}

function formatDate(value) {
  return parseCreatedAt(value).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function groupVideosByDate(videos) {
  const groups = new Map()

  for (const video of videos) {
    const date = parseCreatedAt(video.created_at)
    const year = date.getUTCFullYear()
    const monthIndex = date.getUTCMonth()
    const monthLabel = date.toLocaleString('en-US', { month: 'long', timeZone: 'UTC' })
    const groupKey = `${year}-${monthIndex}`

    if (!groups.has(groupKey)) {
      groups.set(groupKey, { year, monthLabel, items: [] })
    }
    groups.get(groupKey).items.push(video)
  }

  return Array.from(groups.values()).sort((a, b) => {
    if (a.year !== b.year) return b.year - a.year
    const monthOrder = {
      January: 0, February: 1, March: 2, April: 3, May: 4, June: 5,
      July: 6, August: 7, September: 8, October: 9, November: 10, December: 11,
    }
    return monthOrder[b.monthLabel] - monthOrder[a.monthLabel]
  })
}

export default function VideoLibrary({
  videos,
  selectedId,
  onView,
  onEdit,
  onDeleted,
}) {
  async function handleDelete(item) {
    const label = item.title || item.storage_stamp || `Video #${item.id}`
    if (!window.confirm(`Delete "${label}" and all saved files?`)) {
      return
    }

    try {
      await deleteVideo(item.id)
      onDeleted(item.id)
    } catch (err) {
      window.alert(err.message)
    }
  }

  return (
    <section className="card library-panel">
      <div className="library-panel-header">
        <h3>Your Instagram videos</h3>
        <p className="library-panel-subtitle">
          View, edit, or delete any saved video from your library.
        </p>
      </div>

      {!videos.length ? (
        <p className="library-empty">No saved videos yet. Paste an Instagram link above to get started.</p>
      ) : (
        groupedSections(videos, selectedId, onView, onEdit, handleDelete)
      )}
    </section>
  )
}

function groupedSections(videos, selectedId, onView, onEdit, handleDelete) {
  const grouped = groupVideosByDate(videos)

  return grouped.map((group) => (
    <div key={`${group.year}-${group.monthLabel}`} className="library-group">
      <h4>{group.monthLabel} {group.year}</h4>
      <div className="library-table-wrap">
        <table className="library-table">
          <thead>
            <tr>
              <th>Title</th>
              <th>Saved as</th>
              <th>Status</th>
              <th>Date</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {group.items.map((item) => (
              <tr
                key={item.id}
                className={selectedId === item.id ? 'library-row-active' : ''}
              >
                <td className="library-title-cell">
                  {item.title || `Video #${item.id}`}
                </td>
                <td className="library-stamp-cell">
                  {item.storage_stamp || '—'}
                </td>
                <td>
                  <span className="status">{item.status}</span>
                </td>
                <td className="library-date-cell">{formatDate(item.created_at)}</td>
                <td>
                  <div className="library-actions">
                    <button type="button" className="action-button" onClick={() => onView(item.id)}>
                      View
                    </button>
                    <button type="button" className="action-button action-button-secondary" onClick={() => onEdit(item.id)}>
                      Edit
                    </button>
                    <button
                      type="button"
                      className="action-button action-button-danger"
                      onClick={() => handleDelete(item)}
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  ))
}
