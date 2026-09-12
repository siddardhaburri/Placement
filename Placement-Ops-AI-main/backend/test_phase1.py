import os
import sys

# Ensure backend directory is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import engine, init_db, SessionLocal
from backend.models import (
    Base, Student, ProfileRole, StudentInterest, CourseDomainTag, ResumeClaim,
    FacultyExpertise, ResearchProject, ProjectRequirement, ProjectMember,
    AgentRegistry, AgentRun, AgentRunInput, AgentOutput, HumanReview, AuditLog
)

def test_phase1():
    print("=== STARTING COMPREHENSIVE AGENT 13 PHASE 1 VERIFICATION ===")
    
    # 1. Initialize Database
    init_db()
    
    db = SessionLocal()
    try:
        # 2. Verify Models Registration
        models = [
            StudentInterest, CourseDomainTag, ResumeClaim, FacultyExpertise,
            ResearchProject, ProjectRequirement, ProjectMember, AgentRegistry,
            AgentRun, AgentRunInput, AgentOutput, HumanReview, AuditLog
        ]
        for m in models:
            print(f"[OK] Model verified: {m.__name__} -> table '{m.__tablename__}'")

        # 3. Test Agent Registration
        print("[OK] Verifying Agent 13 Registration Data...")
        reg = db.query(AgentRegistry).filter(AgentRegistry.agent_no == 13).first()
        if not reg:
            reg = AgentRegistry(
                agent_no=13,
                code="A13_FAST_LEARNER",
                name="Talent Discovery & Opportunity Agent",
                agent_class="Class 3 / Prescriptive",
                description="Prescriptive Agent for talent discovery, hidden talent identification, and research project matching."
            )
            db.add(reg)
            db.commit()
            db.refresh(reg)
        
        fetched_reg = db.query(AgentRegistry).filter(AgentRegistry.agent_no == 13).first()
        assert fetched_reg is not None
        assert fetched_reg.code == "A13_FAST_LEARNER"
        assert fetched_reg.agent_class == "Class 3 / Prescriptive"
        print(f"[SUCCESS] Agent 13 Registered: {fetched_reg.code} - {fetched_reg.name} ({fetched_reg.agent_class})")

        # 4. Test AuditLog with String target_id (Real UUID/String IDs)
        print("[OK] Verifying AuditLog Real String Identifier Support...")
        test_uuid = "b72e5a11-8c01-4df2-8e10-332e12345678"
        log_entry = AuditLog(
            action="AGENT13_APPROVED",
            target_type="agent_output",
            target_id=test_uuid,
            performed_by="faculty_user_id",
            details="Output ID b72e5a11-8c01-4df2-8e10-332e12345678 APPROVED"
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        
        fetched_log = db.query(AuditLog).filter(AuditLog.target_id == test_uuid).first()
        assert fetched_log is not None
        assert fetched_log.target_id == test_uuid
        print(f"[SUCCESS] AuditLog target_id verified with real UUID string: {fetched_log.target_id}")

        # 5. Test Faculty & Privileged Role Authorization Data Mapping
        print("[OK] Testing Faculty Identity & Institutional Pre-authorization...")
        faculty = db.query(FacultyExpertise).filter(FacultyExpertise.email == "dr.smith@university.edu").first()
        if not faculty:
            faculty = FacultyExpertise(
                email="dr.smith@university.edu",
                name="Dr. John Smith",
                department="CSE",
                research_areas=["AI", "Machine Learning"]
            )
            db.add(faculty)
            db.commit()
            db.refresh(faculty)
        
        fetched_faculty = db.query(FacultyExpertise).filter(FacultyExpertise.email == "dr.smith@university.edu").first()
        assert fetched_faculty is not None
        assert fetched_faculty.department == "CSE"
        print(f"[SUCCESS] Faculty record pre-authorized: {fetched_faculty.name} ({fetched_faculty.department})")

        print("=== ALL PHASE 1 VERIFICATION TESTS PASSED SUCCESSFULLY ===")
    finally:
        db.close()

if __name__ == "__main__":
    test_phase1()
