import { LANGUAGES } from '../i18n'

export default function LanguageToggle({ lang, onChange }) {
  return (
    <div className="inline-flex overflow-hidden rounded-md border border-gold-500/50">
      {Object.entries(LANGUAGES).map(([code, label]) => (
        <button
          type="button"
          key={code}
          onClick={() => onChange(code)}
          data-testid={`lang-${code}`}
          className={`px-3 py-1 text-xs font-medium transition-colors ${
            lang === code ? 'bg-gold-500 text-maroon-900' : 'bg-transparent text-gold-300 hover:bg-gold-500/20'
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  )
}
