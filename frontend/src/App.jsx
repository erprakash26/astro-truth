import { useEffect, useState } from 'react'
import BirthForm from './components/BirthForm'
import ResultsPage from './components/ResultsPage'
import LanguageToggle from './components/LanguageToggle'
import Logo from './components/Logo'
import Footer from './components/Footer'
import { createChart, translateUI } from './api'
import { setOtherTranslations, t } from './i18n'
import { getCachedUITranslation, setCachedUITranslation } from './uiTranslationCache'

function App() {
  const [langMode, setLangMode] = useState('en') // 'en' | 'ne' | 'other'
  const [otherLanguage, setOtherLanguage] = useState(null)
  const [uiTranslationStatus, setUiTranslationStatus] = useState('idle') // idle | loading | ready | unavailable
  const [uiTranslationNote, setUiTranslationNote] = useState(null)
  const [result, setResult] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  // Fetches (or applies a cached) UI-chrome translation once a custom
  // "Other" language is confirmed -- i.e. selected from the dropdown, not
  // on every keystroke while typing. Independent of contentLanguage below,
  // which drives interpretation/PDF content and keeps working even if this
  // fails or mock mode is active.
  useEffect(() => {
    if (langMode !== 'other' || !otherLanguage) {
      setUiTranslationStatus('idle')
      setUiTranslationNote(null)
      return
    }

    const cached = getCachedUITranslation(otherLanguage)
    if (cached) {
      setOtherTranslations(cached)
      setUiTranslationStatus('ready')
      setUiTranslationNote(null)
      return
    }

    let cancelled = false
    setOtherTranslations(null)
    setUiTranslationStatus('loading')
    setUiTranslationNote(null)

    translateUI(otherLanguage)
      .then((res) => {
        if (cancelled) return
        if (res.available && res.translations) {
          setCachedUITranslation(otherLanguage, res.translations)
          setOtherTranslations(res.translations)
          setUiTranslationStatus('ready')
        } else {
          setUiTranslationStatus('unavailable')
          setUiTranslationNote(res.note)
        }
      })
      .catch((err) => {
        if (cancelled) return
        setUiTranslationStatus('unavailable')
        setUiTranslationNote(err.message)
      })

    return () => {
      cancelled = true
    }
  }, [langMode, otherLanguage])

  // UI chrome (buttons, labels) renders in English or Nepali by default; in
  // "Other" mode it switches to the fetched translation once ready, and
  // falls back to English while loading, on failure, or in mock mode.
  // Interpretation/PDF content instead uses contentLanguage, which is
  // whatever was picked from the dropdown regardless of UI-translation status.
  const lang = langMode === 'other' ? (uiTranslationStatus === 'ready' ? 'other' : 'en') : langMode
  const contentLanguage = langMode === 'other' ? (otherLanguage ?? 'en') : langMode

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
          <button
            type="button"
            onClick={() => setResult(null)}
            className="flex cursor-pointer items-center gap-3 rounded-md text-left transition-opacity hover:opacity-80 focus:outline-none focus-visible:ring-2 focus-visible:ring-gold-300"
            aria-label={t(lang, 'newChart')}
            data-testid="logo-home-link"
          >
            <Logo className="h-9 w-9 shrink-0" />
            <div>
              <h1 className="font-serif text-2xl font-bold text-gold-300">{t(lang, 'appName')}</h1>
              <p className="text-xs text-cream-100/80">{t(lang, 'tagline')}</p>
            </div>
          </button>
          <LanguageToggle
            mode={langMode}
            otherLanguage={otherLanguage}
            onModeChange={setLangMode}
            onOtherLanguageChange={setOtherLanguage}
            uiTranslationStatus={uiTranslationStatus}
            uiTranslationNote={uiTranslationNote}
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

      <Footer lang={lang} />
    </div>
  )
}

export default App
