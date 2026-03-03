"""LLM-based resume renderer using Gemini + Tectonic/pdflatex."""

import json
import os
import re

from app.db.mongodb import get_database
from app.models import ScoredUnit
from app.services.gemini import generate_text
from app.services.prompts import generate_latex_prompt
from app.services.tectonic import compile_pdf


def _format_resume_data(header_info: dict, units: list[dict]) -> str:
    """Format header + units into a structured text block for the LLM prompt."""
    parts = []

    name = header_info.get("name", "Your Name")
    email = header_info.get("email", "")
    phone = header_info.get("phone", "")
    linkedin = header_info.get("linkedin", "")
    github = header_info.get("github", "")

    parts.append(f"Name: {name}")
    if phone:
        parts.append(f"Phone: {phone}")
    if email:
        parts.append(f"Email: {email}")
    if linkedin:
        parts.append(f"LinkedIn: {linkedin}")
    if github:
        parts.append(f"GitHub: {github}")
    parts.append("")

    from collections import OrderedDict
    sections: OrderedDict[str, list[dict]] = OrderedDict()
    for u in units:
        sec = (u.get("section") or "other").lower()
        if sec == "other":
            continue  # Drop content that doesn't map to a Jake's template section
        if sec not in sections:
            sections[sec] = []
        sections[sec].append(u)

    section_order = ["education", "experience", "projects", "leadership", "skills"]
    for sec in sections:
        if sec not in section_order:
            section_order.append(sec)

    for sec_name in section_order:
        if sec_name not in sections:
            continue
        sec_units = sections[sec_name]
        title = sec_name.replace("_", " ").title()
        if sec_name == "skills":
            title = "Technical Skills"

        parts.append(f"=== {title} ===")

        current_org = None
        current_role = None
        last_edu_org = None  # Track last education org for grouping GPA/coursework
        for u in sec_units:
            org = u.get("org") or ""
            role = u.get("role") or ""
            dates = u.get("dates")

            # For education section: inherit last-seen org if this unit has no org
            # This groups GPA/coursework bullets under their parent college
            if sec_name == "education":
                if org:
                    last_edu_org = org
                elif not org and last_edu_org:
                    org = last_edu_org

            if org != current_org or role != current_role:
                current_org = org
                current_role = role
                header_line = ""
                if role and org:
                    header_line = f"{role} | {org}"
                elif role:
                    header_line = role
                elif org:
                    header_line = org

                # Only include dates if actually provided (never fabricate)
                date_str = _format_dates(dates) if dates else ""
                if date_str:
                    header_line += f" | {date_str}"

                # For projects: include technology/skill tags if present
                if sec_name == "projects" and u.get("type") == "project":
                    tags = u.get("tags") or {}
                    skills = tags.get("skills", [])
                    if skills:
                        header_line += f" | {', '.join(skills)}"

                if header_line:
                    parts.append(f"\n{header_line}")

            text = u.get("text", "")
            # Clean embedded newlines from PDF extraction (e.g. "Algorithm Abstraction\nand Analysis")
            text = text.replace("\n", " ").strip()
            if text:
                # For education bullets: only keep GPA and Relevant Coursework
                # Drop everything else (e.g. "Member of:", club lists)
                if sec_name == "education" and u.get("type") == "bullet":
                    text_lower = text.lower().strip()
                    if text_lower.startswith("gpa"):
                        gpa_value = text.split(":", 1)[-1].strip() if ":" in text else text
                        text = f"GPA: {gpa_value}"
                    elif text_lower.startswith("relevant coursework"):
                        cw_value = text.split(":", 1)[-1].strip() if ":" in text else text
                        text = f"Relevant Coursework: {cw_value}"
                    else:
                        continue  # Skip non-GPA/coursework education bullets
                parts.append(f"  - {text}")

        parts.append("")

    return "\n".join(parts)


def _format_dates(dates: dict | str | None) -> str:
    if not dates:
        return ""
    if isinstance(dates, str):
        return dates
    months = [
        "", "Jan.", "Feb.", "Mar.", "Apr.", "May", "June",
        "July", "Aug.", "Sep.", "Oct.", "Nov.", "Dec.",
    ]
    def fmt(d: str | None) -> str:
        if not d:
            return ""
        p = d.split("-")
        if len(p) == 2:
            m = int(p[1])
            return f"{months[m]} {p[0]}"
        return d
    start = fmt(dates.get("start"))
    end = fmt(dates.get("end"))
    # Only use "Present" if there IS a start date but no end date (ongoing entry)
    # If both are empty, return nothing — don't fabricate dates
    if start and not end:
        end = "Present"
    if start and end:
        return f"{start} -- {end}"
    return start or end


def _clean_latex_response(text: str) -> str:
    """Strip markdown fences, unsupported commands, and extra text from LLM LaTeX output."""
    text = text.strip()
    if text.startswith("```"):
        match = re.search(r"```(?:latex)?\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()

    doc_start = text.find(r"\documentclass")
    if doc_start > 0:
        text = text[doc_start:]

    doc_end = text.rfind(r"\end{document}")
    if doc_end > 0:
        text = text[: doc_end + len(r"\end{document}")]

    # Remove commands unsupported by Tectonic
    text = re.sub(r"\\input\{glyphtounicode\}\s*\n?", "", text)
    text = re.sub(r"\\pdfgentounicode=1\s*\n?", "", text)

    return text


async def render_resume(
    compile_id: str, selected_units: list[ScoredUnit], master_version_id: str
) -> tuple[str, str]:
    """
    Render resume using LLM-based LaTeX generation + PDF compilation.

    1. Get header info from master resume
    2. Format resume data as structured text
    3. Send to Gemini with Jake's Resume template prompt
    4. Clean up LLM response
    5. Compile to PDF via Tectonic
    6. Save PDF + .tex to output directory
    7. Return (pdf_path, latex_source)
    """
    db = await get_database()

    header_cursor = db.atomic_units.find({"version": master_version_id, "type": "header"})
    header_units = [doc async for doc in header_cursor]
    header_info = extract_header_info(header_units)

    units_for_prompt = [
        {
            "text": u.text,
            "section": u.section,
            "org": u.org,
            "role": u.role,
            "dates": u.dates,
        }
        for u in selected_units
    ]

    resume_data = _format_resume_data(header_info, units_for_prompt)
    prompt = generate_latex_prompt(resume_data)

    latex_content = await generate_text(prompt)
    latex_content = _clean_latex_response(latex_content)

    pdf_bytes = await compile_pdf(latex_content)

    output_dir = os.path.abspath(f"output/{compile_id}")
    os.makedirs(output_dir, exist_ok=True)

    tex_path = os.path.join(output_dir, "cv.tex")
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(latex_content)

    pdf_path = os.path.join(output_dir, "resume.pdf")
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    return pdf_path, latex_content


async def render_from_units(header_info: dict, units: list[dict]) -> tuple[bytes, str]:
    """
    Render a PDF from header + unit dicts (used by the preview endpoint).

    Returns (pdf_bytes, latex_source).
    """
    resume_data = _format_resume_data(header_info, units)
    prompt = generate_latex_prompt(resume_data)

    latex_content = await generate_text(prompt)
    latex_content = _clean_latex_response(latex_content)

    pdf_bytes = await compile_pdf(latex_content)
    return pdf_bytes, latex_content


def extract_header_info(header_units: list[dict]) -> dict:
    """
    Extract name, email, phone, LinkedIn, GitHub from header units.
    Prioritizes structured 'tags' from ingestion, then falls back to regex on text.
    """
    if not header_units:
        return {}

    info = {
        "name": "Your Name",
        "email": "",
        "phone": "",
        "linkedin": "",
        "github": "",
    }

    full_text_parts = []

    for unit in header_units:
        if unit.get("text"):
            full_text_parts.append(unit["text"])
            if info["name"] == "Your Name":
                info["name"] = unit["text"]

        tags = unit.get("tags") or {}
        if isinstance(tags, dict):
            if tags.get("email"):
                info["email"] = tags["email"]
            if tags.get("phone"):
                info["phone"] = tags["phone"]
            if tags.get("linkedin"):
                info["linkedin"] = tags["linkedin"]
            if tags.get("github"):
                info["github"] = tags["github"]

    full_text = "\n".join(full_text_parts)
    lines = [line.strip() for line in full_text.split("\n") if line.strip()]

    if not info["email"]:
        email_pattern = r"[\w\.-]+@[\w\.-]+\.\w+"
        for line in lines:
            if match := re.search(email_pattern, line):
                info["email"] = match.group(0)
                break

    if not info["phone"]:
        phone_pattern = r"\(?\d{3}\)?[\s\-\.]?\d{3}[\s\-\.]?\d{4}"
        for line in lines:
            if match := re.search(phone_pattern, line):
                info["phone"] = match.group(0).strip()
                break

    if not info["linkedin"]:
        for line in lines:
            if "linkedin.com" in line.lower():
                if match := re.search(r"https?://[^\s]+", line):
                    info["linkedin"] = match.group(0)
                else:
                    clean = line.replace("|", "").strip()
                    for part in clean.split():
                        if "linkedin.com" in part:
                            info["linkedin"] = (
                                f"https://{part}" if not part.startswith("http") else part
                            )
                            break
                break

    if not info["github"]:
        for line in lines:
            if "github.com" in line.lower():
                if match := re.search(r"https?://[^\s]+", line):
                    info["github"] = match.group(0)
                else:
                    clean = line.replace("|", "").strip()
                    for part in clean.split():
                        if "github.com" in part:
                            info["github"] = (
                                f"https://{part}" if not part.startswith("http") else part
                            )
                            break
                break

    return info
