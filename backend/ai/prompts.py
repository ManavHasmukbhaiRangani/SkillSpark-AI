"""
SkillPathForge AI — Claude Prompt Templates
---------------------------------------------
All prompt templates for Claude API calls.

Claude does ONE thing in this system:
  Generate human-readable module descriptions
  and reasoning traces.

All logic (gap scoring, ordering, prioritisation)
is done in core/ BEFORE Claude is called.
Claude receives structured data and returns text.

Two prompt templates:
  1. GAP_ANALYSIS_PROMPT   → Call 1 · descriptions per gap
  2. PATHWAY_PROMPT        → Call 2 · pathway + trace text
"""


# ── System prompt — shared base ───────────────────────────────────

BASE_SYSTEM_PROMPT: str = """
You are SkillPathForge AI — an expert learning pathway advisor
specialising in corporate onboarding and skill development.

Your role is STRICTLY to generate clear, professional, human-readable
descriptions and reasoning explanations.

CRITICAL RULES:
1. Never invent skills not provided to you
2. Never recommend modules outside the provided course catalog
3. Always return valid JSON — no markdown, no code blocks
4. Be concise — max 2 sentences per description
5. Use professional but friendly tone
6. Never hallucinate resources or URLs
""".strip()


# ── Prompt 1 — Gap analysis descriptions ─────────────────────────

GAP_ANALYSIS_SYSTEM: str = BASE_SYSTEM_PROMPT + """

You will receive:
  - A list of identified skill gaps with scores
  - The candidate's current skill profile
  - The job description requirements

You must return a JSON object with a description
for each gap explaining WHY it matters for this role.
""".strip()


def build_gap_analysis_prompt(
    candidate_skills:   list[dict],
    jd_skills:          list[dict],
    gaps:               list[dict],
    job_title:          str = "the target role",
    domain:             str = "tech",
) -> str:
    """
    Builds the user message for Claude Call 1.

    Claude receives structured gap data and returns
    human-readable descriptions for each gap.

    Args:
        candidate_skills: list of {skill, confidence} dicts
        jd_skills:        list of {skill, required_confidence} dicts
        gaps:             list of GapResult dicts
        job_title:        target job title from JD
        domain:           "tech" or "ops"

    Returns:
        formatted prompt string for Claude
    """
    # Format candidate skills
    candidate_text = "\n".join([
        f"  - {s['skill']}: {s['confidence']:.2f} confidence"
        for s in candidate_skills
    ])

    # Format JD requirements
    jd_text = "\n".join([
        f"  - {s['skill']}: requires {s['required_confidence']:.2f} confidence"
        for s in jd_skills
    ])

    # Format gaps
    gaps_text = "\n".join([
        f"  - {g['skill_id']}: "
        f"gap={g['gap_score']:.2f}, "
        f"priority={g['priority_score']:.2f}, "
        f"type={'MISSING' if g['is_missing'] else 'WEAK'}"
        for g in gaps
    ])

    prompt = f"""
Candidate is applying for: {job_title}
Domain: {domain.upper()} role

CANDIDATE CURRENT SKILLS:
{candidate_text}

JOB DESCRIPTION REQUIREMENTS:
{jd_text}

IDENTIFIED SKILL GAPS (pre-calculated, do not change scores):
{gaps_text}

For each skill gap listed above, provide a brief explanation
of why this skill is needed for {job_title}.

Return ONLY this JSON structure, no other text:
{{
  "gap_descriptions": {{
    "<skill_id>": "<1-2 sentence explanation of why this skill matters>",
    "<skill_id>": "<explanation>"
  }}
}}
""".strip()

    return prompt


# ── Prompt 2 — Pathway generation ────────────────────────────────

PATHWAY_SYSTEM: str = BASE_SYSTEM_PROMPT + """

You will receive:
  - An ordered learning pathway (dependency order pre-calculated)
  - Gap analysis results with priority scores
  - Course catalog entries for each skill
  - Job title and domain

You must return a JSON object with:
  - A reasoning trace for each module
  - An overall pathway summary
  - Estimated impact statement

DO NOT reorder the pathway — order is already optimised.
DO NOT add skills not in the pathway.
DO NOT reference resources not in the catalog.
""".strip()


def build_pathway_prompt(
    ordered_pathway:  list[str],
    gaps:             list[dict],
    catalog_entries:  list[dict],
    job_title:        str = "the target role",
    domain:           str = "tech",
    hours_total:      int = 0,
    candidate_name:   str = "the candidate",
) -> str:
    """
    Builds the user message for Claude Call 2.

    Claude receives the ordered pathway and returns
    reasoning traces for each module.

    Args:
        ordered_pathway:  dependency-ordered skill ids
        gaps:             GapResult dicts with scores
        catalog_entries:  catalog data for each skill
        job_title:        target role title
        domain:           "tech" or "ops"
        hours_total:      total estimated learning hours
        candidate_name:   optional candidate name

    Returns:
        formatted prompt string for Claude
    """
    # Build gap lookup
    gap_lookup = {g["skill_id"]: g for g in gaps}

    # Format pathway with catalog + gap data
    pathway_text = ""
    for idx, skill_id in enumerate(ordered_pathway, 1):
        catalog = next(
            (c for c in catalog_entries if c["id_key"] == skill_id),
            {}
        )
        gap = gap_lookup.get(skill_id, {})

        pathway_text += f"""
Module {idx}: {skill_id}
  Display name:  {catalog.get('display_name', skill_id)}
  Duration:      {catalog.get('duration_hours', 0)} hours
  Level:         {catalog.get('level', 'beginner')}
  Gap score:     {gap.get('gap_score', 0):.2f}
  Priority:      {gap.get('priority_score', 0):.2f}
  Type:          {'MISSING' if gap.get('is_missing') else 'NEEDS IMPROVEMENT'}
  Prerequisites: {', '.join(catalog.get('prerequisites', [])) or 'None'}
"""

    prompt = f"""
Generate learning pathway for: {candidate_name}
Target role: {job_title}
Domain: {domain.upper()}
Total estimated hours: {hours_total}

ORDERED LEARNING PATHWAY (do not reorder):
{pathway_text}

For each module, provide:
1. reasoning_trace: Why this specific skill is needed
   (reference gap score and job requirements)
2. what_it_unlocks: What skills become available after this
3. quick_win: True if duration <= 10 hours, False otherwise

Return ONLY this JSON structure, no other text:
{{
  "pathway_summary": "<2-3 sentence overview of the learning journey>",
  "estimated_impact": "<1 sentence on how this pathway closes the gap>",
  "modules": [
    {{
      "skill_id": "<skill_id>",
      "reasoning_trace": "<why this skill is needed>",
      "what_it_unlocks": "<what skills this enables>",
      "quick_win": <true/false>
    }}
  ]
}}
""".strip()

    return prompt


# ── Prompt 3 — Fallback trace builder ────────────────────────────
# Used when Claude API fails
# Generates rule-based trace without LLM

def build_fallback_trace(
    skill_id:     str,
    gap:          dict,
    catalog:      dict,
    prerequisites: list[str],
    unlocks:      list[str],
) -> dict:
    """
    Builds a rule-based reasoning trace without Claude.
    Used as fallback when API is unavailable.

    Args:
        skill_id:     canonical skill name
        gap:          GapResult dict
        catalog:      catalog entry for this skill
        prerequisites: list of prereq skill names
        unlocks:      list of skills this unlocks

    Returns:
        trace dict matching Claude output format
    """
    display_name = catalog.get("display_name", skill_id)
    gap_score    = gap.get("gap_score", 0)
    priority     = gap.get("priority_score", 0)
    is_missing   = gap.get("is_missing", False)
    duration     = catalog.get("duration_hours", 0)
    candidate_conf = gap.get("candidate_confidence", 0)
    required_conf  = gap.get("required_confidence", 0)

    # Build reasoning trace from data
    if is_missing:
        reasoning = (
            f"{display_name} is required for this role "
            f"(confidence needed: {required_conf:.0%}) "
            f"but was not found in your profile. "
            f"Priority score: {priority:.2f}."
        )
    else:
        reasoning = (
            f"Your {display_name} proficiency is "
            f"{candidate_conf:.0%} but this role requires "
            f"{required_conf:.0%}. "
            f"Gap of {gap_score:.0%} needs to be closed. "
            f"Priority score: {priority:.2f}."
        )

    # Build unlocks text
    if unlocks:
        unlocks_text = (
            f"Completing this unlocks: "
            f"{', '.join(unlocks)}"
        )
    else:
        unlocks_text = (
            "This is an advanced skill with no "
            "further dependencies in your pathway."
        )

    return {
        "skill_id":        skill_id,
        "reasoning_trace": reasoning,
        "what_it_unlocks": unlocks_text,
        "quick_win":       duration <= 10,
    }


def build_fallback_summary(
    ordered_pathway: list[str],
    hours_total:     int,
    job_title:       str,
    gap_count:       int,
) -> dict:
    """
    Builds rule-based pathway summary without Claude.

    Args:
        ordered_pathway: list of skill ids
        hours_total:     total hours
        job_title:       target role
        gap_count:       number of gaps identified

    Returns:
        summary dict matching Claude output format
    """
    skill_count = len(ordered_pathway)

    summary = (
        f"Your personalised pathway to {job_title} "
        f"consists of {skill_count} modules "
        f"totalling approximately {hours_total} hours. "
        f"We identified {gap_count} skill gaps "
        f"and ordered them by priority and prerequisites."
    )

    impact = (
        f"Completing this pathway will close all "
        f"{gap_count} identified gaps and bring your "
        f"profile to the required competency level "
        f"for {job_title}."
    )

    return {
        "pathway_summary":   summary,
        "estimated_impact":  impact,
    }