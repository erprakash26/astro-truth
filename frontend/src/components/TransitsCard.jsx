import { t, SIGN_NAMES, TRANSIT_PLANET_NAMES, HOUSE_ORDINALS } from '../i18n'

function formatDate(iso) {
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

function ordinal(lang, house) {
  return HOUSE_ORDINALS[lang]?.[house - 1] ?? `${house}`
}

function TransitRow({ lang, planet }) {
  const name = TRANSIT_PLANET_NAMES[lang]?.[planet.name] ?? planet.name
  const signName = SIGN_NAMES[lang][planet.sign]

  return (
    <div className="rounded-lg bg-cream-100 p-4" data-testid={`transit-${planet.name}`}>
      <p className="font-serif text-base font-semibold text-maroon-700">
        {name} {lang === 'en' ? 'in' : ''} {signName}
      </p>
      <p className="mt-1 text-sm text-maroon-600">
        {ordinal(lang, planet.house_from_lagna)} {t(lang, 'fromLagna')} &middot;{' '}
        {ordinal(lang, planet.house_from_moon)} {t(lang, 'fromMoon')}
      </p>
      <p className="mt-2 text-xs text-maroon-500">
        {planet.degrees_in_sign.toFixed(2)}° &middot; {t(lang, 'nextIngress')}: {formatDate(planet.next_ingress)}
      </p>
    </div>
  )
}

export default function TransitsCard({ lang, transits }) {
  if (!transits) return null

  return (
    <div className="rounded-xl border border-gold-500/30 bg-cream-50 p-5">
      <h2 className="mb-3 font-serif text-xl font-semibold text-maroon-700">{t(lang, 'transits')}</h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <TransitRow lang={lang} planet={transits.jupiter} />
        <TransitRow lang={lang} planet={transits.saturn} />
      </div>
    </div>
  )
}
