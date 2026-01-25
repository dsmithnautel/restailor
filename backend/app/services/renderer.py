"""Resume rendering using Jake's Resume LaTeX template."""

import os
import re
from app.models import ScoredUnit
from app.services.template_renderer import populate_template, compile_latex_to_pdf
from app.db.mongodb import get_database


async def render_resume(
    compile_id: str,
    selected_units: list[ScoredUnit],
    master_version_id: str
) -> str:
    """
    Render resume using Jake's Resume template.
    
    1. Get header info from master resume
    2. Populate Jake's template with selected units
    3. Compile to PDF
    4. Return path to generated PDF
    
    Args:
        compile_id: Unique compilation ID
        selected_units: AI-selected atomic units
        master_version_id: Master resume version ID
    
    Returns:
        Path to generated PDF
    """
    # Get header info from database
    db = await get_database()
    header_unit = await db.atomic_units.find_one({
        "version": master_version_id,
        "type": "header"
    })
    
    # Extract header data
    header_info = extract_header_info(header_unit) if header_unit else None
    
    # Populate template with selected units
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
    """
    Extract name, email, phone, LinkedIn, GitHub from header unit.
    
    Args:
        header_unit: Header atomic unit from database
    
    Returns:
        Dictionary with extracted contact information
    """
    text = header_unit.get("text", "")
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    info = {
        "name": lines[0] if lines else "Your Name",
        "email": "",
        "phone": "",
        "linkedin": "",
        "github": ""
    }
    
    # Extract email (look for @ symbol)
    email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
    for line in lines:
        email_match = re.search(email_pattern, line)
        if email_match:
            info["email"] = email_match.group(0)
            break
    
    # Extract phone (look for phone number patterns)
    phone_pattern = r'[\d\-\(\)\s]{10,}'
    for line in lines:
        if any(char.isdigit() for char in line):
            phone_match = re.search(phone_pattern, line)
            if phone_match:
                info["phone"] = phone_match.group(0).strip()
                break
    
    # Extract LinkedIn
    for line in lines:
        if 'linkedin.com' in line.lower():
            # Try to extract URL
            url_match = re.search(r'https?://[^\s]+', line)
            if url_match:
                info["linkedin"] = url_match.group(0)
            else:
                info["linkedin"] = f"https://linkedin.com/in/{line.split('/')[-1]}"
            break
    
    # Extract GitHub
    for line in lines:
        if 'github.com' in line.lower():
            # Try to extract URL
            url_match = re.search(r'https?://[^\s]+', line)
            if url_match:
                info["github"] = url_match.group(0)
            else:
                info["github"] = f"https://github.com/{line.split('/')[-1]}"
            break
    
    return info
