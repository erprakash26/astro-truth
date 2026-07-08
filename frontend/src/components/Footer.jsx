import { FOOTER_DISCLAIMER } from '../i18n'

export default function Footer() {
  return (
    <footer className="mt-auto border-t border-gold-500/30 bg-cream-100 px-4 py-4 text-center">
      <p className="mx-auto max-w-2xl text-xs leading-relaxed text-maroon-500" data-testid="footer-disclaimer">
        {FOOTER_DISCLAIMER.en}
        <br />
        {FOOTER_DISCLAIMER.ne}
      </p>
    </footer>
  )
}
