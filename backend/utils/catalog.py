"""
SkillSpark AI — Catalog Loader
-------------------------------------
Loads and provides access to the course catalog
and skill taxonomies from JSON files.

Responsibilities:
  - Load catalog.json once at startup
  - Load taxonomy files for tech and ops
  - Provide lookup functions for skill data
  - Cache loaded data in memory

No database needed — JSON flat files only.
All data loaded once, reused for every request.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Optional


# ── Paths ─────────────────────────────────────────────────────────

BASE_DIR     = Path(__file__).resolve().parent.parent.parent
DATA_DIR     = BASE_DIR / "data"

CATALOG_PATH      = DATA_DIR / "catalog.json"
TECH_TAXONOMY_PATH = DATA_DIR / "skill_taxonomy_tech.json"
OPS_TAXONOMY_PATH  = DATA_DIR / "skill_taxonomy_ops.json"


# ── Loaders ───────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def load_catalog() -> dict:
    """
    Loads course catalog from JSON file.
    Cached after first load — reads file once only.

    Returns:
        dict mapping skill_id → catalog entry

    Raises:
        FileNotFoundError: if catalog.json missing
        ValueError: if JSON is invalid
    """
    try:
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            catalog = json.load(f)

        return catalog

    except FileNotFoundError:
        raise FileNotFoundError(
            f"catalog.json not found at {CATALOG_PATH}. "
            f"Make sure data/catalog.json exists."
        )
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Invalid JSON in catalog.json: {e}"
        )


@lru_cache(maxsize=1)
def load_tech_taxonomy() -> dict:
    """
    Loads tech skill taxonomy from JSON file.
    Cached after first load.

    Returns:
        dict with metadata + skills
    """
    try:
        with open(TECH_TAXONOMY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Tech taxonomy not found at {TECH_TAXONOMY_PATH}"
        )
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Invalid JSON in skill_taxonomy_tech.json: {e}"
        )


@lru_cache(maxsize=1)
def load_ops_taxonomy() -> dict:
    """
    Loads ops skill taxonomy from JSON file.
    Cached after first load.

    Returns:
        dict with metadata + skills
    """
    try:
        with open(OPS_TAXONOMY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Ops taxonomy not found at {OPS_TAXONOMY_PATH}"
        )
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Invalid JSON in skill_taxonomy_ops.json: {e}"
        )


# ── Lookup functions ──────────────────────────────────────────────

def get_skill(skill_id: str) -> Optional[dict]:
    """
    Returns catalog entry for a single skill.

    Args:
        skill_id: canonical skill name

    Returns:
        catalog entry dict or None if not found
    """
    catalog = load_catalog()
    return catalog.get(skill_id)


def get_skill_display_name(skill_id: str) -> str:
    """
    Returns display name for a skill.

    Args:
        skill_id: canonical skill name

    Returns:
        display name string or skill_id if not found
    """
    entry = get_skill(skill_id)
    if entry:
        return entry.get("display_name", skill_id)
    return skill_id


def get_skill_duration(skill_id: str) -> int:
    """
    Returns learning duration for a skill in hours.

    Args:
        skill_id: canonical skill name

    Returns:
        duration in hours or 0 if not found
    """
    entry = get_skill(skill_id)
    if entry:
        return entry.get("duration_hours", 0)
    return 0


def get_skill_prerequisites(skill_id: str) -> list[str]:
    """
    Returns prerequisites list for a skill from catalog.

    Args:
        skill_id: canonical skill name

    Returns:
        list of prerequisite skill ids
    """
    entry = get_skill(skill_id)
    if entry:
        return entry.get("prerequisites", [])
    return []


def get_skill_resources(skill_id: str) -> list[dict]:
    """
    Returns learning resources for a skill.

    Args:
        skill_id: canonical skill name

    Returns:
        list of resource dicts with title and url
    """
    entry = get_skill(skill_id)
    if entry:
        return entry.get("resources", [])
    return []


def get_skill_importance(skill_id: str) -> float:
    """
    Returns importance weight for a skill.
    Used in priority score calculation.

    Args:
        skill_id: canonical skill name

    Returns:
        importance weight float (0.0-1.0)
        defaults to 0.70 if not found
    """
    entry = get_skill(skill_id)
    if entry:
        return entry.get("importance_weight", 0.70)
    return 0.70


def get_skills_by_domain(domain: str) -> dict:
    """
    Returns all catalog skills for a specific domain.

    Args:
        domain: "tech" or "ops"

    Returns:
        dict of skill_id → entry for matching domain
    """
    catalog = load_catalog()
    return {
        skill_id: entry
        for skill_id, entry in catalog.items()
        if entry.get("domain") == domain
    }


def get_all_skill_ids() -> list[str]:
    """
    Returns list of all skill IDs in catalog.

    Returns:
        list of canonical skill id strings
    """
    catalog = load_catalog()
    return list(catalog.keys())


def get_catalog_for_pathway(
    pathway: list[str]
) -> list[dict]:
    """
    Returns catalog entries for a list of skill IDs.
    Used by generator.py to build module data.

    Args:
        pathway: list of skill canonical names

    Returns:
        list of catalog entry dicts with id_key added
    """
    catalog = load_catalog()
    entries = []

    for skill_id in pathway:
        entry = catalog.get(skill_id, {})
        entries.append({
            "id_key":         skill_id,
            "display_name":   entry.get("display_name", skill_id),
            "domain":         entry.get("domain", "tech"),
            "level":          entry.get("level", "beginner"),
            "duration_hours": entry.get("duration_hours", 0),
            "prerequisites":  entry.get("prerequisites", []),
            "resources":      entry.get("resources", []),
            "importance_weight": entry.get("importance_weight", 0.70),
            "onet_code":      entry.get("onet_code", ""),
            "description":    entry.get("description", ""),
        })

    return entries


def skill_exists(skill_id: str) -> bool:
    """
    Checks if a skill exists in the catalog.
    Used for hallucination prevention —
    only recommend skills that exist in catalog.

    Args:
        skill_id: canonical skill name

    Returns:
        True if skill is in catalog
    """
    catalog = load_catalog()
    return skill_id in catalog


def get_taxonomy_skills(domain: str) -> list[str]:
    """
    Returns list of canonical skill names
    from the taxonomy for a given domain.

    Args:
        domain: "tech" or "ops"

    Returns:
        list of canonical skill name strings
    """
    if domain == "tech":
        taxonomy = load_tech_taxonomy()
    else:
        taxonomy = load_ops_taxonomy()

    skills = taxonomy.get("skills", {})
    return list(skills.keys())


def get_taxonomy_aliases(domain: str) -> dict:
    """
    Returns mapping of alias → canonical name
    for a domain taxonomy.
    Used by normaliser for quick exact lookups.

    Args:
        domain: "tech" or "ops"

    Returns:
        dict mapping alias_string → canonical_name
    """
    if domain == "tech":
        taxonomy = load_tech_taxonomy()
    else:
        taxonomy = load_ops_taxonomy()

    skills  = taxonomy.get("skills", {})
    aliases = {}

    for skill_id, skill_data in skills.items():
        canonical = skill_data.get("canonical_name", skill_id)

        # Map canonical name itself
        aliases[canonical] = canonical
        aliases[canonical.replace("_", " ")] = canonical

        # Map all aliases
        for alias in skill_data.get("aliases", []):
            aliases[alias.lower()] = canonical

    return aliases


def reload_catalog() -> dict:
    """
    Force reloads catalog from disk.
    Clears lru_cache and reloads.
    Used in development when catalog.json is updated.

    Returns:
        freshly loaded catalog dict
    """
    load_catalog.cache_clear()
    load_tech_taxonomy.cache_clear()
    load_ops_taxonomy.cache_clear()
    return load_catalog()