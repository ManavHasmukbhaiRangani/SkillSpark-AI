"""
SkillPathForge AI — Pathway Generator
---------------------------------------
Orchestrates the two Claude API calls and
assembles the final pathway response.

Call 1 → Gap descriptions (why each skill matters)
Call 2 → Pathway modules + reasoning traces

If Claude fails at any point:
  → Fallback to rule-based generator (fallback.py)
  → System never crashes during demo

This is the ONLY file that calls Claude API.
All logic (ordering, scoring) is already done
in core/ before this file is called.
"""

import json
from typing import Optional

from ai.claude_client import (
    call_claude_json,
    ClaudeAPIError,
    ClaudeParseError,
    ClaudeRateLimitError,
)
from ai.prompts import (
    GAP_ANALYSIS_SYSTEM,   # ← add this
    PATHWAY_SYSTEM,        # ← add this
    build_gap_analysis_prompt,
    build_pathway_prompt,
    build_fallback_trace,
    build_fallback_summary,
)
from ai.fallback import rule_based_pathway
from core.dependencies import (
    get_all_prerequisites,
    get_unlocked_skills,
)
from core.gap import GapResult, get_gap_summary
from utils.catalog import load_catalog


# ── PathwayModule ─────────────────────────────────────────────────

class PathwayModule:
    """
    Represents a single learning module in the pathway.
    Combines catalog data + gap data + Claude descriptions.
    """

    def __init__(
        self,
        skill_id:        str,
        display_name:    str,
        domain:          str,
        level:           str,
        duration_hours:  int,
        prerequisites:   list[str],
        resources:       list[dict],
        gap_score:       float,
        priority_score:  float,
        candidate_conf:  float,
        required_conf:   float,
        is_missing:      bool,
        reasoning_trace: str,
        what_it_unlocks: str,
        quick_win:       bool,
        onet_code:       str = "",
    ):
        self.skill_id        = skill_id
        self.display_name    = display_name
        self.domain          = domain
        self.level           = level
        self.duration_hours  = duration_hours
        self.prerequisites   = prerequisites
        self.resources       = resources
        self.gap_score       = gap_score
        self.priority_score  = priority_score
        self.candidate_conf  = candidate_conf
        self.required_conf   = required_conf
        self.is_missing      = is_missing
        self.reasoning_trace = reasoning_trace
        self.what_it_unlocks = what_it_unlocks
        self.quick_win       = quick_win
        self.onet_code       = onet_code

    def to_dict(self) -> dict:
        return {
            "skill_id":        self.skill_id,
            "display_name":    self.display_name,
            "domain":          self.domain,
            "level":           self.level,
            "duration_hours":  self.duration_hours,
            "prerequisites":   self.prerequisites,
            "resources":       self.resources,
            "gap_score":       round(self.gap_score, 3),
            "priority_score":  round(self.priority_score, 3),
            "candidate_conf":  round(self.candidate_conf, 3),
            "required_conf":   round(self.required_conf, 3),
            "is_missing":      self.is_missing,
            "reasoning_trace": self.reasoning_trace,
            "what_it_unlocks": self.what_it_unlocks,
            "quick_win":       self.quick_win,
            "onet_code":       self.onet_code,
        }


# ── PathwayResponse ───────────────────────────────────────────────

class PathwayResponse:
    """
    Complete pathway response sent to frontend.
    """

    def __init__(
        self,
        modules:          list[PathwayModule],
        pathway_summary:  str,
        estimated_impact: str,
        gap_summary:      dict,
        total_hours:      int,
        hours_saved:      int,
        job_title:        str,
        domain:           str,
        used_fallback:    bool = False,
    ):
        self.modules          = modules
        self.pathway_summary  = pathway_summary
        self.estimated_impact = estimated_impact
        self.gap_summary      = gap_summary
        self.total_hours      = total_hours
        self.hours_saved      = hours_saved
        self.job_title        = job_title
        self.domain           = domain
        self.used_fallback    = used_fallback

    def to_dict(self) -> dict:
        return {
            "modules":          [m.to_dict() for m in self.modules],
            "pathway_summary":  self.pathway_summary,
            "estimated_impact": self.estimated_impact,
            "gap_summary":      self.gap_summary,
            "total_hours":      self.total_hours,
            "hours_saved":      self.hours_saved,
            "job_title":        self.job_title,
            "domain":           self.domain,
            "used_fallback":    self.used_fallback,
            "module_count":     len(self.modules),
        }


# ── Main generator function ───────────────────────────────────────

async def generate_pathway(
    ordered_pathway:   list[str],
    gaps:              list[GapResult],
    candidate_skills:  list[dict],
    jd_skills:         list[dict],
    job_title:         str = "Target Role",
    domain:            str = "tech",
    hours_saved:       int = 0,
) -> PathwayResponse:
    """
    Main orchestrator — generates complete pathway response.

    Steps:
      1. Load catalog entries for pathway skills
      2. Call Claude for gap descriptions (Call 1)
      3. Call Claude for pathway traces (Call 2)
      4. Assemble PathwayModule objects
      5. Return PathwayResponse

    Falls back to rule-based generation if Claude fails.

    Args:
        ordered_pathway:  dependency-ordered skill ids
        gaps:             GapResult list from gap analysis
        candidate_skills: list of {skill, confidence} dicts
        jd_skills:        list of {skill, required_confidence}
        job_title:        target role title
        domain:           "tech" or "ops"
        hours_saved:      hours saved from skipped skills

    Returns:
        PathwayResponse with modules + traces + summary
    """
    catalog = load_catalog()
    used_fallback = False

    # Build gap lookup for quick access
    gap_lookup = {g.skill_id: g for g in gaps}

    # Build catalog entries for pathway skills
    catalog_entries = []
    for skill_id in ordered_pathway:
        entry = catalog.get(skill_id, {})
        catalog_entries.append({
            "id_key":        skill_id,
            "display_name":  entry.get("display_name", skill_id),
            "duration_hours":entry.get("duration_hours", 0),
            "level":         entry.get("level", "beginner"),
            "prerequisites": entry.get("prerequisites", []),
            "resources":     entry.get("resources", []),
        })

    # Total hours calculation
    total_hours = sum(
        catalog.get(s, {}).get("duration_hours", 0)
        for s in ordered_pathway
    )

    # Gap summary stats
    gap_summary = get_gap_summary(gaps)

    # Convert gaps to dicts for prompts
    gaps_dicts = [
        {
            "skill_id":           g.skill_id,
            "gap_score":          g.gap_score,
            "priority_score":     g.priority_score,
            "is_missing":         g.is_missing,
            "candidate_confidence": g.candidate_confidence,
            "required_confidence":  g.required_confidence,
        }
        for g in gaps
    ]

    # ── Claude Call 1 — Gap descriptions ─────────────────────────
    gap_descriptions: dict[str, str] = {}

    try:
        gap_prompt = build_gap_analysis_prompt(
            candidate_skills=candidate_skills,
            jd_skills=jd_skills,
            gaps=gaps_dicts,
            job_title=job_title,
            domain=domain,
        )

        gap_response = call_claude_json(
            system_prompt=GAP_ANALYSIS_SYSTEM,
            user_message=gap_prompt,
        )

        gap_descriptions = gap_response.get(
            "gap_descriptions", {}
        )

    except (ClaudeAPIError, ClaudeParseError,
            ClaudeRateLimitError) as e:
        # Fallback — generate descriptions from data
        used_fallback = True
        for gap in gaps:
            gap_descriptions[gap.skill_id] = (
                f"This skill has a gap of "
                f"{gap.gap_score:.0%} from the "
                f"required level for {job_title}."
            )

    # ── Claude Call 2 — Pathway traces ───────────────────────────
    module_traces: list[dict] = []
    pathway_summary  = ""
    estimated_impact = ""

    try:
        pathway_prompt = build_pathway_prompt(
            ordered_pathway=ordered_pathway,
            gaps=gaps_dicts,
            catalog_entries=catalog_entries,
            job_title=job_title,
            domain=domain,
            hours_total=total_hours,
        )

        pathway_response = call_claude_json(
            system_prompt=PATHWAY_SYSTEM,
            user_message=pathway_prompt,
        )

        module_traces    = pathway_response.get("modules", [])
        pathway_summary  = pathway_response.get(
            "pathway_summary", ""
        )
        estimated_impact = pathway_response.get(
            "estimated_impact", ""
        )

    except (ClaudeAPIError, ClaudeParseError,
            ClaudeRateLimitError) as e:
        # Fallback — generate traces from rules
        used_fallback = True

        all_skill_ids = list(catalog.keys())

        for skill_id in ordered_pathway:
            gap = gap_lookup.get(skill_id)
            if not gap:
                continue

            catalog_entry = catalog.get(skill_id, {})
            prereqs       = catalog_entry.get("prerequisites", [])
            unlocks       = get_unlocked_skills(
                skill_id, all_skill_ids
            )

            trace = build_fallback_trace(
                skill_id=skill_id,
                gap=gaps_dicts[0] if gaps_dicts else {},
                catalog=catalog_entry,
                prerequisites=prereqs,
                unlocks=unlocks,
            )
            module_traces.append(trace)

        fallback_summary = build_fallback_summary(
            ordered_pathway=ordered_pathway,
            hours_total=total_hours,
            job_title=job_title,
            gap_count=len(gaps),
        )
        pathway_summary  = fallback_summary["pathway_summary"]
        estimated_impact = fallback_summary["estimated_impact"]

    # ── Assemble PathwayModule objects ────────────────────────────
    trace_lookup = {
        t["skill_id"]: t
        for t in module_traces
        if "skill_id" in t
    }

    modules: list[PathwayModule] = []

    for skill_id in ordered_pathway:
        catalog_entry = catalog.get(skill_id, {})
        gap           = gap_lookup.get(skill_id)
        trace         = trace_lookup.get(skill_id, {})

        # Get gap values safely
        gap_score      = gap.gap_score if gap else 0.0
        priority_score = gap.priority_score if gap else 0.0
        candidate_conf = gap.candidate_confidence if gap else 0.0
        required_conf  = gap.required_confidence if gap else 0.0
        is_missing     = gap.is_missing if gap else False

        modules.append(PathwayModule(
            skill_id=skill_id,
            display_name=catalog_entry.get(
                "display_name", skill_id
            ),
            domain=catalog_entry.get("domain", domain),
            level=catalog_entry.get("level", "beginner"),
            duration_hours=catalog_entry.get(
                "duration_hours", 0
            ),
            prerequisites=catalog_entry.get(
                "prerequisites", []
            ),
            resources=catalog_entry.get("resources", []),
            gap_score=gap_score,
            priority_score=priority_score,
            candidate_conf=candidate_conf,
            required_conf=required_conf,
            is_missing=is_missing,
            reasoning_trace=trace.get(
                "reasoning_trace",
                gap_descriptions.get(skill_id, "")
            ),
            what_it_unlocks=trace.get(
                "what_it_unlocks", ""
            ),
            quick_win=trace.get(
                "quick_win",
                catalog_entry.get("duration_hours", 0) <= 10,
            ),
            onet_code=catalog_entry.get("onet_code", ""),
        ))

    return PathwayResponse(
        modules=modules,
        pathway_summary=pathway_summary,
        estimated_impact=estimated_impact,
        gap_summary=gap_summary,
        total_hours=total_hours,
        hours_saved=hours_saved,
        job_title=job_title,
        domain=domain,
        used_fallback=used_fallback,
    )