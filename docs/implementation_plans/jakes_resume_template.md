# Jake's Resume Template Integration

## Problem Solved

Instead of trying to preserve the user's original PDF formatting (complex and unreliable), we use **Jake's Resume template** - a professional, widely-used LaTeX template that:
- Provides consistent, clean formatting for all users
- Is ATS-friendly and recruiter-approved
- Can be reliably populated with atomic units
- Compiles to PDF with pdflatex

## Approach

### **Flow:**
```
User uploads PDF → Extract atomic units → AI selects best bullets
    ↓
Populate Jake's template with selected units
    ↓
Compile LaTeX → Professional PDF resume
```

### **Key Insight:**
Users don't need their *exact* original formatting - they need a **professional-looking resume**. Jake's template provides that universally.

---

## Implementation Plan

### Phase 1: Store Jake's Template

#### [NEW] [templates/jakes_resume.tex](file:///Users/xalandames/Documents/SwampHacks%202026/restailor/backend/app/templates/jakes_resume.tex)

**Create template file with placeholders:**

```latex
\documentclass[letterpaper,11pt]{article}
% ... (all the preamble from Jake's template) ...

\begin{document}

%----------HEADING----------
\begin{center}
    \textbf{\Huge \scshape {{NAME}}} \\ \vspace{1pt}
    \small {{PHONE}} $|$ \href{mailto:{{EMAIL}}}{\underline{{{EMAIL}}}} $|$ 
    \href{{{LINKEDIN}}}{\underline{{{LINKEDIN_DISPLAY}}}} $|$
    \href{{{GITHUB}}}{\underline{{{GITHUB_DISPLAY}}}}
\end{center}

%-----------EDUCATION-----------
\section{Education}
  \resumeSubHeadingListStart
{{EDUCATION_ENTRIES}}
  \resumeSubHeadingListEnd

%-----------EXPERIENCE-----------
\section{Experience}
  \resumeSubHeadingListStart
{{EXPERIENCE_ENTRIES}}
  \resumeSubHeadingListEnd

%-----------PROJECTS-----------
\section{Projects}
    \resumeSubHeadingListStart
{{PROJECT_ENTRIES}}
    \resumeSubHeadingListEnd

%-----------PROGRAMMING SKILLS-----------
\section{Technical Skills}
 \begin{itemize}[leftmargin=0.15in, label={}]
    \small{\item{
{{SKILLS_ENTRIES}}
    }}
 \end{itemize}

\end{document}
```

---

### Phase 2: Template Population Service

#### [NEW] [services/template_renderer.py](file:///Users/xalandames/Documents/SwampHacks%202026/restailor/backend/app/services/template_renderer.py)

```python
"""Populate Jake's Resume template with atomic units."""

import os
import subprocess
import tempfile
from typing import Optional
from collections import defaultdict

from app.models import ScoredUnit, AtomicUnit


def load_template() -> str:
    """Load Jake's Resume LaTeX template."""
    template_path = os.path.join(
        os.path.dirname(__file__), 
        "..", 
        "templates", 
        "jakes_resume.tex"
    )
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()


def populate_template(
    selected_units: list[ScoredUnit],
    header_info: Optional[dict] = None
) -> str:
    """
    Fill Jake's template with selected atomic units.
    
    Args:
        selected_units: AI-selected bullets
        header_info: Name, email, phone, etc.
    
    Returns:
        Complete LaTeX source ready to compile
    """
    template = load_template()
    
    # Extract header info
    if header_info:
        template = template.replace("{{NAME}}", header_info.get("name", "Your Name"))
        template = template.replace("{{PHONE}}", header_info.get("phone", "123-456-7890"))
        template = template.replace("{{EMAIL}}", header_info.get("email", "email@example.com"))
        template = template.replace("{{LINKEDIN}}", header_info.get("linkedin", "https://linkedin.com"))
        template = template.replace("{{LINKEDIN_DISPLAY}}", "linkedin.com/in/yourname")
        template = template.replace("{{GITHUB}}", header_info.get("github", "https://github.com"))
        template = template.replace("{{GITHUB_DISPLAY}}", "github.com/yourname")
    
    # Group units by section
    sections = defaultdict(list)
    for unit in selected_units:
        sections[unit.section.value].append(unit)
    
    # Build education entries
    education_latex = build_education_section(sections.get("education", []))
    template = template.replace("{{EDUCATION_ENTRIES}}", education_latex)
    
    # Build experience entries
    experience_latex = build_experience_section(sections.get("experience", []))
    template = template.replace("{{EXPERIENCE_ENTRIES}}", experience_latex)
    
    # Build projects entries
    projects_latex = build_projects_section(sections.get("projects", []))
    template = template.replace("{{PROJECT_ENTRIES}}", projects_latex)
    
    # Build skills entries
    skills_latex = build_skills_section(sections.get("skills", []))
    template = template.replace("{{SKILLS_ENTRIES}}", skills_latex)
    
    return template


def build_education_section(units: list[ScoredUnit]) -> str:
    """Build education section in Jake's format."""
    if not units:
        return ""
    
    latex = ""
    for unit in units:
        org = escape_latex(unit.org or "University")
        role = escape_latex(unit.role or "Degree")
        
        # Format dates
        dates = ""
        if unit.dates:
            start = unit.dates.start or ""
            end = unit.dates.end or ""
            dates = f"{start} -- {end}"
        
        latex += f"""    \\resumeSubheading
      {{{org}}}{{Location}}
      {{{role}}}{{{dates}}}
"""
    
    return latex


def build_experience_section(units: list[ScoredUnit]) -> str:
    """Build experience section with bullets grouped by company."""
    if not units:
        return ""
    
    # Group by company + role
    grouped = defaultdict(list)
    for unit in units:
        key = f"{unit.org}|{unit.role}"
        grouped[key].append(unit)
    
    latex = ""
    for key, bullets in grouped.items():
        org, role = key.split("|")
        org = escape_latex(org or "Company")
        role = escape_latex(role or "Position")
        
        # Get dates from first bullet
        dates = ""
        if bullets[0].dates:
            start = bullets[0].dates.start or ""
            end = bullets[0].dates.end or "Present"
            dates = f"{start} -- {end}"
        
        latex += f"""
    \\resumeSubheading
      {{{role}}}{{{dates}}}
      {{{org}}}{{Location}}
      \\resumeItemListStart
"""
        
        # Add bullets
        for bullet in bullets:
            text = escape_latex(bullet.text)
            latex += f"        \\resumeItem{{{text}}}\n"
        
        latex += "      \\resumeItemListEnd\n"
    
    return latex


def build_projects_section(units: list[ScoredUnit]) -> str:
    """Build projects section."""
    if not units:
        return ""
    
    # Group by project name
    grouped = defaultdict(list)
    for unit in units:
        project_name = unit.org or "Project"
        grouped[project_name].append(unit)
    
    latex = ""
    for project_name, bullets in grouped.items():
        project_name = escape_latex(project_name)
        
        # Extract tech stack from tags
        tech_stack = ", ".join(bullets[0].tags.skills[:5]) if bullets[0].tags.skills else "Technologies"
        
        # Get dates
        dates = ""
        if bullets[0].dates:
            start = bullets[0].dates.start or ""
            end = bullets[0].dates.end or "Present"
            dates = f"{start} -- {end}"
        
        latex += f"""      \\resumeProjectHeading
          {{\\textbf{{{project_name}}} $|$ \\emph{{{tech_stack}}}}}{{{dates}}}
          \\resumeItemListStart
"""
        
        for bullet in bullets:
            text = escape_latex(bullet.text)
            latex += f"            \\resumeItem{{{text}}}\n"
        
        latex += "          \\resumeItemListEnd\n"
    
    return latex


def build_skills_section(units: list[ScoredUnit]) -> str:
    """Build technical skills section."""
    if not units:
        return ""
    
    # Aggregate all skills
    all_skills = []
    for unit in units:
        if unit.tags and unit.tags.skills:
            all_skills.extend(unit.tags.skills)
    
    # Remove duplicates, keep order
    seen = set()
    unique_skills = []
    for skill in all_skills:
        if skill.lower() not in seen:
            seen.add(skill.lower())
            unique_skills.append(skill)
    
    # Group by category (simple heuristic)
    languages = [s for s in unique_skills if s in ["Python", "Java", "C++", "JavaScript", "SQL", "Go", "TypeScript"]]
    frameworks = [s for s in unique_skills if s in ["React", "Node.js", "Flask", "Django", "FastAPI", "Spring"]]
    tools = [s for s in unique_skills if s in ["Git", "Docker", "AWS", "GCP", "Kubernetes", "MongoDB"]]
    
    latex = f"""     \\textbf{{Languages}}{{: {", ".join(languages) if languages else "Python, Java"}}} \\\\
     \\textbf{{Frameworks}}{{: {", ".join(frameworks) if frameworks else "React, Flask"}}} \\\\
     \\textbf{{Developer Tools}}{{: {", ".join(tools) if tools else "Git, Docker"}}}"""
    
    return latex


def escape_latex(text: str) -> str:
    """Escape special LaTeX characters."""
    if not text:
        return ""
    
    replacements = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
    }
    
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    
    return text


async def compile_latex_to_pdf(latex_source: str, output_path: str) -> str:
    """Compile LaTeX to PDF using pdflatex."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Write LaTeX source
        tex_path = os.path.join(tmpdir, "resume.tex")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(latex_source)
        
        # Compile (run twice for references)
        for _ in range(2):
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "resume.tex"],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=30
            )
        
        # Copy PDF to output
        pdf_path = os.path.join(tmpdir, "resume.pdf")
        if os.path.exists(pdf_path):
            import shutil
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            shutil.copy(pdf_path, output_path)
            return output_path
        else:
            raise RuntimeError("PDF compilation failed")
```

---

### Phase 3: Update Renderer Service

#### [MODIFY] [renderer.py](file:///Users/xalandames/Documents/SwampHacks%202026/restailor/backend/app/services/renderer.py)

**Replace entire file with:**

```python
"""Resume rendering using Jake's Resume template."""

import os
from app.models import ScoredUnit
from app.services.template_renderer import populate_template, compile_latex_to_pdf
from app.db.mongodb import get_database


async def render_resume(
    compile_id: str,
    selected_units: list[ScoredUnit],
    master_version_id: str
) -> str:
    """
    Render resume using Jake's template.
    
    1. Get header info from master resume
    2. Populate Jake's template with selected units
    3. Compile to PDF
    4. Return path
    """
    # Get header info
    db = await get_database()
    header_unit = await db.atomic_units.find_one({
        "version": master_version_id,
        "type": "header"
    })
    
    # Extract header data
    header_info = extract_header_info(header_unit) if header_unit else None
    
    # Populate template
    latex_source = populate_template(selected_units, header_info)
    
    # Create output directory
    output_dir = f"output/{compile_id}"
    os.makedirs(output_dir, exist_ok=True)
    
    # Save LaTeX source (for debugging)
    tex_path = f"{output_dir}/resume.tex"
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(latex_source)
    
    # Compile to PDF
    pdf_path = f"{output_dir}/resume.pdf"
    await compile_latex_to_pdf(latex_source, pdf_path)
    
    return pdf_path


def extract_header_info(header_unit: dict) -> dict:
    """Extract name, email, phone from header unit."""
    text = header_unit.get("text", "")
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    info = {
        "name": lines[0] if lines else "Your Name",
        "email": "",
        "phone": "",
        "linkedin": "",
        "github": ""
    }
    
    # Simple extraction (can be improved with regex)
    for line in lines:
        if '@' in line:
            info["email"] = line
        elif any(char.isdigit() for char in line) and '-' in line:
            info["phone"] = line
        elif 'linkedin' in line.lower():
            info["linkedin"] = line
        elif 'github' in line.lower():
            info["github"] = line
    
    return info
```

---

## Benefits of This Approach

✅ **100% Reliable** - No PDF editing complexity  
✅ **Professional Output** - Jake's template is recruiter-approved  
✅ **Consistent** - All users get same high-quality formatting  
✅ **ATS-Friendly** - Template is designed for applicant tracking systems  
✅ **Fast** - Simple template population + LaTeX compilation  
✅ **No White Space Issues** - LaTeX reflows text automatically  
✅ **Easy to Maintain** - One template to update/improve  

---

## Verification Plan

### Test 1: Basic Compilation

```bash
cd /Users/xalandames/Documents/SwampHacks\ 2026/restailor/backend

# Test template population
python3 -c "
from app.services.template_renderer import populate_template
from app.models import ScoredUnit

# Create test units
units = [...]  # Sample units

latex = populate_template(units, {'name': 'Test User'})
print(latex[:500])
"
```

### Test 2: End-to-End

1. Upload resume → Extract atomic units
2. Parse job description
3. Compile resume
4. Download PDF
5. **Verify**: PDF looks professional and matches Jake's template style

---

## Dependencies

**System Requirements:**
```bash
# Install LaTeX (if not already installed)
brew install --cask mactex  # macOS
```

**Already have:**
- PyMuPDF (for PDF text extraction during ingestion)
- Pydantic (for models)

---

## Timeline

- **Phase 1** (30 min): Create template file with placeholders
- **Phase 2** (1 hour): Implement template_renderer.py
- **Phase 3** (30 min): Update renderer.py
- **Testing** (30 min): End-to-end test

**Total**: ~2.5 hours to implement

---

## Future Enhancements

1. **Multiple Templates**: Offer 2-3 template options
2. **Custom Styling**: Let users choose colors/fonts
3. **Smart Header Extraction**: Better parsing of contact info
4. **Section Ordering**: Let users reorder sections
