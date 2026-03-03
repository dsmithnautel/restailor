"""Job Description parsing models."""

from datetime import datetime

from pydantic import BaseModel, Field


class StrategicPillar(BaseModel):
    """A strategic focus area extracted from the JD, with grouped keywords."""

    pillar_name: str
    priority: int = 1
    context: str = ""
    keywords: list[str] = Field(default_factory=list)


class JDParseRequest(BaseModel):
    """Request to parse a job description."""

    url: str | None = None  # URL to scrape
    text: str | None = None  # Raw JD text (fallback)

    class Config:
        json_schema_extra = {"example": {"url": "https://careers.google.com/jobs/123"}}


class ParsedJD(BaseModel):
    """
    Structured representation of a job description.
    Extracted via Gemini for narrative-aware tailoring.
    """

    jd_id: str = Field(..., description="Unique identifier for this JD")
    role_title: str
    company: str

    # Narrative fields
    seniority_level: str | None = Field(
        default=None,
        description="intern | entry | mid | senior | staff",
    )
    business_mission: str = Field(
        default="",
        description="What the company/team is trying to achieve",
    )
    strategic_pillars: list[StrategicPillar] = Field(
        default_factory=list,
        description="Prioritized focus areas with grouped keywords",
    )
    soft_signals: list[str] = Field(
        default_factory=list,
        description="Cultural/behavioral signals (e.g. Collaborative, Fast-paced)",
    )
    team_structure: str | None = Field(
        default=None,
        description="cross-functional | embedded | solo",
    )
    impact_language: list[str] = Field(
        default_factory=list,
        description="Verbs/phrases the JD uses for success (e.g. scale, ship, innovate)",
    )

    # Kept for backward compatibility (optimizer uses must_haves)
    must_haves: list[str] = Field(
        default_factory=list, description="Required skills/qualifications"
    )
    nice_to_haves: list[str] = Field(
        default_factory=list, description="Preferred qualifications"
    )

    # Legacy fields — default to empty so old MongoDB docs still load
    responsibilities: list[str] = Field(
        default_factory=list, description="(Legacy) Key job duties"
    )
    keywords: list[str] = Field(
        default_factory=list, description="(Legacy) Technical terms, tools, frameworks"
    )

    source_url: str | None = None
    raw_text: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "jd_id": "jd_google_swe_20260124",
                "role_title": "Software Engineer",
                "company": "Google",
                "seniority_level": "entry",
                "business_mission": "Build scalable infrastructure powering Google Search.",
                "strategic_pillars": [
                    {
                        "pillar_name": "Distributed Systems",
                        "priority": 1,
                        "context": "Design and maintain large-scale backend services.",
                        "keywords": ["Python", "Go", "gRPC", "Kubernetes"],
                    }
                ],
                "soft_signals": ["Collaborative", "Data-driven"],
                "team_structure": "cross-functional",
                "impact_language": ["scale", "optimize", "ship"],
                "must_haves": [
                    "3+ years Python experience",
                    "Distributed systems knowledge",
                    "BS in Computer Science",
                ],
                "nice_to_haves": ["Kubernetes experience", "ML/AI background"],
            }
        }
