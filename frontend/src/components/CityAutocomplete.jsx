import { useEffect, useRef, useState } from 'react'
import { searchCities } from '../api'
import { t } from '../i18n'

export default function CityAutocomplete({ lang, value, onChange }) {
  const [query, setQuery] = useState(value?.label ?? '')
  const [results, setResults] = useState([])
  const [open, setOpen] = useState(false)
  const boxRef = useRef(null)

  useEffect(() => {
    const handle = setTimeout(() => {
      if (!query.trim()) {
        setResults([])
        return
      }
      searchCities(query).then(setResults).catch(() => setResults([]))
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

  function pick(city) {
    const label = city.admin ? `${city.name}, ${city.admin}` : `${city.name}, ${city.country}`
    setQuery(label)
    onChange({ id: city.id, label })
    setOpen(false)
  }

  return (
    <div className="relative" ref={boxRef}>
      <input
        type="text"
        className="w-full rounded-md border border-maroon-100 bg-cream-50 px-3 py-2 text-maroon-700 placeholder:text-maroon-400/50 focus:border-gold-500 focus:outline-none focus:ring-2 focus:ring-gold-400/40"
        placeholder={t(lang, 'birthPlacePlaceholder')}
        value={query}
        onChange={(e) => {
          setQuery(e.target.value)
          onChange(null)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        autoComplete="off"
        data-testid="city-input"
      />
      {open && query.trim() && (
        <ul className="absolute z-10 mt-1 max-h-56 w-full overflow-auto rounded-md border border-maroon-100 bg-cream-50 shadow-lg">
          {results.length === 0 && (
            <li className="px-3 py-2 text-sm text-maroon-400/70">{t(lang, 'noCityResults')}</li>
          )}
          {results.map((city) => (
            <li
              key={city.id}
              className="cursor-pointer px-3 py-2 text-sm text-maroon-600 hover:bg-gold-300/30"
              onClick={() => pick(city)}
              data-testid="city-option"
            >
              {city.name}
              {city.admin ? `, ${city.admin}` : ''} — {city.country}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
