# ResTailor Implementation Plan

I will build a Python script that uses an LLM (Large Language Model) to tailor a user's professional experience to a specific job description.

## User Review Required

> [!IMPORTANT]
> **LLM Provider**: I plan to use **Google's Gemini API** (`google-generativeai`) as it is fast and has a generous free tier. You will need a `GEMINI_API_KEY` environment variable.
> *Alternative*: If you prefer **OpenAI** (`openai`), please let me know!

## Proposed Changes

### Dependencies
- Install `google-generativeai`.

### Core Logic
#### [MODIFY] [main.py](file:///Users/xalandames/Documents/SwampHacks/restailor/main.py)
- Import `google.generativeai`.
- Configure API key from environment variable `GEMINI_API_KEY`.
- Define `tailor_resume(experience, job_description)` function.
- **Prompt Engineering**: Construct a prompt that asks the LLM to rewrite the experience bullets to highlight relevance to the job description.
- **Main Execution**:
    - Prompt user for "Professional Experience" (multi-line input).
    - Prompt user for "Job Description" (multi-line input).
    - Call the tailoring function.
    - Print the result.

## Verification Plan

### Manual Verification
- Run `python main.py`.
- Paste in a sample resume snippet.
- Paste in a sample job description.
- Verify the output is a tailored version of the experience.
