"""
SkillPathForge AI — Domain Classifier
--------------------------------------
Classifies whether a resume or job description
belongs to the TECH (desk) or OPS (operational)
domain.

This determines which skill taxonomy is used:
  tech → skill_taxonomy_tech.json + O*NET
  ops  → skill_taxonomy_ops.json + custom ontology

All logic is deterministic — no LLM involved.

Classification method:
  1. Keyword scoring — count domain-specific keywords
  2. Skill overlap — check against known taxonomy skills
  3. Title matching — job title signals
  4. Final decision — highest score wins
"""

import re
from typing import Optional


# ── Domain keyword lists ──────────────────────────────────────────
# Words strongly associated with each domain
# More matches = higher domain score

TECH_KEYWORDS: list[str] = [
    # Programming
    "python", "java", "javascript", "typescript", "c++", "c#",
    "ruby", "golang", "rust", "scala", "kotlin", "swift",
    "html", "css", "react", "angular", "vue", "node",

    # Data
    "sql", "database", "postgresql", "mysql", "mongodb",
    "data analysis", "data science", "machine learning",
    "deep learning", "artificial intelligence", "nlp",
    "pandas", "numpy", "tensorflow", "pytorch", "sklearn",
    "data pipeline", "etl", "data warehouse", "big data",
    "tableau", "power bi", "data visualization",

    # Infrastructure
    "docker", "kubernetes", "aws", "azure", "gcp",
    "linux", "devops", "ci/cd", "jenkins", "terraform",
    "microservices", "api", "rest", "graphql",
    "cloud", "serverless", "infrastructure",

    # Roles
    "software engineer", "data engineer", "data scientist",
    "ml engineer", "backend developer", "frontend developer",
    "full stack", "devops engineer", "cloud architect",
    "product manager", "business analyst", "data analyst",
    "systems analyst", "it", "technology",

    # Tools
    "git", "github", "jira", "confluence", "agile", "scrum",
    "excel", "powerpoint", "microsoft office",
]

OPS_KEYWORDS: list[str] = [
    # Physical operations
    "forklift", "pallet", "warehouse", "loading", "unloading",
    "stacking", "lifting", "physical", "manual handling",
    "inventory", "stockroom", "freight", "cargo", "shipping",
    "receiving", "dispatch", "logistics",

    # Safety
    "osha", "safety", "ppe", "hazard", "protective equipment",
    "first aid", "cpr", "emergency response", "safety compliance",
    "workplace safety", "health and safety",

    # Operations roles
    "warehouse operative", "warehouse worker", "forklift operator",
    "logistics coordinator", "supply chain", "operations manager",
    "floor supervisor", "shift supervisor", "team leader",
    "production worker", "assembly", "manufacturing",
    "quality control", "quality assurance", "inspection",

    # Physical attributes
    "physical stamina", "standing", "heavy lifting",
    "manual labour", "outdoor", "field work",

    # Certifications
    "forklift certification", "osha 10", "osha 30",
    "counterbalance", "reach truck", "pallet jack",

    # Retail / service operations
    "customer service", "retail", "cashier", "pos system",
    "stock replenishment", "merchandising",
]


# ── Job title signals ─────────────────────────────────────────────
# Job titles that strongly indicate a domain
# Checked before keyword scoring

TECH_TITLES: list[str] = [
    "engineer", "developer", "programmer", "architect",
    "analyst", "scientist", "data", "software", "it ",
    "technical", "devops", "cloud", "machine learning",
    "artificial intelligence", "product manager",
]

OPS_TITLES: list[str] = [
    "warehouse", "forklift", "logistics", "operator",
    "operative", "supervisor", "coordinator", "driver",
    "picker", "packer", "assembler", "technician",
    "maintenance", "production", "manufacturing",
    "supply chain", "field", "site",
]


# ── Skill taxonomy sets ───────────────────────────────────────────
# Known skills per domain for overlap scoring

TECH_SKILL_IDS: set[str] = {
    "python", "sql", "machine_learning", "deep_learning",
    "data_analysis", "data_visualization", "statistics",
    "docker", "linux_basics", "git", "system_design",
    "api_development", "cloud_computing", "microsoft_excel",
    "communication", "project_management",
}

OPS_SKILL_IDS: set[str] = {
    "warehouse_safety", "pallet_handling", "forklift_operation",
    "inventory_management", "quality_control", "first_aid",
    "team_leadership", "communication", "time_management",
    "equipment_maintenance", "supply_chain", "data_entry",
    "customer_service", "physical_fitness", "compliance",
}


# ── classify_domain ───────────────────────────────────────────────
def classify_domain(
    text: str,
    job_title: Optional[str] = None,
    extracted_skills: Optional[list[str]] = None,
) -> dict:
    """
    Classifies text as belonging to tech or ops domain.

    Three-stage classification:
      Stage 1 — Job title check (fastest, most reliable)
      Stage 2 — Keyword scoring (count domain keywords)
      Stage 3 — Skill overlap (compare extracted skills)

    Args:
        text: raw resume or JD text
        job_title: optional job title string for faster classification
        extracted_skills: optional list of already extracted skills

    Returns:
        dict with keys:
            domain:      "tech" or "ops"
            confidence:  float 0.0-1.0
            tech_score:  raw tech keyword count
            ops_score:   raw ops keyword count
            method:      how classification was determined
            reasoning:   explanation string

    Example:
        classify_domain("warehouse forklift safety osha pallet")
        → {
            "domain": "ops",
            "confidence": 0.92,
            "tech_score": 0,
            "ops_score": 5,
            "method": "keyword_scoring",
            "reasoning": "5 ops keywords vs 0 tech keywords"
          }
    """
    text_lower = text.lower()

    # ── Stage 1 — Job title check ─────────────────────────────────
    if job_title:
        title_lower = job_title.lower()

        tech_title_hits = sum(
            1 for t in TECH_TITLES if t in title_lower
        )
        ops_title_hits = sum(
            1 for t in OPS_TITLES if t in title_lower
        )

        if tech_title_hits > ops_title_hits and tech_title_hits > 0:
            return {
                "domain":     "tech",
                "confidence": min(0.95, 0.70 + tech_title_hits * 0.05),
                "tech_score": tech_title_hits,
                "ops_score":  ops_title_hits,
                "method":     "title_match",
                "reasoning":  (
                    f"Job title '{job_title}' contains "
                    f"{tech_title_hits} tech indicators"
                ),
            }

        if ops_title_hits > tech_title_hits and ops_title_hits > 0:
            return {
                "domain":     "ops",
                "confidence": min(0.95, 0.70 + ops_title_hits * 0.05),
                "tech_score": tech_title_hits,
                "ops_score":  ops_title_hits,
                "method":     "title_match",
                "reasoning":  (
                    f"Job title '{job_title}' contains "
                    f"{ops_title_hits} ops indicators"
                ),
            }

    # ── Stage 2 — Keyword scoring ─────────────────────────────────
    tech_score = sum(
        1 for kw in TECH_KEYWORDS
        if kw in text_lower
    )
    ops_score = sum(
        1 for kw in OPS_KEYWORDS
        if kw in text_lower
    )

    # ── Stage 3 — Skill overlap ───────────────────────────────────
    if extracted_skills:
        skill_set = set(extracted_skills)
        tech_overlap = len(skill_set & TECH_SKILL_IDS)
        ops_overlap = len(skill_set & OPS_SKILL_IDS)
        tech_score += tech_overlap
        ops_score += ops_overlap

    # ── Final decision ────────────────────────────────────────────
    total = tech_score + ops_score

    if total == 0:
        # No signals found — default to tech
        return {
            "domain":     "tech",
            "confidence": 0.50,
            "tech_score": 0,
            "ops_score":  0,
            "method":     "default",
            "reasoning":  "No domain signals found — defaulting to tech",
        }

    tech_ratio = tech_score / total
    ops_ratio = ops_score / total

    if tech_ratio >= ops_ratio:
        confidence = round(min(0.95, 0.50 + tech_ratio * 0.50), 2)
        return {
            "domain":     "tech",
            "confidence": confidence,
            "tech_score": tech_score,
            "ops_score":  ops_score,
            "method":     "keyword_scoring",
            "reasoning":  (
                f"{tech_score} tech signals vs "
                f"{ops_score} ops signals"
            ),
        }
    else:
        confidence = round(min(0.95, 0.50 + ops_ratio * 0.50), 2)
        return {
            "domain":     "ops",
            "confidence": confidence,
            "tech_score": tech_score,
            "ops_score":  ops_score,
            "method":     "keyword_scoring",
            "reasoning":  (
                f"{ops_score} ops signals vs "
                f"{tech_score} tech signals"
            ),
        }


# ── get_taxonomy_path ─────────────────────────────────────────────
def get_taxonomy_path(domain: str) -> str:
    """
    Returns the correct taxonomy file path for a domain.

    Args:
        domain: "tech" or "ops"

    Returns:
        relative path to taxonomy JSON file
    """
    paths = {
        "tech": "data/skill_taxonomy_tech.json",
        "ops":  "data/skill_taxonomy_ops.json",
    }
    return paths.get(domain, paths["tech"])


# ── get_domain_label ──────────────────────────────────────────────
def get_domain_label(domain: str) -> str:
    """
    Returns human-readable domain label for UI display.

    Args:
        domain: "tech" or "ops"

    Returns:
        readable label string
    """
    labels = {
        "tech": "Technology / Desk Role",
        "ops":  "Operational / Field Role",
    }
    return labels.get(domain, "Unknown Domain")