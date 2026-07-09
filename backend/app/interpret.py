"""LLM interpretation layer for AstroTruth charts.

The LLM never computes astrology — it only narrates a pre-computed chart
JSON produced by app.engine / app.dasha. Two modes, selected by the
USE_MOCK_LLM env var (default "true"):

- Mock mode (default): returns a canned, realistic interpretation for the
  reference chart, streamed word-by-word with a small artificial delay.
  Never mistaken for a real call — always logs "MOCK MODE" to the console.
- Real mode (USE_MOCK_LLM=false): streams a live interpretation from the
  Anthropic API. Requires ANTHROPIC_API_KEY in the environment.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Iterator

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 2048

LANGUAGE_NAMES = {
    "en": "English",
    "ne": "Nepali (Devanagari script)",
}

DISCLAIMER = (
    "Astrology is a traditional belief system, not a science. It describes "
    "tendencies, not certainties."
)
DISCLAIMER_NE = (
    "ज्योतिषशास्त्र एक परम्परागत विश्वास प्रणाली हो, विज्ञान होइन। यसले "
    "निश्चितता होइन, प्रवृत्तिहरू मात्र वर्णन गर्छ।"
)

PLANET_ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]


def is_mock_mode() -> bool:
    """True unless USE_MOCK_LLM is explicitly set to a falsy string."""
    return os.environ.get("USE_MOCK_LLM", "true").strip().lower() != "false"


def _system_prompt(language: str) -> str:
    language_name = LANGUAGE_NAMES.get(language, "English")
    return f"""You are a Vedic astrology interpreter for AstroTruth.

You are given a pre-computed Vedic chart as JSON. You MUST NOT compute,
assume, or invent any planetary position, dignity, or dasha date. Every
astrological claim you make must reference only the data provided in the
JSON — do not recompute or second-guess it, and do not introduce placements,
yogas, or dates that are not directly derivable from the given fields.

Structure your interpretation into these sections, in this order, each
under its own heading written as "## <title>":

1. Lagna (Ascendant) character — describe the personality signature of the
   lagna sign and any planets placed in house 1.
2. Notable yogas — mention a yoga ONLY if it is directly derivable from the
   JSON. Two you may check for:
   - Gajakesari Yoga: Moon and Jupiter occupy the same house.
   - Budhaditya Yoga: Sun and Mercury occupy the same house (conjunct).
   If neither condition holds, say plainly that no such yoga is present in
   this chart rather than inventing one.
3. Current dasha meaning — explain what the current mahadasha and
   antardasha lords (given in the JSON) traditionally signify, and how they
   interact with the lagna and planets already described.
4. Strengths and cautions — summarize exalted/own-sign/moolatrikona
   planets as strengths and debilitated planets as cautions, citing only
   the dignity flags present in the JSON.
5. Current transits (gochara) — the JSON includes a "transits" object with
   Jupiter's and Saturn's present sign, house from the natal lagna, house
   from the natal Moon, and next sign-ingress date. Describe what these two
   transits classically signify given those exact houses — do not invent a
   transit house, sign, or ingress date beyond what "transits" states.

Tone: warm, direct, and honest — this is a real person reading about their
own chart. Do not hedge excessively, but do not overstate certainty either.

Never give medical, legal, or financial directives or advice, even if the
chart data seems to invite it (e.g. a challenging placement in a health- or
wealth-related house). Describe traditional significations only.

End every response with this disclaimer, translated naturally into the
response language: "{DISCLAIMER}"

Write your entire response in {language_name}.""".strip()


def _user_prompt(chart_json: dict) -> str:
    return (
        "Here is the pre-computed chart JSON. Interpret it following the "
        "structure and constraints in your instructions.\n\n"
        f"{json.dumps(chart_json, indent=2, default=str)}"
    )


def _require_api_key() -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set; cannot call the Anthropic API "
            "in real mode (USE_MOCK_LLM=false)."
        )
    return api_key


def _stream_real(chart_json: dict, language: str) -> Iterator[str]:
    import anthropic

    client = anthropic.Anthropic(api_key=_require_api_key())

    with client.messages.stream(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=_system_prompt(language),
        messages=[{"role": "user", "content": _user_prompt(chart_json)}],
    ) as stream:
        yield from stream.text_stream


def _real_full_text(chart_json: dict, language: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=_require_api_key())

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=_system_prompt(language),
        messages=[{"role": "user", "content": _user_prompt(chart_json)}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


_MOCK_TEXT = {
    "en": (
        "## Lagna (Ascendant) character\n\n"
        "Your lagna is Aries, rising at 0.16° in Ashwini nakshatra. It's a "
        "fitting start for a chart ruled by fast-moving Mars: people with "
        "Aries rising tend to lead with initiative, quick to act and quick "
        "to decide, most comfortable when they're the one setting the pace. "
        "Jupiter and Saturn also sit in this first house, and that "
        "combination is worth noting. Jupiter gives the drive a sense of "
        "purpose and an instinct toward growth and generosity, while Saturn "
        "asks for patience and structure before that instinct is allowed to "
        "run.\n\n"
        "## Notable yogas\n\n"
        "Sun and Mercury are conjunct in your ninth house, Sagittarius, "
        "forming Budhaditya Yoga. This pairing traditionally sharpens "
        "intellect and communication and brings a philosophical or "
        "scholarly bent, especially in the ninth house of belief, higher "
        "learning, and long journeys. No Gajakesari Yoga is present in this "
        "chart. Moon sits in the seventh house, Libra, and Jupiter in the "
        "first, Aries, so they aren't sharing a house, and that particular "
        "combination doesn't apply here.\n\n"
        "## Current dasha meaning\n\n"
        "You're currently running your Saturn mahadasha, in a Saturn–Venus "
        "antardasha. Saturn's period is traditionally a time of "
        "consolidation. It rewards patience, discipline, and long-term "
        "thinking, and it can feel slow if you're hoping for quick wins. "
        "Saturn sits debilitated in your own lagna, Aries, so this "
        "mahadasha carries an extra note of self-discipline: the lesson "
        "isn't about external restriction so much as learning to pace your "
        "naturally quick Aries instincts. The Venus antardasha running "
        "within it softens this. Venus periods within a Saturn mahadasha "
        "often bring attention to relationships, comfort, and shared "
        "resources, tempering Saturn's austerity with some warmth and "
        "pleasure.\n\n"
        "## Strengths and cautions\n\n"
        "Your clearest strength is the Sun–Mercury conjunction in the ninth "
        "house. Budhaditya Yoga generally supports confident, articulate "
        "thinking and a natural pull toward teaching, writing, or "
        "philosophical inquiry. The main caution in this chart is Saturn's "
        "debilitation in Aries. Traditionally this suggests some friction "
        "between your instinct to act immediately and Saturn's demand to "
        "slow down and do things properly. It isn't a weakness so much as "
        "a standing invitation to build patience deliberately, rather than "
        "have it forced on you.\n\n"
        "## Current transits (gochara)\n\n"
        "Jupiter is currently transiting Cancer, your 4th house from lagna "
        "and 10th house from your natal Moon. That's a classic combination "
        "for attention on home, inner security, and career or public "
        "standing, often at the same time. Saturn is transiting Pisces, "
        "your 12th house from lagna and 6th house from your natal Moon. "
        "The 12th-from-lagna leg often asks for rest, withdrawal, or "
        "letting go, while the 6th-from-Moon leg traditionally favors "
        "discipline around health, routine, and clearing obligations. Both "
        "transits will move on into the next sign in due course; see the "
        "exact ingress dates in your chart data.\n\n"
        f"{DISCLAIMER}"
    ),
    "ne": (
        "## लग्न (उदय) चरित्र\n\n"
        "तपाईंको लग्न मेष राशि हो, ०.१६° अंशमा अश्विनी नक्षत्रसँग "
        "उदाउँदै। छिटो निर्णय लिने र पहल गर्ने मंगल ग्रहद्वारा शासित "
        "राशिको लागि यो उपयुक्त सुरुवात हो। मेष लग्न भएका व्यक्तिहरू "
        "सामान्यतया नेतृत्व लिन रुचाउँछन्, छिटो कार्य गर्छन्, र आफैं "
        "गति निर्धारण गर्दा सबैभन्दा सहज महसुस गर्छन्। यही पहिलो "
        "भावमा बृहस्पति र शनि पनि विराजमान छन्, जुन ध्यान दिनुपर्ने "
        "संयोजन हो। बृहस्पतिले यहाँ उद्देश्यको भावना र वृद्धिप्रतिको "
        "झुकाव थप्छ, जबकि शनिले त्यो प्रवृत्तिलाई अघि बढ्नुअघि धैर्य "
        "र संरचना माग्छ।\n\n"
        "## उल्लेखनीय योग\n\n"
        "सूर्य र बुध तपाईंको नवौं भाव, धनु राशिमा युति भएका छन्, "
        "जसले बुधादित्य योग बनाउँछ। यो संयोजनले परम्परागत रूपमा "
        "बुद्धि र संचार क्षमतालाई तीक्ष्ण बनाउँछ र दार्शनिक वा "
        "विद्वत्तापूर्ण झुकाउ ल्याउँछ, विशेष गरी यो विश्वास, उच्च "
        "शिक्षा र लामो यात्राको नवौं भावमा परेकाले। यस कुण्डलीमा "
        "गजकेसरी योग छैन। चन्द्रमा सातौं भाव अर्थात् तुलामा छन् र "
        "बृहस्पति पहिलो भाव अर्थात् मेषमा छन्, त्यसैले तिनीहरू एउटै "
        "भावमा छैनन्, र त्यो विशेष संयोजन यहाँ लागू हुँदैन।\n\n"
        "## हालको दशा\n\n"
        "हाल तपाईं शनि महादशामा हुनुहुन्छ, शनि–शुक्र अन्तर्दशाभित्र। "
        "शनिको अवधि परम्परागत रूपमा सुदृढीकरणको समय हो। यसले धैर्य, "
        "अनुशासन र दीर्घकालीन सोचलाई पुरस्कृत गर्छ, र छिटो नतिजा "
        "खोज्नेहरूका लागि यो ढिलो महसुस हुन सक्छ। शनि तपाईंकै लग्न "
        "मेषमा नीच भएकाले, यो महादशाले आत्म-अनुशासनको थप पाठ बोकेको "
        "छ। पाठ बाहिरी प्रतिबन्धको भन्दा बढी तपाईंको स्वाभाविक छिटो "
        "मेष प्रवृत्तिलाई गति दिन सिक्नुमा छ। यसभित्र चलिरहेको शुक्र "
        "अन्तर्दशाले यसलाई नरम बनाउँछ। शनि महादशाभित्रको शुक्र "
        "अवधिले प्रायः सम्बन्ध, आराम र साझा स्रोतहरूमा ध्यान "
        "ल्याउँछ, र शनिको कठोरतालाई केही न्यानोपन र आनन्दले सन्तुलन "
        "गर्छ।\n\n"
        "## बलहरू र सावधानीहरू\n\n"
        "तपाईंको सबैभन्दा स्पष्ट बल नवौं भावको सूर्य–बुध युति हो। "
        "बुधादित्य योगले सामान्यतया आत्मविश्वासी, स्पष्ट सोच र "
        "शिक्षण, लेखन वा दार्शनिक अन्वेषणतर्फको स्वाभाविक झुकावलाई "
        "समर्थन गर्छ। यस कुण्डलीको मुख्य सावधानी शनिको मेषमा नीच "
        "अवस्था हो। परम्परागत रूपमा यसले तत्काल कार्य गर्ने मेष "
        "प्रवृत्ति र सही ढंगले ढिलो गर्नुपर्ने शनिको माग बीच केही "
        "घर्षण देखाउँछ। यो कमजोरी भन्दा बढी धैर्यलाई जबरजस्ती "
        "थोपरिनुको सट्टा सचेत रूपमा निर्माण गर्ने निम्तो हो।\n\n"
        "## हालको गोचर (ट्रान्जिट)\n\n"
        "बृहस्पति हाल कर्कट राशिमा गोचर गर्दैछ, जुन तपाईंको लग्नबाट "
        "चौथो र चन्द्रमाबाट दशौं भाव हो। यसले घर, आन्तरिक सुरक्षा र "
        "करियर वा सार्वजनिक प्रतिष्ठामा एकैसाथ ध्यान तान्ने संयोजन "
        "बनाउँछ। शनि हाल मीन राशिमा गोचर गर्दैछ, जुन लग्नबाट बाह्रौं "
        "र चन्द्रमाबाट छैटौं भाव हो। लग्नबाटको बाह्रौं पाटोले प्रायः "
        "विश्राम वा त्याग्ने कुरा माग्छ, जबकि चन्द्रमाबाटको छैटौं "
        "पाटोले परम्परागत रूपमा स्वास्थ्य, दिनचर्या र दायित्व "
        "मिलाउने अनुशासन ल्याउँछ। दुवै ग्रह समयक्रममा अर्को राशिमा "
        "सर्नेछन्; ठ्याक्कै मिति तपाईंको कुण्डली डेटामा हेर्नुहोस्।"
        "\n\n"
        "ज्योतिषशास्त्र एक परम्परागत विश्वास प्रणाली हो, विज्ञान "
        "होइन। यसले निश्चितता होइन, प्रवृत्तिहरू मात्र वर्णन गर्छ।"
    ),
}


def _is_reference_chart(chart_json: dict) -> bool:
    """Fingerprint match for the Stage-1 reference chart (AD 2000-01-01
    12:00, London): Aries lagna near 0.16 deg and Libra Moon near 19.47 deg.
    Sign plus approximate degree together make a coincidental match on any
    other real chart astronomically implausible."""
    chart = chart_json.get("chart", {})
    moon = chart.get("planets", {}).get("Moon", {})
    return (
        chart.get("lagna_sign_name") == "Aries"
        and abs(chart.get("lagna_degrees_in_sign", -999) - 0.16) < 0.05
        and moon.get("sign_name") == "Libra"
        and abs(moon.get("degrees_in_sign", -999) - 19.47) < 0.1
    )


# --- Rule-based, chart-grounded generator for any non-reference chart -----
#
# The hand-written _MOCK_TEXT above is a single polished example authored
# for the Stage-1 reference chart only. For any other chart it would state
# facts (signs, houses, yogas) that don't match that chart's own data, which
# defeats the point of a "grounded" mock. This generator instead builds the
# same 5-section structure entirely from the given chart_json's own fields,
# so mock mode stays factually grounded for arbitrary input. It is still a
# deterministic template, not an LLM call — see backend/evals/EVALS.md.

HEADINGS = {
    "en": {
        "lagna": "Lagna (Ascendant) character",
        "yogas": "Notable yogas",
        "dasha": "Current dasha meaning",
        "strengths": "Strengths and cautions",
        "transits": "Current transits (gochara)",
    },
    "ne": {
        "lagna": "लग्न (उदय) चरित्र",
        "yogas": "उल्लेखनीय योग",
        "dasha": "हालको दशा",
        "strengths": "बलहरू र सावधानीहरू",
        "transits": "हालको गोचर (ट्रान्जिट)",
    },
}

ORDINALS = {
    "en": ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th", "10th", "11th", "12th"],
    "ne": [
        "पहिलो", "दोस्रो", "तेस्रो", "चौथो", "पाँचौं", "छैटौं",
        "सातौं", "आठौं", "नवौं", "दशौं", "एघारौं", "बाह्रौं",
    ],
}

SIGN_NAME_NE = {
    "Aries": "मेष", "Taurus": "वृष", "Gemini": "मिथुन", "Cancer": "कर्कट",
    "Leo": "सिंह", "Virgo": "कन्या", "Libra": "तुला", "Scorpio": "वृश्चिक",
    "Sagittarius": "धनु", "Capricorn": "मकर", "Aquarius": "कुम्भ", "Pisces": "मीन",
}

PLANET_NAME_NE = {
    "Sun": "सूर्य", "Moon": "चन्द्रमा", "Mars": "मंगल", "Mercury": "बुध",
    "Jupiter": "बृहस्पति", "Venus": "शुक्र", "Saturn": "शनि", "Rahu": "राहु", "Ketu": "केतु",
}

SIGN_TRAITS = {
    "en": {
        "Aries": "a placement associated with initiative, quick decisions, and a preference for setting the pace, ruled by fast-moving Mars",
        "Taurus": "a placement associated with steadiness, patience, and a preference for comfort and security, ruled by Venus",
        "Gemini": "a placement associated with curiosity, adaptability, and quick communication, ruled by Mercury",
        "Cancer": "a placement associated with emotional depth, nurturing instincts, and a strong attachment to home, ruled by the Moon",
        "Leo": "a placement associated with confidence, warmth, and a natural pull toward leadership, ruled by the Sun",
        "Virgo": "a placement associated with precision, practicality, and a discerning eye for detail, ruled by Mercury",
        "Libra": "a placement associated with balance, diplomacy, and a strong sense of fairness, ruled by Venus",
        "Scorpio": "a placement associated with intensity, depth, and a talent for uncovering what's hidden, ruled by Mars",
        "Sagittarius": "a placement associated with optimism, a love of learning, and a philosophical outlook, ruled by Jupiter",
        "Capricorn": "a placement associated with discipline, ambition, and a patient, long-term approach, ruled by Saturn",
        "Aquarius": "a placement associated with independence, original thinking, and a focus on community, ruled by Saturn",
        "Pisces": "a placement associated with compassion, imagination, and a spiritual or intuitive bent, ruled by Jupiter",
    },
    "ne": {
        "Aries": "छिटो निर्णय लिने, पहल गर्ने र आफैं गति निर्धारण गर्ने स्वभावको प्रतीक",
        "Taurus": "स्थिरता, धैर्य र आराम तथा सुरक्षाप्रतिको रुचिको प्रतीक",
        "Gemini": "जिज्ञासा, अनुकूलनशीलता र छिटो संचारको प्रतीक",
        "Cancer": "भावनात्मक गहिराइ, स्नेहपूर्ण स्वभाव र घरप्रतिको लगावको प्रतीक",
        "Leo": "आत्मविश्वास, न्यानोपन र नेतृत्वप्रतिको स्वाभाविक झुकावको प्रतीक",
        "Virgo": "सूक्ष्मता, व्यावहारिकता र विवरणमा ध्यान दिने बानीको प्रतीक",
        "Libra": "सन्तुलन, कूटनीति र निष्पक्षताको भावनाको प्रतीक",
        "Scorpio": "गहनता, गहिराइ र लुकेको कुरा पत्ता लगाउने क्षमताको प्रतीक",
        "Sagittarius": "आशावाद, ज्ञानप्रतिको रुचि र दार्शनिक दृष्टिकोणको प्रतीक",
        "Capricorn": "अनुशासन, महत्वाकांक्षा र धैर्यपूर्ण दीर्घकालीन दृष्टिकोणको प्रतीक",
        "Aquarius": "स्वतन्त्रता, मौलिक सोच र सामुदायिक चासोको प्रतीक",
        "Pisces": "करुणा, कल्पनाशीलता र आध्यात्मिक वा सहज-ज्ञानको प्रतीक",
    },
}

# Ruling planet per sign, for the Nepali lagna sentence's trailing clause
# ("...jasalāī {planet}le śāsan garcha"). English keeps the ruling planet
# inline within SIGN_TRAITS['en'] instead, since that reads naturally there.
SIGN_RULER_NE = {
    "Aries": "मंगल", "Taurus": "शुक्र", "Gemini": "बुध", "Cancer": "चन्द्रमा",
    "Leo": "सूर्य", "Virgo": "बुध", "Libra": "शुक्र", "Scorpio": "मंगल",
    "Sagittarius": "बृहस्पति", "Capricorn": "शनि", "Aquarius": "शनि", "Pisces": "बृहस्पति",
}

HOUSE_THEMES = {
    "en": {
        1: "self, appearance, and new beginnings", 2: "finances, family, and speech",
        3: "courage, siblings, and short journeys", 4: "home, comfort, and inner peace",
        5: "creativity, children, and intelligence", 6: "health, routine, and obstacles",
        7: "partnerships and close relationships", 8: "transformation, shared resources, and the unknown",
        9: "belief, higher learning, and long journeys", 10: "career and public standing",
        11: "gains, aspirations, and social networks", 12: "rest, withdrawal, and letting go",
    },
    "ne": {
        1: "आफू, रूपरंग र नयाँ सुरुवात", 2: "धन, परिवार र वाणी",
        3: "साहस, दाजुभाइ-दिदीबहिनी र छोटो यात्रा", 4: "घर, आराम र आन्तरिक शान्ति",
        5: "सिर्जनशीलता, सन्तान र बुद्धि", 6: "स्वास्थ्य, दिनचर्या र बाधा",
        7: "साझेदारी र नजिकका सम्बन्ध", 8: "रूपान्तरण, साझा स्रोत र अज्ञात कुरा",
        9: "विश्वास, उच्च शिक्षा र लामो यात्रा", 10: "करियर र सार्वजनिक प्रतिष्ठा",
        11: "लाभ, आकांक्षा र सामाजिक सञ्जाल", 12: "विश्राम, त्याग र छोड्ने कुरा",
    },
}

PLANET_DASHA_MEANING = {
    "en": {
        "Sun": "authority, self-expression, and public recognition",
        "Moon": "emotional life, home, and the people closest to you",
        "Mars": "courage, competition, and decisive action",
        "Mercury": "communication, learning, and business dealings",
        "Jupiter": "growth, wisdom, and good fortune",
        "Venus": "relationships, comfort, and creative or material pleasures",
        "Saturn": "patience and discipline, though it can feel slow if you're hoping for quick wins",
        "Rahu": "ambition, unconventional opportunities, and a restless drive to acquire more",
        "Ketu": "detachment, introspection, and spiritual matters",
    },
    "ne": {
        "Sun": "अख्तियार, आत्म-अभिव्यक्ति र सार्वजनिक पहिचान",
        "Moon": "भावनात्मक जीवन, घर र नजिकका मानिसहरू",
        "Mars": "साहस, प्रतिस्पर्धा र निर्णायक कार्य",
        "Mercury": "संचार, सिकाइ र व्यापारिक कारोबार",
        "Jupiter": "वृद्धि, ज्ञान र सौभाग्य",
        "Venus": "सम्बन्ध, आराम र रचनात्मक वा भौतिक आनन्द",
        "Saturn": "धैर्य र अनुशासन, यद्यपि छिटो नतिजा खोज्नेका लागि यो ढिलो महसुस हुन सक्छ",
        "Rahu": "महत्वाकांक्षा, अपरम्परागत अवसर र थप हासिल गर्ने बेचैन चाहना",
        "Ketu": "वैराग्य, आत्मनिरीक्षण र आध्यात्मिक विषय",
    },
}


def _ordinal(language: str, house: int) -> str:
    ordinals = ORDINALS.get(language, ORDINALS["en"])
    return ordinals[house - 1] if 1 <= house <= 12 else str(house)


def _planet_label(name: str, language: str) -> str:
    return PLANET_NAME_NE.get(name, name) if language == "ne" else name


def _sign_label(sign_name: str, language: str) -> str:
    return SIGN_NAME_NE.get(sign_name, sign_name) if language == "ne" else sign_name


def _join_and(items: list[str], language: str) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} र {items[1]}" if language == "ne" else f"{items[0]} and {items[1]}"
    head = ", ".join(items[:-1])
    return f"{head} र {items[-1]}" if language == "ne" else f"{head}, and {items[-1]}"


def _section_lagna(chart: dict, language: str) -> str:
    lagna_sign = chart["lagna_sign_name"]
    degrees = chart["lagna_degrees_in_sign"]
    nakshatra = chart["lagna_nakshatra"]
    trait = SIGN_TRAITS.get(language, SIGN_TRAITS["en"]).get(lagna_sign, SIGN_TRAITS["en"][lagna_sign])
    house1 = [name for name in PLANET_ORDER if chart["planets"][name]["house"] == 1]
    localized_house1 = [_planet_label(name, language) for name in house1]

    if language == "ne":
        sign_label = _sign_label(lagna_sign, language)
        ruler = SIGN_RULER_NE.get(lagna_sign, "")
        text = f"तपाईंको लग्न {sign_label} राशि हो, {degrees:.2f}° अंशमा {nakshatra} नक्षत्रसँग उदाउँदै। यो {trait} हो, जसलाई {ruler}ले शासन गर्छ।"
        if localized_house1:
            joined = _join_and(localized_house1, language)
            text += f" यही पहिलो भावमा {joined} पनि विराजमान छन्, जुन ध्यान दिनुपर्ने कुरा हो।"
        else:
            text += " यस पहिलो भावमा अरू कुनै ग्रह छैनन्, त्यसैले लग्नकै आफ्नै गुण मुख्य रूपमा देखिन्छ।"
        return text

    text = f"Your lagna is {lagna_sign}, rising at {degrees:.2f}° in {nakshatra} nakshatra. This is {trait}."
    if localized_house1:
        joined = _join_and(localized_house1, language)
        verb = "sits" if len(localized_house1) == 1 else "sit"
        text += f" {joined} also {verb} in this first house, which is worth noting."
    else:
        text += " No other planet sits in this first house, so the lagna's own qualities take center stage."
    return text


def _section_yogas(chart: dict, language: str) -> str:
    planets = chart["planets"]
    moon_house = planets["Moon"]["house"]
    jup_house = planets["Jupiter"]["house"]
    sun_house = planets["Sun"]["house"]
    merc_house = planets["Mercury"]["house"]
    gajakesari = moon_house == jup_house
    budhaditya = sun_house == merc_house

    moon_sign = _sign_label(planets["Moon"]["sign_name"], language)
    jup_sign = _sign_label(planets["Jupiter"]["sign_name"], language)
    sun_sign = _sign_label(planets["Sun"]["sign_name"], language)
    merc_sign = _sign_label(planets["Mercury"]["sign_name"], language)
    moon_ord = _ordinal(language, moon_house)
    jup_ord = _ordinal(language, jup_house)
    sun_ord = _ordinal(language, sun_house)
    merc_ord = _ordinal(language, merc_house)

    if language == "ne":
        if budhaditya and gajakesari:
            return (
                f"यस कुण्डलीमा दुई उल्लेखनीय योग देखिन्छन्। सूर्य र बुध तपाईंको {sun_ord} भाव, {sun_sign} राशिमा "
                f"युति भएका छन्, जसले बुधादित्य योग बनाउँछ, जसले परम्परागत रूपमा बुद्धि र संचार क्षमतालाई तीक्ष्ण "
                f"बनाउँछ। चन्द्रमा र बृहस्पति पनि तपाईंको {moon_ord} भाव, {moon_sign} राशिमा एउटै भावमा छन्, "
                f"जसले गजकेसरी योग बनाउँछ, जुन परम्परागत रूपमा बुद्धिमत्ता, सम्मान र सौभाग्यसँग जोडिन्छ।"
            )
        if budhaditya:
            return (
                f"सूर्य र बुध तपाईंको {sun_ord} भाव, {sun_sign} राशिमा युति भएका छन्, जसले बुधादित्य योग बनाउँछ। "
                f"यो संयोजनले परम्परागत रूपमा बुद्धि र संचार क्षमतालाई तीक्ष्ण बनाउँछ र दार्शनिक वा विद्वत्तापूर्ण "
                f"झुकाउ ल्याउँछ। यस कुण्डलीमा गजकेसरी योग छैन: चन्द्रमा {moon_ord} भाव ({moon_sign}) मा र बृहस्पति "
                f"{jup_ord} भाव ({jup_sign}) मा छन्, त्यसैले तिनीहरू एउटै भावमा छैनन्।"
            )
        if gajakesari:
            return (
                f"चन्द्रमा र बृहस्पति तपाईंको {moon_ord} भाव, {moon_sign} राशिमा एउटै भावमा छन्, जसले गजकेसरी योग "
                f"बनाउँछ, जुन परम्परागत रूपमा बुद्धिमत्ता, धैर्य र सौभाग्यसँग जोडिन्छ। यस कुण्डलीमा बुधादित्य योग "
                f"छैन: सूर्य {sun_ord} भाव ({sun_sign}) मा र बुध {merc_ord} भाव ({merc_sign}) मा छन्, त्यसैले "
                f"तिनीहरू युति भएका छैनन्।"
            )
        return (
            f"यस कुण्डलीमा गजकेसरी योग वा बुधादित्य योग कुनै पनि छैन। चन्द्रमा ({moon_ord} भाव, {moon_sign}) र "
            f"बृहस्पति ({jup_ord} भाव, {jup_sign}) एउटै भावमा छैनन्, र सूर्य ({sun_ord} भाव, {sun_sign}) र बुध "
            f"({merc_ord} भाव, {merc_sign}) पनि युति भएका छैनन्। यो कुण्डलीको स्वाभाविक बनोट मात्र हो, कुनै "
            f"कमजोरी होइन।"
        )

    if budhaditya and gajakesari:
        return (
            f"Two notable yogas stand out in this chart. Sun and Mercury are conjunct in your {sun_ord} house, "
            f"{sun_sign}, forming Budhaditya Yoga, which traditionally sharpens intellect and communication. "
            f"Moon and Jupiter also share your {moon_ord} house, {moon_sign}, forming Gajakesari Yoga, "
            f"traditionally associated with wisdom, respect, and good fortune."
        )
    if budhaditya:
        return (
            f"Sun and Mercury are conjunct in your {sun_ord} house, {sun_sign}, forming Budhaditya Yoga. This "
            f"pairing traditionally sharpens intellect and communication and brings a philosophical or "
            f"scholarly bent. No Gajakesari Yoga is present in this chart: Moon sits in the {moon_ord} house "
            f"({moon_sign}) and Jupiter in the {jup_ord} house ({jup_sign}), so they aren't sharing a house."
        )
    if gajakesari:
        return (
            f"Moon and Jupiter share your {moon_ord} house, {moon_sign}, forming Gajakesari Yoga, traditionally "
            f"associated with wisdom, resilience, and good fortune. No Budhaditya Yoga is present in this "
            f"chart: Sun sits in the {sun_ord} house ({sun_sign}) and Mercury in the {merc_ord} house "
            f"({merc_sign}), so they aren't conjunct."
        )
    return (
        f"Neither Gajakesari Yoga nor Budhaditya Yoga is present in this chart. Moon ({moon_ord} house, "
        f"{moon_sign}) and Jupiter ({jup_ord} house, {jup_sign}) aren't sharing a house, and Sun ({sun_ord} "
        f"house, {sun_sign}) and Mercury ({merc_ord} house, {merc_sign}) aren't conjunct either. That's simply "
        f"the natural shape of this chart, not a shortcoming."
    )


def _section_dasha(chart: dict, current_dasha: dict | None, language: str) -> str:
    themes = PLANET_DASHA_MEANING.get(language, PLANET_DASHA_MEANING["en"])

    if not current_dasha:
        return (
            "यस कुण्डलीको दशा समयरेखामा हाल कुनै सक्रिय अवधि छैन।"
            if language == "ne"
            else "This chart's dasha timeline doesn't currently have an active period in range."
        )

    maha_lord = current_dasha["mahadasha"]["lord"]
    antar_lord = current_dasha["antardasha"]["lord"]
    maha_planet = chart["planets"][maha_lord]
    maha_sign = _sign_label(maha_planet["sign_name"], language)
    maha_ord = _ordinal(language, maha_planet["house"])
    maha_label = _planet_label(maha_lord, language)
    antar_label = _planet_label(antar_lord, language)

    dignity_note = None
    if maha_planet["debilitated"]:
        dignity_note = (
            f"{maha_label} यहाँ नीच अवस्थामा छ, जसले थप आत्म-अनुशासनको पाठ थप्छ: यसको अर्थ बाहिरी प्रतिबन्ध "
            f"भन्दा बढी यो ग्रहको स्वाभाविक प्रवृत्तिसँग सचेत रूपमा काम गर्न सिक्नु हो।"
            if language == "ne"
            else f"{maha_label} sits debilitated here, which adds a note of self-discipline: the lesson is "
            f"less about external restriction and more about learning to work consciously with what this "
            f"placement asks."
        )
    elif maha_planet["exalted"] or maha_planet["own_sign"] or maha_planet["moolatrikona"]:
        dignity_note = (
            f"{maha_label} यहाँ बलियो र सहज अवस्थामा छ, जसले यस अवधिका स्वाभाविक विषयवस्तुलाई समर्थन गर्छ।"
            if language == "ne"
            else f"{maha_label} sits in a strong, comfortable position here, which supports this period's "
            f"natural themes."
        )

    if language == "ne":
        text = (
            f"हाल तपाईं {maha_label} महादशामा हुनुहुन्छ, {maha_label}–{antar_label} अन्तर्दशाभित्र। {maha_label} "
            f"तपाईंको {maha_ord} भाव, {maha_sign} राशिमा छ। {maha_label} अवधिले परम्परागत रूपमा "
            f"{themes[maha_lord]}मा ध्यान ल्याउँछ।"
        )
        if dignity_note:
            text += f" {dignity_note}"
        text += f" यसभित्र चलिरहेको {antar_label} अन्तर्दशाले {themes[antar_lord]} विषयलाई अगाडि ल्याउँछ।"
        return text

    text = (
        f"You're currently running your {maha_label} mahadasha, in a {maha_label}–{antar_label} "
        f"antardasha. {maha_label} sits in your {maha_ord} house, {maha_sign}. {maha_label} periods "
        f"traditionally bring focus to {themes[maha_lord]}."
    )
    if dignity_note:
        text += f" {dignity_note}"
    text += (
        f" The {antar_label} antardasha running within it brings {themes[antar_lord]} to the foreground for "
        f"this stretch of time."
    )
    return text


def _section_strengths_cautions(chart: dict, language: str) -> str:
    planets = chart["planets"]
    gajakesari = planets["Moon"]["house"] == planets["Jupiter"]["house"]
    budhaditya = planets["Sun"]["house"] == planets["Mercury"]["house"]

    strengths: list[str] = []
    if budhaditya:
        strengths.append(
            "बुधादित्य योग (सूर्य–बुध युति)ले सामान्यतया आत्मविश्वासी, स्पष्ट सोच र शिक्षण, लेखन वा दार्शनिक "
            "अन्वेषणतर्फको स्वाभाविक झुकावलाई समर्थन गर्छ"
            if language == "ne"
            else "Budhaditya Yoga (the Sun–Mercury conjunction) generally supports confident, articulate "
            "thinking and a natural pull toward teaching, writing, or philosophical inquiry"
        )
    if gajakesari:
        strengths.append(
            "गजकेसरी योग (चन्द्रमा–बृहस्पति संयोजन)ले परम्परागत रूपमा बुद्धिमत्ता, स्थिरता र सौभाग्यलाई समर्थन "
            "गर्छ"
            if language == "ne"
            else "Gajakesari Yoga (the Moon–Jupiter combination) traditionally supports wisdom, "
            "steadiness, and good fortune"
        )

    for name in PLANET_ORDER:
        p = planets[name]
        label = _planet_label(name, language)
        sign = _sign_label(p["sign_name"], language)
        if p["exalted"]:
            strengths.append(
                f"{label} {sign} मा उच्च अवस्थामा छ, यसको सबैभन्दा आत्मविश्वासी र प्रभावकारी स्थिति"
                if language == "ne"
                else f"{label} is exalted in {sign}, its most confident and effective position"
            )
        elif p["own_sign"]:
            strengths.append(
                f"{label} {sign} मा स्वराशिमा छ, जहाँ यो सहज र आरामदायी रूपमा काम गर्छ"
                if language == "ne"
                else f"{label} is in its own sign in {sign}, operating comfortably and at home"
            )
        elif p["moolatrikona"]:
            strengths.append(
                f"{label} {sign} मा मूलत्रिकोणमा छ, यसको एक स्थिर र प्रभावकारी अवस्था"
                if language == "ne"
                else f"{label} is in moolatrikona in {sign}, one of its stable, effective positions"
            )

    cautions = [
        (
            f"{_planet_label(name, language)} को {_sign_label(planets[name]['sign_name'], language)} मा नीच "
            f"अवस्थाले यसका स्वाभाविक गुण व्यक्त हुने तरिकामा केही घर्षण देखाउँछ, जसका लागि त्यस क्षेत्रमा अलि "
            f"बढी सचेत प्रयास चाहिन्छ"
            if language == "ne"
            else f"{_planet_label(name, language)}'s debilitation in "
            f"{_sign_label(planets[name]['sign_name'], language)} suggests some friction in how its natural "
            f"qualities express, asking for a little more conscious effort in that area"
        )
        for name in PLANET_ORDER
        if planets[name]["debilitated"]
    ]

    if language == "ne":
        parts = []
        if strengths:
            parts.append(f"तपाईंको स्पष्ट बल: {'; '.join(strengths)}।")
        else:
            parts.append(
                "यस कुण्डलीमा कुनै ग्रह उच्च, स्वराशि वा मूलत्रिकोणमा छैन, र माथि उल्लेख गरिएको कुनै प्रमुख योग "
                "पनि छैन। यो कुण्डलीको सामान्य बनोट मात्र हो, चिन्ताको विषय होइन।"
            )
        if cautions:
            parts.append(f"मुख्य सावधानी: {'; '.join(cautions)}।")
        else:
            parts.append("यस कुण्डलीमा कुनै ग्रह नीच छैन, जुन समग्रमा सहज अवस्था हो।")
        return " ".join(parts)

    parts = []
    if strengths:
        parts.append("Your clearest strengths: " + "; ".join(strengths) + ".")
    else:
        parts.append(
            "No planet is exalted, in its own sign, or in moolatrikona in this chart, and neither yoga above "
            "is present. That's an ordinary distribution, not a warning sign."
        )
    if cautions:
        label = "caution" if len(cautions) == 1 else "cautions"
        parts.append(f"The main {label} in this chart: " + "; ".join(cautions) + ".")
    else:
        parts.append("No planet is debilitated in this chart, which is a comfortable placement overall.")
    return " ".join(parts)


def _section_transits(transits: dict | None, language: str) -> str:
    if not transits:
        return (
            "यस चार्टको लागि हालको गोचर डाटा उपलब्ध छैन।"
            if language == "ne"
            else "Current transit data isn't available for this chart."
        )

    themes = HOUSE_THEMES.get(language, HOUSE_THEMES["en"])
    sentences = []
    for key in ("jupiter", "saturn"):
        planet = transits[key]
        label = _planet_label(planet["name"], language)
        sign = _sign_label(planet["sign_name"], language)
        lagna_ord = _ordinal(language, planet["house_from_lagna"])
        moon_ord = _ordinal(language, planet["house_from_moon"])
        theme_lagna = themes[planet["house_from_lagna"]]
        theme_moon = themes[planet["house_from_moon"]]
        ingress_date = planet["next_ingress"][:10]

        if language == "ne":
            sentences.append(
                f"{label} हाल {sign} राशिमा गोचर गर्दैछ, जुन तपाईंको लग्नबाट {lagna_ord} र चन्द्रमाबाट "
                f"{moon_ord} भाव हो, जसले {theme_lagna} र {theme_moon}मा ध्यान ल्याउँछ। यो {ingress_date} "
                f"तिर अर्को राशिमा सर्नेछ।"
            )
        else:
            sentences.append(
                f"{label} is currently transiting {sign}, your {lagna_ord} house from lagna and {moon_ord} "
                f"house from your natal Moon, bringing attention to {theme_lagna} as well as {theme_moon}. It "
                f"will move into the next sign around {ingress_date}."
            )
    return " ".join(sentences)


def _generate_grounded_mock_text(chart_json: dict, language: str) -> str:
    """Deterministic, template-based interpretation built entirely from the
    given chart's own data. Used for any chart other than the Stage-1
    reference chart, so mock mode stays genuinely grounded for arbitrary
    input (see backend/evals)."""
    chart = chart_json["chart"]
    current_dasha = chart_json.get("current_dasha")
    transits = chart_json.get("transits")
    headings = HEADINGS.get(language, HEADINGS["en"])

    sections = [
        (headings["lagna"], _section_lagna(chart, language)),
        (headings["yogas"], _section_yogas(chart, language)),
        (headings["dasha"], _section_dasha(chart, current_dasha, language)),
        (headings["strengths"], _section_strengths_cautions(chart, language)),
        (headings["transits"], _section_transits(transits, language)),
    ]
    body = "\n\n".join(f"## {title}\n\n{text}" for title, text in sections)
    disclaimer = DISCLAIMER_NE if language == "ne" else DISCLAIMER
    return f"{body}\n\n{disclaimer}"


def _log_mock_mode() -> None:
    print(
        "MOCK MODE: interpret_chart is returning a canned example "
        "interpretation (USE_MOCK_LLM=true, no Anthropic API call made)."
    )


def _mock_full_text(chart_json: dict, language: str) -> str:
    if _is_reference_chart(chart_json):
        return _MOCK_TEXT.get(language, _MOCK_TEXT["en"])
    return _generate_grounded_mock_text(chart_json, language)


def _stream_mock(chart_json: dict, language: str) -> Iterator[str]:
    _log_mock_mode()
    text = _mock_full_text(chart_json, language)
    words = text.split(" ")
    for index, word in enumerate(words):
        yield word if index == 0 else " " + word
        time.sleep(0.02)


def interpret_chart(chart_json: dict, language: str = "en") -> Iterator[str]:
    """Stream a natural-language interpretation of a pre-computed chart.

    Yields text chunks in order; concatenating them reconstructs the full
    interpretation. Never computes astrology itself — chart_json must
    already contain all planetary positions, dignities, and dasha data.
    Mode is controlled by the USE_MOCK_LLM env var (default: mock).
    """
    if is_mock_mode():
        yield from _stream_mock(chart_json, language)
    else:
        yield from _stream_real(chart_json, language)


def interpret_chart_text(chart_json: dict, language: str = "en") -> str:
    """Non-streaming variant: returns the full interpretation as one string.

    Used where a synchronous result is needed (e.g. PDF export) rather than
    an SSE stream. Same modes and constraints as interpret_chart().
    """
    if is_mock_mode():
        _log_mock_mode()
        return _mock_full_text(chart_json, language)
    return _real_full_text(chart_json, language)
