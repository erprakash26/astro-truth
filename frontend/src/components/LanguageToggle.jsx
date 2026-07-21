import { LANGUAGES, t } from '../i18n'
import LanguageAutocomplete from './LanguageAutocomplete'

export default function LanguageToggle({
  mode,
  otherLanguage,
  onModeChange,
  onOtherLanguageChange,
  uiTranslationStatus,
  uiTranslationNote,
}) {
  const isOther = mode === 'other'

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
          <LanguageAutocomplete value={otherLanguage} onChange={onOtherLanguageChange} />
          {uiTranslationStatus === 'loading' && (
            <p className="text-[10px] leading-tight text-gold-200/90" data-testid="ui-translation-loading">
              {t('en', 'uiTranslationLoading')}
            </p>
          )}
          {uiTranslationStatus === 'unavailable' && (
            <p className="text-[10px] leading-tight text-gold-200/90" data-testid="ui-translation-unavailable">
              {uiTranslationNote || t('en', 'uiTranslationUnavailable')}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
