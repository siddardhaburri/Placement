-- ============================================================
-- Agent 13 — Canonical Tables, RLS Policies, & Agent Registration (Phase 1)
-- ============================================================

-- 1. Safely extend public.profiles role CHECK constraint
ALTER TABLE public.profiles DROP CONSTRAINT IF EXISTS profiles_role_check;
ALTER TABLE public.profiles ADD CONSTRAINT profiles_role_check 
    CHECK (role IN ('student', 'recruiter', 'tpo', 'faculty', 'hod', 'principal'));

-- 2. Create schemas if they do not exist
CREATE SCHEMA IF NOT EXISTS studentlife;
CREATE SCHEMA IF NOT EXISTS curriculum;
CREATE SCHEMA IF NOT EXISTS research;
CREATE SCHEMA IF NOT EXISTS agentops;
CREATE SCHEMA IF NOT EXISTS people;

-- ============================================================
-- SECURITY & IDENTITY HELPER FUNCTIONS
-- ============================================================
CREATE OR REPLACE FUNCTION public.get_current_profile_role()
RETURNS text
LANGUAGE sql SECURITY DEFINER STABLE
SET search_path = public AS $$
  SELECT role FROM public.profile_roles WHERE profile_id = auth.uid()::text
  UNION ALL
  SELECT role FROM public.profiles WHERE id = auth.uid()
  LIMIT 1;
$$;

CREATE OR REPLACE FUNCTION public.get_current_student_id()
RETURNS int
LANGUAGE sql SECURITY DEFINER STABLE
SET search_path = public AS $$
  SELECT id FROM public.students 
  WHERE profile_id = auth.uid()::text OR profile_id = auth.uid()::varchar
  LIMIT 1;
$$;

CREATE OR REPLACE FUNCTION people.get_current_faculty_id()
RETURNS int
LANGUAGE sql SECURITY DEFINER STABLE
SET search_path = people, public AS $$
  SELECT faculty_id FROM people.faculty_expertise 
  WHERE profile_id = auth.uid() OR profile_id::text = auth.uid()::text
  LIMIT 1;
$$;

CREATE OR REPLACE FUNCTION people.get_current_faculty_department()
RETURNS text
LANGUAGE sql SECURITY DEFINER STABLE
SET search_path = people, public AS $$
  SELECT department FROM people.faculty_expertise 
  WHERE profile_id = auth.uid() OR profile_id::text = auth.uid()::text
  LIMIT 1;
$$;

-- ============================================================
-- CANONICAL TABLES
-- ============================================================

-- STUDENTLIFE.STUDENT_INTEREST
CREATE TABLE IF NOT EXISTS studentlife.student_interest (
    student_interest_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id int NOT NULL REFERENCES public.students(id) ON DELETE CASCADE,
    area text NOT NULL,
    declared_at timestamptz NOT NULL DEFAULT now()
);

-- STUDENTLIFE.RESUME_CLAIM
CREATE TABLE IF NOT EXISTS studentlife.resume_claim (
    claim_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id int NOT NULL REFERENCES public.students(id) ON DELETE CASCADE,
    claim_type text NOT NULL,
    description text NOT NULL,
    domain text NOT NULL,
    verification_status text NOT NULL DEFAULT 'PENDING' 
        CHECK (verification_status IN ('PENDING', 'VERIFIED', 'REJECTED', 'UNVERIFIABLE')),
    promoted_to_achievement_id uuid,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- CURRICULUM.COURSE_DOMAIN_TAG
CREATE TABLE IF NOT EXISTS curriculum.course_domain_tag (
    course_id text PRIMARY KEY,
    domain text NOT NULL 
        CHECK (domain IN ('TECHNICAL', 'RESEARCH', 'INNOVATION', 'COMMUNICATION', 'DESIGN')),
    weight numeric(3,2) NOT NULL DEFAULT 1.0
);

-- PEOPLE.FACULTY_EXPERTISE
CREATE TABLE IF NOT EXISTS people.faculty_expertise (
    faculty_id int PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    profile_id uuid UNIQUE,
    email text UNIQUE,
    name text NOT NULL,
    department text NOT NULL,
    research_areas text[] NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now()
);

-- RESEARCH.PROJECT
CREATE TABLE IF NOT EXISTS research.project (
    project_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    faculty_id int NOT NULL REFERENCES people.faculty_expertise(faculty_id) ON DELETE CASCADE,
    title text NOT NULL,
    description text NOT NULL,
    status text NOT NULL DEFAULT 'ACTIVE' 
        CHECK (status IN ('ACTIVE', 'COMPLETED', 'CANCELLED')),
    capacity int NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- RESEARCH.PROJECT_REQUIREMENT
CREATE TABLE IF NOT EXISTS research.project_requirement (
    requirement_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id uuid NOT NULL REFERENCES research.project(project_id) ON DELETE CASCADE,
    domain text,
    skill text,
    min_score numeric NOT NULL DEFAULT 0,
    is_required boolean NOT NULL DEFAULT true,
    weight numeric(3,2) NOT NULL DEFAULT 1.0
);

-- RESEARCH.PROJECT_MEMBER
CREATE TABLE IF NOT EXISTS research.project_member (
    membership_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id uuid NOT NULL REFERENCES research.project(project_id) ON DELETE CASCADE,
    student_id int NOT NULL REFERENCES public.students(id) ON DELETE CASCADE,
    role text NOT NULL DEFAULT 'RESEARCH_ASSISTANT',
    status text NOT NULL DEFAULT 'ACTIVE',
    assigned_at timestamptz NOT NULL DEFAULT now()
);

-- AGENTOPS.AGENT_REGISTRY
CREATE TABLE IF NOT EXISTS agentops.agent_registry (
    agent_no int PRIMARY KEY,
    code text UNIQUE NOT NULL,
    name text NOT NULL,
    agent_class text NOT NULL DEFAULT 'Class 3 / Prescriptive',
    description text,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- REGISTER AGENT 13
INSERT INTO agentops.agent_registry (agent_no, code, name, agent_class, description)
VALUES (
    13, 
    'A13_FAST_LEARNER', 
    'Talent Discovery & Opportunity Agent', 
    'Class 3 / Prescriptive', 
    'Prescriptive Agent for talent discovery, hidden talent identification, and research opportunity matching.'
)
ON CONFLICT (agent_no) DO UPDATE 
SET code = EXCLUDED.code, name = EXCLUDED.name, agent_class = EXCLUDED.agent_class;

-- AGENTOPS.AGENT_RUN
CREATE TABLE IF NOT EXISTS agentops.agent_run (
    run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_code text NOT NULL DEFAULT 'A13_FAST_LEARNER',
    triggered_by uuid NOT NULL, -- profile_id
    status text NOT NULL DEFAULT 'STARTED',
    created_at timestamptz NOT NULL DEFAULT now()
);

-- AGENTOPS.AGENT_RUN_INPUT
CREATE TABLE IF NOT EXISTS agentops.agent_run_input (
    input_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id uuid NOT NULL REFERENCES agentops.agent_run(run_id) ON DELETE CASCADE,
    context_snapshot jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- AGENTOPS.AGENT_OUTPUT
CREATE TABLE IF NOT EXISTS agentops.agent_output (
    output_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id uuid NOT NULL REFERENCES agentops.agent_run(run_id) ON DELETE CASCADE,
    subject_type text NOT NULL DEFAULT 'STUDENT',
    subject_id int NOT NULL REFERENCES public.students(id) ON DELETE CASCADE,
    payload jsonb NOT NULL,
    reasoning_summary text NOT NULL,
    confidence numeric NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- AGENTOPS.HUMAN_REVIEW
CREATE TABLE IF NOT EXISTS agentops.human_review (
    review_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    output_id uuid NOT NULL REFERENCES agentops.agent_output(output_id) ON DELETE CASCADE,
    decision text NOT NULL DEFAULT 'PENDING'
        CHECK (decision IN ('PENDING', 'APPROVED', 'MODIFY', 'REJECTED', 'EXPIRED')),
    reviewed_by uuid, -- profile_id
    reviewed_at timestamptz,
    comments text
);

-- ============================================================
-- ROW LEVEL SECURITY (RLS) & FORCE RLS
-- ============================================================

ALTER TABLE studentlife.student_interest ENABLE ROW LEVEL SECURITY;
ALTER TABLE studentlife.student_interest FORCE ROW LEVEL SECURITY;

ALTER TABLE studentlife.resume_claim ENABLE ROW LEVEL SECURITY;
ALTER TABLE studentlife.resume_claim FORCE ROW LEVEL SECURITY;

ALTER TABLE curriculum.course_domain_tag ENABLE ROW LEVEL SECURITY;

ALTER TABLE people.faculty_expertise ENABLE ROW LEVEL SECURITY;
ALTER TABLE people.faculty_expertise FORCE ROW LEVEL SECURITY;

ALTER TABLE research.project ENABLE ROW LEVEL SECURITY;
ALTER TABLE research.project FORCE ROW LEVEL SECURITY;

ALTER TABLE research.project_requirement ENABLE ROW LEVEL SECURITY;
ALTER TABLE research.project_requirement FORCE ROW LEVEL SECURITY;

ALTER TABLE research.project_member ENABLE ROW LEVEL SECURITY;
ALTER TABLE research.project_member FORCE ROW LEVEL SECURITY;

ALTER TABLE agentops.agent_registry ENABLE ROW LEVEL SECURITY;

ALTER TABLE agentops.agent_run ENABLE ROW LEVEL SECURITY;
ALTER TABLE agentops.agent_run FORCE ROW LEVEL SECURITY;

ALTER TABLE agentops.agent_run_input ENABLE ROW LEVEL SECURITY;
ALTER TABLE agentops.agent_run_input FORCE ROW LEVEL SECURITY;

ALTER TABLE agentops.agent_output ENABLE ROW LEVEL SECURITY;
ALTER TABLE agentops.agent_output FORCE ROW LEVEL SECURITY;

ALTER TABLE agentops.human_review ENABLE ROW LEVEL SECURITY;
ALTER TABLE agentops.human_review FORCE ROW LEVEL SECURITY;

-- ─── STUDENTLIFE POLICIES ────────────────────────────────────
DROP POLICY IF EXISTS interest_student_all ON studentlife.student_interest;
CREATE POLICY interest_student_all ON studentlife.student_interest FOR ALL USING (
    student_id = public.get_current_student_id()
);

DROP POLICY IF EXISTS interest_leadership_select ON studentlife.student_interest;
CREATE POLICY interest_leadership_select ON studentlife.student_interest FOR SELECT USING (
    public.get_current_profile_role() IN ('faculty', 'hod', 'principal', 'tpo')
);

DROP POLICY IF EXISTS resume_claim_student_all ON studentlife.resume_claim;
CREATE POLICY resume_claim_student_all ON studentlife.resume_claim FOR ALL USING (
    student_id = public.get_current_student_id()
);

DROP POLICY IF EXISTS resume_claim_leadership_select ON studentlife.resume_claim;
CREATE POLICY resume_claim_leadership_select ON studentlife.resume_claim FOR SELECT USING (
    public.get_current_profile_role() IN ('faculty', 'hod', 'principal', 'tpo')
);

-- ─── CURRICULUM POLICIES ─────────────────────────────────────
DROP POLICY IF EXISTS course_tag_all_select ON curriculum.course_domain_tag;
CREATE POLICY course_tag_all_select ON curriculum.course_domain_tag FOR SELECT USING (true);

DROP POLICY IF EXISTS course_tag_admin_write ON curriculum.course_domain_tag;
CREATE POLICY course_tag_admin_write ON curriculum.course_domain_tag FOR ALL USING (
    public.get_current_profile_role() IN ('hod', 'principal', 'tpo')
);

-- ─── PEOPLE POLICIES ─────────────────────────────────────────
DROP POLICY IF EXISTS faculty_expertise_select ON people.faculty_expertise;
CREATE POLICY faculty_expertise_select ON people.faculty_expertise FOR SELECT USING (true);

DROP POLICY IF EXISTS faculty_expertise_update_own ON people.faculty_expertise;
CREATE POLICY faculty_expertise_update_own ON people.faculty_expertise FOR UPDATE USING (
    profile_id = auth.uid()
);

-- ─── RESEARCH POLICIES ───────────────────────────────────────
DROP POLICY IF EXISTS project_student_select ON research.project;
CREATE POLICY project_student_select ON research.project FOR SELECT USING (
    status = 'ACTIVE' OR public.get_current_profile_role() IN ('faculty', 'hod', 'principal', 'tpo')
);

DROP POLICY IF EXISTS project_faculty_all ON research.project;
CREATE POLICY project_faculty_all ON research.project FOR ALL USING (
    faculty_id = people.get_current_faculty_id()
);

DROP POLICY IF EXISTS project_requirement_select ON research.project_requirement;
CREATE POLICY project_requirement_select ON research.project_requirement FOR SELECT USING (true);

DROP POLICY IF EXISTS project_requirement_faculty_write ON research.project_requirement;
CREATE POLICY project_requirement_faculty_write ON research.project_requirement FOR ALL USING (
    project_id IN (SELECT project_id FROM research.project WHERE faculty_id = people.get_current_faculty_id())
);

DROP POLICY IF EXISTS project_member_student_select ON research.project_member;
CREATE POLICY project_member_student_select ON research.project_member FOR SELECT USING (
    student_id = public.get_current_student_id() OR public.get_current_profile_role() IN ('faculty', 'hod', 'principal', 'tpo')
);

DROP POLICY IF EXISTS project_member_faculty_all ON research.project_member;
CREATE POLICY project_member_faculty_all ON research.project_member FOR ALL USING (
    project_id IN (SELECT project_id FROM research.project WHERE faculty_id = people.get_current_faculty_id())
);

-- ─── AGENTOPS POLICIES ───────────────────────────────────────
DROP POLICY IF EXISTS registry_select_all ON agentops.agent_registry;
CREATE POLICY registry_select_all ON agentops.agent_registry FOR SELECT USING (true);

DROP POLICY IF EXISTS run_leadership_all ON agentops.agent_run;
CREATE POLICY run_leadership_all ON agentops.agent_run FOR ALL USING (
    public.get_current_profile_role() IN ('faculty', 'hod', 'principal', 'tpo')
);

DROP POLICY IF EXISTS run_input_leadership_all ON agentops.agent_run_input;
CREATE POLICY run_input_leadership_all ON agentops.agent_run_input FOR ALL USING (
    public.get_current_profile_role() IN ('faculty', 'hod', 'principal', 'tpo')
);

DROP POLICY IF EXISTS output_student_select ON agentops.agent_output;
CREATE POLICY output_student_select ON agentops.agent_output FOR SELECT USING (
    subject_type = 'STUDENT' AND subject_id = public.get_current_student_id()
);

DROP POLICY IF EXISTS output_leadership_select ON agentops.agent_output;
CREATE POLICY output_leadership_select ON agentops.agent_output FOR SELECT USING (
    public.get_current_profile_role() IN ('faculty', 'hod', 'principal', 'tpo')
);

DROP POLICY IF EXISTS review_student_select ON agentops.human_review;
CREATE POLICY review_student_select ON agentops.human_review FOR SELECT USING (
    output_id IN (
        SELECT output_id FROM agentops.agent_output 
        WHERE subject_type = 'STUDENT' AND subject_id = public.get_current_student_id()
    )
);

DROP POLICY IF EXISTS review_leadership_select ON agentops.human_review;
CREATE POLICY review_leadership_select ON agentops.human_review FOR SELECT USING (
    public.get_current_profile_role() IN ('faculty', 'hod', 'principal', 'tpo')
);

DROP POLICY IF EXISTS review_leadership_update ON agentops.human_review;
CREATE POLICY review_leadership_update ON agentops.human_review FOR UPDATE USING (
    public.get_current_profile_role() IN ('faculty', 'hod', 'principal', 'tpo')
);
