"""
SkillPathForge AI — Reroute Route
-----------------------------------
POST /api/v1/reroute

Handles skill skip and pathway recalculation.

When user marks a skill as "already known":
  1. Remove from remaining path
  2. Remove orphaned prerequisites
  3. Re-enforce dependency order
  4. Recalculate hours saved

This route is THIN — all logic in core/reroute.py.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from api.schemas import RerouteRequest
from core.reroute import PathState
from utils.catalog import load_catalog
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post(
    "/reroute",
    summary="Skip skill and recalculate pathway",
    description="Removes a skill from pathway and recalculates dependencies",
)
async def reroute(
    request: RerouteRequest,
) -> JSONResponse:
    """
    Skip a skill and recalculate the pathway.

    Rebuilds PathState from request data then
    calls skip_skill() for deterministic rerouting.

    Args:
        request: RerouteRequest with skill_id + current_path

    Returns:
        RerouteResponse with updated pathway state
    """
    logger.info(
        f"Reroute: skip '{request.skill_id}' "
        f"from {len(request.current_path)} skill path"
    )

    try:
        catalog = load_catalog()

        # Validate skill exists in current path
        if request.skill_id not in request.current_path:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Skill '{request.skill_id}' not found "
                    f"in current pathway"
                ),
            )

        # Rebuild PathState from request
        # Full path = current + already skipped + completed
        full_path = list(request.current_path)

        # Add back previously skipped skills at the end so
        # enforce_order() can re-sort correctly. insert(0, ...) would
        # reverse their original order and potentially re-inject them
        # into the remaining path after re-ordering.
        for skill in request.skipped:
            if skill not in full_path:
                full_path.append(skill)

        path_state = PathState(
            full_path=full_path,
            catalog=catalog,
            remaining=list(request.current_path),
            skipped=set(request.skipped),
            completed=set(request.completed),
        )

        # Execute skip — 3-step reroute algorithm
        result = path_state.skip_skill(request.skill_id)

        logger.info(
            f"Reroute complete: "
            f"{len(result['remaining_path'])} skills remaining, "
            f"{result['hours_saved']}h saved"
        )

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                **result,
            },
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Reroute failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Reroute failed: {str(e)}",
        )


@router.post(
    "/complete",
    summary="Mark skill as completed",
    description="Marks a skill as learned and updates pathway progress",
)
async def complete_skill(
    request: RerouteRequest,
) -> JSONResponse:
    """
    Mark a skill as completed and update progress.

    Args:
        request: RerouteRequest with skill_id + current_path

    Returns:
        Updated pathway state with progress percentage
    """
    logger.info(
        f"Complete: '{request.skill_id}'"
    )

    try:
        catalog = load_catalog()

        if request.skill_id not in request.current_path:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Skill '{request.skill_id}' not found "
                    f"in current pathway"
                ),
            )

        # Rebuild PathState
        full_path = list(request.current_path)
        for skill in request.skipped:
            if skill not in full_path:
                full_path.append(skill)
        for skill in request.completed:
            if skill not in full_path:
                full_path.append(skill)

        path_state = PathState(
            full_path=full_path,
            catalog=catalog,
            remaining=list(request.current_path),
            skipped=set(request.skipped),
            completed=set(request.completed),
        )

        # Mark as complete
        result = path_state.complete_skill(request.skill_id)

        logger.info(
            f"Skill completed: {request.skill_id} — "
            f"{result['progress_percent']}% done"
        )

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                **result,
            },
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Complete skill failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Complete skill failed: {str(e)}",
        )