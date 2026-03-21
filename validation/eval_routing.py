"""
SkillSpark AI — Domain Routing Validation Script
------------------------------------------------------
Validates domain classifier accuracy on sample JDs.
Tests whether desk vs operational roles are correctly
classified.

Measures:
  - Accuracy: correct classifications / total JDs
  - Per-domain accuracy (tech vs ops)

Run:
  cd validation
  python eval_routing.py

Output:
  validation/results/routing_accuracy.json
"""

import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from backend.core.domain import classify_domain


# ── Ground truth JD samples ───────────────────────────────────────

GROUND_TRUTH_JDS = [
    # ── Tech / Desk roles ─────────────────────────────────────────
    {
        "id":             "jd_001",
        "expected_domain": "tech",
        "job_title":      "Data Scientist",
        "text": """
            We are looking for a Data Scientist with strong Python skills.
            Must have machine learning and deep learning experience.
            SQL and data analysis required. Docker knowledge preferred.
            Statistics background essential. Git proficiency needed.
        """
    },
    {
        "id":             "jd_002",
        "expected_domain": "tech",
        "job_title":      "Software Engineer",
        "text": """
            Software engineer needed for backend development.
            Python and API development experience required.
            SQL database management skills essential.
            Docker and Linux proficiency preferred.
            System design and git experience needed.
        """
    },
    {
        "id":             "jd_003",
        "expected_domain": "tech",
        "job_title":      "ML Engineer",
        "text": """
            Machine learning engineer for AI product team.
            Deep learning and Python expertise required.
            Cloud computing on AWS or GCP.
            Docker containerisation skills needed.
            Statistics and data analysis background.
        """
    },
    {
        "id":             "jd_004",
        "expected_domain": "tech",
        "job_title":      "Business Analyst",
        "text": """
            Business analyst with Excel and SQL proficiency.
            Data visualization using Power BI or Tableau.
            Statistical analysis and reporting skills.
            Project management experience preferred.
            Strong communication and presentation skills.
        """
    },
    {
        "id":             "jd_005",
        "expected_domain": "tech",
        "job_title":      "DevOps Engineer",
        "text": """
            DevOps engineer with cloud infrastructure experience.
            AWS and Azure management skills required.
            Docker and Kubernetes expertise essential.
            Linux administration and Python scripting.
            CI/CD pipeline experience with git workflows.
        """
    },
    {
        "id":             "jd_006",
        "expected_domain": "tech",
        "job_title":      "Data Analyst",
        "text": """
            Data analyst for business intelligence team.
            SQL and Excel proficiency required.
            Python for data processing and automation.
            Data visualization and dashboard creation.
            Statistical analysis and reporting experience.
        """
    },
    {
        "id":             "jd_007",
        "expected_domain": "tech",
        "job_title":      "Full Stack Developer",
        "text": """
            Full stack developer for web application team.
            Python backend and API development required.
            SQL database design experience needed.
            Git version control and Linux proficiency.
            Docker and cloud deployment experience.
        """
    },
    # ── Ops / Field roles ─────────────────────────────────────────
    {
        "id":             "jd_008",
        "expected_domain": "ops",
        "job_title":      "Forklift Operator",
        "text": """
            Forklift operator needed for busy warehouse.
            Must have valid forklift certification and OSHA training.
            Pallet handling and loading/unloading experience required.
            Warehouse safety knowledge essential.
            Physical fitness and stamina required.
            Inventory management experience preferred.
        """
    },
    {
        "id":             "jd_009",
        "expected_domain": "ops",
        "job_title":      "Warehouse Supervisor",
        "text": """
            Warehouse supervisor for logistics operation.
            Team leadership and staff management experience.
            Warehouse safety and OSHA compliance knowledge.
            Inventory management and quality control skills.
            Supply chain coordination experience preferred.
            First aid certification an advantage.
        """
    },
    {
        "id":             "jd_010",
        "expected_domain": "ops",
        "job_title":      "Logistics Coordinator",
        "text": """
            Logistics coordinator for distribution centre.
            Supply chain management experience required.
            Inventory tracking and warehouse management skills.
            Forklift certification preferred.
            Safety compliance and quality control knowledge.
            Strong communication and time management skills.
        """
    },
    {
        "id":             "jd_011",
        "expected_domain": "ops",
        "job_title":      "Warehouse Operative",
        "text": """
            Warehouse operative for busy fulfilment centre.
            Picking, packing and dispatching orders.
            Pallet handling and manual handling experience.
            Warehouse safety awareness required.
            Physical stamina and ability to lift heavy loads.
            Quality control checks on outgoing orders.
        """
    },
    {
        "id":             "jd_012",
        "expected_domain": "ops",
        "job_title":      "Operations Manager",
        "text": """
            Operations manager for manufacturing facility.
            Team leadership and people management experience.
            Safety compliance and regulatory knowledge.
            Quality control and process improvement skills.
            Supply chain and inventory oversight.
            Equipment maintenance coordination experience.
        """
    },
    {
        "id":             "jd_013",
        "expected_domain": "ops",
        "job_title":      "Production Supervisor",
        "text": """
            Production supervisor for assembly line operation.
            Manufacturing and production management experience.
            Safety compliance and OSHA knowledge required.
            Team leadership and staff supervision skills.
            Quality control and inspection procedures.
            Equipment maintenance awareness preferred.
        """
    },
    {
        "id":             "jd_014",
        "expected_domain": "tech",
        "job_title":      "Product Manager",
        "text": """
            Product manager for SaaS technology company.
            Agile and scrum project management experience.
            Data analysis and SQL proficiency preferred.
            Strong communication and presentation skills.
            Technical background in software development.
            Git and project management tools experience.
        """
    },
    {
        "id":             "jd_015",
        "expected_domain": "ops",
        "job_title":      "Health and Safety Officer",
        "text": """
            Health and safety officer for industrial facility.
            OSHA certification and safety compliance expertise.
            Hazard identification and risk assessment skills.
            First aid and emergency response certification.
            Warehouse and operational safety knowledge.
            Compliance and regulatory reporting experience.
        """
    },
]


# ── Main evaluation ───────────────────────────────────────────────

def run_evaluation():
    """
    Runs domain routing evaluation on ground truth JDs.
    """
    print("SkillSpark AI — Domain Routing Validation")
    print("=" * 50)

    results      = []
    correct      = 0
    tech_correct = 0
    tech_total   = 0
    ops_correct  = 0
    ops_total    = 0

    for sample in GROUND_TRUTH_JDS:
        result = classify_domain(
            text=sample["text"],
            job_title=sample["job_title"],
        )

        predicted = result["domain"]
        expected  = sample["expected_domain"]
        is_correct = predicted == expected

        if is_correct:
            correct += 1

        if expected == "tech":
            tech_total += 1
            if is_correct:
                tech_correct += 1
        else:
            ops_total += 1
            if is_correct:
                ops_correct += 1

        status = "✓" if is_correct else "✗"
        print(
            f"{status} {sample['id']} — "
            f"{sample['job_title']}: "
            f"expected={expected}, "
            f"predicted={predicted} "
            f"(confidence={result['confidence']:.2f})"
        )

        results.append({
            "id":               sample["id"],
            "job_title":        sample["job_title"],
            "expected_domain":  expected,
            "predicted_domain": predicted,
            "confidence":       result["confidence"],
            "correct":          is_correct,
            "method":           result["method"],
            "reasoning":        result["reasoning"],
        })

    # Overall accuracy
    total    = len(GROUND_TRUTH_JDS)
    accuracy = correct / total

    tech_accuracy = tech_correct / tech_total if tech_total else 0
    ops_accuracy  = ops_correct  / ops_total  if ops_total  else 0

    print("\n" + "=" * 50)
    print("OVERALL RESULTS")
    print("=" * 50)
    print(f"Overall Accuracy:  {accuracy:.3f} ({correct}/{total})")
    print(f"Tech Accuracy:     {tech_accuracy:.3f} ({tech_correct}/{tech_total})")
    print(f"Ops Accuracy:      {ops_accuracy:.3f} ({ops_correct}/{ops_total})")
    print(f"Target > 85%:      {'✓ PASS' if accuracy >= 0.85 else '✗ FAIL'}")

    # Save results
    output = {
        "summary": {
            "overall_accuracy": round(accuracy, 3),
            "tech_accuracy":    round(tech_accuracy, 3),
            "ops_accuracy":     round(ops_accuracy, 3),
            "correct":          correct,
            "total":            total,
            "target_accuracy":  0.85,
            "passed":           accuracy >= 0.85,
        },
        "per_sample": results,
    }

    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)

    output_path = results_dir / "routing_accuracy.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved to: {output_path}")
    return output


if __name__ == "__main__":
    run_evaluation()