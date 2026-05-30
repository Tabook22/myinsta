import { useEffect } from 'react'
import { useLanguage } from '../context/LanguageContext.jsx'

const SHORTCUTS = [
  { keys: ['?'],                   descKey: 'shortcutHelp'      },
  { keys: ['Ctrl', 'S'],           descKey: 'shortcutSaveNotes' },
  { keys: ['Ctrl', 'Enter'],       descKey: 'shortcutSendChat'  },
  { keys: ['Escape'],              descKey: 'shortcutEscape'    },
  { keys: ['Ctrl', 'Z'],          descKey: 'shortcutUndo'      },
  { keys: ['Ctrl', 'Shift', 'Z'], descKey: 'shortcutRedo'      },
]

export default function ShortcutsModal({ onClose }) {
  const { t } = useLanguage()

  // Close on Escape
  useEffect(() => {
    function onKey(e) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="shortcuts-backdrop" onClick={onClose}>
      <div className="shortcuts-modal" onClick={(e) => e.stopPropagation()}
        role="dialog" aria-modal="true" aria-label={t('shortcutsTitle')}>

        <div className="shortcuts-header">
          <h2>{t('shortcutsTitle')}</h2>
          <button type="button" className="shortcuts-close" onClick={onClose}
            aria-label="Close">✕</button>
        </div>

        <table className="shortcuts-table">
          <tbody>
            {SHORTCUTS.map((s, i) => (
              <tr key={i}>
                <td className="shortcut-keys">
                  {s.keys.map((k, ki) => (
                    <span key={ki}>
                      <kbd>{k}</kbd>
                      {ki < s.keys.length - 1 && <span className="shortcut-plus">+</span>}
                    </span>
                  ))}
                </td>
                <td className="shortcut-desc">{t(s.descKey)}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <p className="shortcuts-tip">{t('shortcutsTip')}</p>
      </div>
    </div>
  )
}
