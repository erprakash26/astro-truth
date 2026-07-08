import { useState } from 'react'
import CityAutocomplete from './CityAutocomplete'
import { t, BS_MONTHS } from '../i18n'

const BS_YEAR_MIN = 1975
const BS_YEAR_MAX = 2100

function range(start, end) {
  return Array.from({ length: end - start + 1 }, (_, i) => start + i)
}

export default function BirthForm({ lang, onSubmit, submitting, error }) {
  const [calendarType, setCalendarType] = useState('AD')
  const [adDate, setAdDate] = useState('2000-01-01')
  const [bsYear, setBsYear] = useState(2056)
  const [bsMonth, setBsMonth] = useState(1)
  const [bsDay, setBsDay] = useState(1)
  const [time, setTime] = useState('12:00')
  const [city, setCity] = useState(null)
  const [localError, setLocalError] = useState(null)

  function handleSubmit(e) {
    e.preventDefault()
    setLocalError(null)

    if (!time || !city) {
      setLocalError(t(lang, city ? 'errorRequired' : 'errorCity'))
      return
    }

    const date =
      calendarType === 'AD'
        ? adDate
        : `${bsYear}-${String(bsMonth).padStart(2, '0')}-${String(bsDay).padStart(2, '0')}`

    if (calendarType === 'AD' && !adDate) {
      setLocalError(t(lang, 'errorRequired'))
      return
    }

    onSubmit({ calendar: calendarType, date, time, cityId: city.id })
  }

  const displayError = localError ?? error

  return (
    <form onSubmit={handleSubmit} className="space-y-5" data-testid="birth-form">
      <div>
        <span className="mb-1 block text-sm font-medium text-maroon-600">{t(lang, 'calendar')}</span>
        <div className="inline-flex overflow-hidden rounded-md border border-maroon-100">
          {['AD', 'BS'].map((cal) => (
            <button
              type="button"
              key={cal}
              data-testid={`calendar-${cal}`}
              onClick={() => setCalendarType(cal)}
              className={`px-4 py-1.5 text-sm font-medium transition-colors ${
                calendarType === cal
                  ? 'bg-maroon-500 text-cream-50'
                  : 'bg-cream-50 text-maroon-500 hover:bg-gold-300/20'
              }`}
            >
              {t(lang, cal.toLowerCase())}
            </button>
          ))}
        </div>
      </div>

      {calendarType === 'AD' ? (
        <label className="block">
          <span className="mb-1 block text-sm font-medium text-maroon-600">{t(lang, 'date')}</span>
          <input
            type="date"
            className="w-full rounded-md border border-maroon-100 bg-cream-50 px-3 py-2 text-maroon-700 focus:border-gold-500 focus:outline-none focus:ring-2 focus:ring-gold-400/40"
            value={adDate}
            onChange={(e) => setAdDate(e.target.value)}
            data-testid="ad-date-input"
          />
        </label>
      ) : (
        <div className="grid grid-cols-3 gap-2">
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-maroon-600">{t(lang, 'year')}</span>
            <select
              className="w-full rounded-md border border-maroon-100 bg-cream-50 px-2 py-2 text-maroon-700 focus:border-gold-500 focus:outline-none"
              value={bsYear}
              onChange={(e) => setBsYear(Number(e.target.value))}
              data-testid="bs-year-input"
            >
              {range(BS_YEAR_MIN, BS_YEAR_MAX).map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-maroon-600">{t(lang, 'month')}</span>
            <select
              className="w-full rounded-md border border-maroon-100 bg-cream-50 px-2 py-2 text-maroon-700 focus:border-gold-500 focus:outline-none"
              value={bsMonth}
              onChange={(e) => setBsMonth(Number(e.target.value))}
              data-testid="bs-month-input"
            >
              {BS_MONTHS[lang].map((name, i) => (
                <option key={name} value={i + 1}>{name}</option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-maroon-600">{t(lang, 'day')}</span>
            <select
              className="w-full rounded-md border border-maroon-100 bg-cream-50 px-2 py-2 text-maroon-700 focus:border-gold-500 focus:outline-none"
              value={bsDay}
              onChange={(e) => setBsDay(Number(e.target.value))}
              data-testid="bs-day-input"
            >
              {range(1, 32).map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </label>
        </div>
      )}

      <label className="block">
        <span className="mb-1 block text-sm font-medium text-maroon-600">{t(lang, 'time')}</span>
        <input
          type="time"
          className="w-full rounded-md border border-maroon-100 bg-cream-50 px-3 py-2 text-maroon-700 focus:border-gold-500 focus:outline-none focus:ring-2 focus:ring-gold-400/40"
          value={time}
          onChange={(e) => setTime(e.target.value)}
          data-testid="time-input"
        />
      </label>

      <label className="block">
        <span className="mb-1 block text-sm font-medium text-maroon-600">{t(lang, 'birthPlace')}</span>
        <CityAutocomplete lang={lang} value={city} onChange={setCity} />
      </label>

      {displayError && (
        <p className="text-sm font-medium text-maroon-500" data-testid="form-error">{displayError}</p>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="w-full rounded-md bg-maroon-500 px-4 py-2.5 font-semibold text-gold-300 shadow-md transition-colors hover:bg-maroon-600 disabled:cursor-not-allowed disabled:opacity-60"
        data-testid="submit-button"
      >
        {submitting ? t(lang, 'submitting') : t(lang, 'submit')}
      </button>
    </form>
  )
}
