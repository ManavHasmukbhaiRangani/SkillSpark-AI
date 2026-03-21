"""
SkillSpark AI — Confidence Scoring Engine
----------------------------------------------
Infers skill proficiency from resume context signals.
No explicit skill levels needed from the resume.
Works on real-world resumes that never say "Expert" or "Beginner".

Four signals used:
  1. Years of experience mentioned near the skill
  2. Action verbs used to describe the skill
  3. Role context (led, assisted, managed)
  4. Resume section where skill appears

All logic is deterministic — no LLM involved.
"""

import re
from typing import Optional


# ── Signal 1 — Years of experience ───────────────────────────────
# Maps years → confidence score
# More years = higher confidence, capped at 5 years

YEARS_TO_CONFIDENCE: dict[int, float] = {
    0: 0.35,
    1: 0.60,
    2: 0.72,
    3: 0.82,
    4: 0.88,
    5: 0.95,
}


# ── Signal 2 — Action verbs ───────────────────────────────────────
# Maps verb → confidence score
# Strong verbs (built, led, architected) = high confidence
# Weak verbs (exposure, familiar) = low confidence

VERB_CONFIDENCE: dict[str, float] = {
    # Strong — built and owned it
    "architected":    0.95,
    "designed":       0.92,
    "led":            0.92,
    "built":          0.90,
    "developed":      0.90,
    "created":        0.88,
    "implemented":    0.87,
    "deployed":       0.85,
    "managed":        0.85,
    "established":    0.85,
    "optimised":      0.83,
    "optimized":      0.83,
    "delivered":      0.82,
    "maintained":     0.80,
    "improved":       0.80,
    "automated":      0.82,
    "analysed":       0.78,
    "analyzed":       0.78,
    "reviewed":       0.75,

    # Medium — used it but didn't own it
    "worked":         0.65,
    "used":           0.62,
    "applied":        0.62,
    "contributed":    0.60,
    "supported":      0.55,
    "assisted":       0.45,
    "helped":         0.42,
    "participated":   0.40,
    "involved":       0.40,

    # Weak — barely touched it
    "familiar":       0.30,
    "exposure":       0.25,
    "knowledge of":   0.30,
    "basic":          0.22,
    "learning":       0.18,
    "beginner":       0.18,
    "introduced":     0.20,
    "understanding":  0.28,
}


# ── Signal 3 — Role context ───────────────────────────────────────
# Maps role indicators → confidence modifier
# Added on top of verb score when found

ROLE_MODIFIERS: dict[str, float] = {
    "senior":    0.10,
    "lead":      0.10,
    "principal": 0.12,
    "staff":     0.08,
    "junior":   -0.15,
    "intern":   -0.20,
    "trainee":  -0.20,
    "graduate": -0.10,
    "entry":    -0.15,
}


# ── Signal 4 — Resume section ─────────────────────────────────────
# Maps section name → base confidence
# Skills just listed in Skills section = moderate
# Skills used in Experience = higher

SECTION_CONFIDENCE: dict[str, float] = {
    "work experience":    0.75,
    "experience":         0.75,
    "professional experience": 0.75,
    "employment":         0.72,
    "projects":           0.65,
    "personal projects":  0.62,
    "certifications":     0.78,
    "achievements":       0.70,
    "accomplishments":    0.70,
    "skills":             0.50,
    "technical skills":   0.52,
    "core competencies":  0.52,
    "education":          0.38,
    "coursework":         0.35,
    "training":           0.45,
    "summary":            0.48,
}

# Default if section not recognised
DEFAULT_SECTION_CONFIDENCE: float = 0.50


# ── Signal weights ────────────────────────────────────────────────
# Relative importance of each signal when ALL three are present.
# Weights are normalised at runtime across whichever signals fired,
# so the ratios are preserved regardless of how many are available.
# Ratio: years : verb : section = 40 : 35 : 25

SIGNAL_WEIGHTS: dict[str, float] = {
    "years":   0.40,
    "verb":    0.35,
    "section": 0.25,
}


# ── Helper: extract years from context ───────────────────────────
def _extract_years(context: str) -> Optional[float]:
    """
    Finds year mentions near a skill in resume text.

    Handles patterns like:
      "3 years of Python"
      "2+ years ML experience"
      "over 5 years working with SQL"
      "Python (4 years)"

    Returns:
        confidence float if years found
        None if no year mention found
    """
    context_lower = context.lower()

    # Match patterns: "3 years", "2+ years", "10+ years"
    pattern = r'(\d+)\+?\s*year'
    match = re.search(pattern, context_lower)

    if match:
        years = int(match.group(1))
        # Cap at 5 years for scoring purposes
        years_capped = min(years, 5)
        return YEARS_TO_CONFIDENCE.get(years_capped, 0.95)

    return None


# ── Helper: extract verb score from context ───────────────────────
def _extract_verb_score(context: str) -> Optional[float]:
    """
    Finds the strongest action verb in context text.

    Scans context for all known verbs and returns
    the highest confidence score found.

    Returns:
        highest verb confidence float if found
        None if no known verb found
    """
    context_lower = context.lower()
    best_score: float = 0.0
    found: bool = False

    for verb, score in VERB_CONFIDENCE.items():
        if verb in context_lower:
            best_score = max(best_score, score)
            found = True

    return best_score if found else None


# ── Helper: extract role modifier ────────────────────────────────
def _extract_role_modifier(context: str) -> float:
    """
    Finds role level indicators in context.

    Returns:
        modifier float (positive or negative)
        0.0 if no role indicator found
    """
    context_lower = context.lower()

    for role, modifier in ROLE_MODIFIERS.items():
        if role in context_lower:
            return modifier

    return 0.0


# ── Helper: get section score ─────────────────────────────────────
def _get_section_score(section: str) -> float:
    """
    Returns confidence base score for a resume section.

    Args:
        section: name of the resume section

    Returns:
        confidence float for that section
    """
    section_lower = section.lower().strip()

    for key, score in SECTION_CONFIDENCE.items():
        if key in section_lower:
            return score

    return DEFAULT_SECTION_CONFIDENCE


# ── Main: score_confidence ────────────────────────────────────────
def score_confidence(
    context: str,
    section: str = "skills"
) -> float:
    """
    Combines all four signals into a final confidence score.

    Works on real resumes with NO explicit skill levels.
    Infers proficiency from context clues only.

    Args:
        context: text surrounding the skill mention
                 (the bullet point or sentence it appears in)
        section: resume section name where skill was found
                 defaults to "skills" if unknown

    Returns:
        confidence float between 0.10 and 0.95

    Formula:
        Collect whichever signals fired (years, verb, section).
        Normalise their raw weights so they sum to 1.0, then
        take the weighted average. This means:
          - all three present → years×0.40 + verb×0.35 + section×0.25
          - years + verb only → years×0.533 + verb×0.467
          - verb + section   → verb×0.583  + section×0.417
          - section only     → section×1.0  (full weight, not 0.25)

        + role modifier applied additively after the weighted average.

    Examples:
        "Built ML pipelines for 3 years" → ~0.85
        "Exposure to Docker"             → ~0.30
        "Led Python team (5 years)"      → ~0.93
        "Python" (in Skills section)     → ~0.50
    """
    signals: dict[str, float] = {}

    # Signal 1 — Years
    year_score = _extract_years(context)
    if year_score is not None:
        signals["years"] = year_score

    # Signal 2 — Verb
    verb_score = _extract_verb_score(context)
    if verb_score is not None:
        signals["verb"] = verb_score

    # Signal 3 — Section (always available)
    signals["section"] = _get_section_score(section)

    # Normalise weights across only the signals that fired so
    # their ratios are preserved but they always sum to 1.0.
    # Without normalisation a lone section signal would be
    # multiplied by 0.25 and then divided by 0.25 — correct
    # mathematically but the docstring formula was wrong and
    # the intent is that section carries full weight alone.
    raw_total = sum(SIGNAL_WEIGHTS[k] for k in signals)
    raw_score = sum(
        signals[k] * SIGNAL_WEIGHTS[k]
        for k in signals
    ) / raw_total

    # Signal 4 — Role modifier (additive)
    role_modifier = _extract_role_modifier(context)
    final_score = raw_score + role_modifier

    # Clamp between 0.10 and 0.95
    final_score = round(min(max(final_score, 0.10), 0.95), 2)

    return final_score


# ── batch_score_confidence ────────────────────────────────────────
def batch_score_confidence(
    skill_contexts: list[dict]
) -> dict[str, float]:
    """
    Scores multiple skills at once.

    Args:
        skill_contexts: list of dicts with keys:
            - skill: canonical skill name
            - context: surrounding text
            - section: resume section name

    Returns:
        dict mapping skill name → confidence score

    Example input:
        [
            {
                "skill": "python",
                "context": "Built ML pipelines using Python for 3 years",
                "section": "work experience"
            },
            {
                "skill": "docker",
                "context": "Exposure to Docker",
                "section": "skills"
            }
        ]

    Example output:
        {
            "python": 0.84,
            "docker": 0.28
        }
    """
    results: dict[str, float] = {}

    for item in skill_contexts:
        skill = item.get("skill", "")
        context = item.get("context", "")
        section = item.get("section", "skills")

        if skill:
            results[skill] = score_confidence(context, section)

    return results