import { LanguageProvider } from './context/LanguageContext.jsx'
import { ThemeProvider } from './context/ThemeContext.jsx'
import { ToastProvider } from './context/ToastContext.jsx'
import HomePage from './pages/HomePage.jsx'

export default function App() {
  return (
    <ThemeProvider>
      <LanguageProvider>
        <ToastProvider>
          <HomePage />
        </ToastProvider>
      </LanguageProvider>
    </ThemeProvider>
  )
}
