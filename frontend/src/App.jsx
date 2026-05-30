import { LanguageProvider } from './context/LanguageContext.jsx'
import HomePage from './pages/HomePage.jsx'

export default function App() {
  return (
    <LanguageProvider>
      <HomePage />
    </LanguageProvider>
  )
}
