import { deleteVideo } from '../api/client.js'
import { useLanguage } from '../context/LanguageContext.jsx'

function parseCreatedAt(value) {
  if (!value) return new Date()
  const normalized = value.includes('T') ? value : `${value.replace(' ', 'T')}Z`
  return new Date(normalized)
}

function groupVideosByDate(videos, locale) {
  const groups = new Map()
  for (const video of videos) {
    const date     = parseCreatedAt(video.created_at)
    const year     = date.getUTCFullYear()
    const monthIdx = date.getUTCMonth()
    const monthLabel = date.toLocaleString(locale, { month: 'long', timeZone: 'UTC' })
    const key = `${year}-${monthIdx}`
    if (!groups.has(key)) groups.set(key, { year, monthIdx, monthLabel, items: [] })
    groups.get(key).items.push(video)
  }
  return Array.from(groups.values()).sort((a, b) =>
    a.year !== b.year ? b.year - a.year : b.monthIdx - a.monthIdx
  )
}

function formatDate(value, locale) {
  return parseCreatedAt(value).toLocaleString(locale, {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

export default function VideoLibrary({ videos, selectedId, onView, onEdit, onDeleted }) {
  const { t, lang } = useLanguage()
  const locale = lang === 'ar' ? 'ar-SA' : 'en-US'

  async function handleDelete(item) {
    const label = item.title || item.storage_stamp || t('videoHash', item.id)
    if (!window.confirm(t('deleteConfirm', label))) return
    try {
      await deleteVideo(item.id)
      onDeleted(item.id)
    } catch (err) {
      window.alert(err.message)
    }
  }

  const grouped = groupVideosByDate(videos, locale)

  return (
    <section className="card library-panel">
      <div className="library-panel-header">
        <h3>{t('yourVideos')}</h3>
        <p className="library-panel-subtitle">{t('librarySubtitle')}</p>
      </div>

      {!videos.length ? (
        <p className="library-empty">{t('noVideos')}</p>
      ) : (
        grouped.map((group) => (
          <div key={`${group.year}-${group.monthIdx}`} className="library-group">
            <h4>{group.monthLabel} {group.year}</h4>
            <div className="library-table-wrap">
              <table className="library-table">
                <thead>
                  <tr>
                    <th>{t('colTitle')}</th>
                    <th>{t('colSavedAs')}</th>
                    <th>{t('colStatus')}</th>
                    <th>{t('colDate')}</th>
                    <th>{t('colActions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {group.items.map((item) => (
                    <tr key={item.id} className={selectedId === item.id ? 'library-row-active' : ''}>
                      <td className="library-title-cell">
                        <span className="library-title-text">
                          {item.title || t('videoHash', item.id)}
                        </span>
                        {item.creator_url && (
                          <a
                            className="insta-link"
                            href={item.creator_url}
                            target="_blank"
                            rel="noreferrer"
                            title={t('openOnInstagram', item.uploader || t('creator'))}
                            onClick={(e) => e.stopPropagation()}
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
                              stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <rect x="2" y="2" width="20" height="20" rx="5" ry="5"/>
                              <circle cx="12" cy="12" r="4"/>
                              <circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none"/>
                            </svg>
                          </a>
                        )}
                      </td>
                      <td className="library-stamp-cell">{item.storage_stamp || '—'}</td>
                      <td><span className="status">{item.status}</span></td>
                      <td className="library-date-cell">{formatDate(item.created_at, locale)}</td>
                      <td>
                        <div className="library-actions">
                          <button type="button" className="icon-btn icon-btn-view"
                            title={t('view')} onClick={() => onView(item.id)}>
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
                              stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                              <circle cx="12" cy="12" r="3"/>
                            </svg>
                          </button>
                          <button type="button" className="icon-btn icon-btn-edit"
                            title={t('edit')} onClick={() => onEdit(item.id)}>
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
                              stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                            </svg>
                          </button>
                          <button type="button" className="icon-btn icon-btn-delete"
                            title={t('delete')} onClick={() => handleDelete(item)}>
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
                              stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <polyline points="3 6 5 6 21 6"/>
                              <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
                              <path d="M10 11v6M14 11v6"/>
                              <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>
                            </svg>
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
      )}
    </section>
  )
}
