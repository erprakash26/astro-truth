# AstroTruth evals

This directory holds evals for `app.interpret` — checks that judge the
*quality and safety of generated text*, as distinct from `backend/tests/`,
which checks that deterministic code (the chart engine, dasha math,
transits) returns the right numbers. Both run under the same `pytest`
invocation; they're split into `evals/` because they're testing a
different kind of thing (a generative text property, not a pure function's
return value) and because that's where an LLM-judge eval would eventually
live if we add one (see below).

## What's here

- **`test_grounding.py`** — for three distinct, previously-verified birth
  charts (the Stage-1 London reference chart, plus Kathmandu and New York
  — the same three charts locked in by `tests/test_regression.py`), calls
  `interpret_chart_text()` in mock mode and checks that the output:
  1. never states a `{Planet, Sign}` pair that contradicts the chart JSON
     it was given (checked against `chart.planets[*].sign_name` for natal
     claims, or `transits.{jupiter,saturn}.sign_name` for transit claims),
  2. always includes the required disclaimer sentence, and
  3. never contains medical/legal/financial directive language.

## Why rule-based checking, not an LLM judge

The obvious alternative to a regex/keyword checker is to ask a second LLM
call "does this interpretation contradict this chart JSON? yes/no." We
didn't build that for this eval, for three reasons specific to where this
project is right now:

1. **Cost and speed.** This eval runs in mock mode (`USE_MOCK_LLM=true`,
   the default), specifically so the test suite never makes a paid API
   call. An LLM-judge eval would either force real API calls into the CI
   test run (cost + flakiness + rate limits — see the `slowapi` limiting
   we added elsewhere in this project for exactly this concern) or need
   its own separate opt-in path, which is more machinery than the current
   mock-mode interpretation needs.
2. **Determinism.** A rule-based checker gives the same verdict every
   time for the same input. An LLM judge can disagree with itself between
   runs (different sampling, different day, different judge-model
   version), which makes a *regression* test — something that should fail
   only when the code under test actually changes — noisy. We want "did
   this contradict the chart" to be as deterministic as the chart math
   itself.
3. **The property we're checking is actually simple.** "Every {Planet,
   Sign} pair mentioned must match a real field in the JSON" is a
   structured, mechanically-checkable claim — not a subjective judgment
   call. A regex/keyword checker is the right-sized tool for it. (It's not
   a *free* simplification — see "What rule-based checking can't catch"
   below for the real ambiguities this forced us to confront.)

This is a judgment call for *this* eval, not a blanket rule. The tradeoff
flips once mock mode is off and the checked property becomes genuinely
subjective (see below).

## What rule-based checking can't catch

Building this checker surfaced three concrete ambiguities that a naive
"does the planet name and sign name appear near each other" heuristic gets
wrong — worth recording here since they're the actual argument for
eventually adding an LLM judge, not a hypothetical one:

- **Yoga names contain planet names as substrings.** "Budhaditya" (the
  yoga name) contains "बुध" (Mercury) as a literal Devanagari prefix.
  Naive matching flagged a false claim that Mercury was in whatever sign
  happened to follow the word "Budhaditya" in a sentence about the *yoga*,
  not about Mercury's placement.
- **"Ruled by Mars" states a sign's fixed ruler, not a planet's current
  position.** "A chart ruled by fast-moving Mars" (describing Aries) reads
  lexically identical to a real position claim to a co-occurrence checker.
  We special-cased and masked out rulership phrasing before extraction;
  an LLM judge would understand this distinction natively, with no
  masking required.
- **Clause boundaries matter and periods aren't the only one.** "Gajakesari
  Yoga (the Moon–Jupiter combination) ...; Sun is exalted in Aries..."
  is one semicolon-joined sentence with unrelated clauses; without
  splitting on `;` too, a naive pairing pass could reach across the
  boundary and attribute Sun's sign to Moon and Jupiter.

Each of these was caught by the eval's own sanity checks
(`test_extractor_finds_claims_on_a_known_sentence`,
`test_extractor_flags_a_deliberately_wrong_claim`) actually failing during
development — not discovered by inspection — which is itself the argument
for having this eval at all: rule-based grounding checking is narrow, but
what it does check, it checks for real.

## Adding an LLM-judge eval later

The natural next eval, once real mode (`USE_MOCK_LLM=false`) is exercised
in CI, is a judge call that a rule-based checker structurally cannot do:

- **Faithfulness beyond position claims** — does the *reasoning* the text
  gives for a yoga, dasha period, or transit actually follow from
  classical rules, not just "is the sign name right." A rule-based
  checker can verify "Jupiter is in Cancer" is true; it cannot verify that
  the *significance* attributed to that placement is a defensible
  classical reading rather than a plausible-sounding fabrication.
- **Tone and safety judgment calls that aren't keyword-matchable** — the
  banned-phrase list here catches literal strings like "you should
  invest." It cannot catch a paragraph that dances around the same advice
  without using any of the listed phrases ("this would be a favorable
  time to grow your savings"). A judge model can assess intent, not just
  string membership.
- **Structural/tone conformance** — does the response actually read as
  "warm, direct, and honest" per the system prompt, avoid excessive
  hedging, and stay in the requested language throughout (not just at the
  start)? These are exactly the things an LLM judge is good at and a
  regex is not.

To wire this in without adding cost/flakiness to the default test run:

1. Add `evals/test_llm_judge.py`, decorated so it only collects when
   `USE_MOCK_LLM=false` **and** `ANTHROPIC_API_KEY` is set (skip
   otherwise — mirror the guard already in `app.interpret._require_api_key`
   rather than duplicating the check). This keeps `pytest` green with zero
   API calls by default, matching how `tests/test_rate_limit.py` already
   avoids real network calls.
2. Call `interpret_chart_text(chart_json, language)` in real mode to get
   the text under test, then make a **second**, separate Anthropic call
   with a judge prompt: give it the same `chart_json`, the generated
   text, and ask it to return structured output (`output_config.format`,
   a JSON schema of `{faithful: bool, issues: list[str]}`) rather than
   free text, so the test can assert on a field instead of parsing prose.
3. Use a fixed, cheap model for the judge (e.g. `claude-haiku-4-5`) —
   the judge's job is narrow classification, not generation quality, so
   it doesn't need the same model tier as the interpretation itself.
4. Keep the rule-based checks in `test_grounding.py` running unconditionally
   regardless of mode. The two are complementary, not redundant: rule-based
   catches mechanical contradictions cheaply on every run (including in
   mock mode, which is most of the time); the judge catches the subjective
   failures above, only when real-mode is actually being exercised.

## Why grounding evals matter for LLM apps generally

An LLM that narrates pre-computed data (this project's whole design,
per `CLAUDE.md`: "the LLM never computes... it has no knowledge of the
engine") can still silently *contradict* that data — restating a fact
wrong, inventing a placement that sounds plausible, or blending in
something from training data that has nothing to do with this specific
input. Nothing about "don't let the model compute astrology" stops the
model from getting the astrology it's handed wrong when it puts it into
prose. Fluency is not the same property as correctness, and a
model can be fluently, confidently wrong.

For a domain like this one — astrology interpretation, where a
plausible-sounding but fabricated claim ("Mars is in your 7th house") is
just as easy to produce as a correct one, and where users have no
independent way to check it against the chart themselves — a grounding
eval is the difference between "the LLM layer narrates the engine's
output" (the actual design) and "the LLM layer occasionally makes things
up that happen to be phrased the same way" (an undetected regression). The
same argument applies to any LLM app sitting on top of a source of truth
it isn't supposed to override: RAG systems narrating retrieved documents,
agents reporting tool results, summarizers condensing a source text. In
every one of these, the generative step can drift from the ground truth
it was given, and that drift is invisible to a human unless someone is
specifically checking the generated claims against the source data — which
is what a grounding eval automates.
