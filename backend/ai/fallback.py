"""
SkillPathForge AI — Rule-Based Fallback Engine
------------------------------------------------
Generates complete pathway without Claude API.

Used when:
  - Claude API is unavailable
  - Rate limit is hit
  - API timeout occurs
  - Demo environment has no internet

Produces the same data structure as generator.py
so frontend receives identical format regardless
of whether Claude was used.

All logic is deterministic — pure Python rules.
No LLM involved whatsoever.
"""

from core.dependencies import (
    get_all_prerequisites,
    get_unlocked_skills,
    SKILL_DEPENDENCIES,
)
from core.gap import GapResult, get_gap_summary
from utils.catalog import load_catalog


# ── Rule-based trace builder ──────────────────────────────────────

def build_rule_trace(
    skill_id:   str,
    gap:        GapResult,
    catalog:    dict,
) -> dict:
    """
    Builds reasoning trace from structured data only.
    No LLM — pure string construction from gap scores.

    Args:
        skill_id: canonical skill name
        gap:      GapResult object with scores
        catalog:  full catalog dict

    Returns:
        trace dict with reasoning_trace + what_it_unlocks
    """
    entry        = catalog.get(skill_id, {})
    display_name = entry.get("display_name", skill_id)
    duration     = entry.get("duration_hours", 0)
    level        = entry.get("level", "beginner")
    prereqs      = entry.get("prerequisites", [])

    # Get skills this unlocks
    all_skill_ids = list(catalog.keys())
    unlocks       = get_unlocked_skills(skill_id, all_skill_ids)

    # Build reasoning trace based on gap type
    if gap.is_missing:
        reasoning = (
            f"{display_name} was not found in your profile "
            f"but is required at {gap.required_confidence:.0%} "
            f"confidence for this role. "
            f"Priority score: {gap.priority_score:.2f} — "
            f"this is a {'critical' if gap.priority_score > 0.5 else 'moderate'} gap."
        )
    else:
        reasoning = (
            f"Your {display_name} proficiency is currently "
            f"{gap.candidate_confidence:.0%} but this role "
            f"requires {gap.required_confidence:.0%}. "
            f"Closing this {gap.gap_score:.0%} gap will "
            f"significantly improve your job readiness."
        )

    # Build prerequisites context
    if prereqs:
        prereq_text = (
            f"Requires completion of: "
            f"{', '.join(prereqs)}."
        )
        reasoning = prereq_text + " " + reasoning

    # Build unlocks text
    if unlocks:
        unlocks_text = (
            f"Completing {display_name} unlocks: "
            f"{', '.join(unlocks[:3])}"
            f"{'...' if len(unlocks) > 3 else '.'}"
        )
    else:
        unlocks_text = (
            f"{display_name} is a terminal skill in your "
            f"pathway with no further dependencies."
        )

    return {
        "skill_id":        skill_id,
        "reasoning_trace": reasoning,
        "what_it_unlocks": unlocks_text,
        "quick_win":       duration <= 10,
        "level":           level,
        "duration_hours":  duration,
    }


# ── Rule-based pathway generator ─────────────────────────────────

def rule_based_pathway(
    ordered_pathway: list[str],
    gaps:            list[GapResult],
    job_title:       str = "Target Role",
    domain:          str = "tech",
    hours_saved:     int = 0,
) -> dict:
    """
    Generates complete pathway response without Claude.

    Produces identical structure to generator.py output
    so frontend works the same whether Claude was used or not.

    Args:
        ordered_pathway: dependency-ordered skill id list
        gaps:            GapResult list from gap analysis
        job_title:       target role title
        domain:          "tech" or "ops"
        hours_saved:     hours saved from skipped skills

    Returns:
        dict matching PathwayResponse.to_dict() format
    """
    catalog   = load_catalog()
    gap_lookup = {g.skill_id: g for g in gaps}

    # Build modules
    modules: list[dict] = []
    total_hours = 0

    for skill_id in ordered_pathway:
        entry = catalog.get(skill_id, {})
        gap   = gap_lookup.get(skill_id)

        if not gap:
            continue

        duration    = entry.get("duration_hours", 0)
        total_hours += duration

        # Build rule-based trace
        trace = build_rule_trace(
            skill_id=skill_id,
            gap=gap,
            catalog=catalog,
        )

        modules.append({
            "skill_id":        skill_id,
            "display_name":    entry.get("display_name", skill_id),
            "domain":          entry.get("domain", domain),
            "level":           entry.get("level", "beginner"),
            "duration_hours":  duration,
            "prerequisites":   entry.get("prerequisites", []),
            "resources":       entry.get("resources", []),
            "gap_score":       round(gap.gap_score, 3),
            "priority_score":  round(gap.priority_score, 3),
            "candidate_conf":  round(gap.candidate_confidence, 3),
            "required_conf":   round(gap.required_confidence, 3),
            "is_missing":      gap.is_missing,
            "reasoning_trace": trace["reasoning_trace"],
            "what_it_unlocks": trace["what_it_unlocks"],
            "quick_win":       trace["quick_win"],
            "onet_code":       entry.get("onet_code", ""),
            "status":          "pending",
        })

    # Build summary
    skill_count  = len(ordered_pathway)
    gap_count    = len(gaps)
    missing      = sum(1 for g in gaps if g.is_missing)
    weak         = gap_count - missing

    pathway_summary = (
        f"Your personalised pathway to {job_title} "
        f"consists of {skill_count} modules totalling "
        f"approximately {total_hours} hours. "
        f"We identified {missing} missing skills and "
        f"{weak} skills that need improvement, "
        f"ordered by priority and prerequisites."
    )

    estimated_impact = (
        f"Completing this pathway will close all "
        f"{gap_count} identified gaps and bring your "
        f"profile to the required competency level "
        f"for {job_title}. "
        f"You have already saved {hours_saved} hours "
        f"by skipping skills you already know."
    )

    gap_summary = get_gap_summary(gaps)

    return {
        "modules":          modules,
        "pathway_summary":  pathway_summary,
        "estimated_impact": estimated_impact,
        "gap_summary":      gap_summary,
        "total_hours":      total_hours,
        "hours_saved":      hours_saved,
        "job_title":        job_title,
        "domain":           domain,
        "used_fallback":    True,
        "module_count":     len(modules),
    }


# ── Quick win filter ──────────────────────────────────────────────

def get_quick_wins(
    ordered_pathway: list[str],
    catalog:         dict,
    max_hours:       int = 10,
) -> list[str]:
    """
    Returns skills that can be learned quickly.
    Used to highlight easy wins in the UI.

    Args:
        ordered_pathway: ordered skill id list
        catalog:         full catalog dict
        max_hours:       maximum hours for quick win

    Returns:
        list of skill_ids that are quick wins
    """
    return [
        skill_id
        for skill_id in ordered_pathway
        if catalog.get(skill_id, {}).get(
            "duration_hours", 999
        ) <= max_hours
    ]


# ── Pathway stats ─────────────────────────────────────────────────

def get_pathway_stats(
    ordered_pathway: list[str],
    gaps:            list[GapResult],
    catalog:         dict,
) -> dict:
    """
    Calculates statistics for the pathway.
    Used in UI dashboard summary cards.

    Args:
        ordered_pathway: ordered skill id list
        gaps:            GapResult list
        catalog:         full catalog dict

    Returns:
        dict with pathway statistics
    """
    total_hours = sum(
        catalog.get(s, {}).get("duration_hours", 0)
        for s in ordered_pathway
    )

    quick_wins = get_quick_wins(ordered_pathway, catalog)

    beginner_count = sum(
        1 for s in ordered_pathway
        if catalog.get(s, {}).get("level") == "beginner"
    )
    intermediate_count = sum(
        1 for s in ordered_pathway
        if catalog.get(s, {}).get("level") == "intermediate"
    )
    advanced_count = sum(
        1 for s in ordered_pathway
        if catalog.get(s, {}).get("level") == "advanced"
    )

    missing_count = sum(1 for g in gaps if g.is_missing)
    weak_count    = sum(1 for g in gaps if g.is_weak)

    avg_gap = (
        sum(g.gap_score for g in gaps) / len(gaps)
        if gaps else 0.0
    )

    return {
        "total_modules":      len(ordered_pathway),
        "total_hours":        total_hours,
        "quick_wins":         len(quick_wins),
        "quick_win_ids":      quick_wins,
        "missing_skills":     missing_count,
        "weak_skills":        weak_count,
        "avg_gap_score":      round(avg_gap, 2),
        "beginner_modules":   beginner_count,
        "intermediate_modules": intermediate_count,
        "advanced_modules":   advanced_count,
    }