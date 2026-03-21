"""
SkillSpark AI — Gap Analysis Engine
----------------------------------------
Calculates skill gaps between candidate profile
and job description requirements.

All logic is deterministic arithmetic — no LLM involved.

Three formulas:
  1. gap_score    = required_confidence - candidate_confidence
  2. priority_score = gap_score × importance_weight
  3. final ranking  = sorted by priority_score descending
"""

from dataclasses import dataclass, field
from typing import Optional


# ── Data structures ───────────────────────────────────────────────

@dataclass
class SkillScore:
    """
    Represents a single skill with both candidate
    and required confidence scores.
    """
    skill_id:             str
    display_name:         str
    candidate_confidence: float   # what candidate has (0.0 - 1.0)
    required_confidence:  float   # what JD needs    (0.0 - 1.0)
    importance_weight:    float   # how critical to role (0.0 - 1.0)
    domain:               str     # "tech" or "ops"
    section:              str = "skills"   # where found in resume
    context:              str = ""         # surrounding text


@dataclass
class GapResult:
    """
    Represents the calculated gap for a single skill.
    Used in pathway generation and reasoning trace.
    """
    skill_id:             str
    display_name:         str
    candidate_confidence: float
    required_confidence:  float
    importance_weight:    float
    gap_score:            float    # required - candidate
    priority_score:       float    # gap × importance_weight
    domain:               str
    is_missing:           bool     # True if candidate has 0 confidence
    is_weak:              bool     # True if gap > 0 but skill exists
    prerequisites:        list[str] = field(default_factory=list)
    unlocks:              list[str] = field(default_factory=list)


# ── Thresholds ────────────────────────────────────────────────────

# Minimum gap to consider a skill worth learning
# Below this = negligible gap, skip from pathway
MIN_GAP_THRESHOLD: float = 0.10

# Confidence threshold below which skill is "missing"
# vs "weak" (exists but needs improvement)
MISSING_THRESHOLD: float = 0.15


# ── Core formula 1 — gap_score ────────────────────────────────────
def gap_score(
    required_confidence: float,
    candidate_confidence: float
) -> float:
    """
    Calculates raw skill gap.

    Formula:
        gap = required_confidence - candidate_confidence
        gap is floored at 0.0 (no negative gaps)

    Args:
        required_confidence: what the JD needs (0.0 - 1.0)
        candidate_confidence: what candidate has (0.0 - 1.0)

    Returns:
        gap float between 0.0 and 1.0

    Examples:
        gap_score(0.90, 0.30) → 0.60  (large gap)
        gap_score(0.85, 0.84) → 0.01  (negligible gap)
        gap_score(0.70, 0.90) → 0.00  (no gap — exceeds requirement)
    """
    raw_gap = required_confidence - candidate_confidence
    return round(max(0.0, raw_gap), 4)


# ── Core formula 2 — priority_score ──────────────────────────────
def priority_score(
    gap: float,
    importance_weight: float
) -> float:
    """
    Calculates how urgently a skill gap needs to be addressed.

    Formula:
        priority = gap_score × importance_weight

    A large gap in a critical skill = highest priority
    A small gap in a minor skill = lowest priority

    Args:
        gap: gap_score result (0.0 - 1.0)
        importance_weight: how critical skill is to role (0.0 - 1.0)

    Returns:
        priority float between 0.0 and 1.0

    Examples:
        priority_score(0.75, 0.95) → 0.7125  (urgent)
        priority_score(0.10, 0.70) → 0.0700  (low priority)
        priority_score(0.00, 0.90) → 0.0000  (no gap, skip)
    """
    return round(gap * importance_weight, 4)


# ── Core formula 3 — analyse_gaps ────────────────────────────────
def analyse_gaps(
    skill_scores: list[SkillScore]
) -> list[GapResult]:
    """
    Runs gap analysis on all skills and returns
    prioritised list of gaps to address.

    Steps:
        1. Calculate gap_score per skill
        2. Calculate priority_score per skill
        3. Filter out negligible gaps
        4. Classify as missing vs weak
        5. Sort by priority_score descending

    Args:
        skill_scores: list of SkillScore objects
                      combining candidate + JD data

    Returns:
        list of GapResult sorted by priority (highest first)
        only includes skills with gap > MIN_GAP_THRESHOLD
    """
    results: list[GapResult] = []

    for skill in skill_scores:

        # Formula 1 — calculate gap
        gap = gap_score(
            skill.required_confidence,
            skill.candidate_confidence
        )

        # Skip negligible gaps — not worth learning
        if gap < MIN_GAP_THRESHOLD:
            continue

        # Formula 2 — calculate priority
        priority = priority_score(gap, skill.importance_weight)

        # Classify gap type
        is_missing = skill.candidate_confidence <= MISSING_THRESHOLD
        is_weak = not is_missing and gap > 0

        results.append(GapResult(
            skill_id=skill.skill_id,
            display_name=skill.display_name,
            candidate_confidence=skill.candidate_confidence,
            required_confidence=skill.required_confidence,
            importance_weight=skill.importance_weight,
            gap_score=gap,
            priority_score=priority,
            domain=skill.domain,
            is_missing=is_missing,
            is_weak=is_weak,
        ))

    # Formula 3 — sort by priority descending
    # Highest priority gap = first to learn
    results.sort(key=lambda x: x.priority_score, reverse=True)

    return results


# ── get_strong_skills ─────────────────────────────────────────────
def get_strong_skills(
    skill_scores: list[SkillScore]
) -> list[SkillScore]:
    """
    Returns skills where candidate meets or exceeds requirement.
    Used in reasoning trace to show what candidate already knows.

    Args:
        skill_scores: list of all SkillScore objects

    Returns:
        list of skills with no meaningful gap
    """
    return [
        skill for skill in skill_scores
        if gap_score(
            skill.required_confidence,
            skill.candidate_confidence
        ) < MIN_GAP_THRESHOLD
    ]


# ── calculate_hours_saved ─────────────────────────────────────────
def calculate_hours_saved(
    skipped_skills: list[str],
    catalog: dict
) -> int:
    """
    Calculates total learning hours saved when candidate
    skips skills they already know.

    Args:
        skipped_skills: list of skill canonical_names skipped
        catalog: loaded catalog.json dict

    Returns:
        total hours saved as integer

    Used in UI — hours saved counter widget
    """
    total = 0
    for skill_id in skipped_skills:
        if skill_id in catalog:
            total += catalog[skill_id].get("duration_hours", 0)
    return total


# ── calculate_total_hours ─────────────────────────────────────────
def calculate_total_hours(
    pathway: list[str],
    catalog: dict
) -> int:
    """
    Calculates total estimated learning hours for a pathway.

    Args:
        pathway: ordered list of skill canonical_names
        catalog: loaded catalog.json dict

    Returns:
        total hours as integer
    """
    return sum(
        catalog.get(skill_id, {}).get("duration_hours", 0)
        for skill_id in pathway
    )


# ── get_gap_summary ───────────────────────────────────────────────
def get_gap_summary(gaps: list[GapResult]) -> dict:
    """
    Returns summary statistics for the gap analysis.
    Used in UI dashboard and reasoning trace.

    Args:
        gaps: list of GapResult from analyse_gaps()

    Returns:
        dict with summary stats
    """
    if not gaps:
        return {
            "total_gaps": 0,
            "missing_skills": 0,
            "weak_skills": 0,
            "avg_gap_score": 0.0,
            "avg_priority_score": 0.0,
            "highest_priority_skill": None,
        }

    missing = [g for g in gaps if g.is_missing]
    weak = [g for g in gaps if g.is_weak]

    return {
        "total_gaps":             len(gaps),
        "missing_skills":         len(missing),
        "weak_skills":            len(weak),
        "avg_gap_score":          round(
            sum(g.gap_score for g in gaps) / len(gaps), 2
        ),
        "avg_priority_score":     round(
            sum(g.priority_score for g in gaps) / len(gaps), 2
        ),
        "highest_priority_skill": gaps[0].skill_id if gaps else None,
    }