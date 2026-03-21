"""
SkillSpark AI — API Schemas
---------------------------------
Pydantic models for all API request and response types.

Every API endpoint uses these models for:
  - Request validation (FastAPI auto-validates)
  - Response serialisation
  - OpenAPI docs generation (auto from Pydantic)

Pydantic catches bad input BEFORE it reaches
your logic — zero hallucination from malformed data.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


# ══════════════════════════════════════════════════════════════════
# REQUEST SCHEMAS
# ══════════════════════════════════════════════════════════════════

# ── Upload request ────────────────────────────────────────────────

class UploadResponse(BaseModel):
    """
    Response after uploading resume or JD file.
    Returns parsed text and detected sections.
    """
    success:    bool
    file_type:  str
    raw_text:   str
    sections:   dict[str, str]
    metadata:   dict
    message:    str


# ── Analyse request ───────────────────────────────────────────────

class AnalyseRequest(BaseModel):
    """
    Request to analyse skill gaps between
    resume and job description.
    """
    resume_text:   str = Field(
        ...,
        min_length=50,
        description="Parsed resume text"
    )
    jd_text:       str = Field(
        ...,
        min_length=20,
        description="Job description text"
    )
    job_title:     str = Field(
        default="Target Role",
        description="Job title from JD"
    )
    domain:        Optional[str] = Field(
        default=None,
        description="Force domain: 'tech' or 'ops'. Auto-detected if None."
    )

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v):
        if v is not None and v not in {"tech", "ops"}:
            raise ValueError("domain must be 'tech' or 'ops'")
        return v


# ── Skill score (internal) ────────────────────────────────────────

class SkillScoreSchema(BaseModel):
    """
    Represents a single skill with confidence scores.
    Used internally between analyse and pathway steps.
    """
    skill_id:             str
    display_name:         str
    candidate_confidence: float = Field(ge=0.0, le=1.0)
    required_confidence:  float = Field(ge=0.0, le=1.0)
    importance_weight:    float = Field(ge=0.0, le=1.0)
    domain:               str
    context:              str = ""
    section:              str = "skills"


# ── Pathway request ───────────────────────────────────────────────

class PathwayRequest(BaseModel):
    """
    Request to generate learning pathway.
    Receives gap analysis results from /analyse.
    """
    resume_text:      str = Field(..., min_length=50)
    jd_text:          str = Field(..., min_length=20)
    job_title:        str = Field(default="Target Role")
    domain:           str = Field(default="tech")
    known_skills:     list[str] = Field(
        default=[],
        description="Skills candidate already knows — pre-skipped"
    )

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v):
        if v not in {"tech", "ops"}:
            raise ValueError("domain must be 'tech' or 'ops'")
        return v


# ── Reroute request ───────────────────────────────────────────────

class RerouteRequest(BaseModel):
    """
    Request to skip a skill and recalculate pathway.
    """
    skill_id:      str = Field(
        ...,
        description="Canonical skill id to skip"
    )
    current_path:  list[str] = Field(
        ...,
        min_length=1,
        description="Current ordered pathway"
    )
    skipped:       list[str] = Field(
        default=[],
        description="Already skipped skills"
    )
    completed:     list[str] = Field(
        default=[],
        description="Already completed skills"
    )
    catalog_data:  Optional[dict] = Field(
        default=None,
        description="Catalog data for hours calculation"
    )


# ══════════════════════════════════════════════════════════════════
# RESPONSE SCHEMAS
# ══════════════════════════════════════════════════════════════════

# ── Resource schema ───────────────────────────────────────────────

class ResourceSchema(BaseModel):
    """Learning resource with title and URL."""
    title: str
    url:   str


# ── Gap result schema ─────────────────────────────────────────────

class GapResultSchema(BaseModel):
    """
    Single skill gap result.
    Returned by /analyse endpoint.
    """
    skill_id:             str
    display_name:         str
    candidate_confidence: float
    required_confidence:  float
    importance_weight:    float
    gap_score:            float
    priority_score:       float
    domain:               str
    is_missing:           bool
    is_weak:              bool
    prerequisites:        list[str] = []
    unlocks:              list[str] = []


# ── Gap summary schema ────────────────────────────────────────────

class GapSummarySchema(BaseModel):
    """Summary statistics for gap analysis."""
    total_gaps:              int
    missing_skills:          int
    weak_skills:             int
    avg_gap_score:           float
    avg_priority_score:      float
    highest_priority_skill:  Optional[str]


# ── Analyse response ──────────────────────────────────────────────

class AnalyseResponse(BaseModel):
    """
    Response from /analyse endpoint.
    Contains gap analysis results and domain classification.
    """
    success:           bool
    domain:            str
    domain_label:      str
    domain_confidence: float
    job_title:         str
    gaps:              list[GapResultSchema]
    strong_skills:     list[str]
    gap_summary:       GapSummarySchema
    candidate_skills:  list[dict]
    jd_skills:         list[dict]
    message:           str


# ── Module schema ─────────────────────────────────────────────────

class ModuleSchema(BaseModel):
    """
    Single learning module in the pathway.
    Returned by /pathway endpoint.
    """
    skill_id:        str
    display_name:    str
    domain:          str
    level:           str
    duration_hours:  int
    prerequisites:   list[str]
    resources:       list[ResourceSchema]
    gap_score:       float
    priority_score:  float
    candidate_conf:  float
    required_conf:   float
    is_missing:      bool
    reasoning_trace: str
    what_it_unlocks: str
    quick_win:       bool
    onet_code:       str = ""


# ── Pathway response ──────────────────────────────────────────────

class PathwayResponse(BaseModel):
    """
    Complete learning pathway response.
    Returned by /pathway endpoint.
    """
    success:          bool
    modules:          list[ModuleSchema]
    pathway_summary:  str
    estimated_impact: str
    gap_summary:      GapSummarySchema
    total_hours:      int
    hours_saved:      int
    job_title:        str
    domain:           str
    used_fallback:    bool
    module_count:     int
    message:          str


# ── Reroute response ──────────────────────────────────────────────

class RerouteResponse(BaseModel):
    """
    Response after skipping a skill.
    Contains updated pathway state.
    """
    success:           bool
    message:           str
    remaining_path:    list[str]
    skipped_skills:    list[str]
    completed_skills:  list[str]
    next_skill:        Optional[str]
    is_complete:       bool
    hours_remaining:   int
    hours_saved:       int
    total_hours:       int
    progress_percent:  float
    skill_statuses:    list[dict]


# ── Health check response ─────────────────────────────────────────

class HealthResponse(BaseModel):
    """API health check response."""
    status:       str
    app_name:     str
    version:      str
    claude_status: str
    message:      str


# ── Error response ────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    """Standard error response."""
    success: bool  = False
    error:   str
    detail:  str   = ""
    code:    int   = 500