"""
SkillSpark AI — Analyse Route
-----------------------------------
POST /api/v1/analyse

Runs full skill gap analysis pipeline:
  1. Classify domain (tech vs ops)
  2. Extract skills from resume + JD
  3. Normalise to O*NET canonical names
  4. Score confidence from context
  5. Calculate gaps + priority scores

Returns structured gap analysis ready
for /pathway endpoint.

This route is THIN — all logic in core/ and nlp/.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from api.schemas import AnalyseRequest, AnalyseResponse
from core.confidence import batch_score_confidence
from core.domain import classify_domain, get_domain_label
from core.gap import (
    analyse_gaps,
    get_strong_skills,
    get_gap_summary,
    SkillScore,
)
from core.dependencies import (
    get_all_prerequisites,
    get_unlocked_skills,
)
from nlp.extractor import get_extractor
from nlp.normaliser import get_normaliser
from utils.catalog import (
    load_catalog,
    get_skill_importance,
    skill_exists,
    get_all_skill_ids,
)
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post(
    "/analyse",
    response_model=AnalyseResponse,
    summary="Analyse skill gaps",
    description="Extracts skills from resume and JD then calculates gap scores",
)
async def analyse(
    request: AnalyseRequest,
) -> JSONResponse:
    """
    Full skill gap analysis pipeline.

    Steps:
      1. Classify domain from text
      2. Extract + normalise resume skills
      3. Extract + normalise JD skills
      4. Score candidate confidence per skill
      5. Calculate gap + priority scores
      6. Return structured gap results

    Args:
        request: AnalyseRequest with resume + JD text

    Returns:
        AnalyseResponse with gaps, scores, and summary
    """
    logger.info(f"Analyse request: {request.job_title}")

    try:
        catalog = load_catalog()

        # ── Step 1 — Classify domain ──────────────────────────────
        domain_result = classify_domain(
            text=request.resume_text + " " + request.jd_text,
            job_title=request.job_title,
        )

        # Allow manual domain override
        domain = request.domain or domain_result["domain"]
        domain_label = get_domain_label(domain)

        logger.info(
            f"Domain: {domain} "
            f"(confidence: {domain_result['confidence']})"
        )

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

        logger.info(
            f"Resume: extracted {len(resume_extracted)}, "
            f"normalised {len(resume_normalised)}"
        )

        # ── Step 3 — Score candidate confidence ───────────────────
        skill_contexts = [
            {
                "skill":   s.canonical_name,
                "context": s.context,
                "section": s.section,
            }
            for s in resume_normalised
        ]

        confidence_scores = batch_score_confidence(skill_contexts)

        # Build candidate skills dict
        candidate_skills_map: dict[str, float] = {
            s.canonical_name: confidence_scores.get(
                s.canonical_name, 0.50
            )
            for s in resume_normalised
        }

        # ── Step 4 — Extract + normalise JD skills ────────────────
        jd_extracted = extractor.extract(
            text=request.jd_text,
            domain=domain,
        )

        jd_normalised = normaliser.normalise_batch(
            extracted_skills=jd_extracted,
            domain=domain,
        )

        logger.info(
            f"JD: extracted {len(jd_extracted)}, "
            f"normalised {len(jd_normalised)}"
        )

        # Build JD requirements map
        # required_confidence = proficiency level the role demands (fixed 0.80)
        # importance_weight   = how critical the skill is (fetched separately)
        # These are distinct concepts — conflating them produces wrong gap scores.
        JD_REQUIRED_CONFIDENCE = 0.80
        jd_skills_map: dict[str, float] = {
            skill.canonical_name: JD_REQUIRED_CONFIDENCE
            for skill in jd_normalised
        }

        # ── Step 5 — Build SkillScore objects ─────────────────────
        all_skill_ids = get_all_skill_ids()
        skill_scores: list[SkillScore] = []

        for skill_id, required_conf in jd_skills_map.items():
            candidate_conf = candidate_skills_map.get(
                skill_id, 0.0
            )
            importance = get_skill_importance(skill_id)

            # Get domain for this skill
            skill_entry = catalog.get(skill_id, {})
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

        # ── Step 6 — Calculate gaps ───────────────────────────────
        gaps = analyse_gaps(skill_scores)

        # Add prerequisites and unlocks to each gap
        for gap in gaps:
            prereqs = get_all_prerequisites(gap.skill_id)
            unlocks = get_unlocked_skills(
                gap.skill_id, all_skill_ids
            )
            gap.prerequisites = prereqs
            gap.unlocks = unlocks

        # Get strong skills (no gap)
        strong = get_strong_skills(skill_scores)
        strong_skill_ids = [s.skill_id for s in strong]

        # Gap summary
        gap_summary = get_gap_summary(gaps)

        logger.info(
            f"Gaps found: {gap_summary['total_gaps']} "
            f"({gap_summary['missing_skills']} missing, "
            f"{gap_summary['weak_skills']} weak)"
        )

        # Format for response
        candidate_skills_list = [
            {
                "skill":      s.canonical_name,
                "confidence": candidate_skills_map.get(
                    s.canonical_name, 0.50
                ),
            }
            for s in resume_normalised
        ]

        jd_skills_list = [
            {
                "skill":               s.canonical_name,
                "required_confidence": jd_skills_map.get(
                    s.canonical_name, 0.80
                ),
            }
            for s in jd_normalised
        ]

        return JSONResponse(
            status_code=200,
            content={
                "success":           True,
                "domain":            domain,
                "domain_label":      domain_label,
                "domain_confidence": domain_result["confidence"],
                "job_title":         request.job_title,
                "gaps": [
                    {
                        "skill_id":             g.skill_id,
                        "display_name":         g.display_name,
                        "candidate_confidence": g.candidate_confidence,
                        "required_confidence":  g.required_confidence,
                        "importance_weight":    g.importance_weight,
                        "gap_score":            g.gap_score,
                        "priority_score":       g.priority_score,
                        "domain":               g.domain,
                        "is_missing":           g.is_missing,
                        "is_weak":              g.is_weak,
                        "prerequisites":        g.prerequisites,
                        "unlocks":              g.unlocks,
                    }
                    for g in gaps
                ],
                "strong_skills":    strong_skill_ids,
                "gap_summary":      gap_summary,
                "candidate_skills": candidate_skills_list,
                "jd_skills":        jd_skills_list,
                "message": (
                    f"Found {gap_summary['total_gaps']} skill gaps "
                    f"for {request.job_title}"
                ),
            },
        )

    except Exception as e:
        logger.error(f"Analyse failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}",
        )