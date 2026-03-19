"""
SkillPathForge AI — Skill Dependency Engine
--------------------------------------------
Owns the prerequisite relationships between skills.
This is YOUR original logic — no LLM involved.
Rule: prereqs always appear before the skill that needs them.
"""


# ── Skill dependency map ──────────────────────────────────────────
# Key   = skill that needs prerequisites
# Value = list of skills that must be learned first
# Source: derived from O*NET skill relationships + domain knowledge

SKILL_DEPENDENCIES: dict[str, list[str]] = {

    # ── Tech domain ──────────────────────────────────────────────
    "data_analysis": [
        "python",
        "statistics"
    ],
    "machine_learning": [
        "python",
        "statistics",
        "data_analysis"
    ],
    "deep_learning": [
        "python",
        "machine_learning",
        "statistics"
    ],
    "data_visualization": [
        "python",
        "data_analysis"
    ],
    "docker": [
        "linux_basics"
    ],
    "system_design": [
        "sql",
        "linux_basics"
    ],
    "api_development": [
        "python",
        "sql"
    ],
    "cloud_computing": [
        "linux_basics",
        "docker"
    ],

    # ── Ops domain ───────────────────────────────────────────────
    "pallet_handling": [
        "warehouse_safety"
    ],
    "forklift_operation": [
        "warehouse_safety",
        "pallet_handling"
    ],
    "inventory_management": [
        "warehouse_safety"
    ],
    "quality_control": [
        "warehouse_safety"
    ],
    "equipment_maintenance": [
        "warehouse_safety"
    ],
    "supply_chain": [
        "inventory_management"
    ],
    "team_leadership": [
        "communication"
    ],
    "compliance": [
        "warehouse_safety"
    ],

    # ── Shared ───────────────────────────────────────────────────
    "project_management": [
        "communication"
    ],

    # ── No prerequisites (standalone skills) ─────────────────────
    # python, statistics, sql, git, linux_basics,
    # communication, microsoft_excel, warehouse_safety,
    # first_aid, physical_fitness, customer_service,
    # data_entry, time_management
    # → these are NOT listed here intentionally
    # → missing key = no prerequisites needed
}


# ── enforce_order — deterministic DFS ────────────────────────────
def enforce_order(suggested_path: list[str]) -> list[str]:
    """
    Takes a list of skills and returns them in correct
    dependency order using Depth First Search (DFS).

    Rule:
      - Prerequisites always appear before the skill
        that depends on them
      - If a skill has no prerequisites it stays in place
      - Handles circular references safely via visited set

    Args:
        suggested_path: list of skill canonical_names

    Returns:
        ordered list with prerequisites inserted correctly

    Example:
        Input:  ["machine_learning", "python"]
        Output: ["python", "statistics", "data_analysis",
                 "machine_learning"]
    """
    ordered: list[str] = []
    visited: set[str] = set()

    def dfs(skill: str) -> None:
        # Skip if already processed
        if skill in visited:
            return

        # Mark as visited immediately to prevent cycles
        visited.add(skill)

        # Recursively process all prerequisites first
        for prereq in SKILL_DEPENDENCIES.get(skill, []):
            dfs(prereq)

        # Add skill only after all its prereqs are added
        ordered.append(skill)

    for skill in suggested_path:
        dfs(skill)

    return ordered


# ── get_prerequisites — fetch direct prereqs ─────────────────────
def get_prerequisites(skill: str) -> list[str]:
    """
    Returns direct prerequisites for a given skill.

    Args:
        skill: canonical skill name

    Returns:
        list of prerequisite skill names
        empty list if no prerequisites
    """
    return SKILL_DEPENDENCIES.get(skill, [])


# ── get_all_prerequisites — fetch full chain ──────────────────────
def get_all_prerequisites(skill: str) -> list[str]:
    """
    Returns ALL prerequisites recursively (full chain).
    Useful for reasoning trace — show complete dependency chain.

    Args:
        skill: canonical skill name

    Returns:
        flat list of all prerequisite skills in order

    Example:
        get_all_prerequisites("machine_learning")
        → ["python", "statistics", "data_analysis"]
    """
    all_prereqs: list[str] = []
    visited: set[str] = set()

    def collect(s: str) -> None:
        if s in visited:
            return
        visited.add(s)
        for prereq in SKILL_DEPENDENCIES.get(s, []):
            collect(prereq)
            if prereq not in all_prereqs:
                all_prereqs.append(prereq)

    collect(skill)
    return all_prereqs


# ── has_prerequisites_met ─────────────────────────────────────────
def has_prerequisites_met(
    skill: str,
    known_skills: list[str]
) -> bool:
    """
    Checks if all prerequisites for a skill are already
    in the candidate's known skills list.

    Args:
        skill: canonical skill name to check
        known_skills: list of skills candidate already has

    Returns:
        True if all prereqs met or no prereqs needed
        False if any prereq is missing

    Used in reasoning trace to explain why a skill
    is or is not immediately learnable.
    """
    prereqs = get_prerequisites(skill)
    if not prereqs:
        return True
    return all(prereq in known_skills for prereq in prereqs)


# ── get_unlocked_skills ───────────────────────────────────────────
def get_unlocked_skills(
    skill: str,
    all_skills: list[str]
) -> list[str]:
    """
    Returns skills that become available after learning
    the given skill. Used in reasoning trace to show
    what a module unlocks next.

    Args:
        skill: canonical skill name just learned
        all_skills: full list of skills in catalog

    Returns:
        list of skills this skill directly unlocks
    """
    unlocked = []
    for s in all_skills:
        prereqs = SKILL_DEPENDENCIES.get(s, [])
        if skill in prereqs:
            unlocked.append(s)
    return unlocked