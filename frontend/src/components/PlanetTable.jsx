import { t, SIGN_NAMES } from '../i18n'

const PLANET_ORDER = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu']

function dignityLabel(lang, planet) {
  if (planet.exalted) return t(lang, 'exalted')
  if (planet.debilitated) return t(lang, 'debilitated')
  if (planet.moolatrikona) return t(lang, 'moolatrikona')
  if (planet.own_sign) return t(lang, 'ownSign')
  return ''
}

function dignityClasses(planet) {
  if (planet.exalted || planet.own_sign || planet.moolatrikona) {
    return 'bg-green-100 text-green-800'
  }
  if (planet.debilitated) {
    return 'bg-amber-100 text-amber-800'
  }
  return ''
}

export default function PlanetTable({ lang, chart }) {
  const rows = PLANET_ORDER.filter((name) => chart.planets[name]).map((name) => chart.planets[name])

  return (
    <div className="overflow-x-auto rounded-lg border border-maroon-100">
      <table className="w-full min-w-[560px] border-collapse text-sm">
        <thead>
          <tr className="bg-maroon-500 text-cream-50">
            <th className="px-3 py-2 text-left font-serif font-semibold">{t(lang, 'graha')}</th>
            <th className="px-3 py-2 text-left font-serif font-semibold">{t(lang, 'sign')}</th>
            <th className="px-3 py-2 text-left font-serif font-semibold">{t(lang, 'degree')}</th>
            <th className="px-3 py-2 text-left font-serif font-semibold">{t(lang, 'nakshatraPada')}</th>
            <th className="px-3 py-2 text-left font-serif font-semibold">{t(lang, 'house')}</th>
            <th className="px-3 py-2 text-left font-serif font-semibold">{t(lang, 'dignity')}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((planet, idx) => (
            <tr
              key={planet.name}
              className={idx % 2 === 0 ? 'bg-cream-50' : 'bg-cream-100'}
              data-testid={`planet-row-${planet.name}`}
            >
              <td className="px-3 py-2 font-medium text-maroon-700">{planet.name}</td>
              <td className="px-3 py-2 text-maroon-600">{SIGN_NAMES[lang][planet.sign]}</td>
              <td className="px-3 py-2 text-maroon-600">{planet.degrees_in_sign.toFixed(2)}°</td>
              <td className="px-3 py-2 text-maroon-600">
                {planet.nakshatra} / {planet.pada}
              </td>
              <td className="px-3 py-2 text-maroon-600">{planet.house}</td>
              <td className="px-3 py-2">
                {dignityLabel(lang, planet) && (
                  <span className={`rounded px-2 py-0.5 text-xs font-medium ${dignityClasses(planet)}`}>
                    {dignityLabel(lang, planet)}
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
