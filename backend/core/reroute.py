"""
SkillPathForge AI — Re-route Engine
-------------------------------------
Manages the learning pathway state and handles
skill skipping with automatic path recalculation.

When a user marks a skill as "already known":
  Step 1 — Remove skill from remaining path
  Step 2 — Remove orphaned prerequisites
           (prereqs only needed for skipped skill)
  Step 3 — Re-enforce dependency order on trimmed path
  Step 4 — Recalculate estimated hours

All logic is deterministic — no LLM involved.
PathState is the single source of truth for pathway.
"""

from dataclasses import dataclass, field
from typing import Optional

from core.dependencies import (
    enforce_order,
    get_prerequisites,
    get_all_prerequisites,
    get_unlocked_skills,
    SKILL_DEPENDENCIES,
)
from core.gap import calculate_hours_saved, calculate_total_hours


# ── SkillStatus ───────────────────────────────────────────────────

@dataclass
class SkillStatus:
    """
    Represents the current status of a single skill
    in the learning pathway.
    """
    skill_id:    str
    status:      str    # "pending" | "skipped" | "completed"
    reason:      str    # why it's in this status
    hours:       int    # estimated learning hours
    order:       int    # position in pathway (1-indexed)


# ── PathState ─────────────────────────────────────────────────────

@dataclass
class PathState:
    """
    Single source of truth for the learning pathway.

    Tracks:
      - full original pathway (never modified)
      - remaining skills to learn
      - skipped skills (user marked as known)
      - completed skills (user finished learning)
      - hours saved and remaining

    All pathway mutations go through this class.
    Frontend calls skip_skill() or complete_skill()
    and receives updated pathway back.
    """

    # Original pathway — never modified after init
    full_path:    list[str]

    # Course catalog for hours lookup
    catalog:      dict

    # Current state
    remaining:    list[str] = field(default_factory=list)
    skipped:      set[str]  = field(default_factory=set)
    completed:    set[str]  = field(default_factory=set)

    def __post_init__(self):
        """
        Initialise remaining path as copy of full path.
        Called automatically after dataclass __init__.
        """
        if not self.remaining:
            self.remaining = list(self.full_path)

    # ── skip_skill ────────────────────────────────────────────────
    def skip_skill(self, skill_id: str) -> dict:
        """
        Marks a skill as already known and recalculates path.

        Three-step algorithm:
          1. Remove skill from remaining
          2. Remove orphaned prerequisites
          3. Re-enforce dependency order

        Args:
            skill_id: canonical skill name to skip

        Returns:
            dict with updated pathway state
        """
        # Validate skill is in pathway
        if skill_id not in self.remaining:
            return self._build_state_response(
                message=f"{skill_id} not in current pathway"
            )

        # Step 1 — Mark as skipped + remove from remaining
        self.skipped.add(skill_id)
        self.remaining = [
            s for s in self.remaining
            if s != skill_id
        ]

        # Step 2 — Remove orphaned prerequisites
        # A prereq is orphaned if:
        #   - it was only needed for the skipped skill
        #   - no other remaining skill needs it
        self.remaining = self._remove_orphaned_prereqs()

        # Step 3 — Re-enforce dependency order
        self.remaining = enforce_order(self.remaining)

        return self._build_state_response(
            message=f"Skipped {skill_id} — pathway recalculated"
        )

    # ── complete_skill ────────────────────────────────────────────
    def complete_skill(self, skill_id: str) -> dict:
        """
        Marks a skill as completed (user finished learning it).
        Removes from remaining, adds to completed set.

        Args:
            skill_id: canonical skill name completed

        Returns:
            dict with updated pathway state
        """
        if skill_id not in self.remaining:
            return self._build_state_response(
                message=f"{skill_id} not in current pathway"
            )

        # Move from remaining to completed
        self.completed.add(skill_id)
        self.remaining = [
            s for s in self.remaining
            if s != skill_id
        ]

        # Re-enforce order after removal
        self.remaining = enforce_order(self.remaining)

        return self._build_state_response(
            message=f"Completed {skill_id} — pathway updated"
        )

    # ── reset_pathway ─────────────────────────────────────────────
    def reset_pathway(self) -> dict:
        """
        Resets pathway to original full path.
        Clears all skipped and completed skills.

        Returns:
            dict with reset pathway state
        """
        self.remaining = list(self.full_path)
        self.skipped = set()
        self.completed = set()

        return self._build_state_response(
            message="Pathway reset to original"
        )

    # ── hours_saved ───────────────────────────────────────────────
    def hours_saved(self) -> int:
        """
        Total hours saved by skipping known skills.

        Returns:
            integer hours saved
        """
        return calculate_hours_saved(
            list(self.skipped),
            self.catalog
        )

    # ── hours_remaining ───────────────────────────────────────────
    def hours_remaining(self) -> int:
        """
        Total estimated hours left in pathway.

        Returns:
            integer hours remaining
        """
        return calculate_total_hours(
            self.remaining,
            self.catalog
        )

    # ── total_hours ───────────────────────────────────────────────
    def total_hours(self) -> int:
        """
        Total hours of the original full pathway.

        Returns:
            integer total hours
        """
        return calculate_total_hours(
            self.full_path,
            self.catalog
        )

    # ── get_next_skill ────────────────────────────────────────────
    def get_next_skill(self) -> Optional[str]:
        """
        Returns the next skill to learn in pathway.

        Returns:
            skill_id string or None if pathway complete
        """
        return self.remaining[0] if self.remaining else None

    # ── is_complete ───────────────────────────────────────────────
    def is_complete(self) -> bool:
        """
        Returns True if all skills in pathway are done.

        Returns:
            bool
        """
        return len(self.remaining) == 0

    # ── get_skill_statuses ────────────────────────────────────────
    def get_skill_statuses(self) -> list[SkillStatus]:
        """
        Returns status of every skill in the full pathway.
        Used by frontend to render pathway graph node colours.

        Status values:
            pending   → still in remaining
            skipped   → user marked as known
            completed → user finished learning

        Returns:
            list of SkillStatus ordered by original position
        """
        statuses = []

        for idx, skill_id in enumerate(self.full_path):
            if skill_id in self.completed:
                status = "completed"
                reason = "Marked as completed"
            elif skill_id in self.skipped:
                status = "skipped"
                reason = "Already known — skipped"
            else:
                status = "pending"
                reason = "Pending learning"

            hours = self.catalog.get(
                skill_id, {}
            ).get("duration_hours", 0)

            statuses.append(SkillStatus(
                skill_id=skill_id,
                status=status,
                reason=reason,
                hours=hours,
                order=idx + 1,
            ))

        return statuses

    # ── _remove_orphaned_prereqs ──────────────────────────────────
    def _remove_orphaned_prereqs(self) -> list[str]:
        """
        Internal method.
        Removes prerequisites that are no longer needed
        by any remaining skill.

        A prerequisite is orphaned when:
          - it was in the pathway as a prereq for skill X
          - skill X was skipped
          - no other remaining skill needs this prereq

        Returns:
            cleaned remaining list
        """
        # Collect all prereqs still needed by remaining skills
        still_needed: set[str] = set()

        for skill in self.remaining:
            prereqs = get_all_prerequisites(skill)
            still_needed.update(prereqs)

        # Keep skill if:
        #   - it's still needed as a prereq by someone
        #   - OR it's not in skipped set (it's a target skill)
        cleaned = [
            s for s in self.remaining
            if s in still_needed or s not in self.skipped
        ]

        return cleaned

    # ── _build_state_response ─────────────────────────────────────
    def _build_state_response(
        self,
        message: str = ""
    ) -> dict:
        """
        Builds a complete state snapshot for API response.
        Called after every mutation to return updated state.

        Returns:
            dict with full current pathway state
        """
        return {
            "message":          message,
            "remaining_path":   self.remaining,
            "skipped_skills":   list(self.skipped),
            "completed_skills": list(self.completed),
            "next_skill":       self.get_next_skill(),
            "is_complete":      self.is_complete(),
            "hours_remaining":  self.hours_remaining(),
            "hours_saved":      self.hours_saved(),
            "total_hours":      self.total_hours(),
            "progress_percent": self._calculate_progress(),
            "skill_statuses":   [
                {
                    "skill_id": s.skill_id,
                    "status":   s.status,
                    "reason":   s.reason,
                    "hours":    s.hours,
                    "order":    s.order,
                }
                for s in self.get_skill_statuses()
            ],
        }

    # ── _calculate_progress ───────────────────────────────────────
    def _calculate_progress(self) -> float:
        """
        Calculates completion percentage.

        Returns:
            float 0.0 to 100.0
        """
        total = len(self.full_path)
        if total == 0:
            return 100.0

        done = len(self.skipped) + len(self.completed)
        return round((done / total) * 100, 1)


# ── create_path_state ─────────────────────────────────────────────
def create_path_state(
    ordered_path: list[str],
    catalog: dict,
    known_skills: Optional[list[str]] = None,
) -> PathState:
    """
    Factory function — creates a PathState from an ordered pathway.
    Optionally pre-skips skills the candidate already knows.

    Args:
        ordered_path: dependency-ordered list of skill ids
        catalog: loaded catalog.json dict
        known_skills: optional list of skills to pre-skip

    Returns:
        initialised PathState ready for use
    """
    state = PathState(
        full_path=ordered_path,
        catalog=catalog,
    )

    # Pre-skip skills candidate already knows well
    if known_skills:
        for skill in known_skills:
            if skill in ordered_path:
                state.skip_skill(skill)

    return state