export const LANGUAGES = {
  en: 'English',
  ne: 'नेपाली',
  other: 'Other',
}

// Basic sanity check for a free-typed language name: non-empty, letters in
// any script plus spaces/hyphens/apostrophes only (so "Tamil", "Français",
// "தமிழ்" all pass), within a reasonable length. Anything else — empty,
// numbers, symbols — is nonsense we won't forward to the LLM; callers
// should fall back to English when this returns null.
const CUSTOM_LANGUAGE_PATTERN = /^[\p{L}\s'-]{2,40}$/u

export function validateCustomLanguage(input) {
  const trimmed = (input ?? '').trim()
  if (!CUSTOM_LANGUAGE_PATTERN.test(trimmed)) return null
  return trimmed
}

const DICT = {
  en: {
    appName: 'AstroTruth',
    tagline: 'Your Vedic birth chart, precisely computed.',
    name: 'Name (optional)',
    namePlaceholder: 'e.g. Priya',
    calendar: 'Calendar',
    ad: 'AD',
    bs: 'BS',
    date: 'Date',
    year: 'Year',
    month: 'Month',
    day: 'Day',
    time: 'Time',
    birthPlace: 'Birth place',
    birthPlacePlaceholder: 'Search for a city…',
    submit: 'Generate chart',
    submitting: 'Computing chart…',
    newChart: 'New chart',
    lagna: 'Lagna',
    chart: 'Kundali chart',
    planets: 'Planets',
    graha: 'Graha',
    sign: 'Sign',
    degree: 'Degree',
    nakshatraPada: 'Nakshatra / Pada',
    house: 'House',
    dignity: 'Dignity',
    exalted: 'Exalted',
    ownSign: 'Own sign',
    debilitated: 'Debilitated',
    moolatrikona: 'Moolatrikona',
    dashaTimeline: 'Vimshottari dasha timeline',
    mahadasha: 'Mahadasha',
    antardasha: 'Antardasha',
    current: 'Current',
    errorRequired: 'Please fill in all fields.',
    errorCity: 'Please choose a city from the list.',
    errorGeneric: 'Something went wrong. Please try again.',
    noCityResults: 'No matching cities',
    interpret: 'Interpret my chart',
    interpreting: 'Interpreting…',
    mockBadge: 'mock',
    interpretError: 'Could not generate an interpretation. Please try again.',
    transits: 'Current transits',
    fromLagna: 'from your Lagna',
    fromMoon: 'from your Moon',
    nextIngress: 'Next sign change',
    downloadPdf: 'Download PDF',
    downloadingPdf: 'Generating PDF…',
    downloadError: 'Could not generate the PDF. Please try again.',
    langOther: 'Other',
    langOtherPlaceholder: 'Type a language, e.g. Spanish',
    langOtherInvalid: 'Could not recognize that language — falling back to English.',
    chatTitle: 'Ask about your chart',
    chatMockNote: 'Mock mode only understands a few question patterns — try one of the examples below. Full conversational chat requires live mode.',
    chatPlaceholder: 'Ask a question about your chart…',
    chatPlaceholderMock: 'Try: "What sign is my Moon in?" / "Any yogas?" / "What\'s my dasha on 2030-01-01?"',
    chatSend: 'Send',
    chatSending: 'Sending…',
    chatError: 'Could not get a reply. Please try again.',
  },
  ne: {
    appName: 'AstroTruth',
    tagline: 'तपाईंको ज्योतिष जन्मकुण्डली, सटीक गणना सहित।',
    name: 'नाम (वैकल्पिक)',
    namePlaceholder: 'जस्तै: प्रिया',
    calendar: 'पात्रो',
    ad: 'ईस्वी',
    bs: 'विक्रम सम्वत',
    date: 'मिति',
    year: 'वर्ष',
    month: 'महिना',
    day: 'गते',
    time: 'समय',
    birthPlace: 'जन्मस्थान',
    birthPlacePlaceholder: 'शहर खोज्नुहोस्…',
    submit: 'कुण्डली बनाउनुहोस्',
    submitting: 'गणना गर्दै…',
    newChart: 'नयाँ कुण्डली',
    lagna: 'लग्न',
    chart: 'कुण्डली चक्र',
    planets: 'ग्रहहरू',
    graha: 'ग्रह',
    sign: 'राशि',
    degree: 'डिग्री',
    nakshatraPada: 'नक्षत्र / पाद',
    house: 'भाव',
    dignity: 'स्थिति',
    exalted: 'उच्च',
    ownSign: 'स्वराशि',
    debilitated: 'नीच',
    moolatrikona: 'मूलत्रिकोण',
    dashaTimeline: 'विंशोत्तरी दशा समयरेखा',
    mahadasha: 'महादशा',
    antardasha: 'अन्तर्दशा',
    current: 'हालको',
    errorRequired: 'कृपया सबै फिल्डहरू भर्नुहोस्।',
    errorCity: 'कृपया सूचीबाट शहर छान्नुहोस्।',
    errorGeneric: 'केही समस्या भयो। फेरि प्रयास गर्नुहोस्।',
    noCityResults: 'कुनै शहर फेला परेन',
    interpret: 'मेरो कुण्डली व्याख्या गर्नुहोस्',
    interpreting: 'व्याख्या गर्दै…',
    mockBadge: 'नमूना',
    interpretError: 'व्याख्या तयार गर्न सकिएन। फेरि प्रयास गर्नुहोस्।',
    transits: 'हालको गोचर',
    fromLagna: 'लग्नबाट',
    fromMoon: 'चन्द्रमाबाट',
    nextIngress: 'अर्को राशि परिवर्तन',
    downloadPdf: 'PDF डाउनलोड गर्नुहोस्',
    downloadingPdf: 'PDF तयार गर्दै…',
    downloadError: 'PDF तयार गर्न सकिएन। फेरि प्रयास गर्नुहोस्।',
    langOther: 'Other',
    langOtherPlaceholder: 'Type a language, e.g. Spanish',
    langOtherInvalid: 'Could not recognize that language — falling back to English.',
    chatTitle: 'आफ्नो कुण्डलीबारे सोध्नुहोस्',
    // The mock-mode pattern matcher only understands English question
    // shapes, so its note and examples stay English regardless of UI
    // language — asking in Nepali wouldn't match the patterns anyway.
    chatMockNote: 'Mock mode only understands a few question patterns — try one of the examples below. Full conversational chat requires live mode.',
    chatPlaceholder: 'Ask a question about your chart…',
    chatPlaceholderMock: 'Try: "What sign is my Moon in?" / "Any yogas?" / "What\'s my dasha on 2030-01-01?"',
    chatSend: 'पठाउनुहोस्',
    chatSending: 'पठाउँदै…',
    chatError: 'जवाफ प्राप्त गर्न सकिएन। फेरि प्रयास गर्नुहोस्।',
  },
}

export function t(lang, key) {
  return DICT[lang]?.[key] ?? DICT.en[key] ?? key
}

// Named heading ("Priya's Kundali Chart"), falling back to the generic
// localized title when no name was given.
export function chartTitle(lang, name) {
  if (!name) return t(lang, 'chart')
  return lang === 'ne' ? `${name} को कुण्डली चक्र` : `${name}'s Kundali Chart`
}

// Nepali month names (Baishakh..Chaitra), used for BS date entry.
export const BS_MONTHS = {
  en: [
    'Baishakh', 'Jestha', 'Ashadh', 'Shrawan', 'Bhadra', 'Ashwin',
    'Kartik', 'Mangsir', 'Poush', 'Magh', 'Falgun', 'Chaitra',
  ],
  ne: [
    'बैशाख', 'जेठ', 'असार', 'श्रावण', 'भदौ', 'आश्विन',
    'कार्तिक', 'मंसिर', 'पुष', 'माघ', 'फाल्गुन', 'चैत',
  ],
}

export const PLANET_ABBR = {
  Sun: 'Su', Moon: 'Mo', Mars: 'Ma', Mercury: 'Me',
  Jupiter: 'Ju', Venus: 'Ve', Saturn: 'Sa', Rahu: 'Ra', Ketu: 'Ke',
}

export const TRANSIT_PLANET_NAMES = {
  en: { Jupiter: 'Jupiter', Saturn: 'Saturn' },
  ne: { Jupiter: 'बृहस्पति', Saturn: 'शनि' },
}

// House ordinals 1..12, indexed [house - 1].
export const HOUSE_ORDINALS = {
  en: ['1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th', '9th', '10th', '11th', '12th'],
  ne: [
    'पहिलो', 'दोस्रो', 'तेस्रो', 'चौथो', 'पाँचौं', 'छैटौं',
    'सातौं', 'आठौं', 'नवौं', 'दशौं', 'एघारौं', 'बाह्रौं',
  ],
}

// Always shown together, regardless of the selected UI language — the
// footer disclaimer is bilingual on every page, not language-toggled.
export const FOOTER_DISCLAIMER = {
  en: 'Astrology is a traditional belief system, not a science. It describes tendencies, not certainties.',
  ne: 'ज्योतिषशास्त्र एक परम्परागत विश्वास प्रणाली हो, विज्ञान होइन। यसले निश्चितता होइन, प्रवृत्तिहरू मात्र वर्णन गर्छ।',
}

export const SIGN_NAMES = {
  en: [
    'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
    'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces',
  ],
  ne: [
    'मेष', 'वृष', 'मिथुन', 'कर्कट', 'सिंह', 'कन्या',
    'तुला', 'वृश्चिक', 'धनु', 'मकर', 'कुम्भ', 'मीन',
  ],
}
