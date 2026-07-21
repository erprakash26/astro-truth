import { FOOTER_DISCLAIMER } from '../i18n'

export default function Footer({ lang }) {
  // "Other" custom languages have no hand-translated disclaimer, so fall
  // back to English -- same fallback UI chrome already uses when a custom
  // language's translation isn't available.
  const disclaimer = FOOTER_DISCLAIMER[lang] ?? FOOTER_DISCLAIMER.en

  return (
    <footer className="mt-auto border-t border-gold-500/30 bg-cream-100 px-4 py-4 text-center">
      <p className="mx-auto max-w-2xl text-xs leading-relaxed text-maroon-500" data-testid="footer-disclaimer">
        {disclaimer}
      </p>
    </footer>
  )
}
