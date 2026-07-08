import { useEffect, useRef, useState } from 'react'
import { getConfig, streamInterpretation } from '../api'
import { t } from '../i18n'

function renderFormatted(text) {
  return text.split('\n').map((line, i) => {
    if (line.startsWith('## ')) {
      return (
        <h3 key={i} className="mt-4 mb-1 font-serif text-lg font-semibold text-maroon-700 first:mt-0">
          {line.slice(3)}
        </h3>
      )
    }
    if (line.trim() === '') return null
    return (
      <p key={i} className="mb-2 leading-relaxed text-maroon-600">
        {line}
      </p>
    )
  })
}

export default function InterpretationPanel({ lang, shareId }) {
  const [mockLlm, setMockLlm] = useState(null)
  const [status, setStatus] = useState('idle') // idle | streaming | done | error
  const [text, setText] = useState('')
  const [error, setError] = useState(null)
  const abortRef = useRef(null)

  useEffect(() => {
    getConfig()
      .then((cfg) => setMockLlm(cfg.mock_llm))
      .catch(() => setMockLlm(null))
    return () => abortRef.current?.abort()
  }, [])

  function handleInterpret() {
    setStatus('streaming')
    setText('')
    setError(null)

    const controller = new AbortController()
    abortRef.current = controller

    streamInterpretation({
      shareId,
      language: lang,
      signal: controller.signal,
      onChunk: (chunk) => setText((prev) => prev + chunk),
      onDone: () => setStatus('done'),
      onError: (err) => {
        setError(err.message || t(lang, 'interpretError'))
        setStatus('error')
      },
    })
  }

  return (
    <div className="rounded-xl border border-gold-500/30 bg-cream-50 p-5">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <h2 className="font-serif text-xl font-semibold text-maroon-700">{t(lang, 'interpret')}</h2>
          {mockLlm && (
            <span
              className="rounded-full bg-gold-400/30 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-maroon-600"
              data-testid="mock-badge"
            >
              {t(lang, 'mockBadge')}
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={handleInterpret}
          disabled={status === 'streaming'}
          className="rounded-md bg-maroon-500 px-4 py-2 text-sm font-semibold text-gold-300 shadow-md hover:bg-maroon-600 disabled:cursor-not-allowed disabled:opacity-60"
          data-testid="interpret-button"
        >
          {status === 'streaming' ? t(lang, 'interpreting') : t(lang, 'interpret')}
        </button>
      </div>

      {status === 'error' && (
        <p className="text-sm font-medium text-maroon-500" data-testid="interpret-error">
          {error}
        </p>
      )}

      {text && (
        <div className="rounded-lg bg-cream-100 p-4" data-testid="interpretation-text">
          {renderFormatted(text)}
          {status === 'streaming' && <span className="animate-pulse text-gold-600">▍</span>}
        </div>
      )}
    </div>
  )
}
