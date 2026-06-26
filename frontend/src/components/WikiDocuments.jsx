import { useEffect, useState } from 'react'
import {
  deleteWikiDocument,
  getWikiDocument,
  getWikiDownloadUrl,
  listWikiDocuments,
  syncWikiDocument,
} from '../api/client.js'
import { useLanguage } from '../context/LanguageContext.jsx'

export default function WikiDocuments({ video }) {
  const { t } = useLanguage()
  const [documents, setDocuments] = useState(video.wiki_documents || [])
  const [selected, setSelected] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isSyncing, setIsSyncing] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    setDocuments(video.wiki_documents || [])
    setSelected(null)
    setError('')
  }, [video.id, video.wiki_documents])

  async function loadDocuments() {
    setIsLoading(true)
    setError('')
    try {
      setDocuments(await listWikiDocuments(video.id))
    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  async function handleSync() {
    setIsSyncing(true)
    setError('')
    try {
      const document = await syncWikiDocument(video.id)
      setDocuments([document])
      setSelected(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setIsSyncing(false)
    }
  }

  async function handleView(document) {
    setIsLoading(true)
    setError('')
    try {
      setSelected(await getWikiDocument(video.id, document.id))
    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  async function handleDelete(document) {
    if (!window.confirm(t('wikiDeleteConfirm', document.filename))) return
    setError('')
    try {
      await deleteWikiDocument(video.id, document.id)
      setDocuments((items) => items.filter((item) => item.id !== document.id))
      setSelected((current) => (current?.id === document.id ? null : current))
    } catch (err) {
      setError(err.message)
    }
  }

  if (video.status !== 'ready') return null

  return (
    <section className="wiki-panel">
      <div className="wiki-header">
        <div>
          <h3>{t('myWiki')}</h3>
          <p>{t('wikiSubtitle')}</p>
        </div>
        <div className="wiki-actions">
          <button type="button" onClick={loadDocuments} disabled={isLoading || isSyncing}>
            {isLoading ? t('loading') : t('wikiRefresh')}
          </button>
          <button type="button" onClick={handleSync} disabled={isSyncing || isLoading}>
            {isSyncing ? t('wikiSaving') : t('wikiCreateUpdate')}
          </button>
        </div>
      </div>

      {error ? <p className="error">{error}</p> : null}

      {documents.length ? (
        <div className="wiki-list">
          {documents.map((document) => (
            <div key={document.id} className="wiki-item">
              <div className="wiki-item-main">
                <strong>{document.filename}</strong>
                <span>{t('wikiUpdatedAt', document.updated_at)}</span>
              </div>
              <div className="wiki-item-actions">
                <button type="button" onClick={() => handleView(document)}>
                  {t('view')}
                </button>
                <a href={getWikiDownloadUrl(document)} download>
                  {t('download')}
                </a>
                <button type="button" onClick={() => handleDelete(document)}>
                  {t('delete')}
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="wiki-empty">{t('wikiEmpty')}</p>
      )}

      {selected ? (
        <div className="wiki-preview">
          <div className="wiki-preview-header">
            <strong>{selected.filename}</strong>
            <button type="button" onClick={() => setSelected(null)}>
              {t('close')}
            </button>
          </div>
          <pre>{selected.content}</pre>
        </div>
      ) : null}
    </section>
  )
}
