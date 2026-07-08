# AstroTruth — project conventions

- The product name is **AstroTruth** — use it in the README and any UI text.

- The astrology engine (`backend/app/engine.py`, `backend/app/dasha.py`) must
  be pure, deterministic functions with no I/O — no network calls, no file
  reads, no database access, no logging side effects. Every function takes
  inputs and returns values, so it is fully unit-testable without mocks.

- The LLM never computes planetary positions; it only interprets pre-computed
  JSON produced by the engine. The engine never interprets — it has no
  knowledge of, or dependency on, the LLM layer. Data flows one direction:
  engine → JSON → LLM.

- Astronomical conventions, fixed across the whole codebase:
  - Sidereal zodiac with the **Lahiri ayanamsa**.
  - **Whole-sign houses**.
  - **Mean lunar node** (Rahu/Ketu), not true node.
  - Timezone handling must correctly support fractional-hour offsets,
    including **UTC+5:45 (Nepal)**.

- Every computed value (planetary longitude, house cusp, dasha period, etc.)
  needs a unit test that checks it against a known reference chart — not just
  a smoke test that the function runs.
