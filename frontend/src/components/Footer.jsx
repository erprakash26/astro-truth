import { FOOTER_BETA_NOTICE, FOOTER_DISCLAIMER } from '../i18n'

export default function Footer({ lang }) {
  // "Other" custom languages have no hand-translated disclaimer/notice, so
  // fall back to English -- same fallback UI chrome already uses when a
  // custom language's translation isn't available.
  const disclaimer = FOOTER_DISCLAIMER[lang] ?? FOOTER_DISCLAIMER.en
  const betaNotice = FOOTER_BETA_NOTICE[lang] ?? FOOTER_BETA_NOTICE.en
  const year = new Date().getFullYear()

  return (
    <footer className="mt-auto border-t border-gold-500/30 bg-cream-100 px-4 py-4 text-center">
      <p className="mx-auto max-w-2xl text-xs leading-relaxed text-maroon-500" data-testid="footer-disclaimer">
        {disclaimer}
      </p>
      <p className="mt-1 text-[10px] text-maroon-400/70" data-testid="footer-copyright">
        © {year} AstroTruth.
      </p>
      <p className="mx-auto mt-1 max-w-2xl text-[11px] text-maroon-500/60" data-testid="footer-beta-notice">
        {betaNotice}
      </p>
    </footer>
  )
}
