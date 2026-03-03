# Implementation Plan - LLM-Based LaTeX Resume Generation

The goal is to move from the current `RenderCV`-based rendering pipeline to a direct LLM-based approach. We will feed the tailored "atomic units" (JSON) and "Jake's Resume Template" (raw LaTeX) into the LLM, asking it to generate the final LaTeX code, which we then compile to PDF.

## User Review Required

> [!WARNING]
> This change replaces the deterministic `RenderCV` engine with an LLM-based generation. While more flexible, LLMs can sometimes produce invalid LaTeX syntax which may cause compilation failures.

## Proposed Changes

### Backend

#### [NEW] [prompts.py](file:///Users/xalandames/Documents/SwampHacks%202026/restailor/backend/app/services/prompts.py)
*   Port `JAKES_TEMPLATE` from the Ruby snippet to a Python string constant.
*   Implement `generate_latex_prompt(resume_data: str) -> str` that inserts the data and template into the prompt.

#### [MODIFY] [renderer.py](file:///Users/xalandames/Documents/SwampHacks%202026/restailor/backend/app/services/renderer.py)
*   Import `generate_text` from `app.services.gemini`.
*   Import `generate_latex_prompt` from `app.services.prompts`.
*   Refactor `render_resume` function:
    1.  Serialize `selected_units` + `header_info` into a clean JSON string.
    2.  Construct the prompt using `generate_latex_prompt`.
    3.  Call `gemini.generate_text` to get the raw LaTeX.
    4.  Save the LaTeX to `output/{compile_id}/cv.tex`.
    5.  Run `pdflatex` (or `latexmk`) on `cv.tex` to generate the PDF.
    6.  Ensure the final PDF is at `output/{compile_id}/resume.pdf`.

#### [MODIFY] [resume.py](file:///Users/xalandames/Documents/SwampHacks%202026/restailor/backend/app/routers/resume.py)
*   No major changes needed if we keep the `render_resume` signature compatible, but we will double check proper error handling for LaTeX compilation failures.

## Verification Plan

### Automated Tests
*   We will rely on manual verification as this involves LLM output quality and PDF visual inspection.
*   We can run `pytest backend/test_renderer.py` if it exists, or create a simple script to trigger the rendering.

### Manual Verification
- Asking the user to deploy to staging and testing, verifying UI changes on an iOS app etc.

## Latency Optimization [REVERTED]
> [!WARNING]
> These changes were reverted because the parallel request volume triggered the Gemini Free Tier rate limits (15 RPM), causing 60s delays that negated the speed gains.


### [MODIFY] [gemini.py](file:///Users/xalandames/Documents/SwampHacks%202026/restailor/backend/app/services/gemini.py)
- Relax `RATE_LIMIT_DELAY` from 4.0s to 0.1s to allow bursty parallel requests.
- Rely on 429 retries for rate limiting rather than preemptive slowing.

### [MODIFY] [scoring.py](file:///Users/xalandames/Documents/SwampHacks%202026/restailor/backend/app/services/scoring.py)
- Refactor `tailor_units_against_jd` to:
    - Split `tailorable` units into individual items.
    - Create a helper `tailor_single_bullet` function.
    - Use `asyncio.gather` to execute all tailoring requests in parallel.
    - Aggregate results and handle failures gracefully.

### [MODIFY] [resume.py](file:///Users/xalandames/Documents/SwampHacks%202026/restailor/backend/app/routers/resume.py)
- **Problem**: When using `jd_text` (on-the-fly parsing), two LLM calls happen in rapid succession (Parse -> Tailor), triggering burst rate limits.
- **Fix**: Add a safety `await asyncio.sleep(5)` inside the `elif request.jd_text:` block to allow the token bucket to refill.
- **Fix**: Add a safety `await asyncio.sleep(5)` after `tailor_units_against_jd` returns.

### [Fix Tailoring Logic]
#### [MODIFY] [scoring.py](file:///Users/xalandames/Documents/SwampHacks%202026/restailor/backend/app/services/scoring.py)
*   **Problem**: Current tailoring logic might be insufficient or broken (needs verification).
*   **Plan**:
    *   Review `tailor_units_against_jd` prompts and logic.
    *   Ensure it correctly uses the parsed Job Description.
    *   Verify it returns valid `ScoredUnit` objects with tailored text.
    *   Consider moving to a dedicated `tailoring.py` service if `scoring.py` becomes too cluttered.

