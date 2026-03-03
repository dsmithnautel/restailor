"""Job Description parsing service."""

import uuid
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from app.models import ParsedJD
from app.models.job_description import StrategicPillar
from app.services.gemini import generate_json

JD_EXTRACTION_PROMPT = """
You are an expert career strategist. Analyze this job description and extract a narrative-aware understanding of what the employer is looking for.

Return a JSON object with:
{
  "role_title": "exact job title",
  "company": "company name",
  "seniority_level": "intern" | "entry" | "mid" | "senior" | "staff" | null,
  "business_mission": "A 1-2 sentence summary of what this company/team is trying to achieve. Focus on the business goal, not the job duties.",
  "strategic_pillars": [
    {
      "pillar_name": "Short label for this focus area (e.g. 'Backend Infrastructure', 'ML & Data')",
      "priority": 1,
      "context": "Why this area matters for the role — what problems they are solving.",
      "keywords": ["specific tools", "frameworks", "technologies", "methodologies"]
    }
  ],
  "soft_signals": ["Cultural or behavioral traits emphasized (e.g. 'Collaborative', 'Self-starter', 'Detail-oriented')"],
  "team_structure": "cross-functional" | "embedded" | "solo" | null,
  "impact_language": ["Verbs and phrases the JD uses to describe success, e.g. 'scale', 'ship', 'drive', 'optimize'"],
  "must_haves": ["required qualification 1", "required qualification 2"],
  "nice_to_haves": ["preferred qualification 1"]
}

RULES:
- strategic_pillars: Group related keywords into 2-4 thematic areas. Assign priority 1 to the most-emphasized area, 2 to secondary, etc. Each pillar should have a context explaining WHY these skills matter for the role.
- seniority_level: Infer from years of experience requirements, language tone, and scope of responsibilities.
- business_mission: Synthesize from company description, team description, and product context. If not stated, infer from the role's goals.
- soft_signals: Extract from phrases about culture, values, or working style.
- team_structure: "cross-functional" if multiple teams/stakeholders mentioned, "embedded" if within a single team, "solo" if independent contributor, null if unclear.
- impact_language: Pull the exact action verbs and outcome phrases used in the JD.
- must_haves: Items with "required", "must have", "minimum", "X+ years required".
- nice_to_haves: Items with "preferred", "bonus", "nice to have", "ideally", "plus".
- keywords within pillars should be SPECIFIC tools/technologies/frameworks, not generic terms.

Job Description:
"""


async def scrape_url(url: str) -> str:
    """Scrape text content from a job posting URL."""
    try:
        # Try trafilatura first (better for job boards)
        import trafilatura

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )
            response.raise_for_status()
            html = response.text

        # Extract main content
        text = trafilatura.extract(html)

        if text and len(text) > 100:
            return text

        # Fallback to BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()

        # Get text
        text = soup.get_text(separator="\n", strip=True)

        return text

    except Exception as e:
        raise ValueError(f"Failed to scrape URL: {str(e)}")


async def parse_job_description(url: str | None = None, text: str | None = None) -> ParsedJD:
    """
    Parse a job description from URL or text.

    Uses Gemini to extract narrative-aware structured requirements.
    """
    # Get the JD text
    if url:
        try:
            jd_text = await scrape_url(url)
        except Exception as e:
            if text:
                jd_text = text
            else:
                raise ValueError(f"Failed to scrape URL and no fallback text provided: {e}")
    elif text:
        jd_text = text
    else:
        raise ValueError("Either url or text must be provided")

    # Generate unique ID
    jd_id = f"jd_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"

    # Extract structured data using Gemini
    prompt = JD_EXTRACTION_PROMPT + jd_text[:8000]  # Limit to avoid token limits

    try:
        result = await generate_json(prompt)
    except Exception:
        # Return minimal parsed JD on failure
        return ParsedJD(
            jd_id=jd_id,
            role_title="Unknown",
            company="Unknown",
            must_haves=[],
            nice_to_haves=[],
            source_url=url,
            raw_text=jd_text[:5000],
        )

    # Parse strategic pillars
    raw_pillars = result.get("strategic_pillars", [])
    pillars = []
    for p in raw_pillars:
        pillars.append(
            StrategicPillar(
                pillar_name=p.get("pillar_name", ""),
                priority=p.get("priority", 1),
                context=p.get("context", ""),
                keywords=p.get("keywords", []),
            )
        )
    # Sort by priority
    pillars.sort(key=lambda p: p.priority)

    return ParsedJD(
        jd_id=jd_id,
        role_title=result.get("role_title") or "Unknown",
        company=result.get("company") or "Unknown",
        seniority_level=result.get("seniority_level"),
        business_mission=result.get("business_mission", ""),
        strategic_pillars=pillars,
        soft_signals=result.get("soft_signals", []),
        team_structure=result.get("team_structure"),
        impact_language=result.get("impact_language", []),
        must_haves=result.get("must_haves", []),
        nice_to_haves=result.get("nice_to_haves", []),
        source_url=url,
        raw_text=jd_text[:5000],
    )
