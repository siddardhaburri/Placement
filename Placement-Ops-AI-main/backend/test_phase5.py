import os
import sys
import unittest
import uuid
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.database import DATABASE_URL
from backend.models import (
    Base, Student, ProfileRole, FacultyExpertise, ResearchProject,
    ProjectRequirement, ProjectMember, AgentRun, AgentOutput, HumanReview,
    Agent13AuditLog, Agent13Outcome
)
from backend.agents.talent_discovery_agent import TalentDiscoveryAgent, Agent13ApprovalService
from backend.database import DATABASE_URL, init_db, SessionLocal

class TestAgent13Phase5(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()
        cls.db = SessionLocal()
        res = cls.db.execute(text("SELECT 1;")).first()
        print(f"\n[PHASE 5 TEST] Database in use: {DATABASE_URL}")

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def setUp(self):
        self.db.rollback()
        self.db.execute(text("""
            INSERT INTO public.students (id, name, email, branch, cgpa, tenth_pct, twelfth_pct)
            VALUES (1, 'Test Student 1', 'student1@test.com', 'CSE', 8.8, 90.0, 90.0),
                   (2, 'Test Student 2', 'student2@test.com', 'ECE', 8.2, 85.0, 85.0),
                   (3, 'Test Student 3', 'student3@test.com', 'CSE', 9.1, 92.0, 92.0),
                   (4, 'Test Student 4', 'student4@test.com', 'ISE', 7.9, 80.0, 80.0)
            ON CONFLICT (id) DO NOTHING;
        """))
        self.db.commit()

    def test_01_pending_recommendation_cannot_assign_without_review(self):
        # A. Pending recommendation cannot assign without approval
        reviews = Agent13ApprovalService.get_pending_reviews(self.db)
        self.assertIsInstance(reviews, list)
        for r in reviews:
            self.assertEqual(r["decision"], "PENDING")

    def test_02_student_cannot_approve_own_recommendation(self):
        # D. Student cannot approve own recommendation
        student_prof = str(uuid.uuid4())
        self.db.execute(
            text("INSERT INTO public.profile_roles (profile_id, email, role) VALUES (:pid, :email, 'student') ON CONFLICT DO NOTHING"),
            {"pid": student_prof, "email": f"student_{student_prof[:6]}@test.com"}
        )
        self.db.commit()

        output_id = TalentDiscoveryAgent.run_discovery_for_student(self.db, student_id=1, triggered_by_profile_id=student_prof)
        self.assertIsNotNone(output_id)

        review = self.db.query(HumanReview).filter(HumanReview.output_id == output_id).first()
        self.assertIsNotNone(review)

        # Attempt approval by student -> MUST FAIL
        res = Agent13ApprovalService.process_review_decision(
            self.db,
            review_id=review.review_id,
            reviewer_profile_id=student_prof,
            decision="APPROVE"
        )
        self.assertFalse(res["success"])
        self.assertEqual(res["status_code"], "ASSIGNMENT_FAILED_AUTHORIZATION")

    def test_03_unauthorized_faculty_cannot_approve_other_faculty_project(self):
        # C & N. Unauthorized reviewer cannot approve
        fac1_prof = str(uuid.uuid4())
        fac2_prof = str(uuid.uuid4())

        self.db.execute(
            text("INSERT INTO public.profile_roles (profile_id, email, role) VALUES (:p1, :e1, 'faculty'), (:p2, :e2, 'faculty') ON CONFLICT DO NOTHING"),
            {
                "p1": fac1_prof, "e1": f"fac1_{fac1_prof[:6]}@cs.test.com",
                "p2": fac2_prof, "e2": f"fac2_{fac2_prof[:6]}@ee.test.com"
            }
        )
        self.db.execute(
            text("INSERT INTO people.faculty_expertise (profile_id, email, name, department) VALUES (:p1, :e1, 'Prof One', 'CSE'), (:p2, :e2, 'Prof Two', 'ECE') ON CONFLICT DO NOTHING"),
            {
                "p1": fac1_prof, "e1": f"fac1_{fac1_prof[:6]}@cs.test.com",
                "p2": fac2_prof, "e2": f"fac2_{fac2_prof[:6]}@ee.test.com"
            }
        )
        self.db.commit()

        proj_id = str(uuid.uuid4())
        fac2_id = self.db.execute(
            text("SELECT faculty_id FROM people.faculty_expertise WHERE profile_id = :p"),
            {"p": fac2_prof}
        ).first()[0]

        self.db.execute(
            text("INSERT INTO research.project (project_id, faculty_id, title, description, status, capacity) VALUES (:pid, :fid, 'ECE Quantum Sensor', 'Quantum project', 'ACTIVE', 1)"),
            {"pid": proj_id, "fid": fac2_id}
        )
        self.db.commit()

        run_id = str(uuid.uuid4())
        self.db.execute(text("INSERT INTO agentops.agent_run (run_id, triggered_by, status) VALUES (:r, :t, 'COMPLETED')"), {"r": run_id, "t": fac1_prof})
        out_id = str(uuid.uuid4())
        self.db.execute(
            text("INSERT INTO agentops.agent_output (output_id, run_id, subject_type, subject_id, payload, reasoning_summary, confidence) VALUES (:oid, :rid, 'STUDENT', 1, :p, 'Test reasoning', 0.9)"),
            {"oid": out_id, "rid": run_id, "p": '{"opportunities": [{"project_id": "' + proj_id + '", "eligible": true, "fit_score": 90}]}'}
        )
        rev_id = str(uuid.uuid4())
        self.db.execute(text("INSERT INTO agentops.human_review (review_id, output_id, decision) VALUES (:rev, :out, 'PENDING')"), {"rev": rev_id, "out": out_id})
        self.db.commit()

        # Faculty 1 (CSE) attempts to approve Faculty 2's ECE project -> MUST FAIL
        res = Agent13ApprovalService.process_review_decision(
            self.db,
            review_id=rev_id,
            reviewer_profile_id=fac1_prof,
            decision="APPROVE"
        )
        self.assertFalse(res["success"])
        self.assertEqual(res["status_code"], "ASSIGNMENT_FAILED_AUTHORIZATION")

    def test_04_authorized_approve_assigns_successfully(self):
        # B. Authorized APPROVE assigns successfully
        fac_prof = str(uuid.uuid4())
        self.db.execute(text("INSERT INTO public.profile_roles (profile_id, email, role) VALUES (:p, :e, 'faculty')"), {"p": fac_prof, "e": f"f_{fac_prof[:6]}@cs.com"})
        self.db.execute(text("INSERT INTO people.faculty_expertise (profile_id, email, name, department) VALUES (:p, :e, 'Dr. Smith', 'CSE')"), {"p": fac_prof, "e": f"f_{fac_prof[:6]}@cs.com"})
        self.db.commit()

        fac_id = self.db.execute(text("SELECT faculty_id FROM people.faculty_expertise WHERE profile_id = :p"), {"p": fac_prof}).first()[0]
        proj_id = str(uuid.uuid4())
        self.db.execute(text("INSERT INTO research.project (project_id, faculty_id, title, description, status, capacity) VALUES (:pid, :fid, 'AI Medical Imaging', 'AI Project', 'ACTIVE', 2)"), {"pid": proj_id, "fid": fac_id})
        self.db.commit()

        run_id = str(uuid.uuid4())
        self.db.execute(text("INSERT INTO agentops.agent_run (run_id, triggered_by, status) VALUES (:r, :t, 'COMPLETED')"), {"r": run_id, "t": fac_prof})
        out_id = str(uuid.uuid4())
        self.db.execute(
            text("INSERT INTO agentops.agent_output (output_id, run_id, subject_type, subject_id, payload, reasoning_summary, confidence) VALUES (:oid, :rid, 'STUDENT', 1, :p, 'Test reasoning', 0.95)"),
            {"oid": out_id, "rid": run_id, "p": '{"opportunities": [{"project_id": "' + proj_id + '", "eligible": true, "fit_score": 95}]}'}
        )
        rev_id = str(uuid.uuid4())
        self.db.execute(text("INSERT INTO agentops.human_review (review_id, output_id, decision) VALUES (:rev, :out, 'PENDING')"), {"rev": rev_id, "out": out_id})
        self.db.commit()

        res = Agent13ApprovalService.process_review_decision(self.db, review_id=rev_id, reviewer_profile_id=fac_prof, decision="APPROVE")
        self.assertTrue(res["success"])
        self.assertEqual(res["status_code"], "ASSIGNMENT_EXECUTED")

        mem = self.db.execute(text("SELECT * FROM research.project_member WHERE project_id = :pid AND student_id = 1"), {"pid": proj_id}).first()
        self.assertIsNotNone(mem)

    def test_05_rejection_never_creates_project_member(self):
        # E. REJECT never creates project_member
        fac_prof = str(uuid.uuid4())
        self.db.execute(text("INSERT INTO public.profile_roles (profile_id, email, role) VALUES (:p, :e, 'faculty')"), {"p": fac_prof, "e": f"f_{fac_prof[:6]}@cs.com"})
        self.db.execute(text("INSERT INTO people.faculty_expertise (profile_id, email, name, department) VALUES (:p, :e, 'Dr. Jones', 'CSE')"), {"p": fac_prof, "e": f"f_{fac_prof[:6]}@cs.com"})
        self.db.commit()

        fac_id = self.db.execute(text("SELECT faculty_id FROM people.faculty_expertise WHERE profile_id = :p"), {"p": fac_prof}).first()[0]
        proj_id = str(uuid.uuid4())
        self.db.execute(text("INSERT INTO research.project (project_id, faculty_id, title, description, status, capacity) VALUES (:pid, :fid, 'NLP Research', 'NLP Project', 'ACTIVE', 1)"), {"pid": proj_id, "fid": fac_id})
        self.db.commit()

        run_id = str(uuid.uuid4())
        self.db.execute(text("INSERT INTO agentops.agent_run (run_id, triggered_by, status) VALUES (:r, :t, 'COMPLETED')"), {"r": run_id, "t": fac_prof})
        out_id = str(uuid.uuid4())
        self.db.execute(
            text("INSERT INTO agentops.agent_output (output_id, run_id, subject_type, subject_id, payload, reasoning_summary, confidence) VALUES (:oid, :rid, 'STUDENT', 2, :p, 'Test reasoning', 0.9)"),
            {"oid": out_id, "rid": run_id, "p": '{"opportunities": [{"project_id": "' + proj_id + '", "eligible": true, "fit_score": 85}]}'}
        )
        rev_id = str(uuid.uuid4())
        self.db.execute(text("INSERT INTO agentops.human_review (review_id, output_id, decision) VALUES (:rev, :out, 'PENDING')"), {"rev": rev_id, "out": out_id})
        self.db.commit()

        res = Agent13ApprovalService.process_review_decision(self.db, review_id=rev_id, reviewer_profile_id=fac_prof, decision="REJECT", comments="Student lacks prerequisite depth")
        self.assertTrue(res["success"])
        self.assertEqual(res["status_code"], "RECOMMENDATION_REJECTED")

        mem = self.db.execute(text("SELECT * FROM research.project_member WHERE project_id = :pid AND student_id = 2"), {"pid": proj_id}).first()
        self.assertIsNone(mem)

    def test_06_idempotent_duplicate_execution(self):
        # I. Duplicate execution is idempotent
        fac_prof = str(uuid.uuid4())
        self.db.execute(text("INSERT INTO public.profile_roles (profile_id, email, role) VALUES (:p, :e, 'faculty')"), {"p": fac_prof, "e": f"f_{fac_prof[:6]}@cs.com"})
        self.db.execute(text("INSERT INTO people.faculty_expertise (profile_id, email, name, department) VALUES (:p, :e, 'Dr. Alan', 'CSE')"), {"p": fac_prof, "e": f"f_{fac_prof[:6]}@cs.com"})
        self.db.commit()

        fac_id = self.db.execute(text("SELECT faculty_id FROM people.faculty_expertise WHERE profile_id = :p"), {"p": fac_prof}).first()[0]
        proj_id = str(uuid.uuid4())
        self.db.execute(text("INSERT INTO research.project (project_id, faculty_id, title, description, status, capacity) VALUES (:pid, :fid, 'Robotics Vision', 'Vision Project', 'ACTIVE', 5)"), {"pid": proj_id, "fid": fac_id})
        self.db.commit()

        run_id = str(uuid.uuid4())
        self.db.execute(text("INSERT INTO agentops.agent_run (run_id, triggered_by, status) VALUES (:r, :t, 'COMPLETED')"), {"r": run_id, "t": fac_prof})
        out_id = str(uuid.uuid4())
        self.db.execute(
            text("INSERT INTO agentops.agent_output (output_id, run_id, subject_type, subject_id, payload, reasoning_summary, confidence) VALUES (:oid, :rid, 'STUDENT', 3, :p, 'Test reasoning', 0.9)"),
            {"oid": out_id, "rid": run_id, "p": '{"opportunities": [{"project_id": "' + proj_id + '", "eligible": true, "fit_score": 88}]}'}
        )
        rev_id = str(uuid.uuid4())
        self.db.execute(text("INSERT INTO agentops.human_review (review_id, output_id, decision) VALUES (:rev, :out, 'PENDING')"), {"rev": rev_id, "out": out_id})
        self.db.commit()

        res1 = Agent13ApprovalService.process_review_decision(self.db, review_id=rev_id, reviewer_profile_id=fac_prof, decision="APPROVE")
        self.assertTrue(res1["success"])
        self.assertEqual(res1["status_code"], "ASSIGNMENT_EXECUTED")

        res2 = Agent13ApprovalService.process_review_decision(self.db, review_id=rev_id, reviewer_profile_id=fac_prof, decision="APPROVE")
        self.assertTrue(res2["success"])
        self.assertEqual(res2["status_code"], "ALREADY_ASSIGNED")

        count = self.db.execute(text("SELECT COUNT(*) FROM research.project_member WHERE project_id = :pid AND student_id = 3"), {"pid": proj_id}).first()[0]
        self.assertEqual(count, 1)

    def test_07_full_project_capacity_triggers_expiration(self):
        # H & J. Full project at execution time -> EXPIRED
        fac_prof = str(uuid.uuid4())
        self.db.execute(text("INSERT INTO public.profile_roles (profile_id, email, role) VALUES (:p, :e, 'faculty')"), {"p": fac_prof, "e": f"f_{fac_prof[:6]}@cs.com"})
        self.db.execute(text("INSERT INTO people.faculty_expertise (profile_id, email, name, department) VALUES (:p, :e, 'Dr. Capacity', 'CSE')"), {"p": fac_prof, "e": f"f_{fac_prof[:6]}@cs.com"})
        self.db.commit()

        fac_id = self.db.execute(text("SELECT faculty_id FROM people.faculty_expertise WHERE profile_id = :p"), {"p": fac_prof}).first()[0]
        proj_id = str(uuid.uuid4())
        self.db.execute(text("INSERT INTO research.project (project_id, faculty_id, title, description, status, capacity) VALUES (:pid, :fid, 'Limited Spot Project', 'Single spot project', 'ACTIVE', 1)"), {"pid": proj_id, "fid": fac_id})
        self.db.execute(text("INSERT INTO research.project_member (membership_id, project_id, student_id, role, status) VALUES (gen_random_uuid(), :pid, 3, 'RA', 'ACTIVE')"), {"pid": proj_id})
        self.db.commit()

        run_id = str(uuid.uuid4())
        self.db.execute(text("INSERT INTO agentops.agent_run (run_id, triggered_by, status) VALUES (:r, :t, 'COMPLETED')"), {"r": run_id, "t": fac_prof})
        out_id = str(uuid.uuid4())
        self.db.execute(
            text("INSERT INTO agentops.agent_output (output_id, run_id, subject_type, subject_id, payload, reasoning_summary, confidence) VALUES (:oid, :rid, 'STUDENT', 4, :p, 'Test reasoning', 0.9)"),
            {"oid": out_id, "rid": run_id, "p": '{"opportunities": [{"project_id": "' + proj_id + '", "eligible": true, "fit_score": 92}]}'}
        )
        rev_id = str(uuid.uuid4())
        self.db.execute(text("INSERT INTO agentops.human_review (review_id, output_id, decision) VALUES (:rev, :out, 'PENDING')"), {"rev": rev_id, "out": out_id})
        self.db.commit()

        res = Agent13ApprovalService.process_review_decision(self.db, review_id=rev_id, reviewer_profile_id=fac_prof, decision="APPROVE")
        self.assertFalse(res["success"])
        self.assertEqual(res["status_code"], "ASSIGNMENT_FAILED_CAPACITY")

        rev_row = self.db.execute(text("SELECT decision FROM agentops.human_review WHERE review_id = :r"), {"r": rev_id}).first()
        self.assertEqual(rev_row[0], "EXPIRED")

    def test_08_outcome_recording_and_feedback(self):
        # P & Q. Outcome is recorded & future run feedback
        res = Agent13ApprovalService.record_outcome(
            self.db,
            student_id=1,
            project_id=None,
            event_type="RESEARCH_MILESTONE",
            outcome_result="SUCCESSFUL",
            details={"paper_title": "Deep Learning in Healthcare", "venue": "IEEE Conference"}
        )
        self.assertTrue(res["success"])
        self.assertIsNotNone(res["outcome_id"])

        row = self.db.execute(
            text("SELECT * FROM outcomes.agent13_outcome WHERE outcome_id = :oid"),
            {"oid": res["outcome_id"]}
        ).mappings().first()
        self.assertIsNotNone(row)
        self.assertEqual(row["event_type"], "RESEARCH_MILESTONE")
        self.assertEqual(row["outcome_result"], "SUCCESSFUL")

if __name__ == "__main__":
    unittest.main()
