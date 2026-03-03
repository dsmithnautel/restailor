# Implementation Plan - Migration to RenderCV

## Goal
Replace the custom, fragile LaTeX string-replacement backend with the robust **RenderCV** library. This ensures the output PDF perfectly matches the "Jake's Resume" (sb2nov) template and handles all formatting edge cases (page breaks, special characters, missing sections) automatically.

## Proposed Changes

### 1. Dependencies
- Add `rendercv` to the project.

### 2. Data Mapping Service (`app/services/rendercv_mapper.py`) [NEW]
- **Purpose:** Transform our internal `ScoredUnit` list into the specific YAML/JSON structure required by RenderCV.
- **Logic:**
    -  **CV Model:**
       ```json
       {
         "cv": {
           "name": "Name",
           "phone": "...",
           "email": "...",
           "social_networks": [...], # GitHub, LinkedIn
           "sections": {
             "education": [...],
             "experience": [...], # Grouped by Company
             "projects": [...],   # Grouped by Project
             "leadership": [...], # Grouped by Org?
             "skills": [...]      # List of strings
           }
         },
         "design": {
           "theme": "sb2nov"
         }
       }
       ```
    -  **Grouping:** We must group our flat list of units into these nested structures (similar to what we did in `template_renderer.py` but mapping to dicts instead of strings).

### 3. Renderer Service (`app/services/renderer.py`)
- **Action:** Rewrite `render_resume`.
- **New Flow:**
    1.  Fetch units & header info (same as before).
    2.  Call `rendercv_mapper.map_to_rendercv_model(units, header)`.
    3.  Dump to a temporary YAML file.
    4.  Call `rendercv` CLI or Python API to generate the PDF.
    5.  Return the path.

### 4. Cleanup
- Remove `app/services/template_renderer.py` (no longer needed).
- Remove `app/templates/jakes_resume.tex` (RenderCV handles the templates internally).

## Verification
-  **Automated:** Verify `rendercv` is installed and reachable.
-  **Manual:** Generate a resume and check that:
    -  It uses the "Jake's Resume" style.
    -  All content (Education, Exp, Projects, Leadership, Skills) is present.
    -  Formatting is correct.
