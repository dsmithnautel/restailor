# Full Stack ResTailor Implementation Plan

The goal is to migrate the current CLI-based Resume Tailor ("ResTailor") into a modern full-stack web application. The text-based interaction will be replaced with a responsive web UI.

## User Review Required
> [!IMPORTANT]
> **MongoDB Requirement**: This plan assumes you have a MongoDB instance running (locally or Atlas). We will configure the application to look for `MONGODB_URI` in the `.env` file. If you do not have MongoDB running, the persistence feature will fail, though generation can be made to work without it if requested.

> [!NOTE]
> We will create two distinct folders: `backend/` and `frontend/` in the root directory.

## Proposed Changes

### Backend (`/backend`)
We will use **FastAPI** for its speed and native async support, which works well with **Motor** (async MongoDB driver) and the Gemini async API.

#### [NEW] `requirements.txt`
Dependencies: `fastapi`, `uvicorn`, `motor`, `python-dotenv`, `google-generativeai`.

#### [NEW] `app/main.py`
The entry point. Will define:
- `POST /api/tailor`:
    - **Input**: JSON `{ "experience": str, "job_description": str }`
    - **Process**:
        1. Call Gemini API (using reused logic).
        2. Store Input + Output in MongoDB.
    - **Output**: JSON `{ "tailored_experience": str, "id": str }`

#### [NEW] `app/database.py`
Helper to connect to `MONGODB_URI`.

### Frontend (`/frontend`)
We will use **Next.js** (App Router) with **TailwindCSS** for styling.

#### [NEW] `app/page.tsx`
A split-screen or stacked layout:
- **Left/Top**: Two text areas (Experience, Job Description) + "Tailor My Resume" button.
- **Right/Bottom**: Output area for the generated text (Markdown rendered).

#### [NEW] `app/components/`
Reusable UI components for inputs and buttons to ensure a "premium" feel as requested.

## Verification Plan

### Automated Tests
- We will try to curl the backend endpoint to ensure it returns 200 OK.

### Manual Verification
- Start Backend: `uvicorn app.main:app --reload`
- Start Frontend: `npm run dev`
- **User Flow**:
    1. Open `http://localhost:3000`
    2. Paste dummy experience and JD.
    3. Click "Tailor".
    4. Verify the loading state appears.
    5. Verify the tailored resume appears.
    6. (Internal) Verify the entry was saved to MongoDB.
