"""Follow-up chat over an already-computed chart, via tool use.

Same engine -> JSON -> LLM direction as app.interpret: the chat LLM never
computes or free-invents a chart fact. It only ever gets facts by calling
one of the app.chat_tools functions, so every claim in a reply is
traceable to already-computed data. Two modes, selected by the same
USE_MOCK_LLM env var as app.interpret:

- Mock mode (default): a small pattern matcher recognizes a handful of
  common question shapes and calls the SAME tool functions directly,
  templating their result into a sentence — no invented prose, genuinely
  grounded, just not open-ended. Always logs "MOCK MODE" like
  app.interpret. Anything it doesn't recognize gets a clear message that
  full conversational chat requires live mode.
- Real mode (USE_MOCK_LLM=false): Claude answers using the Anthropic
  tool-use API. It is given the tool schemas below, never the raw chart
  JSON, so it must call a tool to get any fact rather than guessing.
"""

from __future__ import annotations

import json
import re

from app.chat_tools import ChartToolError, get_dasha_at, get_planet, get_transit, get_yogas
from app.interpret import MAX_TOKENS, MODEL, is_mock_mode, require_api_key

MAX_TOOL_ROUNDS = 6

TOOLS = [
    {
        "name": "get_planet",
        "description": (
            "Get this chart's sign, degree, house, dignity, and nakshatra for one planet."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "planet_name": {
                    "type": "string",
                    "description": "Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, or Ketu",
                },
            },
            "required": ["planet_name"],
        },
    },
    {
        "name": "get_dasha_at",
        "description": (
            "Get the active Vimshottari mahadasha/antardasha lords for a given calendar "
            "date, from this chart's already-computed dasha timeline."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "on_date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
            },
            "required": ["on_date"],
        },
    },
    {
        "name": "get_transit",
        "description": (
            "Get the current transit (gochara) position for Jupiter or Saturn — the "
            "only two planets this app tracks in transit."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "planet_name": {"type": "string", "description": "Jupiter or Saturn"},
            },
            "required": ["planet_name"],
        },
    },
    {
        "name": "get_yogas",
        "description": "List the yogas (planetary combinations) present in this chart.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

_DISPATCH = {
    "get_planet": lambda stored, args: get_planet(stored, args["planet_name"]),
    "get_dasha_at": lambda stored, args: get_dasha_at(stored, args["on_date"]),
    "get_transit": lambda stored, args: get_transit(stored, args["planet_name"]),
    "get_yogas": lambda stored, args: get_yogas(stored),
}

SYSTEM_PROMPT = """You are AstroTruth's chat assistant, answering follow-up questions about
one specific, already-computed Vedic chart.

You MUST NOT compute, assume, or invent any planetary position, dignity,
dasha date, transit, or yoga. Every fact you state must come from calling
one of the provided tools first — never answer a factual question about
this chart from your own knowledge or by guessing.

If a question asks for medical, legal, or financial decisions or
directives, decline and suggest a qualified professional instead —
describe traditional astrological significations only, never directives.

If a question is unrelated to this chart, politely redirect the user
back to asking about their chart.

Keep answers concise and conversational.""".strip()


def _call_tool(stored: dict, name: str, tool_input: dict) -> dict:
    try:
        result = _DISPATCH[name](stored, tool_input)
    except ChartToolError as exc:
        return {"error": str(exc)}
    return {"result": result}


def _log_mock_mode() -> None:
    print(
        "MOCK MODE: chat_reply is answering via pattern-matched tool calls "
        "(USE_MOCK_LLM=true, no Anthropic API call made)."
    )


def _real_chat_reply(stored: dict, message: str, history: list[dict]) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=require_api_key())
    messages = [dict(turn) for turn in history] + [{"role": "user", "content": message}]

    for _ in range(MAX_TOOL_ROUNDS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )
        if response.stop_reason != "tool_use":
            return "".join(block.text for block in response.content if block.type == "text")

        messages.append({"role": "assistant", "content": response.content})
        tool_results = [
            {
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(_call_tool(stored, block.name, block.input)),
            }
            for block in response.content
            if block.type == "tool_use"
        ]
        messages.append({"role": "user", "content": tool_results})

    return "I wasn't able to work out an answer to that — could you rephrase?"


_PLANET_PATTERN = re.compile(
    r"\b(sun|moon|mars|mercury|jupiter|venus|saturn|rahu|ketu)\b", re.IGNORECASE
)
_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
_YOGA_PATTERN = re.compile(r"\byogas?\b", re.IGNORECASE)
_TRANSIT_PATTERN = re.compile(r"\btransit", re.IGNORECASE)

MOCK_UNRECOGNIZED_MESSAGE = (
    "Mock mode only understands a few question patterns right now — try things like "
    '"What sign is my Moon in?", "Any yogas in my chart?", '
    '"What\'s my dasha on 2030-01-01?", or "What\'s the current transit for Jupiter?". '
    "Full open-ended chat requires live mode (USE_MOCK_LLM=false with an Anthropic API key)."
)


def _mock_chat_reply(stored: dict, message: str) -> str:
    _log_mock_mode()

    yoga_match = _YOGA_PATTERN.search(message)
    date_match = _DATE_PATTERN.search(message)
    planet_match = _PLANET_PATTERN.search(message)
    transit_match = _TRANSIT_PATTERN.search(message)

    try:
        if yoga_match:
            yogas = get_yogas(stored)
            if not yogas:
                return (
                    "This chart doesn't have Gajakesari Yoga or Budhaditya Yoga — the "
                    "two yogas I can check for."
                )
            names = ", ".join(y["name"] for y in yogas)
            return f"Yes — this chart has: {names}."

        if transit_match and planet_match:
            info = get_transit(stored, planet_match.group(1))
            return (
                f"{info['planet']} is currently transiting {info['sign']} "
                f"({info['degrees_in_sign']:.2f}° in), {info['house_from_lagna']}th house "
                f"from your lagna and {info['house_from_moon']}th from your natal Moon. "
                f"Next sign change: {info['next_ingress'][:10]}."
            )

        if date_match:
            info = get_dasha_at(stored, date_match.group(0))
            return (
                f"On {info['date']}, your mahadasha lord is {info['mahadasha']} "
                f"and antardasha lord is {info['antardasha']}."
            )

        if planet_match:
            info = get_planet(stored, planet_match.group(1))
            dignity_phrase = f", {info['dignity'].replace('_', ' ')}" if info["dignity"] else ""
            return (
                f"{info['planet']} is in {info['sign']} ({info['degrees_in_sign']:.2f}°), "
                f"house {info['house']}{dignity_phrase}, in {info['nakshatra']} nakshatra "
                f"(pada {info['pada']})."
            )
    except ChartToolError as exc:
        return str(exc)

    return MOCK_UNRECOGNIZED_MESSAGE


def chat_reply(stored: dict, message: str, history: list[dict] | None = None) -> str:
    """Answer one chat turn about an already-computed chart.

    `history` is a list of {"role": "user"|"assistant", "content": str}
    prior turns; the caller (main.py) is stateless and resends it each
    request, same pattern as app.interpret's SSE endpoint being handed
    the full stored chart each time rather than holding server state.
    """
    history = history or []
    if is_mock_mode():
        return _mock_chat_reply(stored, message)
    return _real_chat_reply(stored, message, history)
