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


def _log_mock_mode() -> None:
    print(
        "MOCK MODE: interpret_chart is returning a canned example "
        "interpretation (USE_MOCK_LLM=true, no Anthropic API call made)."
    )


def _mock_full_text(language: str) -> str:
    return _MOCK_TEXT.get(language, _MOCK_TEXT["en"])


def _stream_mock(language: str) -> Iterator[str]:
    _log_mock_mode()
    text = _mock_full_text(language)
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
        yield from _stream_mock(language)
    else:
        yield from _stream_real(chart_json, language)


def interpret_chart_text(chart_json: dict, language: str = "en") -> str:
    """Non-streaming variant: returns the full interpretation as one string.

    Used where a synchronous result is needed (e.g. PDF export) rather than
    an SSE stream. Same modes and constraints as interpret_chart().
    """
    if is_mock_mode():
        _log_mock_mode()
        return _mock_full_text(language)
    return _real_full_text(chart_json, language)
