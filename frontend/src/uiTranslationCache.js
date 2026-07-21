// Caches successful UI-chrome translations (POST /api/translate-ui results)
// keyed by language name, so switching back to a previously-used "Other"
// language doesn't re-call the API -- in memory for this tab, and in
// localStorage so a previously-translated language survives a reload.
//
// Only successful {key: string} translation maps are cached here, never the
// mock-mode "unavailable" result -- if the server is later run in real mode,
// a language that was unavailable before should still get a real shot at
// translation rather than staying stuck on a stale "unavailable" verdict.

const STORAGE_PREFIX = 'astrotruth:ui-translation:'
const memoryCache = new Map()

export function getCachedUITranslation(language) {
  if (memoryCache.has(language)) return memoryCache.get(language)

  try {
    const raw = localStorage.getItem(STORAGE_PREFIX + language)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    memoryCache.set(language, parsed)
    return parsed
  } catch {
    return null
  }
}

export function setCachedUITranslation(language, translations) {
  memoryCache.set(language, translations)
  try {
    localStorage.setItem(STORAGE_PREFIX + language, JSON.stringify(translations))
  } catch {
    // localStorage unavailable or full -- the in-memory cache still serves
    // this tab for the rest of the session.
  }
}
