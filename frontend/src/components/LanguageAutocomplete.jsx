import { useEffect, useRef, useState } from 'react'
import { searchLanguages } from '../api'
import { t } from '../i18n'

export default function LanguageAutocomplete({ value, onChange }) {
  const [query, setQuery] = useState(value ?? '')
  const [results, setResults] = useState([])
  const [open, setOpen] = useState(false)
  const boxRef = useRef(null)

  useEffect(() => {
    const handle = setTimeout(() => {
      if (!query.trim()) {
        setResults([])
        return
      }
      searchLanguages(query).then(setResults).catch(() => setResults([]))
    }, 200)
    return () => clearTimeout(handle)
  }, [query])

  useEffect(() => {
    function onClickOutside(e) {
      if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  function pick(language) {
    setQuery(language.name)
    onChange(language.name)
    setOpen(false)
  }

  return (
    <div className="relative" ref={boxRef}>
      <input
        type="text"
        className="w-40 rounded-md border border-gold-500/50 bg-transparent px-2 py-1 text-xs text-gold-100 placeholder:text-gold-300/60 focus:outline-none focus:ring-1 focus:ring-gold-400"
        placeholder={t('en', 'langOtherPlaceholder')}
        value={query}
        onChange={(e) => {
          setQuery(e.target.value)
          onChange(null)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        autoComplete="off"
        data-testid="lang-other-input"
      />
      {open && query.trim() && (
        <ul className="absolute z-10 mt-1 max-h-56 w-40 overflow-auto rounded-md border border-maroon-100 bg-cream-50 shadow-lg">
          {results.length === 0 && (
            <li className="px-3 py-2 text-sm text-maroon-400/70">{t('en', 'noLanguageResults')}</li>
          )}
          {results.map((language) => (
            <li
              key={language.code}
              className="cursor-pointer px-3 py-2 text-sm text-maroon-600 hover:bg-gold-300/30"
              onClick={() => pick(language)}
              data-testid="lang-other-option"
            >
              {language.name}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
