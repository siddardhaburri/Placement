import uuid
import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey, JSON, ARRAY
from sqlalchemy.orm import relationship
from .database import Base

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    # Supabase auth.users.id (uuid, as text) -- the single source of truth for
    # "who is this row." Nullable only to allow existing seeded/demo rows to
    # exist without an owner; a real student row created via /auth/sync-profile
    # always has this set, and app-level access checks require it.
    profile_id = Column(String, ForeignKey("profile_roles.profile_id"), unique=True, nullable=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    branch = Column(String, nullable=False)
    cgpa = Column(Float, nullable=False)
    tenth_pct = Column(Float, nullable=False)
    twelfth_pct = Column(Float, nullable=False)
    semester_marks = Column(JSON, default=dict)  # e.g., {"sem1": 8.5, "sem2": 9.0}
    backlog_count = Column(Integer, default=0)
    skills = Column(JSON, default=list)  # e.g., [{"skill": "Python", "level": "Advanced"}, ...]
    certifications = Column(JSON, default=list)  # e.g., [{"name": "AWS Certified Cloud Practitioner", "issuer": "Amazon"}]
    projects = Column(JSON, default=list)  # e.g., [{"title": "Placement Ops", "tech_stack": ["FastAPI", "React"]}]
    internship_history = Column(JSON, default=list)  # e.g., [{"company": "Google", "duration_months": 3}]
    hackathons = Column(JSON, default=list)  # e.g., [{"name": "Smart India Hackathon", "result": "Finalist"}]
    current_best_offer = Column(Float, nullable=True)  # LPA of current best offer
    applied_drives = Column(JSON, default=list)  # list of drive IDs applied to

    # Profile media / links
    profile_photo_url = Column(String, nullable=True)
    resume_url = Column(String, nullable=True)
    resume_filename = Column(String, nullable=True)
    github_url = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    portfolio_url = Column(String, nullable=True)
    coding_profiles = Column(JSON, default=dict)  # {"leetcode": "url_or_handle", "codeforces": "...", "hackerrank": "..."}

    # Preferences
    preferred_roles = Column(JSON, default=list)  # e.g., ["Backend Engineer", "SDE"]
    expected_salary = Column(Float, nullable=True)  # LPA
    location_preference = Column(JSON, default=list)  # e.g., ["Bangalore", "Remote"]
    languages = Column(JSON, default=list)  # e.g., ["English", "Hindi"]

    # Resume AI (Milestone 2). resume_ats_score is the headline number shown
    # elsewhere; resume_analysis holds the full structured result (extracted
    # skills, missing skills, suggestions, missing keywords) so it can be
    # displayed without re-running analysis on every page load.
    resume_ats_score = Column(Float, nullable=True)
    resume_analysis = Column(JSON, nullable=True)
    resume_analyzed_at = Column(DateTime, nullable=True)

    # Derived scores
    api_score = Column(Float, default=0.0)  # Academic Performance Index
    ssi_score = Column(Float, default=0.0)  # Skill Strength Index
    prs_score = Column(Float, default=0.0)  # Placement Readiness Score

    eligibility_results = relationship("EligibilityResult", back_populates="student", cascade="all, delete-orphan")
    match_scores = relationship("MatchScore", back_populates="student", cascade="all, delete-orphan")
    interviews = relationship("Interview", back_populates="student", cascade="all, delete-orphan")


class Drive(Base):
    __tablename__ = "drives"

    id = Column(Integer, primary_key=True, index=True)
    # Recruiter (Supabase profile) who owns this drive. Nullable for
    # existing/seeded demo drives; enforced for anything created through
    # POST /drives going forward.
    recruiter_profile_id = Column(String, ForeignKey("profile_roles.profile_id"), nullable=True, index=True)
    company_name = Column(String, nullable=False)
    role_title = Column(String, nullable=False)
    location = Column(String, nullable=True)
    jd_raw_text = Column(Text, nullable=False)
    required_skills = Column(JSON, default=dict)  # e.g., {"required": ["Python", "SQL"], "preferred": ["FastAPI"]}
    cgpa_cutoff = Column(Float, default=0.0)
    eligible_branches = Column(JSON, default=list)  # e.g., ["CSE", "ECE", "ISE"]
    package_min = Column(Float, default=0.0)  # LPA min
    package_max = Column(Float, default=0.0)  # LPA max
    headcount = Column(Integer, default=0)
    status = Column(String, default="draft")  # draft, published, closed
    stage = Column(String, default="intake")  # intake, eligibility, matching, scheduling, coordination, notified, completed
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    eligibility_results = relationship("EligibilityResult", back_populates="drive", cascade="all, delete-orphan")
    match_scores = relationship("MatchScore", back_populates="drive", cascade="all, delete-orphan")
    interviews = relationship("Interview", back_populates="drive", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="drive", cascade="all, delete-orphan")
    exceptions = relationship("ExceptionItem", back_populates="drive", cascade="all, delete-orphan")


class EligibilityResult(Base):
    __tablename__ = "eligibility_results"

    id = Column(Integer, primary_key=True, index=True)
    drive_id = Column(Integer, ForeignKey("drives.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    eligible = Column(Boolean, default=False)
    reason = Column(Text, nullable=True)
    overridden_by_tpo = Column(Boolean, default=False)
    flagged_for_review = Column(Boolean, default=False)

    drive = relationship("Drive", back_populates="eligibility_results")
    student = relationship("Student", back_populates="eligibility_results")


class MatchScore(Base):
    __tablename__ = "match_scores"

    id = Column(Integer, primary_key=True, index=True)
    drive_id = Column(Integer, ForeignKey("drives.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    overall_score = Column(Float, default=0.0)
    skill_score = Column(Float, default=0.0)
    academic_score = Column(Float, default=0.0)
    project_score = Column(Float, default=0.0)
    readiness_score = Column(Float, default=0.0)
    feature_importance = Column(JSON, default=dict)  # SHAP-style breakdown
    rank = Column(Integer, nullable=True)
    approved = Column(Boolean, default=False)
    # Set by a future recruiter workflow (not built yet -- see technical
    # debt notes). Null until then; the student dashboard only shows a
    # Rejected/Offer status when this is actually set, never inferred.
    outcome = Column(String, nullable=True)  # null, "offer", "rejected"

    drive = relationship("Drive", back_populates="match_scores")
    student = relationship("Student", back_populates="match_scores")


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    drive_id = Column(Integer, ForeignKey("drives.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    panel_members = Column(JSON, default=list)  # e.g., ["Dr. Prasad", "Mr. Amit"]
    room_or_link = Column(String, nullable=True)
    time_slot = Column(String, nullable=False)  # e.g., "2026-08-22 10:00 - 10:30"
    status = Column(String, default="scheduled")  # scheduled, completed, no_show, cancelled
    conflict_flag = Column(Boolean, default=False)

    drive = relationship("Drive", back_populates="interviews")
    student = relationship("Student", back_populates="interviews")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    drive_id = Column(Integer, ForeignKey("drives.id"), nullable=True)
    recipient_type = Column(String, nullable=False)  # student, panel
    recipient_id = Column(Integer, nullable=False)  # Student ID or Panel identifier
    channel = Column(String, nullable=False)  # email, sms, portal
    message_template = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=datetime.datetime.utcnow)
    delivery_status = Column(String, default="sent")  # sent, delivered, failed

    drive = relationship("Drive", back_populates="notifications")


class ExceptionItem(Base):
    __tablename__ = "exception_items"

    id = Column(Integer, primary_key=True, index=True)
    drive_id = Column(Integer, ForeignKey("drives.id"), nullable=True)
    type = Column(String, nullable=False)  # eligibility_edge_case, low_confidence_match, schedule_conflict, double_booking, missing_data
    severity = Column(String, nullable=False)  # low, medium, high
    description = Column(Text, nullable=False)
    resolved = Column(Boolean, default=False)
    resolved_by = Column(String, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    drive = relationship("Drive", back_populates="exceptions")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String, nullable=False)  # e.g., "eligibility_override", "shortlist_approve"
    target_type = Column(String, nullable=False)  # e.g., "eligibility", "shortlist", "schedule", "exception"
    target_id = Column(String, nullable=False)
    performed_by = Column(String, default="TPO")
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    details = Column(Text, nullable=True)


class ProfileRole(Base):
    """
    Single source of truth for "which Supabase-authenticated identity has
    which role in this backend." Supabase Auth (via profiles/auth.users) is
    the identity provider; this table is where WE decide and lock in the
    role, because Supabase `user_metadata` is writable by the end user and
    must never be trusted directly for authorization (a student could set
    user_metadata.role = "tpo" via the Supabase client SDK otherwise).

    Populated once by POST /auth/sync-profile on first login and never
    overwritten by later syncs -- role changes are an explicit admin action,
    not something a client request can trigger.
    """
    __tablename__ = "profile_roles"

    profile_id = Column(String, primary_key=True)  # Supabase auth.users.id (uuid, as text)
    email = Column(String, nullable=False)
    role = Column(String, nullable=False)  # student, recruiter, tpo, faculty, hod, principal
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# ==========================================
# AGENT 13 - STUDENTLIFE / CURRICULUM
# ==========================================
class StudentInterest(Base):
    __tablename__ = "student_interest"
    __table_args__ = {"schema": "studentlife"}
    student_interest_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    area = Column(String, nullable=False)
    declared_at = Column(DateTime, default=datetime.datetime.utcnow)

class CourseDomainTag(Base):
    __tablename__ = "course_domain_tag"
    __table_args__ = {"schema": "curriculum"}
    course_id = Column(String, primary_key=True)
    domain = Column(String, nullable=False)
    weight = Column(Float, default=1.0)

class ResumeClaim(Base):
    __tablename__ = "resume_claim"
    __table_args__ = {"schema": "studentlife"}
    claim_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    claim_type = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    domain = Column(String, nullable=False)
    verification_status = Column(String, default="PENDING")
    promoted_to_achievement_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# ==========================================
# AGENT 13 - RESEARCH / FACULTY
# ==========================================
class FacultyExpertise(Base):
    __tablename__ = "faculty_expertise"
    __table_args__ = {"schema": "people"}
    faculty_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    profile_id = Column(String, ForeignKey("profile_roles.profile_id"), unique=True, nullable=True)
    email = Column(String, unique=True, nullable=True)
    name = Column(String, nullable=False)
    department = Column(String, nullable=False)
    research_areas = Column(ARRAY(String).with_variant(JSON, "sqlite"), default=list)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ResearchProject(Base):
    __tablename__ = "project"
    __table_args__ = {"schema": "research"}
    project_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    faculty_id = Column(Integer, ForeignKey("people.faculty_expertise.faculty_id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String, default="ACTIVE")
    capacity = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

class ProjectRequirement(Base):
    __tablename__ = "project_requirement"
    __table_args__ = {"schema": "research"}
    requirement_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("research.project.project_id", ondelete="CASCADE"), nullable=False)
    domain = Column(String, nullable=True)
    skill = Column(String, nullable=True)
    min_score = Column(Float, default=0.0)
    is_required = Column(Boolean, default=True)
    weight = Column(Float, default=1.0)

class ProjectMember(Base):
    __tablename__ = "project_member"
    __table_args__ = {"schema": "research"}
    membership_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("research.project.project_id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    role = Column(String, default="RESEARCH_ASSISTANT")
    status = Column(String, default="ACTIVE")
    assigned_at = Column(DateTime, default=datetime.datetime.utcnow)

# ==========================================
# AGENT 13 - AGENTOPS / RUN TRACKING
# ==========================================
class AgentRegistry(Base):
    __tablename__ = "agent_registry"
    __table_args__ = {"schema": "agentops"}
    agent_no = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    agent_class = Column(String, default="Class 3 / Prescriptive")
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class AgentRun(Base):
    __tablename__ = "agent_run"
    __table_args__ = {"schema": "agentops"}
    run_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_code = Column(String, default="A13_FAST_LEARNER")
    triggered_by = Column(String, ForeignKey("profile_roles.profile_id"), nullable=False)
    status = Column(String, default="STARTED")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class AgentRunInput(Base):
    __tablename__ = "agent_run_input"
    __table_args__ = {"schema": "agentops"}
    input_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String, ForeignKey("agentops.agent_run.run_id", ondelete="CASCADE"), nullable=False)
    context_snapshot = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class AgentOutput(Base):
    __tablename__ = "agent_output"
    __table_args__ = {"schema": "agentops"}
    output_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String, ForeignKey("agentops.agent_run.run_id", ondelete="CASCADE"), nullable=False)
    subject_type = Column(String, default="STUDENT")
    subject_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    payload = Column(JSON, nullable=False)
    reasoning_summary = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class HumanReview(Base):
    __tablename__ = "human_review"
    __table_args__ = {"schema": "agentops"}
    review_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    output_id = Column(String, ForeignKey("agentops.agent_output.output_id", ondelete="CASCADE"), nullable=False)
    decision = Column(String, default="PENDING")
    reviewed_by = Column(String, ForeignKey("profile_roles.profile_id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    comments = Column(Text, nullable=True)

class Agent13AuditLog(Base):
    __tablename__ = "agent13_audit"
    __table_args__ = {"schema": "agentops"}
    audit_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String, ForeignKey("agentops.agent_run.run_id", ondelete="SET NULL"), nullable=True)
    output_id = Column(String, ForeignKey("agentops.agent_output.output_id", ondelete="SET NULL"), nullable=True)
    reviewer_profile_id = Column(String, nullable=True)
    action = Column(String, nullable=False)
    old_state = Column(String, nullable=True)
    new_state = Column(String, nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="SET NULL"), nullable=True)
    project_id = Column(String, ForeignKey("research.project.project_id", ondelete="SET NULL"), nullable=True)
    faculty_id = Column(Integer, ForeignKey("people.faculty_expertise.faculty_id", ondelete="SET NULL"), nullable=True)
    comments = Column(Text, nullable=True)
    execution_result = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Agent13Outcome(Base):
    __tablename__ = "agent13_outcome"
    __table_args__ = {"schema": "outcomes"}
    outcome_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(String, ForeignKey("research.project.project_id", ondelete="SET NULL"), nullable=True)
    event_type = Column(String, nullable=False)
    outcome_result = Column(String, default="IN_PROGRESS")
    details = Column(JSON, default=dict)
    verified = Column(Boolean, default=True)
    recorded_at = Column(DateTime, default=datetime.datetime.utcnow)


