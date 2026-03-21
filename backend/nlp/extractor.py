"""
SkillSpark AI — Skill Extractor
--------------------------------------
Extracts skill mentions from resume and JD text
using spaCy NER with custom EntityRuler patterns.

Pipeline:
  1. Load spaCy model (en_core_web_lg)
  2. Add custom EntityRuler with skill patterns
  3. Run NLP on text
  4. Return extracted skill mentions with context

This is YOUR original NLP work:
  - Custom entity patterns built from taxonomies
  - Context window extraction for confidence scoring
  - Section-aware extraction

Output is passed to normaliser.py for O*NET mapping.
"""

import json
import re
from pathlib import Path
from typing import Optional

import spacy
from spacy.pipeline import EntityRuler
from spacy.language import Language


# ── Paths ─────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"

TECH_TAXONOMY_PATH = DATA_DIR / "skill_taxonomy_tech.json"
OPS_TAXONOMY_PATH  = DATA_DIR / "skill_taxonomy_ops.json"


# ── Extracted skill dataclass ─────────────────────────────────────

class ExtractedSkill:
    """
    Represents a single skill extracted from text.
    Carries context for confidence scoring.
    """

    def __init__(
        self,
        raw_text:    str,      # exact text matched
        context:     str,      # surrounding sentence
        section:     str,      # resume section found in
        start_char:  int,      # character position start
        end_char:    int,      # character position end
        domain_hint: str = "", # "tech" or "ops" or ""
    ):
        self.raw_text    = raw_text
        self.context     = context
        self.section     = section
        self.start_char  = start_char
        self.end_char    = end_char
        self.domain_hint = domain_hint

    def to_dict(self) -> dict:
        return {
            "raw_text":    self.raw_text,
            "context":     self.context,
            "section":     self.section,
            "start_char":  self.start_char,
            "end_char":    self.end_char,
            "domain_hint": self.domain_hint,
        }


# ── Load taxonomies ───────────────────────────────────────────────

def _load_taxonomy(path: Path) -> dict:
    """
    Loads a skill taxonomy JSON file.

    Args:
        path: Path to taxonomy JSON

    Returns:
        dict of skill data
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("skills", {})
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Taxonomy file not found: {path}"
        )
    except json.JSONDecodeError:
        raise ValueError(
            f"Invalid JSON in taxonomy: {path}"
        )


# ── Build spaCy patterns ──────────────────────────────────────────

def _build_patterns(
    tech_skills: dict,
    ops_skills:  dict,
) -> list[dict]:
    """
    Builds spaCy EntityRuler patterns from taxonomies.

    Creates patterns for:
      - Canonical skill name
      - All aliases

    Args:
        tech_skills: tech taxonomy skills dict
        ops_skills:  ops taxonomy skills dict

    Returns:
        list of spaCy pattern dicts
    """
    patterns: list[dict] = []

    # Tech skill patterns
    for skill_id, skill_data in tech_skills.items():
        # Canonical name pattern
        patterns.append({
            "label":   "SKILL",
            "pattern": skill_data["canonical_name"].replace("_", " "),
            "id":      skill_id,
        })

        # Alias patterns
        for alias in skill_data.get("aliases", []):
            if len(alias) > 1:  # skip single chars
                patterns.append({
                    "label":   "SKILL",
                    "pattern": alias.lower(),
                    "id":      skill_id,
                })

    # Ops skill patterns
    for skill_id, skill_data in ops_skills.items():
        # Canonical name pattern
        patterns.append({
            "label":   "SKILL",
            "pattern": skill_data["canonical_name"].replace("_", " "),
            "id":      skill_id,
        })

        # Alias patterns
        for alias in skill_data.get("aliases", []):
            if len(alias) > 1:
                patterns.append({
                    "label":   "SKILL",
                    "pattern": alias.lower(),
                    "id":      skill_id,
                })

    return patterns


# ── SkillExtractor class ──────────────────────────────────────────

class SkillExtractor:
    """
    Main skill extractor using spaCy + custom EntityRuler.

    Usage:
        extractor = SkillExtractor()
        extractor.load()
        skills = extractor.extract(text, sections)
    """

    def __init__(self):
        self.nlp:     Optional[Language] = None
        self.loaded:  bool = False
        self._tech_skills: dict = {}
        self._ops_skills:  dict = {}

    def load(self) -> None:
        """
        Loads spaCy model and builds custom EntityRuler.
        Call once at startup — not on every request.

        Raises:
            RuntimeError: if spaCy model not found
        """
        try:
            # Load base spaCy model
            self.nlp = spacy.load("en_core_web_lg")

        except OSError:
            # Fallback to smaller model if lg not available
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                raise RuntimeError(
                    "spaCy model not found. Run: "
                    "python -m spacy download en_core_web_lg"
                )

        # Load taxonomies
        self._tech_skills = _load_taxonomy(TECH_TAXONOMY_PATH)
        self._ops_skills  = _load_taxonomy(OPS_TAXONOMY_PATH)

        # Build patterns from taxonomies
        patterns = _build_patterns(
            self._tech_skills,
            self._ops_skills,
        )

        # Add EntityRuler BEFORE ner component
        # so our patterns take priority
        if "entity_ruler" not in self.nlp.pipe_names:
            ruler = self.nlp.add_pipe(
                "entity_ruler",
                before="ner",
                config={"overwrite_ents": True},
            )
            ruler.add_patterns(patterns)

        self.loaded = True

    def extract(
        self,
        text:     str,
        sections: Optional[dict[str, str]] = None,
        domain:   str = "tech",
    ) -> list[ExtractedSkill]:
        """
        Extracts skill mentions from text.

        Args:
            text:     cleaned resume or JD text
            sections: optional section dict from parser
                      used to determine section context
            domain:   "tech" or "ops" — affects context

        Returns:
            list of ExtractedSkill objects
            deduplicated by raw_text
        """
        if not self.loaded:
            raise RuntimeError(
                "Extractor not loaded. Call load() first."
            )

        if not text or not text.strip():
            return []

        # Run spaCy NLP pipeline
        doc = self.nlp(text.lower())

        extracted: list[ExtractedSkill] = []
        seen_skills: set[str] = set()

        for ent in doc.ents:
            if ent.label_ != "SKILL":
                continue

            raw_text = ent.text.strip()

            # Skip duplicates
            if raw_text in seen_skills:
                continue
            seen_skills.add(raw_text)

            # Skip very short matches (likely noise)
            if len(raw_text) < 2:
                continue

            # Extract context window (surrounding sentence)
            context = _extract_context(
                text,
                ent.start_char,
                ent.end_char,
            )

            # Determine which section this skill is in
            section = _find_section(
                ent.start_char,
                text,
                sections or {},
            )

            extracted.append(ExtractedSkill(
                raw_text=raw_text,
                context=context,
                section=section,
                start_char=ent.start_char,
                end_char=ent.end_char,
                domain_hint=domain,
            ))

        return extracted

    def extract_from_sections(
        self,
        sections: dict[str, str],
        domain:   str = "tech",
    ) -> list[ExtractedSkill]:
        """
        Extracts skills from each resume section separately.
        More accurate than extracting from full text because
        section name is known for confidence scoring.

        Args:
            sections: dict of {section_name: section_text}
            domain:   "tech" or "ops"

        Returns:
            deduplicated list of ExtractedSkill objects
        """
        all_extracted: list[ExtractedSkill] = []
        seen_skills: set[str] = set()

        for section_name, section_text in sections.items():
            if not section_text.strip():
                continue

            # Run spaCy on this section
            doc = self.nlp(section_text.lower())

            for ent in doc.ents:
                if ent.label_ != "SKILL":
                    continue

                raw_text = ent.text.strip()

                # Skip duplicates across sections
                # First occurrence wins (experience > skills)
                if raw_text in seen_skills:
                    continue
                seen_skills.add(raw_text)

                if len(raw_text) < 2:
                    continue

                context = _extract_context(
                    section_text,
                    ent.start_char,
                    ent.end_char,
                )

                all_extracted.append(ExtractedSkill(
                    raw_text=raw_text,
                    context=context,
                    section=section_name,
                    start_char=ent.start_char,
                    end_char=ent.end_char,
                    domain_hint=domain,
                ))

        return all_extracted


# ── Context extraction ────────────────────────────────────────────

def _extract_context(
    text:       str,
    start_char: int,
    end_char:   int,
    window:     int = 150,
) -> str:
    """
    Extracts surrounding context around a skill mention.

    Tries to get the full sentence first.
    Falls back to character window if sentence too long.

    Args:
        text:       full text
        start_char: skill mention start position
        end_char:   skill mention end position
        window:     character window size fallback

    Returns:
        context string for confidence scoring
    """
    # Try to find sentence boundaries
    text_before = text[:start_char]
    text_after  = text[end_char:]

    # Find sentence start
    sent_start = max(
        text_before.rfind("."),
        text_before.rfind("\n"),
        text_before.rfind("*"),
        text_before.rfind("-"),
    )
    sent_start = sent_start + 1 if sent_start >= 0 else max(0, start_char - window)

    # Find sentence end
    sent_end_dot  = text_after.find(".")
    sent_end_nl   = text_after.find("\n")

    candidates = [x for x in [sent_end_dot, sent_end_nl] if x >= 0]
    sent_end = end_char + (min(candidates) if candidates else window)
    sent_end = min(sent_end, len(text))

    context = text[sent_start:sent_end].strip()

    # Clean context
    context = re.sub(r"\s+", " ", context)

    return context[:300]  # cap at 300 chars


# ── Section finder ────────────────────────────────────────────────

def _find_section(
    char_pos:  int,
    full_text: str,
    sections:  dict[str, str],
) -> str:
    """
    Determines which resume section a character
    position belongs to.

    Args:
        char_pos:  character position in full text
        full_text: complete resume text
        sections:  section dict from parser

    Returns:
        section name string
    """
    if not sections:
        return "skills"

    # Find which section this position falls into
    current_pos = 0
    for section_name, section_text in sections.items():
        section_start = full_text.find(section_text[:50])
        if section_start == -1:
            continue
        section_end = section_start + len(section_text)

        if section_start <= char_pos <= section_end:
            return section_name

        current_pos = section_end

    # Default to skills if section not found
    return "skills"


# ── Singleton instance ────────────────────────────────────────────
# Created once at module level
# Loaded lazily on first use

_extractor_instance: Optional[SkillExtractor] = None


def get_extractor() -> SkillExtractor:
    """
    Returns singleton SkillExtractor instance.
    Loads model on first call.

    Returns:
        loaded SkillExtractor
    """
    global _extractor_instance

    if _extractor_instance is None:
        _extractor_instance = SkillExtractor()
        _extractor_instance.load()

    return _extractor_instance