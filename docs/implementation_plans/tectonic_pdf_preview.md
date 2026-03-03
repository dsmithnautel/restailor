# Switch to Tectonic PDF Preview

Replace the HTML/CSS `ResumePreview` component with actual PDF preview compiled by Tectonic (~130ms per build), rendered via `react-pdf`.

## Architecture

```
User edits bullet text → 1.5s debounce → POST /resume/preview (JSON)
→ backend generates LaTeX deterministically → tectonic compiles → PDF bytes returned
→ frontend renders via react-pdf
```

## Proposed Changes

---

### Backend: Deterministic LaTeX Generator

#### [NEW] [template_latex.py](file:///Users/xalandames/Documents/SwampHacks%202026/restailor/backend/app/services/template_latex.py)

Function `generate_latex(header, sections) → str` that:
- Takes header info + `ScoredUnit[]` grouped by section
- Produces a complete `.tex` file matching [cv.tex](file:///Users/xalandames/Documents/SwampHacks%202026/restailor/backend/output/cmp_20260219_7d341f/cv.tex)
- Uses Jake's template preamble but removes `\input{glyphtounicode}` (Tectonic incompatible)
- Pure string formatting — no LLM, no randomness

#### [NEW] [tectonic.py](file:///Users/xalandames/Documents/SwampHacks%202026/restailor/backend/app/services/tectonic.py)

Function `compile_pdf(latex_source: str) → bytes`:
- Writes `.tex` to a temp file
- Runs `tectonic` subprocess (~130ms)
- Returns PDF bytes

#### [MODIFY] [resume.py](file:///Users/xalandames/Documents/SwampHacks%202026/restailor/backend/app/routers/resume.py)

New endpoint `POST /resume/preview`:
- Request body: `{header: HeaderInfo, units: ScoredUnit[]}`
- Calls `generate_latex()` → `compile_pdf()`
- Returns `Response(content=pdf_bytes, media_type="application/pdf")`

---

### Frontend: react-pdf + Debounced Editing

#### [MODIFY] [page.tsx](file:///Users/xalandames/Documents/SwampHacks%202026/restailor/frontend/app/compare/%5BcompileId%5D/page.tsx)

- Replace `ResumePreview` with a split layout:
  - **Left pane**: editable text fields grouped by section
  - **Right pane**: `react-pdf` `<Document>` / `<Page>` rendering the PDF blob
- 1.5s debounce on edits → call `POST /resume/preview` → update PDF blob
- Loading spinner overlay during compilation

#### Install dependency

```bash
npm install react-pdf
```

> [!NOTE]
> The existing `resume-preview.tsx` and `resume-preview.css` will no longer be imported but can be kept for reference.

---

### Tectonic Compatibility

Remove `\input{glyphtounicode}` from the template preamble. Keep `\pdfgentounicode=1` (Tectonic supports this).

## Verification Plan

### Automated Tests
- `time tectonic output.tex` to verify ~130ms
- `curl -X POST /resume/preview -d '...'` to verify PDF response

### Manual Verification
- Edit a bullet in the compare page → verify PDF updates within ~2s
- Compare rendered PDF against the existing `Download PDF` output
