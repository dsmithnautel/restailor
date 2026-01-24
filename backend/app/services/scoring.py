"""LLM-based scoring service for atomic units against job descriptions."""

import json
from typing import Any

from app.models import ParsedJD, ScoredUnit
from app.services.gemini import generate_json


SCORING_PROMPT = """
You are a resume expert. Score each resume bullet against this job description.

For EACH bullet, evaluate how relevant it is to the JD requirements and return:
- id: the bullet's ID (provided)
- score: 0-10 (10 = perfect match, 0 = completely irrelevant)
- matched_requirements: which specific JD requirements this bullet addresses
- reasoning: brief explanation of the score (1-2 sentences)

Scoring guidelines:
- 9-10: Directly addresses a must-have requirement with specific, quantified impact
- 7-8: Strongly relevant to responsibilities or uses key required skills
- 5-6: Somewhat relevant, demonstrates transferable skills
- 3-4: Tangentially related
- 0-2: Not relevant to this role

JOB DESCRIPTION:
Company: {company}
Role: {role_title}

Must-Have Requirements:
{must_haves}

Key Responsibilities:
{responsibilities}

Technical Keywords: {keywords}

---

RESUME BULLETS TO SCORE:
{bullets_json}

---

Return a JSON array with one object per bullet:
[
  {{"id": "bullet_id", "score": 8.5, "matched_requirements": ["Python", "APIs"], "reasoning": "Shows API development experience..."}},
  ...
]
"""


async def score_units_against_jd(
    units: list[dict[str, Any]],
    parsed_jd: ParsedJD
) -> list[ScoredUnit]:
    """
    Score atomic units against a job description using Gemini LLM.
    
    This is the core of the LLM-direct scoring approach:
    1. Format all units + JD into a prompt
    2. Let Gemini score each unit holistically
    3. Parse results into ScoredUnit objects
    """
    # Filter to scoreable units (bullets, projects, not headers/skills)
    scoreable = [u for u in units if u.get("type") in ["bullet", "project", "education"]]
    
    if not scoreable:
        return []
    
    # Prepare bullets for the prompt
    bullets_for_prompt = []
    for u in scoreable:
        bullets_for_prompt.append({
            "id": u.get("id"),
            "text": u.get("text"),
            "section": u.get("section"),
            "org": u.get("org"),
            "role": u.get("role")
        })
    
    # Format the prompt
    prompt = SCORING_PROMPT.format(
        company=parsed_jd.company,
        role_title=parsed_jd.role_title,
        must_haves="\n".join(f"- {req}" for req in parsed_jd.must_haves),
        responsibilities="\n".join(f"- {resp}" for resp in parsed_jd.responsibilities),
        keywords=", ".join(parsed_jd.keywords),
        bullets_json=json.dumps(bullets_for_prompt, indent=2)
    )
    
    # Get scores from Gemini
    try:
        scores_raw = await generate_json(prompt)
    except Exception as e:
        # On failure, return units with default scores
        return [
            ScoredUnit(
                unit_id=u.get("id"),
                text=u.get("text", ""),
                section=u.get("section", "experience"),
                org=u.get("org"),
                role=u.get("role"),
                llm_score=5.0,
                matched_requirements=[],
                reasoning="Scoring failed - default score applied"
            )
            for u in scoreable
        ]
    
    # Map scores back to units
    score_map = {s["id"]: s for s in scores_raw}
    
    scored_units = []
    for u in scoreable:
        unit_id = u.get("id")
        score_data = score_map.get(unit_id, {})
        
        scored_units.append(ScoredUnit(
            unit_id=unit_id,
            text=u.get("text", ""),
            section=u.get("section", "experience"),
            org=u.get("org"),
            role=u.get("role"),
            llm_score=float(score_data.get("score", 5.0)),
            matched_requirements=score_data.get("matched_requirements", []),
            reasoning=score_data.get("reasoning", "")
        ))
    
    # Sort by score descending
    scored_units.sort(key=lambda x: x.llm_score, reverse=True)
    
    return scored_units
