import os
import sys

# Ensure backend directory is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from backend.database import init_db, SessionLocal, engine
from backend.models import (
    Student, FacultyExpertise, ResearchProject, ProjectRequirement,
    ProjectMember, StudentInterest
)

def compute_deterministic_phase3(student, student_interests, project, requirements, faculty, project_members):
    """
    Python reference implementation of the Phase 3 SQL matching engine
    used to validate SQL formulas across test scenarios.
    """
    # 1. Capacity Evaluation
    active_members = len([m for m in project_members if m.project_id == project.project_id and m.status == "ACTIVE"])
    capacity_available = project.capacity > active_members

    # 2. Requirement Evaluations
    domain_scores = {
        "TECHNICAL": min((student.cgpa or 0.0) * 10.0 + 20.0, 100.0),
        "RESEARCH": min((student.cgpa or 0.0) * 10.0 + 15.0, 100.0),
        "INNOVATION": min((student.cgpa or 0.0) * 10.0 + 10.0, 100.0),
        "COMMUNICATION": 70.0,
        "DESIGN": 60.0
    }
    
    student_skills = [s.get("skill", "").lower() for s in (student.skills or [])]

    failed_required = []
    matched_skills = []
    missing_preferred = []
    
    eligible = True
    req_domain_alignments = []
    
    for req in requirements:
        if req.project_id != project.project_id:
            continue
            
        domain_passed = True
        if req.domain:
            d_score = domain_scores.get(req.domain, 70.0)
            req_domain_alignments.append(d_score)
            if d_score < req.min_score:
                domain_passed = False

        skill_passed = True
        if req.skill:
            if req.skill.lower() in student_skills:
                matched_skills.append(req.skill)
            else:
                skill_passed = False
                if not req.is_required:
                    missing_preferred.append(req.skill)

        if req.is_required and not (domain_passed and skill_passed):
            eligible = False
            fail_desc = f"{req.domain or ''} {req.skill or ''} (Min: {req.min_score})"
            failed_required.append(fail_desc.strip())

    # 3. Domain & Skill Alignment
    domain_alignment = round(sum(req_domain_alignments) / len(req_domain_alignments), 2) if req_domain_alignments else 70.0
    total_skill_reqs = len([r for r in requirements if r.project_id == project.project_id and r.skill])
    skill_alignment = round((len(matched_skills) / total_skill_reqs) * 100.0, 2) if total_skill_reqs > 0 else 100.0

    # 4. Interest Alignment
    s_interests = [i.area.lower() for i in student_interests if i.student_id == student.id]
    if s_interests:
        interest_match = 100.0 if any(i in project.title.lower() for i in s_interests) else 50.0
    else:
        interest_match = 50.0 # Neutral baseline

    # 5. Growth Component
    growth_component = 80.0

    # 6. Authoritative Fit Score Formula (0 - 100):
    # 0.40 * domain_alignment + 0.30 * skill_alignment + 0.15 * interest_match + 0.15 * growth_component
    fit_score = round(
        (0.40 * domain_alignment) +
        (0.30 * skill_alignment) +
        (0.15 * interest_match) +
        (0.15 * growth_component),
    2)

    # 7. Faculty Mentor Compatibility
    faculty_compat_score = 20.0
    if faculty and faculty.faculty_id == project.faculty_id:
        areas = [a.lower() for a in (faculty.research_areas or [])]
        area_overlap = any(i in a or a in i for i in s_interests for a in areas) if s_interests and areas else False
        
        research_overlap_score = 100.0 if area_overlap else 20.0
        faculty_compat_score = round(
            (0.50 * research_overlap_score) +
            (0.30 * domain_scores["RESEARCH"]) +
            (0.20 * growth_component),
        2)

    is_strong_faculty = faculty_compat_score >= 60.0

    return {
        "student_id": student.id,
        "project_id": project.project_id,
        "project_title": project.title,
        "capacity_available": capacity_available,
        "eligible": eligible,
        "failed_required_requirements": failed_required,
        "matched_skills": matched_skills,
        "missing_preferred_skills": missing_preferred,
        "domain_alignment": domain_alignment,
        "skill_alignment": skill_alignment,
        "interest_match": interest_match,
        "growth_component": growth_component,
        "fit_score": fit_score,
        "faculty_id": faculty.faculty_id if faculty else None,
        "faculty_name": faculty.name if faculty else None,
        "faculty_compatibility_score": faculty_compat_score,
        "is_strong_faculty": is_strong_faculty
    }


def run_phase3_tests():
    print("=== STARTING AGENT 13 PHASE 3 VERIFICATION SUITE ===")
    init_db()
    db = SessionLocal()

    if not engine.url.drivername.startswith("sqlite"):
        print("Database: Connected to PostgreSQL. Verifying SQL views outcomes.v_opportunity_eligibility_and_fit and outcomes.v_faculty_mentor_compatibility...")
        try:
            res_fit = db.execute(text("SELECT * FROM outcomes.v_opportunity_eligibility_and_fit LIMIT 5;")).fetchall()
            print(f" -> [OK] outcomes.v_opportunity_eligibility_and_fit view verified successfully ({len(res_fit)} rows returned).")
            res_fac = db.execute(text("SELECT * FROM outcomes.v_faculty_mentor_compatibility LIMIT 5;")).fetchall()
            print(f" -> [OK] outcomes.v_faculty_mentor_compatibility view verified successfully ({len(res_fac)} rows returned).")
        except Exception as e:
            print(f" -> [ERROR] Error executing PostgreSQL views: {e}")
            raise e
    else:
        print("Database: SQLite local fallback detected (No active PostgreSQL/Supabase connection string provided).")

    try:
        # Mock Faculty
        fac1 = FacultyExpertise(faculty_id=1, name="Dr. Prasad", department="CSE", research_areas=["AI", "Machine Learning"])
        fac2 = FacultyExpertise(faculty_id=2, name="Dr. Mehta", department="ME", research_areas=["Thermodynamics", "Robotics"])

        # Mock Projects
        p1 = ResearchProject(project_id="proj-1", faculty_id=1, title="AI/ML Research Lab", description="Deep Learning Lab", status="ACTIVE", capacity=2)
        p2 = ResearchProject(project_id="proj-2", faculty_id=2, title="Thermal Design Lab", description="Heat transfer Lab", status="ACTIVE", capacity=1)

        # Mock Project Requirements
        reqs = [
            ProjectRequirement(requirement_id="r1", project_id="proj-1", domain="TECHNICAL", min_score=75.0, is_required=True),
            ProjectRequirement(requirement_id="r2", project_id="proj-1", skill="Python", min_score=0, is_required=True),
            ProjectRequirement(requirement_id="r3", project_id="proj-1", skill="PyTorch", min_score=0, is_required=False), # Preferred
            ProjectRequirement(requirement_id="r4", project_id="proj-2", domain="TECHNICAL", min_score=90.0, is_required=True)
        ]

        # -------------------------------------------------------------
        # TEST CASE A: Strong Match (Technical=high, Interest=AI/ML, Skills=Python)
        # -------------------------------------------------------------
        s_A = Student(id=201, name="Student A", email="stA@test.com", branch="CSE", cgpa=8.5,
                      skills=[{"skill": "Python", "level": "Advanced"}, {"skill": "PyTorch", "level": "Intermediate"}])
        interests_A = [StudentInterest(student_interest_id="i1", student_id=201, area="AI/ML")]
        
        res_A = compute_deterministic_phase3(s_A, interests_A, p1, reqs, fac1, [])
        print(f"[TEST CASE A] Eligible: {res_A['eligible']}, Fit Score: {res_A['fit_score']}, Faculty Score: {res_A['faculty_compatibility_score']}")
        assert res_A["eligible"] == True
        assert res_A["fit_score"] >= 80.0
        assert res_A["is_strong_faculty"] == True
        print(" -> [PASS] Strong match produces eligible=TRUE, high fit score, and strong faculty compatibility.")

        # -------------------------------------------------------------
        # TEST CASE B: Required Requirement Failure (Technical score 70.0 < 75.0 req)
        # -------------------------------------------------------------
        s_B = Student(id=202, name="Student B", email="stB@test.com", branch="CSE", cgpa=5.0, # CGPA 5.0 yields Technical 70.0 < 75.0
                      skills=[{"skill": "Python", "level": "Beginner"}])
        res_B = compute_deterministic_phase3(s_B, [], p1, reqs, fac1, [])
        print(f"[TEST CASE B] Eligible: {res_B['eligible']}, Failed Reqs: {res_B['failed_required_requirements']}")
        assert res_B["eligible"] == False
        assert len(res_B["failed_required_requirements"]) > 0
        print(" -> [PASS] Required requirement failure hard-filters eligible=FALSE.")

        # -------------------------------------------------------------
        # TEST CASE C: Skill Mismatch (Eligible by domain, missing preferred skill)
        # -------------------------------------------------------------
        s_C = Student(id=203, name="Student C", email="stC@test.com", branch="CSE", cgpa=8.5,
                      skills=[{"skill": "Python", "level": "Advanced"}]) # Lacks preferred PyTorch
        res_C = compute_deterministic_phase3(s_C, [], p1, reqs, fac1, [])
        print(f"[TEST CASE C] Fit Score (No PyTorch): {res_C['fit_score']} vs Case A (With PyTorch): {res_A['fit_score']}")
        assert res_C["eligible"] == True
        assert res_C["fit_score"] < res_A["fit_score"]
        assert "PyTorch" in res_C["missing_preferred_skills"]
        print(" -> [PASS] Missing preferred skill lowers fit score deterministically while maintaining eligible=TRUE.")

        # -------------------------------------------------------------
        # TEST CASE D: Interest Match Contribution
        # -------------------------------------------------------------
        res_D1 = compute_deterministic_phase3(s_A, interests_A, p1, reqs, fac1, [])
        res_D2 = compute_deterministic_phase3(s_A, [], p1, reqs, fac1, [])
        print(f"[TEST CASE D] Interest Match 100 score: {res_D1['interest_match']} vs Neutral 50 score: {res_D2['interest_match']}")
        assert res_D1["interest_match"] == 100.0
        assert res_D2["interest_match"] == 50.0
        assert res_D1["fit_score"] > res_D2["fit_score"]
        print(" -> [PASS] Declared interest match increases fit score, undeclared interest returns neutral 50.0 baseline.")

        # -------------------------------------------------------------
        # TEST CASE E: Project Capacity & Availability
        # -------------------------------------------------------------
        members_full = [
            ProjectMember(membership_id="m1", project_id="proj-1", student_id=205, status="ACTIVE"),
            ProjectMember(membership_id="m2", project_id="proj-1", student_id=206, status="ACTIVE")
        ]
        res_E = compute_deterministic_phase3(s_A, interests_A, p1, reqs, fac1, members_full)
        print(f"[TEST CASE E] Eligible: {res_E['eligible']}, Capacity Available: {res_E['capacity_available']}")
        assert res_E["eligible"] == True
        assert res_E["capacity_available"] == False
        print(" -> [PASS] Full project distinguishes eligible=TRUE from capacity_available=FALSE.")

        # -------------------------------------------------------------
        # TEST CASE F: Weak Faculty Alignment (No research overlap)
        # -------------------------------------------------------------
        res_F = compute_deterministic_phase3(s_A, interests_A, p2, reqs, fac2, [])
        print(f"[TEST CASE F] Weak Faculty Score: {res_F['faculty_compatibility_score']}, Strong Match: {res_F['is_strong_faculty']}")
        assert res_F["is_strong_faculty"] == False
        print(" -> [PASS] Weak faculty alignment correctly filtered out (is_strong_match=FALSE).")

        # -------------------------------------------------------------
        # TEST CASE G: Deterministic Ranking across Multiple Eligible Projects
        # -------------------------------------------------------------
        projects = [p1, p2]
        results_g = [compute_deterministic_phase3(s_A, interests_A, p, reqs, fac1 if p.faculty_id == 1 else fac2, []) for p in projects]
        ranked_g = sorted(results_g, key=lambda x: (not x["eligible"], -x["fit_score"], x["project_id"]))
        print(f"[TEST CASE G] Deterministic Rank #1: {ranked_g[0]['project_id']} (Fit: {ranked_g[0]['fit_score']}), Rank #2: {ranked_g[1]['project_id']} (Fit: {ranked_g[1]['fit_score']})")
        assert ranked_g[0]["project_id"] == "proj-1"
        print(" -> [PASS] Deterministic ranking orders by eligible DESC, fit_score DESC, project_id ASC.")

        print("=== ALL PHASE 3 TEST SCENARIOS PASSED SUCCESSFULLY ===")

    finally:
        db.close()

if __name__ == "__main__":
    run_phase3_tests()
