# Architecture Refactor: Atomic Units → Full-Text LaTeX Generation

## Goal
Simplify the resume tailoring system by eliminating atomic unit extraction and using direct LaTeX template generation with Jake's Resume template.

---

## User Review Required

> [!WARNING]
> **Breaking Changes**
> - This refactor will remove atomic unit storage and granular bullet-level editing
> - Users will need to re-upload resumes (incompatible with current MongoDB schema)
> - Provenance tracking (which bullet changed and why) will be limited
> - Cannot selectively include/exclude specific experiences

> [!IMPORTANT]
> **System Dependencies**
> - Requires LaTeX installation on server (`pdflatex` command)
> - MacTeX on macOS or TeXLive on Linux
> - Increases PDF compilation time (~2-5 seconds vs ~500ms with RenderCV)

---

## Proposed Changes

### 1. Data Model Simplification

#### Current: `master_resume.py`
```python
class MasterResumeResponse(BaseModel):
    master_version_id: str
    atomic_units: list[AtomicUnit]  # 50+ granular units
    summary: str
```

#### New: `master_resume.py`
```python
class MasterResumeResponse(BaseModel):
    master_version_id: str
    resume_text: str  # Full extracted text
    extracted_json: dict  # Structured data (name, education, etc.)
```

---

### 2. Ingestion Service (`ingestion.py`)

#### [MODIFY] [`ingestion.py`](file:///Users/xalandames/Documents/SwampHacks%202026/restailor/backend/app/services/ingestion.py)

**Current Flow:**
```
PDF → PyMuPDF extract text → Gemini parses to atomic units → Store 50+ units in DB
```

**New Flow:**
```
PDF → PyMuPDF extract text → Store full text → (Parsing happens on-demand during compile)
```

**Changes:**
- Remove `EXTRACTION_PROMPT` (lines 45-142)
- Remove `generate_json()` call for atomic unit parsing
- Store `resume_text` as single string
- Remove atomic unit loop and database inserts

---

### 3. LaTeX Templates Module

#### [NEW] `app/services/latex_templates.py`

```python
"""Jake's Resume LaTeX template and prompts."""

JAKES_TEMPLATE = """
\\documentclass[letterpaper,11pt]{article}
...
[Full Jake's template code from your example]
...
\\end{document}
"""

EXTRACTION_PROMPT = """
Extract resume information into structured JSON...
[Extraction prompt from your example]
"""

def latex_generation_prompt(extracted_json: dict, jd_text: str) -> str:
    """Generate prompt for converting JSON to tailored LaTeX."""
    return f"""
    You are a LaTeX expert. Convert this resume to Jake's template,
    tailoring content to match this job description.
    
    JOB DESCRIPTION:
    {jd_text}
    
    RESUME DATA:
    {json.dumps(extracted_json, indent=2)}
    
    TEMPLATE:
    {JAKES_TEMPLATE}
    
    [Latex prompt from your example]
    """
```

---

### 4. Tailoring Service (`scoring.py`)

#### [MODIFY] [`scoring.py`](file:///Users/xalandames/Documents/SwampHacks%202026/restailor/backend/app/services/scoring.py)

**Replace entire file with:**

```python
"""Resume tailoring using Jake's LaTeX template."""

from app.services.gemini import generate_text
from app.services.latex_templates import EXTRACTION_PROMPT, latex_generation_prompt

async def tailor_resume_to_latex(resume_text: str, jd_text: str) -> str:
    """
    Tailor resume to job description using Jake's LaTeX template.
    
    Returns:
        Complete LaTeX source code ready for pdflatex compilation
    """
    # Step 1: Extract resume info to JSON
    extraction_prompt = EXTRACTION_PROMPT.format(resume_content=resume_text)
    extracted_json_str = await generate_text(extraction_prompt)
    extracted_json = json.loads(extracted_json_str)
    
    # Step 2: Generate tailored LaTeX
    latex_prompt = latex_generation_prompt(extracted_json, jd_text)
    tailored_latex = await generate_text(latex_prompt)
    
    return tailored_latex
```

---

### 5. Renderer Service (`renderer.py`)

#### [MODIFY] [`renderer.py`](file:///Users/xalandames/Documents/SwampHacks%202026/restailor/backend/app/services/renderer.py)

**Changes:**
- Remove RenderCV subprocess call
- Replace with `pdflatex` compilation
- Remove `rendercv_mapper` import

```python
async def compile_latex_to_pdf(latex_source: str, compile_id: str):
    """Compile LaTeX source to PDF using pdflatex."""
    output_dir = Path(OUTPUT_DIR) / compile_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Write LaTeX file
    tex_file = output_dir / "resume.tex"
    tex_file.write_text(latex_source)
    
    # Compile with pdflatex (run twice for references)
    for _ in range(2):
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "resume.tex"],
            cwd=output_dir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"LaTeX compilation failed: {result.stderr}")
    
    pdf_path = output_dir / "resume.pdf"
    if not pdf_path.exists():
        raise RuntimeError("PDF generation failed")
    
    return str(pdf_path)
```

---

### 6. API Endpoints

#### [MODIFY] [`resume.py`](file:///Users/xalandames/Documents/SwampHacks%202026/restailor/backend/app/routers/resume.py)

**Changes to `/resume/compile`:**

```python
@router.post("/compile")
async def compile_resume(request: CompileRequest):
    # Fetch resume text
    master = await db.master_versions.find_one({"master_version_id": request.master_version_id})
    resume_text = master["resume_text"]
    
    # Parse JD
    parsed_jd = await parse_job_description(request.jd_text or fetch_jd(request.jd_id))
    
    # Tailor to LaTeX
    tailored_latex = await tailor_resume_to_latex(resume_text, parsed_jd.full_text)
    
    # Compile to PDF
    pdf_path = await compile_latex_to_pdf(tailored_latex, compile_id)
    
    return CompileResponse(
        compile_id=compile_id,
        latex_source=tailored_latex,  # NEW: return LaTeX
        pdf_url=f"/resume/{compile_id}/pdf"
    )
```

---

## Verification Plan

### Automated Tests
1. Test PDF ingestion stores full text
2. Test extraction prompt returns valid JSON
3. Test LaTeX generation compiles without errors
4. Test JD tailoring modifies content appropriately

### Manual Verification
1. Upload sample resume → verify text extraction
2. Compile with Adobe SWE JD → verify PDF matches Jake's template
3. Check LaTeX output for proper escaping
4. Verify contact info appears in header

---

## Migration Strategy

> [!CAUTION]
> **Data Migration Required**
> Existing MongoDB documents with atomic units are incompatible with new schema.

**Options:**
1. **Clean slate:** Drop `atomic_units` collection, users re-upload
2. **Migration script:** Convert existing atomic units back to full text (complex)

**Recommendation:** Clean slate - simpler and atomic unit data can't be perfectly reconstructed into original resume format.

---

## Trade-offs Summary

| Feature | Atomic Units (Current) | Full-Text LaTeX (Proposed) |
|---------|----------------------|---------------------------|
| **Complexity** | High | Low |
| **Development Time** | Weeks | Days |
| **User Editing** | Bullet-level in UI | Must edit LaTeX or re-generate |
| **Multi-Job Support** | ✅ Upload once, tailor many | ✅ Upload once, tailor many |
| **Provenance** | Per-bullet tracking | Document-level only |
| **Formatting Control** | Template-based (RenderCV) | Template-based (Jake's) |
| **Dependencies** | RenderCV, Typst | pdflatex (LaTeX) |
| **Cost per Compile** | $0.01-0.02 (score 23 bullets) | $0.05-0.10 (generate full LaTeX) |
