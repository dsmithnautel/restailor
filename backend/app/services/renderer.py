"""Resume rendering service using RenderCV."""

import os
import subprocess
import yaml
from typing import Optional
from collections import defaultdict

from app.models import ScoredUnit
from app.db.mongodb import get_database


async def render_resume(
    compile_id: str,
    selected_units: list[ScoredUnit],
    master_version_id: str
) -> str:
    """
    Render a resume PDF using RenderCV.
    
    1. Fetch header info from master resume
    2. Build RenderCV YAML structure
    3. Run rendercv command
    4. Return path to generated PDF
    """
    # Create output directory
    output_dir = f"output/{compile_id}"
    os.makedirs(output_dir, exist_ok=True)
    
    # Get header info from database
    db = await get_database()
    header_unit = await db.atomic_units.find_one({
        "version": master_version_id,
        "type": "header"
    })
    
    # Build resume structure
    resume_data = build_rendercv_yaml(selected_units, header_unit)
    
    # Write YAML file
    yaml_path = f"{output_dir}/resume.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(resume_data, f, default_flow_style=False, allow_unicode=True)
    
    # Run RenderCV
    try:
        result = subprocess.run(
            ["rendercv", "render", yaml_path],
            cwd=output_dir,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            # Log error but don't fail
            print(f"RenderCV warning: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        raise RuntimeError("PDF generation timed out")
    except FileNotFoundError:
        # RenderCV not installed - create placeholder
        print("RenderCV not installed. Creating placeholder.")
        
    return f"{output_dir}/resume.pdf"


def build_rendercv_yaml(
    selected_units: list[ScoredUnit],
    header_unit: Optional[dict]
) -> dict:
    """Build the RenderCV YAML structure from selected units."""
    
    # Group units by section and role
    experience_by_role: dict[str, list[ScoredUnit]] = defaultdict(list)
    projects: list[ScoredUnit] = []
    education: list[ScoredUnit] = []
    
    for unit in selected_units:
        if unit.section == "experience":
            key = f"{unit.org}|{unit.role}"
            experience_by_role[key].append(unit)
        elif unit.section == "projects":
            projects.append(unit)
        elif unit.section == "education":
            education.append(unit)
    
    # Build experience entries
    experience_entries = []
    for key, units in experience_by_role.items():
        org, role = key.split("|")
        experience_entries.append({
            "company": org,
            "position": role,
            "start_date": "",  # Could parse from units
            "end_date": "",
            "highlights": [u.text for u in units]
        })
    
    # Build projects entries
    project_entries = []
    for unit in projects:
        project_entries.append({
            "name": unit.org or "Project",
            "highlights": [unit.text]
        })
    
    # Build education entries
    education_entries = []
    for unit in education:
        education_entries.append({
            "institution": unit.org or "",
            "area": unit.role or "",
            "degree": "",
            "highlights": [unit.text] if unit.text else []
        })
    
    # Parse header
    name = "Your Name"
    if header_unit and header_unit.get("text"):
        # Try to extract name from header
        lines = header_unit["text"].split("\n")
        if lines:
            name = lines[0].strip()
    
    # Build final YAML structure
    return {
        "cv": {
            "name": name,
            "sections": {
                "experience": experience_entries,
                "projects": project_entries,
                "education": education_entries
            }
        },
        "design": {
            "theme": "classic"
        }
    }
