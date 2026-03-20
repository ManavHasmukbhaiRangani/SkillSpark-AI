"""
SkillPathForge AI — Skill Normaliser
--------------------------------------
Maps raw extracted skill mentions to canonical
O*NET skill names using Sentence Transformers.

Pipeline:
  1. Load Sentence Transformer model (all-MiniLM-L6-v2)
  2. Encode all taxonomy canonical names + aliases
  3. For each extracted skill:
     a. Encode raw text
     b. Compute cosine similarity against taxonomy
     c. Return best match above threshold

Why this matters:
  "ML"           → "machine_learning"
  "sklearn"      → "machine_learning"
  "neural nets"  → "deep_learning"
  "pallet jack"  → "pallet_handling"

Output feeds into confidence.py and gap.py.
All logic is YOUR original threshold decisions.
"""

import json
from pathlib import Path
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer, util


# ── Paths ─────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"

TECH_TAXONOMY_PATH = DATA_DIR / "skill_taxonomy_tech.json"
OPS_TAXONOMY_PATH  = DATA_DIR / "skill_taxonomy_ops.json"


# ── Thresholds — YOUR engineering decisions ───────────────────────

# Minimum cosine similarity to accept a match
# Below this = no match, keep raw text
MATCH_THRESHOLD: float = 0.72

# High confidence match threshold
# Above this = very confident in match
HIGH_CONFIDENCE_THRESHOLD: float = 0.88

# Model name — lightweight but accurate
MODEL_NAME: str = "all-MiniLM-L6-v2"


# ── NormalisedSkill ───────────────────────────────────────────────

class NormalisedSkill:
    """
    Represents a skill after normalisation.
    Maps raw extracted text to canonical O*NET name.
    """

    def __init__(
        self,
        raw_text:        str,
        canonical_name:  str,
        display_name:    str,
        similarity:      float,
        domain:          str,
        matched:         bool,
        context:         str = "",
        section:         str = "skills",
        onet_code:       str = "",
    ):
        self.raw_text       = raw_text
        self.canonical_name = canonical_name
        self.display_name   = display_name
        self.similarity     = similarity
        self.domain         = domain
        self.matched        = matched
        self.context        = context
        self.section        = section
        self.onet_code      = onet_code

    def to_dict(self) -> dict:
        return {
            "raw_text":       self.raw_text,
            "canonical_name": self.canonical_name,
            "display_name":   self.display_name,
            "similarity":     round(self.similarity, 3),
            "domain":         self.domain,
            "matched":        self.matched,
            "context":        self.context,
            "section":        self.section,
            "onet_code":      self.onet_code,
        }


# ── SkillNormaliser class ─────────────────────────────────────────

class SkillNormaliser:
    """
    Maps raw skill text to canonical O*NET names
    using Sentence Transformer semantic similarity.

    Usage:
        normaliser = SkillNormaliser()
        normaliser.load()
        results = normaliser.normalise_batch(extracted_skills)
    """

    def __init__(self):
        self.model:         Optional[SentenceTransformer] = None
        self.loaded:        bool = False
        self._tech_skills:  dict = {}
        self._ops_skills:   dict = {}

        # Pre-computed embeddings for taxonomy terms
        self._tech_embeddings: Optional[np.ndarray] = None
        self._ops_embeddings:  Optional[np.ndarray] = None

        # Flat lists for lookup after similarity search
        self._tech_entries: list[dict] = []
        self._ops_entries:  list[dict] = []

    def load(self) -> None:
        """
        Loads Sentence Transformer model and
        pre-computes embeddings for all taxonomy terms.

        Call once at startup — expensive operation.
        Subsequent calls are fast (embeddings cached).

        Raises:
            RuntimeError: if model fails to load
        """
        try:
            self.model = SentenceTransformer(MODEL_NAME)
        except Exception as e:
            raise RuntimeError(
                f"Failed to load Sentence Transformer: {e}"
            )

        # Load taxonomies
        self._tech_skills = _load_taxonomy(TECH_TAXONOMY_PATH)
        self._ops_skills  = _load_taxonomy(OPS_TAXONOMY_PATH)

        # Build flat entry lists with all aliases
        self._tech_entries = _build_entries(self._tech_skills, "tech")
        self._ops_entries  = _build_entries(self._ops_skills, "ops")

        # Pre-compute embeddings for all taxonomy terms
        tech_texts = [e["text"] for e in self._tech_entries]
        ops_texts  = [e["text"] for e in self._ops_entries]

        self._tech_embeddings = self.model.encode(
            tech_texts,
            convert_to_tensor=False,
            show_progress_bar=False,
        )

        self._ops_embeddings = self.model.encode(
            ops_texts,
            convert_to_tensor=False,
            show_progress_bar=False,
        )

        self.loaded = True

    def normalise(
        self,
        raw_text: str,
        domain:   str = "tech",
        context:  str = "",
        section:  str = "skills",
    ) -> NormalisedSkill:
        """
        Normalises a single raw skill text to
        canonical O*NET name.

        Args:
            raw_text: raw extracted skill text
            domain:   "tech" or "ops"
            context:  surrounding text (for logging)
            section:  resume section (for logging)

        Returns:
            NormalisedSkill with canonical name + similarity
        """
        if not self.loaded:
            raise RuntimeError(
                "Normaliser not loaded. Call load() first."
            )

        if not raw_text or not raw_text.strip():
            return _no_match(raw_text, domain, context, section)

        # Encode raw text
        raw_embedding = self.model.encode(
            raw_text.lower().strip(),
            convert_to_tensor=False,
            show_progress_bar=False,
        )

        # Select correct taxonomy based on domain
        if domain == "ops":
            entries    = self._ops_entries
            embeddings = self._ops_embeddings
        else:
            entries    = self._tech_entries
            embeddings = self._tech_embeddings

        if embeddings is None or len(entries) == 0:
            return _no_match(raw_text, domain, context, section)

        # Compute cosine similarities
        similarities = util.cos_sim(
            raw_embedding,
            embeddings
        )[0].numpy()

        # Find best match
        best_idx   = int(np.argmax(similarities))
        best_score = float(similarities[best_idx])

        # Apply threshold — YOUR decision
        if best_score < MATCH_THRESHOLD:
            return _no_match(raw_text, domain, context, section)

        best_entry = entries[best_idx]

        return NormalisedSkill(
            raw_text=raw_text,
            canonical_name=best_entry["canonical_name"],
            display_name=best_entry["display_name"],
            similarity=best_score,
            domain=domain,
            matched=True,
            context=context,
            section=section,
            onet_code=best_entry.get("onet_code", ""),
        )

    def normalise_batch(
        self,
        extracted_skills: list,
        domain: str = "tech",
    ) -> list[NormalisedSkill]:
        """
        Normalises a list of ExtractedSkill objects.
        More efficient than calling normalise() in a loop
        because embeddings are computed in batch.

        Args:
            extracted_skills: list of ExtractedSkill objects
            domain:           "tech" or "ops"

        Returns:
            list of NormalisedSkill objects
            only includes successfully matched skills
        """
        if not self.loaded:
            raise RuntimeError(
                "Normaliser not loaded. Call load() first."
            )

        if not extracted_skills:
            return []

        # Extract raw texts
        raw_texts = [
            s.raw_text.lower().strip()
            for s in extracted_skills
        ]

        # Batch encode all raw texts at once
        raw_embeddings = self.model.encode(
            raw_texts,
            convert_to_tensor=False,
            show_progress_bar=False,
        )

        # Select taxonomy
        if domain == "ops":
            entries    = self._ops_entries
            embeddings = self._ops_embeddings
        else:
            entries    = self._tech_entries
            embeddings = self._tech_embeddings

        results: list[NormalisedSkill] = []
        seen_canonical: set[str] = set()

        for i, raw_embedding in enumerate(raw_embeddings):
            skill = extracted_skills[i]

            if embeddings is None or len(entries) == 0:
                continue

            # Compute similarities for this skill
            similarities = util.cos_sim(
                raw_embedding,
                embeddings,
            )[0].numpy()

            best_idx   = int(np.argmax(similarities))
            best_score = float(similarities[best_idx])

            # Skip below threshold
            if best_score < MATCH_THRESHOLD:
                continue

            best_entry     = entries[best_idx]
            canonical_name = best_entry["canonical_name"]

            # Skip duplicate canonical names
            # First occurrence wins (highest context quality)
            if canonical_name in seen_canonical:
                continue
            seen_canonical.add(canonical_name)

            results.append(NormalisedSkill(
                raw_text=skill.raw_text,
                canonical_name=canonical_name,
                display_name=best_entry["display_name"],
                similarity=best_score,
                domain=domain,
                matched=True,
                context=skill.context,
                section=skill.section,
                onet_code=best_entry.get("onet_code", ""),
            ))

        return results

    def normalise_jd_skills(
        self,
        jd_text: str,
        domain:  str = "tech",
    ) -> list[NormalisedSkill]:
        """
        Extracts and normalises skills from JD text.
        JD skills get default required_confidence from catalog.

        Args:
            jd_text: raw job description text
            domain:  "tech" or "ops"

        Returns:
            list of NormalisedSkill for JD requirements
        """
        # Import here to avoid circular imports
        from nlp.extractor import get_extractor

        extractor = get_extractor()

        # Extract skills from JD text
        extracted = extractor.extract(
            text=jd_text,
            domain=domain,
        )

        # Normalise extracted skills
        return self.normalise_batch(extracted, domain)


# ── Helper functions ──────────────────────────────────────────────

def _load_taxonomy(path: Path) -> dict:
    """Loads taxonomy JSON file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("skills", {})
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Taxonomy not found: {path}"
        )


def _build_entries(
    skills: dict,
    domain: str,
) -> list[dict]:
    """
    Builds flat list of all taxonomy terms with metadata.
    Includes canonical name + all aliases for each skill.

    Args:
        skills: taxonomy skills dict
        domain: "tech" or "ops"

    Returns:
        list of entry dicts for embedding
    """
    entries: list[dict] = []

    for skill_id, skill_data in skills.items():
        canonical = skill_data["canonical_name"]
        display   = skill_data["display_name"]
        onet_code = skill_data.get("onet_code", "")

        # Add canonical name
        entries.append({
            "text":           canonical.replace("_", " "),
            "canonical_name": canonical,
            "display_name":   display,
            "domain":         domain,
            "onet_code":      onet_code,
            "skill_id":       skill_id,
        })

        # Add each alias
        for alias in skill_data.get("aliases", []):
            if len(alias) > 1:
                entries.append({
                    "text":           alias.lower(),
                    "canonical_name": canonical,
                    "display_name":   display,
                    "domain":         domain,
                    "onet_code":      onet_code,
                    "skill_id":       skill_id,
                })

    return entries


def _no_match(
    raw_text: str,
    domain:   str,
    context:  str,
    section:  str,
) -> NormalisedSkill:
    """
    Returns a NormalisedSkill with matched=False.
    Used when no taxonomy match found above threshold.
    """
    return NormalisedSkill(
        raw_text=raw_text,
        canonical_name=raw_text.lower().replace(" ", "_"),
        display_name=raw_text.title(),
        similarity=0.0,
        domain=domain,
        matched=False,
        context=context,
        section=section,
    )


# ── Singleton instance ────────────────────────────────────────────

_normaliser_instance: Optional[SkillNormaliser] = None


def get_normaliser() -> SkillNormaliser:
    """
    Returns singleton SkillNormaliser instance.
    Loads model on first call — subsequent calls are instant.

    Returns:
        loaded SkillNormaliser
    """
    global _normaliser_instance

    if _normaliser_instance is None:
        _normaliser_instance = SkillNormaliser()
        _normaliser_instance.load()

    return _normaliser_instance