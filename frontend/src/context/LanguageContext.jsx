import { createContext, useContext, useEffect, useState } from 'react'
import { translations } from '../i18n/translations.js'

const LanguageContext = createContext(null)

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(() => localStorage.getItem('app-lang') || 'en')

  // Apply dir + lang attributes to <html> whenever language changes
  useEffect(() => {
    document.documentElement.dir  = lang === 'ar' ? 'rtl' : 'ltr'
    document.documentElement.lang = lang
  }, [lang])

  /** Translate a key. Parameterised keys are functions — pass args after the key. */
  function t(key, ...args) {
    const entry = translations[lang]?.[key] ?? translations.en?.[key] ?? key
    return typeof entry === 'function' ? entry(...args) : entry
  }

  /** Switch language and persist choice */
  function switchLang(newLang) {
    setLang(newLang)
    localStorage.setItem('app-lang', newLang)
  }

  return (
    <LanguageContext.Provider value={{ lang, t, switchLang }}>
      {children}
    </LanguageContext.Provider>
  )
}

/** Hook for any component that needs translations */
export function useLanguage() {
  const ctx = useContext(LanguageContext)
  if (!ctx) throw new Error('useLanguage must be used inside <LanguageProvider>')
  return ctx
}
