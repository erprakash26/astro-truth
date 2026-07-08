import { useState } from 'react'
import { t } from '../i18n'

const LORD_COLORS = {
  Ketu: '#8a2432',
  Venus: '#b8912a',
  Sun: '#d4af37',
  Moon: '#6b1a24',
  Mars: '#a83246',
  Rahu: '#5a151d',
  Jupiter: '#e8cd7a',
  Saturn: '#3f0f15',
  Mercury: '#c98a4b',
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

export default function DashaTimeline({ lang, dashaTimeline, currentDasha }) {
  const [expanded, setExpanded] = useState(currentDasha?.mahadasha?.lord ?? null)

  const start = new Date(dashaTimeline[0].start).getTime()
  const end = new Date(dashaTimeline[dashaTimeline.length - 1].end).getTime()
  const totalMs = end - start

  return (
    <div>
      <h2 className="mb-3 font-serif text-xl font-semibold text-maroon-700">{t(lang, 'dashaTimeline')}</h2>

      <div className="flex h-10 w-full overflow-hidden rounded-md border border-maroon-100" data-testid="dasha-bar">
        {dashaTimeline.map((maha) => {
          const widthPct =
            ((new Date(maha.end).getTime() - new Date(maha.start).getTime()) / totalMs) * 100
          const isCurrent = currentDasha?.mahadasha?.lord === maha.lord && currentDasha?.mahadasha?.start === maha.start
          return (
            <button
              type="button"
              key={`${maha.lord}-${maha.start}`}
              onClick={() => setExpanded(expanded === maha.lord ? null : maha.lord)}
              title={`${maha.lord}: ${formatDate(maha.start)} – ${formatDate(maha.end)}`}
              style={{ width: `${widthPct}%`, backgroundColor: LORD_COLORS[maha.lord] }}
              className={`relative flex items-center justify-center text-[10px] font-semibold text-cream-50 transition-transform hover:z-10 hover:scale-y-110 ${
                isCurrent ? 'ring-2 ring-inset ring-gold-400' : ''
              }`}
              data-testid={`maha-segment-${maha.lord}`}
            >
              {widthPct > 4 ? maha.lord : ''}
            </button>
          )
        })}
      </div>

      <ul className="mt-4 divide-y divide-maroon-100 rounded-md border border-maroon-100">
        {dashaTimeline.map((maha) => {
          const isCurrent = currentDasha?.mahadasha?.lord === maha.lord && currentDasha?.mahadasha?.start === maha.start
          const isExpanded = expanded === maha.lord
          return (
            <li key={`${maha.lord}-${maha.start}`}>
              <button
                type="button"
                onClick={() => setExpanded(isExpanded ? null : maha.lord)}
                className={`flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-gold-300/10 ${
                  isCurrent ? 'bg-gold-300/20 font-semibold' : ''
                }`}
                data-testid={`maha-toggle-${maha.lord}`}
              >
                <span className="text-maroon-700">
                  {maha.lord} {t(lang, 'mahadasha')}
                  {isCurrent && (
                    <span className="ml-2 rounded bg-maroon-500 px-1.5 py-0.5 text-[10px] font-semibold text-cream-50">
                      {t(lang, 'current')}
                    </span>
                  )}
                </span>
                <span className="text-maroon-500">
                  {formatDate(maha.start)} – {formatDate(maha.end)}
                </span>
              </button>
              {isExpanded && (
                <ul className="bg-cream-50 px-3 py-2" data-testid={`antardasha-list-${maha.lord}`}>
                  {maha.antardashas.map((antar) => {
                    const isCurrentAntar =
                      isCurrent &&
                      currentDasha?.antardasha?.lord === antar.lord &&
                      currentDasha?.antardasha?.start === antar.start
                    return (
                      <li
                        key={`${antar.lord}-${antar.start}`}
                        className={`flex items-center justify-between rounded px-2 py-1 text-xs ${
                          isCurrentAntar ? 'bg-gold-300/30 font-semibold text-maroon-700' : 'text-maroon-500'
                        }`}
                      >
                        <span>
                          {maha.lord}–{antar.lord} {t(lang, 'antardasha')}
                        </span>
                        <span>
                          {formatDate(antar.start)} – {formatDate(antar.end)}
                        </span>
                      </li>
                    )
                  })}
                </ul>
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )
}
