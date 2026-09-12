import os
import sys

# Ensure backend directory is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import init_db, SessionLocal
from backend.models import Student, ResumeClaim

def compute_all_profiles(all_students, resume_claims):
    """
    Computes deterministic strength profiles for all students non-recursively.
    Formula: 0.45 * academic + 0.35 * achievement + 0.10 * cert + 0.10 * resume
    """
    domains = ["TECHNICAL", "RESEARCH", "INNOVATION", "COMMUNICATION", "DESIGN"]
    
    # 1. First Pass: Calculate raw components & domain scores for each student
    raw_profiles = {}
    for s in all_students:
        # Resume Component
        resume_scores = {}
        for d in domains:
            claims = [r for r in resume_claims if r.student_id == s.id and r.domain == d]
            score = 0.0
            for c in claims:
                if c.verification_status == "VERIFIED":
                    score += 50.0
                elif c.verification_status == "PENDING":
                    score += 15.0  # 0.30 weight of 50.0
            resume_scores[d] = min(score, 100.0)

        # Semester Marks Analysis
        sem_marks = s.semester_marks or {}
        acad_count = len([k for k, v in sem_marks.items() if str(v).replace('.', '', 1).isdigit()])
        has_sufficient_history = acad_count >= 2
        
        early_sems = [float(v) for k, v in sem_marks.items() if k in ['sem1', 'sem2'] and str(v).replace('.', '', 1).isdigit()]
        recent_sems = [float(v) for k, v in sem_marks.items() if k in ['sem3', 'sem4', 'sem5', 'sem6'] and str(v).replace('.', '', 1).isdigit()]
        
        growth_value = None
        if has_sufficient_history and early_sems and recent_sems:
            growth_value = round((sum(recent_sems) / len(recent_sems)) - (sum(early_sems) / len(early_sems)), 2)

        # Domain Component Scores
        scores = {}
        for d in domains:
            acad_comp = min((s.cgpa or 0.0) * 10.0, 100.0)
            
            proj_count = len(s.projects or [])
            hack_count = len(s.hackathons or [])
            intern_count = len(s.internship_history or [])
            cert_count = len(s.certifications or [])
            
            if d == "TECHNICAL":
                ach_comp = min((proj_count * 25.0) + (hack_count * 20.0), 100.0)
                cert_comp = min(cert_count * 33.33, 100.0)
            elif d == "RESEARCH":
                ach_comp = min((proj_count * 20.0) + (intern_count * 30.0), 100.0)
                cert_comp = min(cert_count * 33.33, 100.0)
            elif d == "INNOVATION":
                ach_comp = min((hack_count * 40.0) + (proj_count * 15.0), 100.0)
                cert_comp = min(cert_count * 20.0, 100.0)
            elif d == "COMMUNICATION":
                ach_comp = min(intern_count * 35.0, 100.0)
                cert_comp = min(cert_count * 20.0, 100.0)
            else: # DESIGN
                ach_comp = min(proj_count * 30.0, 100.0)
                cert_comp = min(cert_count * 20.0, 100.0)
                
            res_comp = resume_scores[d]
            
            # Authoritative Frozen Formula: 0.45*acad + 0.35*ach + 0.10*cert + 0.10*res
            weighted = round((0.45 * acad_comp) + (0.35 * ach_comp) + (0.10 * cert_comp) + (0.10 * res_comp), 2)
            scores[d] = min(max(weighted, 0.0), 100.0)

        raw_profiles[s.id] = {
            "student_id": s.id,
            "branch": s.branch,
            "cgpa": s.cgpa,
            "scores": scores,
            "resume_scores": resume_scores,
            "growth_value": growth_value,
            "has_sufficient_history": has_sufficient_history
        }

    # 2. Second Pass: Calculate relative cohort percentiles, medians, hidden talent, and growth buckets
    final_profiles = {}
    by_branch = {}
    for s in all_students:
        by_branch.setdefault(s.branch, []).append(s.id)

    for branch, student_ids in by_branch.items():
        branch_cgpas = sorted([raw_profiles[sid]["cgpa"] for sid in student_ids])
        
        # Branch domain medians & score lists
        domain_lists = {d: sorted([raw_profiles[sid]["scores"][d] for sid in student_ids]) for d in domains}
        domain_medians = {d: domain_lists[d][len(domain_lists[d]) // 2] for d in domains}
        
        # Branch growth values
        growth_values = sorted([raw_profiles[sid]["growth_value"] for sid in student_ids if raw_profiles[sid]["growth_value"] is not None])

        for sid in student_ids:
            p = raw_profiles[sid]
            cgpa_percentile = branch_cgpas.index(p["cgpa"]) / max(len(branch_cgpas) - 1, 1)
            
            hidden_talent_domains = []
            domain_percentiles = {}
            for d in domains:
                d_scores = domain_lists[d]
                d_rank = d_scores.index(p["scores"][d]) / max(len(d_scores) - 1, 1)
                domain_percentiles[d] = d_rank
                
                # Hidden Talent Signal: Sufficient History AND domain_score > median + 10 AND domain_rank > cgpa_rank
                if p["has_sufficient_history"] and p["scores"][d] > (domain_medians[d] + 10.0) and d_rank > cgpa_percentile:
                    hidden_talent_domains.append(d)
            
            # Growth Bucket
            growth_bucket = "INSUFFICIENT_DATA"
            growth_percentile = None
            if p["has_sufficient_history"] and p["growth_value"] is not None and len(growth_values) > 0:
                growth_percentile = growth_values.index(p["growth_value"]) / max(len(growth_values) - 1, 1)
                if growth_percentile >= 0.80:
                    growth_bucket = "HIGH"
                elif growth_percentile >= 0.40:
                    growth_bucket = "MODERATE"
                else:
                    growth_bucket = "LOW"

            final_profiles[sid] = {
                **p,
                "cgpa_percentile": cgpa_percentile,
                "domain_percentiles": domain_percentiles,
                "hidden_talent": len(hidden_talent_domains) > 0,
                "hidden_talent_domains": hidden_talent_domains,
                "growth_percentile": growth_percentile,
                "growth_bucket": growth_bucket,
                "high_growth": growth_bucket == "HIGH"
            }

    return final_profiles


def run_phase2_tests():
    print("=== STARTING AGENT 13 PHASE 2 VERIFICATION SUITE ===")
    init_db()
    db = SessionLocal()
    
    try:
        # Create test cohort
        students = [
            # CASE A: High CGPA + Strong Evidence
            Student(id=101, name="Case A - High Perf", email="caseA@test.com", branch="CSE", cgpa=9.5,
                    semester_marks={"sem1": 9.2, "sem2": 9.4, "sem3": 9.6, "sem4": 9.8},
                    projects=[{"title": "P1"}, {"title": "P2"}], hackathons=[{"name": "H1"}], certifications=[{"name": "C1"}]),
            
            # CASE B: Moderate CGPA + Very Strong Technical/Innovation Evidence (Expect Hidden Talent = True)
            Student(id=102, name="Case B - Hidden Talent", email="caseB@test.com", branch="CSE", cgpa=7.2,
                    semester_marks={"sem1": 7.0, "sem2": 7.2, "sem3": 7.5, "sem4": 7.8},
                    projects=[{"title": "P1"}, {"title": "P2"}, {"title": "P3"}], hackathons=[{"name": "H1"}, {"name": "H2"}], certifications=[{"name": "C1"}, {"name": "C2"}]),
            
            # CASE C: Strong Academic Growth (Sem1/2 = 7.0 -> Sem3/4 = 9.5) -> Expect HIGH Growth
            Student(id=103, name="Case C - High Growth", email="caseC@test.com", branch="CSE", cgpa=8.2,
                    semester_marks={"sem1": 7.0, "sem2": 7.0, "sem3": 9.5, "sem4": 9.5},
                    projects=[], hackathons=[], certifications=[]),
            
            # CASE D: Average Cohort Performance -> Expect MODERATE or LOW Growth
            Student(id=104, name="Case D - Avg Cohort", email="caseD@test.com", branch="CSE", cgpa=7.5,
                    semester_marks={"sem1": 7.5, "sem2": 7.5, "sem3": 7.5, "sem4": 7.5},
                    projects=[], hackathons=[], certifications=[]),
            
            # CASE E: Fewer than 2 semesters -> Expect INSUFFICIENT_DATA
            Student(id=105, name="Case E - Insufficient Hist", email="caseE@test.com", branch="CSE", cgpa=8.0,
                    semester_marks={"sem1": 8.0},
                    projects=[], hackathons=[], certifications=[]),
            
            # CASE F/G: Student for Resume Claim Weighting Test (Pending vs Verified)
            Student(id=106, name="Case F/G - Resume Claim", email="caseF@test.com", branch="CSE", cgpa=8.0,
                    semester_marks={"sem1": 8.0, "sem2": 8.0, "sem3": 8.0, "sem4": 8.0},
                    projects=[], hackathons=[], certifications=[])
        ]
        
        claims = [
            ResumeClaim(claim_id="c1", student_id=106, claim_type="PROJECT", description="ML Model", domain="TECHNICAL", verification_status="PENDING")
        ]

        profiles = compute_all_profiles(students, claims)

        # -------------------------------------------------------------
        # TEST CASE A: High CGPA + Strong Evidence
        # -------------------------------------------------------------
        prof_A = profiles[101]
        print(f"[TEST CASE A] High CGPA Profile Scores: {prof_A['scores']}")
        assert all(0.0 <= score <= 100.0 for score in prof_A["scores"].values())
        print(" -> [PASS] All domain scores bounded 0-100.")

        # -------------------------------------------------------------
        # TEST CASE B: Moderate CGPA + Strong Technical Evidence (Hidden Talent)
        # -------------------------------------------------------------
        prof_B = profiles[102]
        print(f"[TEST CASE B] Moderate CGPA Technical Score: {prof_B['scores']['TECHNICAL']} vs CGPA Percentile: {prof_B['cgpa_percentile']}")
        assert prof_B["hidden_talent"] == True
        assert "TECHNICAL" in prof_B["hidden_talent_domains"] or "INNOVATION" in prof_B["hidden_talent_domains"]
        print(f" -> [PASS] Hidden Talent triggered correctly for domains: {prof_B['hidden_talent_domains']}")

        # -------------------------------------------------------------
        # TEST CASE C: High Growth
        # -------------------------------------------------------------
        prof_C = profiles[103]
        print(f"[TEST CASE C] Growth Value: {prof_C['growth_value']}, Bucket: {prof_C['growth_bucket']}")
        assert prof_C["growth_bucket"] == "HIGH"
        print(" -> [PASS] High relative growth correctly classified.")

        # -------------------------------------------------------------
        # TEST CASE D: Average/Low Growth
        # -------------------------------------------------------------
        prof_D = profiles[104]
        print(f"[TEST CASE D] Growth Value: {prof_D['growth_value']}, Bucket: {prof_D['growth_bucket']}")
        assert prof_D["growth_bucket"] in ["MODERATE", "LOW"]
        print(f" -> [PASS] Average growth correctly classified as {prof_D['growth_bucket']}.")

        # -------------------------------------------------------------
        # TEST CASE E: Insufficient History (< 2 semesters)
        # -------------------------------------------------------------
        prof_E = profiles[105]
        print(f"[TEST CASE E] Sufficient History: {prof_E['has_sufficient_history']}, Growth Bucket: {prof_E['growth_bucket']}")
        assert prof_E["has_sufficient_history"] == False
        assert prof_E["growth_bucket"] == "INSUFFICIENT_DATA"
        assert prof_E["hidden_talent"] == False
        print(" -> [PASS] Insufficient history correctly exposes INSUFFICIENT_DATA and suppresses hidden talent.")

        # -------------------------------------------------------------
        # TEST CASE F: PENDING Resume Claim Weighting (0.30 weight -> 15.0 points)
        # -------------------------------------------------------------
        prof_F = profiles[106]
        score_pending = prof_F["resume_scores"]["TECHNICAL"]
        print(f"[TEST CASE F] PENDING Resume Claim Contribution: {score_pending}")
        assert score_pending == 15.0
        print(" -> [PASS] PENDING claim weighted correctly at 0.30 (15.0 pts).")

        # -------------------------------------------------------------
        # TEST CASE G: PENDING -> VERIFIED Claim Transition
        # -------------------------------------------------------------
        claims_g = [
            ResumeClaim(claim_id="c1", student_id=106, claim_type="PROJECT", description="ML Model", domain="TECHNICAL", verification_status="VERIFIED")
        ]
        profiles_g = compute_all_profiles(students, claims_g)
        score_verified = profiles_g[106]["resume_scores"]["TECHNICAL"]
        print(f"[TEST CASE G] VERIFIED Resume Claim Contribution: {score_verified}")
        assert score_verified == 50.0
        assert score_verified > score_pending
        print(f" -> [PASS] Claim transition PENDING (15.0) -> VERIFIED (50.0) updated score deterministically.")

        print("=== ALL PHASE 2 TEST SCENARIOS PASSED SUCCESSFULLY ===")

    finally:
        db.close()

if __name__ == "__main__":
    run_phase2_tests()
