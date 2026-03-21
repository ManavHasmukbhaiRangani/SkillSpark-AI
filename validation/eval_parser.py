"""
SkillSpark AI — Parser Validation Script
---------------------------------------------
Validates spaCy + Sentence Transformer extraction
accuracy against Kaggle resume dataset.

Measures:
  - Precision: correctly extracted / all extracted
  - Recall:    correctly extracted / all actual skills
  - F1 score:  harmonic mean of precision + recall

Run:
  cd validation
  python eval_parser.py

Output:
  validation/results/parser_accuracy.json
"""

import json
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from backend.nlp.extractor import get_extractor
from backend.nlp.normaliser import get_normaliser


# ── Ground truth samples ──────────────────────────────────────────
# Manually labelled skill sets for 10 sample resumes
# In production: use full Kaggle dataset
# These are representative samples for demo validation

GROUND_TRUTH = [
    {
        "id": "resume_001",
        "category": "Data Science",
        "text": """
            Experienced data scientist with 3 years of Python development.
            Built machine learning models using scikit-learn and pandas.
            Strong SQL skills and data visualization using matplotlib.
            Familiar with docker and git version control.
            Used statistics and probability for model evaluation.
        """,
        "expected_skills": [
            "python", "machine_learning", "data_analysis",
            "sql", "data_visualization", "docker",
            "git", "statistics"
        ]
    },
    {
        "id": "resume_002",
        "category": "Software Engineering",
        "text": """
            Software engineer with expertise in Python and system design.
            Developed REST APIs using FastAPI and Flask frameworks.
            Managed SQL and PostgreSQL databases.
            Used docker and kubernetes for deployment.
            Experienced with git workflows and linux administration.
            Cloud computing experience with AWS services.
        """,
        "expected_skills": [
            "python", "system_design", "api_development",
            "sql", "docker", "linux_basics",
            "git", "cloud_computing"
        ]
    },
    {
        "id": "resume_003",
        "category": "Warehouse Operations",
        "text": """
            Warehouse operative with 5 years experience.
            Certified forklift operator with OSHA forklift certification.
            Strong knowledge of warehouse safety and pallet handling.
            Experience in inventory management and quality control.
            First aid and CPR certified.
            Team leader for warehouse floor operations.
        """,
        "expected_skills": [
            "forklift_operation", "warehouse_safety",
            "pallet_handling", "inventory_management",
            "quality_control", "first_aid", "team_leadership"
        ]
    },
    {
        "id": "resume_004",
        "category": "Data Analysis",
        "text": """
            Data analyst with expertise in Excel and SQL.
            Built dashboards using data visualization tools.
            Python scripting for data processing and automation.
            Statistical analysis and reporting experience.
            Strong communication and presentation skills.
            Project management using agile methodology.
        """,
        "expected_skills": [
            "microsoft_excel", "sql", "data_visualization",
            "python", "statistics", "communication",
            "project_management"
        ]
    },
    {
        "id": "resume_005",
        "category": "Machine Learning",
        "text": """
            ML engineer with deep learning expertise.
            Built neural networks using TensorFlow and PyTorch.
            Strong Python and statistics background.
            Data analysis using pandas and numpy.
            Deployed models using docker containers on AWS cloud.
            Git version control and linux proficiency.
        """,
        "expected_skills": [
            "deep_learning", "python", "statistics",
            "data_analysis", "docker", "cloud_computing",
            "git", "linux_basics"
        ]
    },
    {
        "id": "resume_006",
        "category": "Logistics",
        "text": """
            Logistics coordinator with supply chain management experience.
            Managed inventory systems and warehouse operations.
            Forklift certified with strong safety compliance record.
            Quality control and equipment maintenance experience.
            Data entry and record keeping proficiency.
            Customer service and communication skills.
        """,
        "expected_skills": [
            "supply_chain", "inventory_management",
            "forklift_operation", "warehouse_safety",
            "quality_control", "equipment_maintenance",
            "data_entry", "customer_service"
        ]
    },
    {
        "id": "resume_007",
        "category": "DevOps",
        "text": """
            DevOps engineer with cloud computing expertise.
            Managed AWS and Azure infrastructure.
            Docker and kubernetes containerisation.
            Linux system administration and bash scripting.
            CI/CD pipelines using git workflows.
            Python automation scripts for deployment.
            System design and architecture experience.
        """,
        "expected_skills": [
            "cloud_computing", "docker", "linux_basics",
            "git", "python", "system_design"
        ]
    },
    {
        "id": "resume_008",
        "category": "Business Analyst",
        "text": """
            Business analyst with strong Excel and SQL skills.
            Data visualization using Power BI and Tableau.
            Statistical analysis and reporting.
            Project management and agile experience.
            Strong communication and presentation skills.
            Python for data processing tasks.
        """,
        "expected_skills": [
            "microsoft_excel", "sql", "data_visualization",
            "statistics", "project_management",
            "communication", "python"
        ]
    },
    {
        "id": "resume_009",
        "category": "Operations Manager",
        "text": """
            Operations manager with team leadership experience.
            Managed warehouse safety and compliance programs.
            Supply chain and inventory management oversight.
            Quality control and process improvement.
            Strong communication and time management skills.
            First aid certified and safety compliance expert.
        """,
        "expected_skills": [
            "team_leadership", "warehouse_safety",
            "supply_chain", "inventory_management",
            "quality_control", "communication",
            "compliance", "first_aid"
        ]
    },
    {
        "id": "resume_010",
        "category": "Full Stack Developer",
        "text": """
            Full stack developer with Python and API development.
            Built REST APIs and web services.
            SQL database design and management.
            Docker containerisation and cloud deployment.
            Git version control and linux proficiency.
            System design and microservices architecture.
            Strong communication and project management.
        """,
        "expected_skills": [
            "python", "api_development", "sql",
            "docker", "git", "linux_basics",
            "system_design", "communication",
            "project_management"
        ]
    },
]


# ── Evaluation functions ──────────────────────────────────────────

def precision(extracted: set, expected: set) -> float:
    """
    Precision = correctly extracted / all extracted
    """
    if not extracted:
        return 0.0
    correct = len(extracted & expected)
    return correct / len(extracted)


def recall(extracted: set, expected: set) -> float:
    """
    Recall = correctly extracted / all actual skills
    """
    if not expected:
        return 0.0
    correct = len(extracted & expected)
    return correct / len(expected)


def f1_score(p: float, r: float) -> float:
    """
    F1 = 2 × (precision × recall) / (precision + recall)
    """
    if p + r == 0:
        return 0.0
    return 2 * (p * r) / (p + r)


# ── Main evaluation ───────────────────────────────────────────────

def run_evaluation():
    """
    Runs parser evaluation on ground truth samples.
    """
    print("SkillSpark AI — Parser Validation")
    print("=" * 50)

    # Load models
    print("\nLoading NLP models...")
    extractor  = get_extractor()
    normaliser = get_normaliser()
    print("Models loaded.\n")

    results = []
    all_precisions = []
    all_recalls    = []
    all_f1s        = []

    for sample in GROUND_TRUTH:
        print(f"Evaluating: {sample['id']} ({sample['category']})")

        # Extract skills
        extracted_raw = extractor.extract(
            text=sample["text"],
            domain="tech" if sample["category"] not in
                   ["Warehouse Operations", "Logistics",
                    "Operations Manager"]
                   else "ops"
        )

        # Normalise
        domain = "ops" if sample["category"] in [
            "Warehouse Operations", "Logistics", "Operations Manager"
        ] else "tech"

        normalised = normaliser.normalise_batch(
            extracted_skills=extracted_raw,
            domain=domain,
        )

        # Get canonical names
        extracted_skills = {s.canonical_name for s in normalised}
        expected_skills  = set(sample["expected_skills"])

        # Calculate metrics
        p  = precision(extracted_skills, expected_skills)
        r  = recall(extracted_skills, expected_skills)
        f1 = f1_score(p, r)

        all_precisions.append(p)
        all_recalls.append(r)
        all_f1s.append(f1)

        # Correct + missed + extra
        correct = extracted_skills & expected_skills
        missed  = expected_skills - extracted_skills
        extra   = extracted_skills - expected_skills

        result = {
            "id":               sample["id"],
            "category":         sample["category"],
            "precision":        round(p, 3),
            "recall":           round(r, 3),
            "f1_score":         round(f1, 3),
            "extracted_count":  len(extracted_skills),
            "expected_count":   len(expected_skills),
            "correct":          list(correct),
            "missed":           list(missed),
            "extra":            list(extra),
        }
        results.append(result)

        print(f"  Precision: {p:.3f} | Recall: {r:.3f} | F1: {f1:.3f}")
        if missed:
            print(f"  Missed: {missed}")

    # Overall metrics
    avg_precision = sum(all_precisions) / len(all_precisions)
    avg_recall    = sum(all_recalls)    / len(all_recalls)
    avg_f1        = sum(all_f1s)        / len(all_f1s)

    print("\n" + "=" * 50)
    print("OVERALL RESULTS")
    print("=" * 50)
    print(f"Average Precision: {avg_precision:.3f}")
    print(f"Average Recall:    {avg_recall:.3f}")
    print(f"Average F1 Score:  {avg_f1:.3f}")
    print(f"Target F1 > 0.80:  {'✓ PASS' if avg_f1 >= 0.80 else '✗ FAIL'}")

    # Save results
    output = {
        "summary": {
            "avg_precision": round(avg_precision, 3),
            "avg_recall":    round(avg_recall, 3),
            "avg_f1":        round(avg_f1, 3),
            "target_f1":     0.80,
            "passed":        avg_f1 >= 0.80,
            "samples_tested": len(GROUND_TRUTH),
        },
        "per_sample": results,
    }

    # Create results directory
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)

    output_path = results_dir / "parser_accuracy.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved to: {output_path}")
    return output


if __name__ == "__main__":
    run_evaluation()