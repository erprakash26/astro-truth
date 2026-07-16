import { useState } from 'react'
import BirthForm from './components/BirthForm'
import ResultsPage from './components/ResultsPage'
import LanguageToggle from './components/LanguageToggle'
import Logo from './components/Logo'
import Footer from './components/Footer'
import { createChart } from './api'
import { t, validateCustomLanguage } from './i18n'

function App() {
  const [langMode, setLangMode] = useState('en') // 'en' | 'ne' | 'other'
  const [customLanguage, setCustomLanguage] = useState('')
  const [result, setResult] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  // UI chrome (buttons, labels) only ever renders in English or Nepali —
  // when "Other" is active it stays in English, per the language selector's
  // contract. Interpretation/PDF content instead uses contentLanguage,
  // which may be an arbitrary validated string.
  const lang = langMode === 'other' ? 'en' : langMode
  const contentLanguage = langMode === 'other' ? (validateCustomLanguage(customLanguage) ?? 'en') : langMode

  async function handleSubmit(payload) {
    setSubmitting(true)
    setError(null)
    try {
      const data = await createChart(payload)
      setResult(data)
    } catch (err) {
      setError(err.message || t(lang, 'errorGeneric'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-cream-100 text-maroon-700">
      <header className="bg-maroon-500 px-4 py-4 shadow-md">
        <div className="mx-auto flex max-w-4xl flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-3">
            <Logo className="h-9 w-9 shrink-0" />
            <div>
              <h1 className="font-serif text-2xl font-bold text-gold-300">{t(lang, 'appName')}</h1>
              <p className="text-xs text-cream-100/80">{t(lang, 'tagline')}</p>
            </div>
          </div>
          <LanguageToggle
            mode={langMode}
            customLanguage={customLanguage}
            onModeChange={setLangMode}
            onCustomLanguageChange={setCustomLanguage}
          />
        </div>
      </header>

      <main className="flex-1">
        {result ? (
          <ResultsPage
            lang={lang}
            contentLanguage={contentLanguage}
            result={result}
            onReset={() => setResult(null)}
          />
        ) : (
          <div className="mx-auto max-w-md px-4 py-10">
            <div className="rounded-xl border border-gold-500/30 bg-cream-50 p-6 shadow-lg">
              <BirthForm lang={lang} onSubmit={handleSubmit} submitting={submitting} error={error} />
            </div>
          </div>
        )}
      </main>

      <Footer />
    </div>
  )
}

export default App
