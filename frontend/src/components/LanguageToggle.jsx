import { LANGUAGES, t, validateCustomLanguage } from '../i18n'

export default function LanguageToggle({ mode, customLanguage, onModeChange, onCustomLanguageChange }) {
  const isOther = mode === 'other'
  const showFallbackNotice = isOther && !validateCustomLanguage(customLanguage)

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="inline-flex overflow-hidden rounded-md border border-gold-500/50">
        {Object.entries(LANGUAGES).map(([code, label]) => (
          <button
            type="button"
            key={code}
            onClick={() => onModeChange(code)}
            data-testid={`lang-${code}`}
            className={`px-3 py-1 text-xs font-medium transition-colors ${
              mode === code ? 'bg-gold-500 text-maroon-900' : 'bg-transparent text-gold-300 hover:bg-gold-500/20'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {isOther && (
        <div className="flex flex-col items-end gap-0.5">
          <input
            type="text"
            value={customLanguage}
            onChange={(e) => onCustomLanguageChange(e.target.value)}
            placeholder={t('en', 'langOtherPlaceholder')}
            data-testid="lang-other-input"
            className="w-40 rounded-md border border-gold-500/50 bg-transparent px-2 py-1 text-xs text-gold-100 placeholder:text-gold-300/60 focus:outline-none focus:ring-1 focus:ring-gold-400"
          />
          {showFallbackNotice && (
            <p className="text-[10px] leading-tight text-gold-200/90" data-testid="lang-other-fallback-notice">
              {t('en', 'langOtherInvalid')}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
