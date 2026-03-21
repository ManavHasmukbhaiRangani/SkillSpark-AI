"""
SkillSpark AI — Pathway Route
-----------------------------------
POST /api/v1/pathway

Generates personalised learning pathway
from gap analysis results.

Steps:
  1. Receive gaps from /analyse response
  2. Sort by priority score
  3. Enforce dependency order
  4. Call Claude for descriptions + traces
  5. Return complete pathway

This route is THIN — logic in core/ and ai/.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from api.schemas import PathwayRequest
from core.confidence import batch_score_confidence
from core.dependencies import enforce_order
from core.domain import classify_domain, get_domain_label
from core.gap import (
    analyse_gaps,
    get_gap_summary,
    get_strong_skills,
    calculate_total_hours,
    SkillScore,
)
from core.reroute import create_path_state
from nlp.extractor import get_extractor
from nlp.normaliser import get_normaliser
from ai.generator import generate_pathway
from utils.catalog import (
    load_catalog,
    get_skill_importance,
    get_all_skill_ids,
)
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post(
    "/pathway",
    summary="Generate learning pathway",
    description="Generates dependency-ordered pathway with reasoning traces",
)
async def pathway(
    request: PathwayRequest,
) -> JSONResponse:
    """
    Generates complete personalised learning pathway.

    Steps:
      1. Re-run gap analysis (fresh data)
      2. Sort gaps by priority score
      3. Build ordered pathway via enforce_order()
      4. Pre-skip known skills via PathState
      5. Call Claude generator for traces
      6. Return complete pathway response

    Args:
        request: PathwayRequest with resume + JD text

    Returns:
        Complete pathway with modules and reasoning traces
    """
    logger.info(
        f"Pathway request: {request.job_title} "
        f"domain={request.domain}"
    )

    try:
        catalog = load_catalog()

        # ── Step 1 — Classify domain ──────────────────────────────
        domain_result = classify_domain(
            text=request.resume_text + " " + request.jd_text,
            job_title=request.job_title,
        )
        domain = request.domain or domain_result["domain"]

        # ── Step 2 — Extract + normalise resume skills ────────────
        extractor  = get_extractor()
        normaliser = get_normaliser()

        resume_extracted = extractor.extract(
            text=request.resume_text,
            domain=domain,
        )
        resume_normalised = normaliser.normalise_batch(
            extracted_skills=resume_extracted,
            domain=domain,
        )

        # Score confidence
        skill_contexts = [
            {
                "skill":   s.canonical_name,
                "context": s.context,
                "section": s.section,
            }
            for s in resume_normalised
        ]
        confidence_scores = batch_score_confidence(skill_contexts)

        candidate_skills_map: dict[str, float] = {
            s.canonical_name: confidence_scores.get(
                s.canonical_name, 0.50
            )
            for s in resume_normalised
        }

        # ── Step 3 — Extract + normalise JD skills ────────────────
        jd_extracted = extractor.extract(
            text=request.jd_text,
            domain=domain,
        )
        jd_normalised = normaliser.normalise_batch(
            extracted_skills=jd_extracted,
            domain=domain,
        )

        # JD skills need a required confidence level (how proficient
        # the role demands) which is separate from importance_weight
        # (how critical the skill is to the role). Using importance as
        # required_confidence conflates two different concepts and
        # produces incorrect gap scores. Default required level = 0.80.
        JD_REQUIRED_CONFIDENCE = 0.80
        jd_skills_map: dict[str, float] = {
            s.canonical_name: JD_REQUIRED_CONFIDENCE
            for s in jd_normalised
        }

        # ── Step 4 — Build SkillScores + analyse gaps ─────────────
        skill_scores: list[SkillScore] = []

        for skill_id, required_conf in jd_skills_map.items():
            candidate_conf = candidate_skills_map.get(
                skill_id, 0.0
            )
            importance   = get_skill_importance(skill_id)
            skill_entry  = catalog.get(skill_id, {})
            skill_domain = skill_entry.get("domain", domain)

            skill_scores.append(SkillScore(
                skill_id=skill_id,
                display_name=skill_entry.get(
                    "display_name", skill_id
                ),
                candidate_confidence=candidate_conf,
                required_confidence=required_conf,
                importance_weight=importance,
                domain=skill_domain,
            ))

        gaps = analyse_gaps(skill_scores)

        if not gaps:
            return JSONResponse(
                status_code=200,
                content={
                    "success":         True,
                    "modules":         [],
                    "pathway_summary": (
                        "Great news! No significant skill gaps "
                        f"found for {request.job_title}. "
                        "Your profile meets the requirements."
                    ),
                    "estimated_impact": "",
                    "gap_summary":      get_gap_summary([]),
                    "total_hours":      0,
                    "hours_saved":      0,
                    "job_title":        request.job_title,
                    "domain":           domain,
                    "used_fallback":    False,
                    "module_count":     0,
                    "message":          "No gaps found",
                },
            )

        # ── Step 5 — Build ordered pathway ────────────────────────
        # Sort gaps by priority (highest first)
        sorted_gaps = sorted(
            gaps,
            key=lambda g: g.priority_score,
            reverse=True,
        )

        # Get skill ids in priority order
        priority_ordered = [g.skill_id for g in sorted_gaps]

        # Enforce dependency order — YOUR deterministic logic
        dependency_ordered = enforce_order(priority_ordered)

        logger.info(
            f"Pathway: {len(dependency_ordered)} skills "
            f"in dependency order"
        )

        # ── Step 6 — Pre-skip known skills ────────────────────────
        path_state = create_path_state(
            ordered_path=dependency_ordered,
            catalog=catalog,
            known_skills=request.known_skills,
        )

        final_pathway = path_state.remaining
        hours_saved   = path_state.hours_saved()

        logger.info(
            f"After pre-skip: {len(final_pathway)} skills, "
            f"{hours_saved}h saved"
        )

        # ── Step 7 — Format skill lists for Claude ─────────────────
        candidate_skills_list = [
            {
                "skill":      skill_id,
                "confidence": conf,
            }
            for skill_id, conf in candidate_skills_map.items()
        ]

        jd_skills_list = [
            {
                "skill":               skill_id,
                "required_confidence": conf,
            }
            for skill_id, conf in jd_skills_map.items()
        ]

        # ── Step 8 — Generate pathway with Claude ─────────────────
        pathway_response = await generate_pathway(
            ordered_pathway=final_pathway,
            gaps=gaps,
            candidate_skills=candidate_skills_list,
            jd_skills=jd_skills_list,
            job_title=request.job_title,
            domain=domain,
            hours_saved=hours_saved,
        )

        response_dict = pathway_response.to_dict()
        response_dict["success"] = True
        response_dict["message"] = (
            f"Generated {len(final_pathway)}-module pathway "
            f"for {request.job_title}"
        )

        logger.info(
            f"Pathway generated: {len(final_pathway)} modules, "
            f"{response_dict['total_hours']}h total"
        )

        return JSONResponse(
            status_code=200,
            content=response_dict,
        )

    except Exception as e:
        logger.error(f"Pathway generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Pathway generation failed: {str(e)}",
        )