import KundaliChart from './KundaliChart'
import PlanetTable from './PlanetTable'
import DashaTimeline from './DashaTimeline'
import TransitsCard from './TransitsCard'
import InterpretationPanel from './InterpretationPanel'
import { t, SIGN_NAMES } from '../i18n'

export default function ResultsPage({ lang, result, onReset }) {
  const { share_id: shareId, chart, dasha_timeline: dashaTimeline, current_dasha: currentDasha, transits } = result

  return (
    <div className="mx-auto max-w-4xl space-y-8 px-4 py-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-serif text-2xl font-bold text-maroon-700">{t(lang, 'chart')}</h1>
        <button
          type="button"
          onClick={onReset}
          className="rounded-md border border-maroon-400 px-3 py-1.5 text-sm font-medium text-maroon-600 hover:bg-maroon-500 hover:text-cream-50"
          data-testid="new-chart-button"
        >
          {t(lang, 'newChart')}
        </button>
      </div>

      <div className="grid gap-8 md:grid-cols-2 md:items-start">
        <div className="flex justify-center rounded-xl bg-cream-100 p-4 shadow-inner">
          <KundaliChart lang={lang} chart={chart} />
        </div>
        <div className="space-y-2 rounded-xl border border-gold-500/30 bg-cream-50 p-4">
          <h2 className="font-serif text-lg font-semibold text-maroon-700">{t(lang, 'lagna')}</h2>
          <p className="text-maroon-600" data-testid="lagna-summary">
            {SIGN_NAMES[lang][chart.lagna_sign]} — {chart.lagna_degrees_in_sign.toFixed(2)}°,{' '}
            {chart.lagna_nakshatra} ({chart.lagna_pada})
          </p>
        </div>
      </div>

      <section>
        <TransitsCard lang={lang} transits={transits} />
      </section>

      <section>
        <h2 className="mb-3 font-serif text-xl font-semibold text-maroon-700">{t(lang, 'planets')}</h2>
        <PlanetTable lang={lang} chart={chart} />
      </section>

      <section>
        <DashaTimeline lang={lang} dashaTimeline={dashaTimeline} currentDasha={currentDasha} />
      </section>

      <section>
        <InterpretationPanel lang={lang} shareId={shareId} />
      </section>
    </div>
  )
}
