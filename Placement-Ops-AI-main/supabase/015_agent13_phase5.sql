-- ============================================================
-- Agent 13 — Phase 5: Audit Logging & Outcome Tracking Schema
-- ============================================================

CREATE SCHEMA IF NOT EXISTS agentops;
CREATE SCHEMA IF NOT EXISTS outcomes;

-- 1. Agent 13 Audit Log Table
CREATE TABLE IF NOT EXISTS agentops.agent13_audit (
    audit_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id uuid REFERENCES agentops.agent_run(run_id) ON DELETE SET NULL,
    output_id uuid REFERENCES agentops.agent_output(output_id) ON DELETE SET NULL,
    reviewer_profile_id text,
    action text NOT NULL,
    old_state text,
    new_state text NOT NULL,
    student_id int REFERENCES public.students(id) ON DELETE SET NULL,
    project_id uuid REFERENCES research.project(project_id) ON DELETE SET NULL,
    faculty_id int REFERENCES people.faculty_expertise(faculty_id) ON DELETE SET NULL,
    comments text,
    execution_result text,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- 2. Agent 13 Outcome Event Table
CREATE TABLE IF NOT EXISTS outcomes.agent13_outcome (
    outcome_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id int NOT NULL REFERENCES public.students(id) ON DELETE CASCADE,
    project_id uuid REFERENCES research.project(project_id) ON DELETE SET NULL,
    event_type text NOT NULL CHECK (event_type IN (
        'PROJECT_ASSIGNMENT', 'PROJECT_PARTICIPATION', 'PROJECT_COMPLETION',
        'MENTOR_INTERACTION', 'RESEARCH_MILESTONE', 'HACKATHON_PARTICIPATION',
        'ADVANCED_OPPORTUNITY_PROGRESSION'
    )),
    outcome_result text NOT NULL DEFAULT 'IN_PROGRESS' CHECK (outcome_result IN (
        'SUCCESSFUL', 'IN_PROGRESS', 'WITHDRAWN', 'COMPLETED_WITH_DISTINCTION', 'FAILED'
    )),
    details jsonb NOT NULL DEFAULT '{}'::jsonb,
    verified boolean NOT NULL DEFAULT true,
    recorded_at timestamptz NOT NULL DEFAULT now()
);

-- RLS Configuration
ALTER TABLE agentops.agent13_audit ENABLE ROW LEVEL SECURITY;
ALTER TABLE agentops.agent13_audit FORCE ROW LEVEL SECURITY;

ALTER TABLE outcomes.agent13_outcome ENABLE ROW LEVEL SECURITY;
ALTER TABLE outcomes.agent13_outcome FORCE ROW LEVEL SECURITY;

-- Audit Log Policies
DROP POLICY IF EXISTS audit_student_select ON agentops.agent13_audit;
CREATE POLICY audit_student_select ON agentops.agent13_audit FOR SELECT USING (
    student_id = public.get_current_student_id()
);

DROP POLICY IF EXISTS audit_leadership_select ON agentops.agent13_audit;
CREATE POLICY audit_leadership_select ON agentops.agent13_audit FOR SELECT USING (
    public.get_current_profile_role() IN ('faculty', 'hod', 'principal', 'tpo')
);

-- Outcome Event Policies
DROP POLICY IF EXISTS outcome_student_select ON outcomes.agent13_outcome;
CREATE POLICY outcome_student_select ON outcomes.agent13_outcome FOR SELECT USING (
    student_id = public.get_current_student_id()
);

DROP POLICY IF EXISTS outcome_leadership_all ON outcomes.agent13_outcome;
CREATE POLICY outcome_leadership_all ON outcomes.agent13_outcome FOR ALL USING (
    public.get_current_profile_role() IN ('faculty', 'hod', 'principal', 'tpo')
);
